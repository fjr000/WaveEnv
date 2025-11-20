"""
模拟任务模型定义。
"""

from dataclasses import dataclass, field
from typing import List, Optional
from uuid import UUID

from app.models.grid import WaveGrid
from app.schemas.base import (
    DiscretizationConfig,
    Region,
    SpectrumConfig,
    TimeConfig,
    WindConfig,
)
from app.schemas.data import SimulationFrame, SimulationStatus


@dataclass
class SimulationTask:
    """模拟任务。"""

    simulation_id: str  # 任务 ID
    status: SimulationStatus  # 任务状态
    region: Region  # 区域配置
    wind_config: WindConfig  # 风场配置
    spectrum_config: SpectrumConfig  # 波浪谱配置
    discretization_config: DiscretizationConfig  # 离散化配置
    time_config: TimeConfig  # 时间配置
    wave_grid: Optional[WaveGrid] = None  # 模拟结果（网格数据，用于向后兼容）
    frames: List[SimulationFrame] = field(default_factory=list)  # 流式帧列表（异步计算）
    clock_paused: bool = False  # 是否暂停外部时钟
    stop_requested: bool = False  # 是否请求停止模拟

