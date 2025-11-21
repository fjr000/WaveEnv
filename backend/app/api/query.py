"""
查询相关 API 路由。
"""

from typing import Optional

import numpy as np
from fastapi import APIRouter, HTTPException, Query

from app.core.storage import task_storage
from app.core.task_manager import get_simulation_task
from app.models.grid import GridPoint, WaveGrid
from app.schemas.api import (
    ErrorResponse,
    PointQueryResponse,
    SimulationFramesResponse,
)
from app.schemas.data import SimulationFrame, SimulationStatus, WavePoint
from app.services.interpolation import query_point

router = APIRouter(prefix="/query", tags=["query"])


def _build_wave_grid_from_frames(frames, region):
    """
    从frames列表构建WaveGrid（用于向后兼容）。
    
    Args:
        frames: SimulationFrame列表
        region: 区域配置
    
    Returns:
        WaveGrid对象
    """
    if not frames:
        return None
    
    # 从第一帧提取网格点信息
    first_frame = frames[0]
    
    # 提取唯一的经纬度值（排序）
    lons = sorted(set(p.lon for p in first_frame.points))
    lats = sorted(set(p.lat for p in first_frame.points))
    
    # 创建经纬度到索引的映射
    lon_to_idx = {lon: i for i, lon in enumerate(lons)}
    lat_to_idx = {lat: i for i, lat in enumerate(lats)}
    
    # 创建GridPoint列表
    # 使用区域的左下角作为原点
    origin_lon = region.lon_min
    origin_lat = region.lat_min
    
    from app.utils.coordinate import lonlat_to_xy
    
    grid_points = []
    # 按照lat（从下到上），lon（从左到右）的顺序创建网格点
    for lat in lats:
        for lon in lons:
            x, y = lonlat_to_xy(lon, lat, origin_lon, origin_lat)
            # 使用深度范围的中间值作为默认深度
            depth = (region.depth_min + region.depth_max) / 2.0
            grid_points.append(GridPoint(x=x, y=y, lon=lon, lat=lat, depth=depth))
    
    # 提取时间数组
    times = np.array([frame.time for frame in frames])
    
    # 创建高度数组 (n_times, n_points)
    n_times = len(frames)
    n_points = len(grid_points)
    wave_heights = np.zeros((n_times, n_points))
    
    # 填充高度数据
    for time_idx, frame in enumerate(frames):
        # 创建当前帧的经纬度到高度的映射
        frame_dict = {(p.lon, p.lat): p.wave_height for p in frame.points}
        
        # 填充高度数组
        for point_idx, grid_point in enumerate(grid_points):
            key = (grid_point.lon, grid_point.lat)
            if key in frame_dict:
                wave_heights[time_idx, point_idx] = frame_dict[key]
    
    return WaveGrid(
        grid_points=grid_points,
        wave_heights=wave_heights,
        times=times,
    )


