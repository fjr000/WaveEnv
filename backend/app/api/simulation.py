"""
模拟相关 API 路由。
"""

import asyncio
from typing import Optional

import numpy as np
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

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
from app.services.simulation_stream import simulate_area_stream

router = APIRouter(tags=["simulation"])


def _cleanup_task_resources(task) -> None:
    """
    清理任务资源，释放内存。
    
    停止仿真时需要调用此函数来回收资源，而暂停时不应该调用（暂停保留资源）。
    
    清理的内容包括：
    - 清空帧列表（frames），可能包含大量数据
    - 清空波形网格（wave_grid），可能包含大量数据
    
    Args:
        task: 模拟任务对象
    """
    # 清空帧列表（可能包含大量数据）
    if task.frames:
        task.frames.clear()
    
    # 清空波形网格（可能包含大量数据）
    task.wave_grid = None
    
    # 更新任务存储
    task_storage.update_task(task)


async def _run_simulation_stream(
    simulation_id: str,
    region,
    wind_config,
    spectrum_config,
    discretization_config,
    time_config,
) -> None:
    """
    后台任务：使用外部时钟控制模拟步进，按时钟间隔计算并存储帧。
    
    使用外部时钟（定时器）定期调用 step() 方法，每次调用代表过了一个时间步长（dt_backend）。
    
    Args:
        simulation_id: 模拟任务ID
        region: 区域配置
        wind_config: 风场配置
        spectrum_config: 波浪谱配置
        discretization_config: 离散化配置
        time_config: 时间配置
    """
    try:
        loop = asyncio.get_running_loop()

        task = get_simulation_task(simulation_id)
        if task is None:
            return

        # 创建模拟步进器
        stepper = await simulate_area_stream(
            region=region,
            wind_config=wind_config,
            spectrum_config=spectrum_config,
            discretization_config=discretization_config,
            time_config=time_config,
        )

        # 获取时间步长（秒）
        dt = time_config.dt_backend
        # 获取缓存保留时间（秒），None 表示不限制
        cache_retention_time = time_config.cache_retention_time

        # 首次调用获取初始帧（t=0）
        frame = stepper.step()
        if frame is not None:
            task.frames.append(frame)
            task_storage.update_task(task)
            
            # 立即开始预计算第一个时间步（t=dt），实现流水线计算
            await stepper.precompute_next_frame(loop)

        # 定时器循环：根据控制状态持续运行
        while True:
            task = get_simulation_task(simulation_id)
            if task is None:
                break

            # 若请求停止，立即终止并回收资源
            if task.stop_requested:
                stepper.stop()
                # 回收资源：清理任务数据
                _cleanup_task_resources(task)
                update_task_status(simulation_id, SimulationStatus.STOPPED)
                break

            # 如果达到时间上限（仅限配置了 T_total 的旧模式）
            if stepper.is_completed and stepper.time_limit is not None:
                update_task_status(simulation_id, SimulationStatus.COMPLETED)
                break

            # 若暂停，则短暂休眠后继续检查（不清理资源，保留所有数据）
            if task.clock_paused:
                await asyncio.sleep(0.1)
                continue

            # 正常运行：使用真实时间控制，确保模拟时间与真实时间同步
            # 记录开始时间
            step_start_time = loop.time()
            
            # 获取预计算的下一帧（应该已经准备好了，无延迟）
            frame = await stepper.get_precomputed_frame()
            
            # 计算实际耗时（获取预计算帧的耗时应该很短）
            step_elapsed = loop.time() - step_start_time
            
            # 如果获取预计算帧的时间小于 dt，则等待剩余时间；如果超过 dt，则不等待
            # 这样可以确保模拟时间与真实时间同步（1:1）
            if step_elapsed < dt:
                await asyncio.sleep(dt - step_elapsed)
            
            # 再次检查任务状态（避免等待期间状态变化）
            task = get_simulation_task(simulation_id)
            if task is None:
                break
            if task.stop_requested:
                stepper.stop()
                # 回收资源：清理任务数据
                _cleanup_task_resources(task)
                update_task_status(simulation_id, SimulationStatus.STOPPED)
                break
            if task.clock_paused:
                # 暂停时不清理资源，只暂停时钟，保留所有数据
                continue

            if frame is None:
                # 可能是达到时间上限或收到停止指令
                if task.stop_requested:
                    stepper.stop()
                    # 回收资源：清理任务数据
                    _cleanup_task_resources(task)
                    update_task_status(simulation_id, SimulationStatus.STOPPED)
                elif stepper.is_completed and stepper.time_limit is not None:
                    update_task_status(simulation_id, SimulationStatus.COMPLETED)
                break

            # 存储帧到任务中
            task.frames.append(frame)
            
            # 如果配置了缓存保留时间，清理过期的旧帧
            if cache_retention_time is not None and len(task.frames) > 0:
                current_time = frame.time
                # 保留时间阈值：当前时间 - 保留时间
                retention_threshold = current_time - cache_retention_time
                
                # 过滤掉时间小于阈值的旧帧（保留时间阈值之后的所有帧）
                original_count = len(task.frames)
                task.frames = [f for f in task.frames if f.time >= retention_threshold]
                
                # 如果清理了帧，更新存储
                if len(task.frames) < original_count:
                    task_storage.update_task(task)
            else:
                # 如果没有配置缓存保留时间，直接更新
                task_storage.update_task(task)

    except Exception as e:
        # 如果出错，更新状态为失败
        update_task_status(simulation_id, SimulationStatus.FAILED)
        # 可以在这里添加日志记录
        print(f"Simulation stream error for {simulation_id}: {e}")


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

        # 获取任务
        task = get_simulation_task(simulation_id)
        if task is None:
            raise HTTPException(
                status_code=500, detail="Failed to create simulation task"
            )

        # 启动后台任务，使用异步流式模拟按时钟间隔计算并存储帧
        # 使用 asyncio.create_task 替代 BackgroundTasks，避免阻塞响应（特别是对于无限运行的任务）
        asyncio.create_task(
            _run_simulation_stream(
                simulation_id=simulation_id,
                region=request.region,
                wind_config=request.wind,
                spectrum_config=request.spectrum,
                discretization_config=request.discretization,
                time_config=request.time,
            )
        )

        # 返回运行中状态，因为任务正在后台执行
        return AreaSimulationResponse(
            simulation_id=simulation_id, status=SimulationStatus.RUNNING
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
    summary="获取区域模拟结果帧（单时刻）",
)
async def get_simulation_frames(
    simulation_id: str,
    time: float = Query(
        ..., description="指定时间（秒），相对于 t=0 的偏移。time=-1 表示最新帧"
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


def _ensure_task_for_control(simulation_id: str):
    task = get_simulation_task(simulation_id)
    if task is None:
        raise HTTPException(
            status_code=404, detail=f"Simulation {simulation_id} not found"
        )
    return task


@router.post(
    "/simulation/{simulation_id}/clock/pause",
    response_model=AreaSimulationResponse,
    summary="暂停模拟时钟",
)
async def pause_simulation_clock(simulation_id: str) -> AreaSimulationResponse:
    """
    暂停指定模拟任务的外部时钟，使其停止推进。
    
    暂停会：
    - 停止模拟时钟的推进
    - 保留所有数据和资源（frames, wave_grid等）
    - 可以通过恢复功能继续模拟
    
    注意：暂停不会清理资源，所有数据都保留，可以随时恢复。
    """
    task = _ensure_task_for_control(simulation_id)
    if task.status in {
        SimulationStatus.COMPLETED,
        SimulationStatus.FAILED,
        SimulationStatus.STOPPED,
    }:
        raise HTTPException(
            status_code=400, detail="Simulation is not running"
        )

    if not task.clock_paused:
        task.clock_paused = True
        task_storage.update_task(task)
        update_task_status(simulation_id, SimulationStatus.PAUSED)

    return AreaSimulationResponse(
        simulation_id=simulation_id, status=SimulationStatus.PAUSED
    )


@router.post(
    "/simulation/{simulation_id}/clock/resume",
    response_model=AreaSimulationResponse,
    summary="恢复模拟时钟",
)
async def resume_simulation_clock(simulation_id: str) -> AreaSimulationResponse:
    """
    恢复已经暂停的模拟任务，让外部时钟继续推进。
    
    恢复会：
    - 重新启动模拟时钟
    - 从暂停时的状态继续计算
    - 保留所有之前的数据和资源
    
    注意：恢复不会丢失任何数据，从暂停点继续模拟。
    """
    task = _ensure_task_for_control(simulation_id)
    if task.status in {
        SimulationStatus.COMPLETED,
        SimulationStatus.FAILED,
        SimulationStatus.STOPPED,
    }:
        raise HTTPException(
            status_code=400, detail="Simulation is not running"
        )

    if task.clock_paused:
        task.clock_paused = False
        task_storage.update_task(task)
        update_task_status(simulation_id, SimulationStatus.RUNNING)

    return AreaSimulationResponse(
        simulation_id=simulation_id, status=SimulationStatus.RUNNING
    )


@router.post(
    "/simulation/{simulation_id}/stop",
    response_model=AreaSimulationResponse,
    summary="停止模拟任务",
)
async def stop_simulation(simulation_id: str) -> AreaSimulationResponse:
    """
    请求立即停止指定的模拟任务，并释放计算资源。
    
    停止会：
    1. 终止模拟计算循环
    2. 清理所有帧数据（frames）
    3. 清理波形网格数据（wave_grid）
    4. 释放内存资源
    
    注意：停止后无法恢复，需要重新创建任务。如需保留数据，请使用暂停功能。
    """
    task = _ensure_task_for_control(simulation_id)
    if task.status in {
        SimulationStatus.COMPLETED,
        SimulationStatus.FAILED,
        SimulationStatus.STOPPED,
    }:
        # 即使已停止，也确保资源已清理
        if task.status == SimulationStatus.STOPPED:
            _cleanup_task_resources(task)
        return AreaSimulationResponse(
            simulation_id=simulation_id, status=task.status
        )

    # 标记停止请求
    task.stop_requested = True
    task.clock_paused = False
    task_storage.update_task(task)
    
    # 注意：实际的资源清理会在后台任务循环中执行
    # 这里先更新状态，让客户端知道已请求停止
    update_task_status(simulation_id, SimulationStatus.STOPPED)

    return AreaSimulationResponse(
        simulation_id=simulation_id, status=SimulationStatus.STOPPED
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


@router.post(
    "/simulations/stop-all",
    summary="停止所有运行中的仿真任务",
)
async def stop_all_simulations() -> dict:
    """
    停止所有运行中的仿真任务。
    
    Returns:
        包含停止结果统计的字典
    """
    all_tasks = task_storage.list_tasks()
    
    # 过滤出运行中的任务（RUNNING 或 PENDING）
    running_tasks = [
        task for task in all_tasks
        if task.status in (SimulationStatus.RUNNING, SimulationStatus.PENDING)
    ]
    
    stopped_count = 0
    for task in running_tasks:
        try:
            task.stop_requested = True
            task.clock_paused = False
            task_storage.update_task(task)
            update_task_status(task.simulation_id, SimulationStatus.STOPPED)
            stopped_count += 1
        except Exception as e:
            print(f"Error stopping task {task.simulation_id}: {e}")
    
    return {
        "total_tasks": len(all_tasks),
        "running_tasks": len(running_tasks),
        "stopped_count": stopped_count,
        "message": f"Stopped {stopped_count} running simulation(s)"
    }

