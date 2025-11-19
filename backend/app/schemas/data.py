"""
数据 Schema 定义。

包含海浪点、模拟帧、任务状态等数据模型。
"""

from enum import Enum
from typing import List

from pydantic import BaseModel, Field

from app.schemas.base import Region


class SimulationStatus(str, Enum):
    """模拟任务状态枚举。"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class WavePoint(BaseModel):
    """某一时刻某一点的海浪高度。"""

    lon: float = Field(..., description="经度（度）")
    lat: float = Field(..., description="纬度（度）")
    wave_height: float = Field(..., description="海浪高度（米）")


class SimulationFrame(BaseModel):
    """某一时刻的区域海浪高度场。"""

    time: float = Field(..., description="时间（秒），相对于 t=0 的偏移")
    region: Region = Field(..., description="区域定义")
    points: List[WavePoint] = Field(..., description="该区域内离散点的海浪高度数据")

