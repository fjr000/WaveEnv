"""
单点插值查询服务。

基于区域模拟结果，使用空间双线性插值和时间线性插值查询任意点的海浪高度。
"""

import numpy as np

from app.models.grid import WaveGrid
from app.schemas.data import SimulationStatus
from app.utils.coordinate import lonlat_to_xy
from app.utils.numerical import bilinear_interpolation, linear_interpolation


def query_point(
    wave_grid: WaveGrid,
    lon: float,
    lat: float,
    time: float,
) -> float:
    """
    查询指定点的海浪高度。

    使用空间双线性插值 + 时间线性插值。

    Args:
        wave_grid: 海浪高度网格
        lon: 查询点经度（度）
        lat: 查询点纬度（度）
        time: 查询时间（秒）

    Returns:
        海浪高度（米）
    """
    # 检查时间范围
    if time < wave_grid.times[0] or time > wave_grid.times[-1]:
        # 超出范围，返回边界值
        if time < wave_grid.times[0]:
            time = wave_grid.times[0]
        else:
            time = wave_grid.times[-1]

    # 找到时间索引
    time_idx = np.searchsorted(wave_grid.times, time)

    # 如果正好在某个时间点上
    if time_idx < len(wave_grid.times) and abs(
        wave_grid.times[time_idx] - time
    ) < 1e-6:
        # 直接使用该时刻的值
        values = wave_grid.wave_heights[time_idx]
    else:
        # 需要时间插值
        if time_idx == 0:
            # 在第一个时间点之前
            values = wave_grid.wave_heights[0]
        elif time_idx >= len(wave_grid.times):
            # 在最后一个时间点之后
            values = wave_grid.wave_heights[-1]
        else:
            # 在两个时间点之间，进行线性插值
            t1 = wave_grid.times[time_idx - 1]
            t2 = wave_grid.times[time_idx]
            v1 = wave_grid.wave_heights[time_idx - 1]
            v2 = wave_grid.wave_heights[time_idx]

            # 对每个网格点进行时间插值
            values = np.zeros(len(wave_grid.grid_points))
            for i in range(len(wave_grid.grid_points)):
                values[i] = linear_interpolation(
                    time, t1, v1[i], t2, v2[i]
                )

    # 计算查询点的本地坐标
    # 使用所有网格点的中心作为原点（更准确）
    origin_lon = np.mean([p.lon for p in wave_grid.grid_points])
    origin_lat = np.mean([p.lat for p in wave_grid.grid_points])
    x, y = lonlat_to_xy(lon, lat, origin_lon, origin_lat)

    # 空间双线性插值
    height = bilinear_interpolation(
        x, y, wave_grid.grid_points, values
    )

    return height
