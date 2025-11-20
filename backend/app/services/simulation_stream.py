"""
区域海浪模拟服务（流式版本）。

支持实时获取每个时间步的海浪高度场。
"""

import math
from typing import Iterator, List

import numpy as np

from app.models.grid import GridPoint
from app.models.spectrum import WaveSpectrum
from app.schemas.base import (
    DiscretizationConfig,
    Region,
    SpectrumConfig,
    TimeConfig,
    WindConfig,
)
from app.schemas.data import SimulationFrame, WavePoint
from app.services.spectrum import generate_spectrum
from app.services.wind import create_wind_field
from app.utils.coordinate import create_grid

# 重力加速度（m/s²）
G = 9.81


def simulate_area_stream(
    region: Region,
    wind_config: WindConfig,
    spectrum_config: SpectrumConfig,
    discretization_config: DiscretizationConfig,
    time_config: TimeConfig,
) -> Iterator[SimulationFrame]:
    """
    流式区域模拟流程，实时生成每个时间步的帧。
    
    这是一个生成器函数，每计算完一个时间步就立即yield一个帧，
    不需要等所有时间步计算完成。

    Args:
        region: 区域配置
        wind_config: 风场配置
        spectrum_config: 波浪谱配置
        discretization_config: 离散化配置
        time_config: 时间配置

    Yields:
        每个时间步的 SimulationFrame
    """
    # 1. 创建网格
    grid_points = create_grid(region, discretization_config)

    # 2. 生成风场
    wind = create_wind_field(wind_config)

    # 3. 生成波浪谱
    spectrum = generate_spectrum(wind, spectrum_config)

    # 4. 初始化 t=0 海浪场
    current_wave_height = _initialize_wave_field(spectrum, grid_points)

    # 5. 生成时间序列
    dt = time_config.dt_backend
    T_total = time_config.T_total
    times = np.arange(0, T_total + dt / 2, dt)

    # 6. 立即yield初始时刻（t=0）
    yield _create_frame(
        time=times[0],
        wave_height=current_wave_height,
        grid_points=grid_points,
        region=region,
    )

    # 7. 时间步进，每计算完一个时间步就yield
    for t_idx in range(1, len(times)):
        current_time = times[t_idx - 1]
        current_wave_height = _advance_wave_field(
            current_wave_height,
            spectrum,
            grid_points,
            dt,
            current_time,
        )

        # 立即yield当前时间步的帧
        yield _create_frame(
            time=times[t_idx],
            wave_height=current_wave_height,
            grid_points=grid_points,
            region=region,
        )


def _initialize_wave_field(
    spectrum: WaveSpectrum, grid_points: List[GridPoint]
) -> np.ndarray:
    """初始化 t=0 时刻的海浪场。"""
    n_points = len(grid_points)
    wave_height = np.zeros(n_points)

    for component in spectrum.components:
        k = component.wave_number
        direction_rad = math.radians(component.direction_deg)
        kx = k * math.sin(direction_rad)
        ky = k * math.cos(direction_rad)
        omega = 2.0 * math.pi * component.frequency

        for i, point in enumerate(grid_points):
            k_dot_r = kx * point.x + ky * point.y
            wave_height[i] += component.amplitude * math.cos(
                k_dot_r - omega * 0.0 + component.phase
            )

    return wave_height


def _advance_wave_field(
    wave_height: np.ndarray,
    spectrum: WaveSpectrum,
    grid_points: List[GridPoint],
    dt: float,
    current_time: float,
) -> np.ndarray:
    """时间步进：推进一个时间步长。"""
    n_points = len(grid_points)
    new_wave_height = np.zeros(n_points)

    for component in spectrum.components:
        k = component.wave_number
        direction_rad = math.radians(component.direction_deg)
        kx = k * math.sin(direction_rad)
        ky = k * math.cos(direction_rad)
        omega = 2.0 * math.pi * component.frequency

        for i, point in enumerate(grid_points):
            k_dot_r = kx * point.x + ky * point.y
            new_wave_height[i] += component.amplitude * math.cos(
                k_dot_r - omega * (current_time + dt) + component.phase
            )

    return new_wave_height


def _create_frame(
    time: float,
    wave_height: np.ndarray,
    grid_points: List[GridPoint],
    region: Region,
) -> SimulationFrame:
    """创建单个时间步的帧。"""
    points = [
        WavePoint(
            lon=point.lon,
            lat=point.lat,
            wave_height=float(wave_height[i]),
        )
        for i, point in enumerate(grid_points)
    ]

    return SimulationFrame(time=float(time), region=region, points=points)


