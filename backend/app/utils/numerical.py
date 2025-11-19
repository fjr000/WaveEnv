"""
数值计算工具。

提供插值、数值计算等功能。
"""

from typing import List, Optional, Tuple

import numpy as np

from app.models.grid import GridPoint, WaveGrid


def bilinear_interpolation(
    x: float, y: float, grid_points: List[GridPoint], values: np.ndarray
) -> float:
    """
    双线性插值。

    在网格中查找包含点 (x, y) 的单元，并进行双线性插值。

    Args:
        x: 查询点 x 坐标（本地坐标，米）
        y: 查询点 y 坐标（本地坐标，米）
        grid_points: 网格点列表
        values: 网格点对应的值数组，shape: (n_points,)

    Returns:
        插值结果
    """
    if len(grid_points) < 4:
        # 如果网格点太少，使用最近邻
        distances = np.array(
            [
                np.sqrt((p.x - x) ** 2 + (p.y - y) ** 2)
                for p in grid_points
            ]
        )
        idx = np.argmin(distances)
        return float(values[idx])

    # 找到包含点 (x, y) 的网格单元
    # 简化实现：找到最近的 4 个点
    distances = np.array(
        [np.sqrt((p.x - x) ** 2 + (p.y - y) ** 2) for p in grid_points]
    )
    nearest_indices = np.argsort(distances)[:4]
    nearest_points = [grid_points[i] for i in nearest_indices]

    # 使用这 4 个点进行双线性插值
    # 简化：使用加权平均（距离倒数加权）
    weights = 1.0 / (distances[nearest_indices] + 1e-10)
    weights = weights / np.sum(weights)

    result = np.sum(values[nearest_indices] * weights)
    return float(result)


def linear_interpolation(
    t: float, t1: float, v1: float, t2: float, v2: float
) -> float:
    """
    线性插值。

    Args:
        t: 查询时间
        t1: 时间点 1
        v1: 值 1
        t2: 时间点 2
        v2: 值 2

    Returns:
        插值结果
    """
    if abs(t2 - t1) < 1e-10:
        return v1

    alpha = (t - t1) / (t2 - t1)
    return v1 + alpha * (v2 - v1)


def find_grid_cell(
    x: float, y: float, grid_points: List[GridPoint]
) -> Optional[Tuple[int, int, int, int]]:
    """
    找到包含点 (x, y) 的网格单元（4 个角点索引）。

    简化实现：假设网格是规则的矩形网格。

    Args:
        x: 查询点 x 坐标
        y: 查询点 y 坐标
        grid_points: 网格点列表

    Returns:
        (i1, i2, i3, i4) 四个角点的索引，如果找不到则返回 None
    """
    if len(grid_points) < 4:
        return None

    # 找到 x、y 坐标的范围
    x_coords = np.array([p.x for p in grid_points])
    y_coords = np.array([p.y for p in grid_points])

    # 找到唯一的 x、y 值（假设是规则网格）
    unique_x = np.unique(x_coords)
    unique_y = np.unique(y_coords)

    # 找到 x、y 所在的区间
    x_idx = np.searchsorted(unique_x, x) - 1
    y_idx = np.searchsorted(unique_y, y) - 1

    if x_idx < 0 or x_idx >= len(unique_x) - 1:
        return None
    if y_idx < 0 or y_idx >= len(unique_y) - 1:
        return None

    # 找到对应的 4 个点
    x1, x2 = unique_x[x_idx], unique_x[x_idx + 1]
    y1, y2 = unique_y[y_idx], unique_y[y_idx + 1]

    # 找到这 4 个点的索引
    indices = []
    for target_x, target_y in [(x1, y1), (x2, y1), (x1, y2), (x2, y2)]:
        mask = (np.abs(x_coords - target_x) < 1e-6) & (
            np.abs(y_coords - target_y) < 1e-6
        )
        idx = np.where(mask)[0]
        if len(idx) > 0:
            indices.append(idx[0])
        else:
            return None

    return tuple(indices)