@router.get(
    "/simulation/{simulation_id}/frames",
    response_model=SimulationFramesResponse,
    summary="获取区域模拟结果帧（单时刻）",
)
async def get_simulation_frames(
    simulation_id: str,
    time: float = Query(
        ..., 
        description="指定时间（秒），相对于 t=0 的偏移。time=-1 表示最新帧",
        examples={"latest": {"value": -1.0}, "specific_time": {"value": 0.6}},
    ),
) -> SimulationFramesResponse:
    """
    获取区域模拟结果帧（单时刻）。

    根据 simulation_id 和时间点，获取该模拟任务在指定时刻的海浪高度场结果。
    
    优先使用流式存储的frames，如果不存在则使用wave_grid（向后兼容）。
    
    特殊值：time=-1 表示使用最新帧的时间。
    """
    task = get_simulation_task(simulation_id)
    if task is None:
        raise HTTPException(
            status_code=404, detail=f"Simulation {simulation_id} not found"
        )

    # 处理 time=-1 的特殊情况（获取最新帧）
    if time == -1:
        if task.frames:
            latest_frame = task.frames[-1]
            return SimulationFramesResponse(
                simulation_id=simulation_id,
                status=task.status,
                frames=[latest_frame],
            )
        elif task.wave_grid is not None and len(task.wave_grid.times) > 0:
            # 从 wave_grid 获取最新帧
            latest_time = task.wave_grid.times[-1]
            time_idx = len(task.wave_grid.times) - 1
            points = [
                WavePoint(
                    lon=point.lon,
                    lat=point.lat,
                    wave_height=float(
                        task.wave_grid.wave_heights[time_idx, i]
                    ),
                )
                for i, point in enumerate(task.wave_grid.grid_points)
            ]
            frame = SimulationFrame(
                time=float(latest_time),
                region=task.region,
                points=points,
            )
            return SimulationFramesResponse(
                simulation_id=simulation_id,
                status=task.status,
                frames=[frame],
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Simulation {simulation_id} has no results yet",
            )
    
    # 获取指定时刻的数据
    target_time = time
    
    # 检查缓存保留时间配置
    cache_retention_time = task.time_config.cache_retention_time
    if cache_retention_time is not None and task.frames:
        latest_time = task.frames[-1].time
        cache_time_range = (latest_time - cache_retention_time, latest_time)
        if target_time < cache_time_range[0]:
            raise HTTPException(
                status_code=410,
                detail=(
                    f"请求的时间 {target_time:.2f} s 已超出缓存保留范围。"
                    f"当前缓存范围: [{cache_time_range[0]:.2f}, {cache_time_range[1]:.2f}] s "
                    f"(保留时间: {cache_retention_time:.2f} s)"
                )
            )
    
    # 优先使用流式存储的frames
    if task.frames:
        # 在frames中查找最接近的时间点
        frames = task.frames
        closest_frame = None
        min_time_diff = float('inf')
        
        for frame in frames:
            time_diff = abs(frame.time - target_time)
            if time_diff < min_time_diff:
                min_time_diff = time_diff
                closest_frame = frame
        
        if closest_frame is not None:
            return SimulationFramesResponse(
                simulation_id=simulation_id,
                status=task.status,
                frames=[closest_frame],
            )
    elif task.wave_grid is not None:
        # 从 wave_grid 获取指定时刻的数据
        times = task.wave_grid.times
        time_idx = np.argmin(np.abs(times - target_time))
        actual_time = times[time_idx]
        
        points = [
            WavePoint(
                lon=point.lon,
                lat=point.lat,
                wave_height=float(
                    task.wave_grid.wave_heights[time_idx, i]
                ),
            )
            for i, point in enumerate(task.wave_grid.grid_points)
        ]
        frame = SimulationFrame(
            time=float(actual_time),
            region=task.region,
            points=points,
        )
        return SimulationFramesResponse(
            simulation_id=simulation_id,
            status=task.status,
            frames=[frame],
        )
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Simulation {simulation_id} has no results yet",
        )


