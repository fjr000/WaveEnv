"""
模拟相关 API 路由。
"""

from typing import Optional

import numpy as np
from fastapi import APIRouter, HTTPException, Query

from app.core.storage import task_storage
from app.core.task_manager import (
    create_simulation_task,
    get_simulation_task,
    update_task_status,
)
from app.schemas.api import (
    AreaSimulationRequest,
    AreaSimulationResponse,
    SimulationFramesResponse,
)
from app.schemas.data import SimulationFrame, SimulationStatus, WavePoint
from app.services.simulation import create_wave_grid

router = APIRouter(tags=["simulation"])


@router.post(
    "/simulate/area",
    response_model=AreaSimulationResponse,
    status_code=201,
    summary="创建区域海浪模拟任务",
)
async def create_area_simulation(
    request: AreaSimulationRequest,
) -> AreaSimulationResponse:
    """
    创建区域海浪模拟任务。

    根据输入的区域、风场参数、波浪谱参数以及离散化和时间设置，
    创建一次区域海浪模拟任务。返回 simulation_id，用于后续查询模拟结果。
    """
    try:
        # 创建任务
        simulation_id = create_simulation_task(
            region=request.region,
            wind_config=request.wind,
            spectrum_config=request.spectrum,
            discretization_config=request.discretization,
            time_config=request.time,
        )

        # 更新状态为运行中
        update_task_status(simulation_id, SimulationStatus.RUNNING)

        # 执行模拟（同步执行，后续可改为异步）
        task = get_simulation_task(simulation_id)
        if task is None:
            raise HTTPException(
                status_code=500, detail="Failed to create simulation task"
            )

        # 生成波浪网格
        wave_grid = create_wave_grid(
            region=task.region,
            wind_config=task.wind_config,
            spectrum_config=task.spectrum_config,
            discretization_config=task.discretization_config,
            time_config=task.time_config,
        )

        # 更新任务
        task.wave_grid = wave_grid
        update_task_status(simulation_id, SimulationStatus.COMPLETED)
        task_storage.update_task(task)

        return AreaSimulationResponse(
            simulation_id=simulation_id, status=SimulationStatus.COMPLETED
        )

    except Exception as e:
        # 如果任务已创建，更新状态为失败
        if "simulation_id" in locals():
            update_task_status(simulation_id, SimulationStatus.FAILED)

        raise HTTPException(
            status_code=500,
            detail=f"Simulation failed: {str(e)}",
        )


@router.get(
    "/simulation/{simulation_id}/frames",
    response_model=SimulationFramesResponse,
    summary="获取区域模拟结果帧",
)
async def get_simulation_frames(
    simulation_id: str,
    time_min: Optional[float] = Query(
        None, description="起始时间（秒），相对于 t=0 的偏移"
    ),
    time_max: Optional[float] = Query(
        None, description="结束时间（秒），相对于 t=0 的偏移"
    ),
    max_frames: int = Query(100, ge=1, description="返回的最大时间帧数量上限"),
) -> SimulationFramesResponse:
    """
    获取区域模拟结果帧。

    根据 simulation_id 获取该模拟任务的海浪高度场结果。
    可通过可选参数限制时间范围或帧数量。
    """
    task = get_simulation_task(simulation_id)
    if task is None:
        raise HTTPException(
            status_code=404, detail=f"Simulation {simulation_id} not found"
        )

    if task.wave_grid is None:
        raise HTTPException(
            status_code=404,
            detail=f"Simulation {simulation_id} has no results yet",
        )

    # 从网格生成帧
    wave_grid = task.wave_grid
    frames = []

    # 时间过滤
    times = wave_grid.times.copy()
    if time_min is not None:
        mask = times >= time_min
        times = times[mask]
    if time_max is not None:
        mask = times <= time_max
        times = times[mask]

    # 如果过滤后没有时间点，返回空结果
    if len(times) == 0:
        return SimulationFramesResponse(
            simulation_id=simulation_id,
            status=task.status,
            frames=[],
        )

    # 限制帧数
    if len(times) > max_frames:
        indices = np.linspace(0, len(times) - 1, max_frames, dtype=int)
        times = times[indices]

    # 生成帧
    for time in times:
        time_idx = np.argmin(np.abs(wave_grid.times - time))
        points = [
            WavePoint(
                lon=point.lon,
                lat=point.lat,
                wave_height=float(
                    wave_grid.wave_heights[time_idx, i]
                ),
            )
            for i, point in enumerate(wave_grid.grid_points)
        ]

        frames.append(
            SimulationFrame(
                time=float(time), region=task.region, points=points
            )
        )

    return SimulationFramesResponse(
        simulation_id=simulation_id,
        status=task.status,
        frames=frames,
    )

