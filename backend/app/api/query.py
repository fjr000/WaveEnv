"""
查询相关 API 路由。
"""

from fastapi import APIRouter, HTTPException

from app.core.task_manager import get_simulation_task
from app.schemas.api import (
    ErrorResponse,
    PointQueryRequest,
    PointQueryResponse,
)
from app.services.interpolation import query_point

router = APIRouter(prefix="/query", tags=["query"])


@router.post(
    "/point",
    response_model=PointQueryResponse,
    summary="单点海浪高度查询",
)
async def query_wave_at_point(
    request: PointQueryRequest,
) -> PointQueryResponse:
    """
    单点海浪高度查询。

    基于指定的 simulation_id，在已有区域模拟结果上对某一经纬度点进行插值查询。
    空间插值采用双线性插值，时间可线性插值或取最近帧。
    """
    # 获取任务
    task = get_simulation_task(request.simulation_id)
    if task is None:
        raise HTTPException(
            status_code=404,
            detail=f"Simulation {request.simulation_id} not found",
        )

    if task.wave_grid is None:
        raise HTTPException(
            status_code=404,
            detail=f"Simulation {request.simulation_id} has no results yet",
        )

    # 执行插值查询
    try:
        wave_height = query_point(
            wave_grid=task.wave_grid,
            lon=request.lon,
            lat=request.lat,
            time=request.time,
        )

        return PointQueryResponse(
            simulation_id=request.simulation_id,
            time=request.time,
            lon=request.lon,
            lat=request.lat,
            wave_height=wave_height,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Query failed: {str(e)}",
        )


