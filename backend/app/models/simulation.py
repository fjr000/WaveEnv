"""
模拟任务模型定义。
"""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from app.models.grid import WaveGrid
from app.schemas.base import (
    DiscretizationConfig,
    Region,
    SpectrumConfig,
    TimeConfig,
    WindConfig,
)
from app.schemas.data import SimulationStatus


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
    wave_grid: Optional[WaveGrid] = None  # 模拟结果（网格数据）

