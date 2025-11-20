# -*- coding: utf-8 -*-
"""
数据转换模块。

将 API 响应转换为可视化所需的数据格式。
"""

import numpy as np
from typing import List, Dict, Tuple


def frames_to_grid_data(frames: List[Dict]) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    将模拟帧列表转换为网格数据。

    Args:
        frames: SimulationFrame 列表（从 API 获取）

    Returns:
        (lon_grid, lat_grid, height_grid, times)
        - lon_grid: 经度网格 (n_lat, n_lon)
        - lat_grid: 纬度网格 (n_lat, n_lon)
        - height_grid: 海浪高度网格 (n_times, n_lat, n_lon)
        - times: 时间数组 (n_times,)
    """
    if not frames:
        raise ValueError("frames 列表不能为空")

    # 从第一帧提取网格点信息
    first_frame = frames[0]
    points = first_frame["points"]

    # 提取唯一的经纬度值
    lons = sorted(set(p["lon"] for p in points))
    lats = sorted(set(p["lat"] for p in points))

    n_lon = len(lons)
    n_lat = len(lats)
    n_times = len(frames)

    # 创建经纬度到索引的映射
    lon_to_idx = {lon: i for i, lon in enumerate(lons)}
    lat_to_idx = {lat: i for i, lat in enumerate(lats)}

    # 创建网格
    lon_grid, lat_grid = np.meshgrid(lons, lats)

    # 创建高度网格 (n_times, n_lat, n_lon)
    height_grid = np.zeros((n_times, n_lat, n_lon))

    # 提取时间数组
    times = np.array([frame["time"] for frame in frames])

    # 填充高度数据
    for time_idx, frame in enumerate(frames):
        for point in frame["points"]:
            lon_idx = lon_to_idx[point["lon"]]
            lat_idx = lat_to_idx[point["lat"]]
            height_grid[time_idx, lat_idx, lon_idx] = point["wave_height"]

    return lon_grid, lat_grid, height_grid, times


def get_frame_at_time(
    lon_grid: np.ndarray,
    lat_grid: np.ndarray,
    height_grid: np.ndarray,
    times: np.ndarray,
    target_time: float,
) -> Tuple[np.ndarray, float]:
    """
    获取指定时间点的帧数据（线性插值）。

    Args:
        lon_grid: 经度网格
        lat_grid: 纬度网格
        height_grid: 高度网格 (n_times, n_lat, n_lon)
        times: 时间数组
        target_time: 目标时间

    Returns:
        (height_frame, actual_time)
        - height_frame: 该时间点的海浪高度场 (n_lat, n_lon)
        - actual_time: 实际使用的时间（可能是插值后的时间）
    """
    # 找到最近的时间索引
    time_idx = np.argmin(np.abs(times - target_time))
    actual_time = times[time_idx]

    # 如果目标时间正好匹配，直接返回
    if abs(actual_time - target_time) < 1e-6:
        return height_grid[time_idx], actual_time

    # 否则进行线性插值
    if time_idx == 0:
        # 如果是最早的时间，直接返回第一帧
        return height_grid[0], times[0]
    elif time_idx == len(times) - 1:
        # 如果是最晚的时间，直接返回最后一帧
        return height_grid[-1], times[-1]
    else:
        # 线性插值
        t1 = times[time_idx - 1]
        t2 = times[time_idx]
        if target_time < t1:
            return height_grid[time_idx - 1], t1
        elif target_time > t2:
            return height_grid[time_idx], t2
        else:
            # 在 t1 和 t2 之间插值
            alpha = (target_time - t1) / (t2 - t1)
            height_frame = (
                height_grid[time_idx - 1] * (1 - alpha)
                + height_grid[time_idx] * alpha
            )
            return height_frame, target_time