@router.get(
    "/point",
    response_model=PointQueryResponse,
    summary="单点海浪高度查询",
)
async def query_wave_at_point(
    simulation_id: str = Query(..., description="对应的区域模拟任务 ID", examples={"default": {"value": "abcd-1234"}}),
    lon: float = Query(..., description="查询点经度（度）", examples={"default": {"value": 120.25}}),
    lat: float = Query(..., description="查询点纬度（度）", examples={"default": {"value": 30.25}}),
    time: float = Query(..., description="查询时间（秒），相对于 t=0 的偏移。time=-1 表示获取最新帧的信息", examples={"latest": {"value": -1.0}, "specific_time": {"value": 0.6}}),
) -> PointQueryResponse:
    """
    单点海浪高度查询。

    基于指定的 simulation_id，在已有区域模拟结果上对某一经纬度点进行插值查询。
    空间插值采用双线性插值，时间可线性插值或取最近帧。
    
    支持使用frames（流式存储）或wave_grid（向后兼容）。
    
    特殊值：time=-1 表示获取最新帧的信息（最后一个可用帧）。
    """
    # 获取任务
    task = get_simulation_task(simulation_id)
    if task is None:
        raise HTTPException(
            status_code=404,
            detail=f"Simulation {simulation_id} not found",
        )

    # 处理 time=-1 的特殊情况（获取最新帧）
    query_time = time
    if query_time == -1:
        # 获取最新帧的时间
        if task.frames:
            # 使用frames时，获取最后一帧的时间
            query_time = task.frames[-1].time
        elif task.wave_grid is not None:
            # 使用wave_grid时，获取最后一个时间点
            query_time = task.wave_grid.times[-1]
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Simulation {simulation_id} has no results yet",
            )
    
    # 检查缓存保留时间，验证请求时间是否在缓存范围内
    cache_retention_time = task.time_config.cache_retention_time
    if cache_retention_time is not None:
        if task.frames:
            latest_time = task.frames[-1].time
            cache_time_range = (latest_time - cache_retention_time, latest_time)
            
            if query_time < cache_time_range[0]:
                raise HTTPException(
                    status_code=410,  # 410 Gone - 资源已被淘汰
                    detail=(
                        f"请求的时间 {query_time:.2f} s 已超出缓存保留范围。"
                        f"当前缓存范围: [{cache_time_range[0]:.2f}, {cache_time_range[1]:.2f}] s "
                        f"(保留时间: {cache_retention_time:.2f} s)"
                    )
                )
        elif task.wave_grid is not None:
            # 对于 wave_grid，也检查缓存范围
            latest_time = task.wave_grid.times[-1]
            cache_time_range = (latest_time - cache_retention_time, latest_time)
            
            if query_time < cache_time_range[0]:
                raise HTTPException(
                    status_code=410,
                    detail=(
                        f"请求的时间 {query_time:.2f} s 已超出缓存保留范围。"
                        f"当前缓存范围: [{cache_time_range[0]:.2f}, {cache_time_range[1]:.2f}] s "
                        f"(保留时间: {cache_retention_time:.2f} s)"
                    )
                )

    # 优先使用wave_grid，如果没有则从frames构建
    wave_grid = task.wave_grid
    if wave_grid is None:
        if not task.frames:
            raise HTTPException(
                status_code=404,
                detail=f"Simulation {simulation_id} has no results yet",
            )
        # 从frames构建wave_grid用于查询
        wave_grid = _build_wave_grid_from_frames(task.frames, task.region)
        if wave_grid is None:
            raise HTTPException(
                status_code=404,
                detail=f"Simulation {simulation_id} has no valid results",
            )

    # 执行插值查询
    try:
        wave_height = query_point(
            wave_grid=wave_grid,
            lon=lon,
            lat=lat,
            time=query_time,  # 使用处理后的时间
        )

        return PointQueryResponse(
            simulation_id=simulation_id,
            time=query_time,  # 返回实际使用的时间
            lon=lon,
            lat=lat,
            wave_height=wave_height,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Query failed: {str(e)}",
        )


@router.get(
    "/simulations",
    summary="获取所有仿真任务列表",
)
async def list_simulations(
    status: Optional[SimulationStatus] = Query(None, description="按状态过滤")
) -> dict:
    """
    获取所有仿真任务列表。
    
    Args:
        status: 可选的状态过滤器，只返回指定状态的任务
    
    Returns:
        包含任务列表的字典
    """
    all_tasks = task_storage.list_tasks()
    
    # 如果指定了状态过滤，则过滤任务
    if status is not None:
        filtered_tasks = [task for task in all_tasks if task.status == status]
    else:
        filtered_tasks = all_tasks
    
    # 返回任务列表（只返回基本信息，不包括大量数据）
    return {
        "total": len(all_tasks),
        "count": len(filtered_tasks),
        "simulations": [
            {
                "simulation_id": task.simulation_id,
                "status": task.status,
                "created_at": getattr(task, "created_at", None),
            }
            for task in filtered_tasks
        ]
    }


