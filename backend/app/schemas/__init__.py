"""
Pydantic Schema 模块。

包含请求/响应模型、配置模型、数据模型等。
"""

from app.schemas.api import (
    AreaSimulationRequest,
    AreaSimulationResponse,
    ErrorResponse,
    PointQueryRequest,
    PointQueryResponse,
    SimulationFramesResponse,
)
from app.schemas.base import (
    DiscretizationConfig,
    Region,
    SpectrumConfig,
    TimeConfig,
    WindConfig,
)
from app.schemas.data import (
    SimulationFrame,
    SimulationStatus,
    WavePoint,
)

__all__ = [
    # 基础配置
    "Region",
    "WindConfig",
    "SpectrumConfig",
    "DiscretizationConfig",
    "TimeConfig",
    # 数据模型
    "WavePoint",
    "SimulationFrame",
    "SimulationStatus",
    # API 请求/响应
    "AreaSimulationRequest",
    "AreaSimulationResponse",
    "SimulationFramesResponse",
    "PointQueryRequest",
    "PointQueryResponse",
    "ErrorResponse",
]
