"""
波浪谱模型定义。
"""

from dataclasses import dataclass
from typing import List

import numpy as np


@dataclass
class WaveComponent:
    """单个波成分。"""

    frequency: float  # 频率（Hz）
    direction_deg: float  # 波向（度）
    amplitude: float  # 振幅（米）
    phase: float  # 相位（弧度）
    wave_number: float  # 波数（1/m）


@dataclass
class WaveSpectrum:
    """波浪谱参数。"""

    components: List[WaveComponent]  # 波成分列表
    Hs: float  # 显著波高（m）
    Tp: float  # 峰值周期（s）
    main_direction_deg: float  # 主浪向（度）

