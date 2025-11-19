"""
网格模型定义。

用于表示空间离散化的网格点。
"""

from dataclasses import dataclass
from typing import List

import numpy as np


@dataclass
class GridPoint:
    """网格点数据。"""

    x: float  # 本地 x 坐标
    y: float  # 本地 y 坐标
    lon: float  # 经度（度）
    lat: float  # 纬度（度）
    depth: float  # 深度（米）


@dataclass
class WaveGrid:
    """海浪高度网格（时间序列）。"""

    grid_points: List[GridPoint]  # 网格点列表
    wave_heights: np.ndarray  # 海浪高度数组，shape: (n_times, n_points)
    times: np.ndarray  # 时间数组，shape: (n_times,)

    def get_height_at_time(self, time: float) -> np.ndarray:
        """获取指定时刻的海浪高度。"""
        # 找到最接近的时间索引
        idx = np.argmin(np.abs(self.times - time))
        return self.wave_heights[idx]

    def get_height_at_point(self, point_idx: int) -> np.ndarray:
        """获取指定点的海浪高度时间序列。"""
        return self.wave_heights[:, point_idx]

