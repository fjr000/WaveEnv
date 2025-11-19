"""
坐标转换工具。

提供经纬度与本地平面坐标之间的转换，以及网格生成功能。
"""

import math
from typing import List, Tuple

import numpy as np

from app.models.grid import GridPoint
from app.schemas.base import DiscretizationConfig, Region


# 地球半径（米）
EARTH_RADIUS = 6371000.0


def lonlat_to_xy(
    lon: float, lat: float, origin_lon: float, origin_lat: float
) -> Tuple[float, float]:
    """
    将经纬度转换为本地平面坐标（米）。

    使用简单的平面近似（适用于小区域）。

    Args:
        lon: 经度（度）
        lat: 纬度（度）
        origin_lon: 原点经度（度）
        origin_lat: 原点纬度（度）

    Returns:
        (x, y) 本地坐标（米），x 指向东，y 指向北
    """
    # 转换为弧度
    lon_rad = math.radians(lon)
    lat_rad = math.radians(lat)
    origin_lon_rad = math.radians(origin_lon)
    origin_lat_rad = math.radians(origin_lat)

    # 计算经度差和纬度差（弧度）
    dlon = lon_rad - origin_lon_rad
    dlat = lat_rad - origin_lat_rad

    # 转换为米（使用平均纬度）
    avg_lat_rad = (lat_rad + origin_lat_rad) / 2.0
    x = dlon * EARTH_RADIUS * math.cos(avg_lat_rad)  # 东西方向
    y = dlat * EARTH_RADIUS  # 南北方向

    return x, y


def xy_to_lonlat(
    x: float, y: float, origin_lon: float, origin_lat: float
) -> Tuple[float, float]:
    """
    将本地平面坐标转换为经纬度。

    Args:
        x: 本地 x 坐标（米），指向东
        y: 本地 y 坐标（米），指向北
        origin_lon: 原点经度（度）
        origin_lat: 原点纬度（度）

    Returns:
        (lon, lat) 经纬度（度）
    """
    origin_lon_rad = math.radians(origin_lon)
    origin_lat_rad = math.radians(origin_lat)

    # 转换为弧度差
    avg_lat_rad = origin_lat_rad  # 使用原点纬度作为近似
    dlon_rad = x / (EARTH_RADIUS * math.cos(avg_lat_rad))
    dlat_rad = y / EARTH_RADIUS

    # 转换为度
    lon = math.degrees(origin_lon_rad + dlon_rad)
    lat = math.degrees(origin_lat_rad + dlat_rad)

    return lon, lat


def create_grid(
    region: Region, config: DiscretizationConfig
) -> List[GridPoint]:
    """
    创建离散网格。

    Args:
        region: 区域定义
        config: 离散化配置

    Returns:
        网格点列表
    """
    # 计算网格范围
    lon_range = region.lon_max - region.lon_min
    lat_range = region.lat_max - region.lat_min

    # 计算网格数量
    n_lon = max(1, int(lon_range / config.dx) + 1)
    n_lat = max(1, int(lat_range / config.dy) + 1)
    total_points = n_lon * n_lat

    # 检查点数上限
    if total_points > config.max_points:
        # 按比例缩小网格
        scale = math.sqrt(config.max_points / total_points)
        n_lon = max(1, int(n_lon * scale))
        n_lat = max(1, int(n_lat * scale))
        total_points = n_lon * n_lat

    # 生成网格点
    lon_values = np.linspace(region.lon_min, region.lon_max, n_lon)
    lat_values = np.linspace(region.lat_min, region.lat_max, n_lat)

    # 使用原点（区域中心）进行坐标转换
    origin_lon = (region.lon_min + region.lon_max) / 2.0
    origin_lat = (region.lat_min + region.lat_max) / 2.0

    # 深度插值（简单线性插值）
    depth_range = region.depth_max - region.depth_min

    grid_points = []
    for lat in lat_values:
        for lon in lon_values:
            # 计算本地坐标
            x, y = lonlat_to_xy(lon, lat, origin_lon, origin_lat)

            # 计算深度（简单线性插值）
            lon_ratio = (lon - region.lon_min) / lon_range if lon_range > 0 else 0.5
            lat_ratio = (lat - region.lat_min) / lat_range if lat_range > 0 else 0.5
            depth = region.depth_min + depth_range * (lon_ratio + lat_ratio) / 2.0

            grid_points.append(
                GridPoint(x=x, y=y, lon=lon, lat=lat, depth=depth)
            )

    return grid_points

