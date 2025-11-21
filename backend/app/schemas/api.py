"""
API 请求/响应 Schema 定义。
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.base import (
    DiscretizationConfig,
    Region,
    SpectrumConfig,
    TimeConfig,
    WindConfig,
)
from app.schemas.data import SimulationFrame, SimulationStatus


class AreaSimulationRequest(BaseModel):
    """创建区域模拟任务请求体。"""

    region: Region
    wind: WindConfig
    spectrum: SpectrumConfig
    discretization: DiscretizationConfig
    time: TimeConfig


class AreaSimulationResponse(BaseModel):
    """创建区域模拟任务的响应。"""

    simulation_id: str = Field(..., description="模拟任务唯一 ID")
    status: SimulationStatus = Field(..., description="任务状态")


class SimulationFramesResponse(BaseModel):
    """区域模拟结果（多帧）。"""

    simulation_id: str = Field(..., description="模拟任务 ID")
    status: SimulationStatus = Field(..., description="任务状态")
    frames: List[SimulationFrame] = Field(..., description="模拟时间序列帧")


class PointQueryRequest(BaseModel):
    """单点查询请求体。"""

    simulation_id: str = Field(..., description="对应的区域模拟任务 ID", example="abcd-1234")
    lon: float = Field(..., description="查询点经度（度）", example=120.25)
    lat: float = Field(..., description="查询点纬度（度）", example=30.25)
    time: float = Field(..., description="查询时间（秒），相对于 t=0 的偏移。time=-1 表示获取最新帧的信息", example=-1.0)


class PointQueryResponse(BaseModel):
    """单点查询响应体。"""

    simulation_id: str = Field(..., description="模拟任务 ID")
    time: float = Field(..., description="查询时间（秒）")
    lon: float = Field(..., description="查询点经度（度）")
    lat: float = Field(..., description="查询点纬度（度）")
    wave_height: float = Field(..., description="海浪高度（米）")


class ErrorResponse(BaseModel):
    """通用错误响应。"""

    code: str = Field(..., description="错误码")
    message: str = Field(..., description="错误描述")
    details: Optional[Dict] = Field(
        default=None, description="可选的详细错误信息"
    )

