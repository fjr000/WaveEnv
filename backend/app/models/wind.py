"""
风场模型定义。
"""

from dataclasses import dataclass
from typing import Tuple

import numpy as np


@dataclass
class WindField:
    """风场状态。"""

    wind_speed: float  # 风速（m/s）
    wind_direction_deg: float  # 风向（度），0°表示从北向南，顺时针增加
    reference_height_m: float  # 参考高度（米）

    def get_wind_components(self) -> Tuple[float, float]:
        """获取风速的 x、y 分量（本地坐标系）。"""
        # 将风向转换为弧度（从北开始，顺时针）
        angle_rad = np.deg2rad(self.wind_direction_deg)
        # 计算 x、y 分量（x 指向东，y 指向北）
        u = self.wind_speed * np.sin(angle_rad)  # 东西分量
        v = self.wind_speed * np.cos(angle_rad)  # 南北分量
        return u, v

