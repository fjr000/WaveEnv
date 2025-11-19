"""
区域海浪模拟服务。

根据区域、风场、波浪谱等配置，生成时变海浪高度场。
"""

import math
from typing import List

import numpy as np

from app.models.grid import GridPoint, WaveGrid
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


def initialize_wave_field(
    spectrum: WaveSpectrum, grid_points: List[GridPoint]
) -> np.ndarray:
    """
    初始化 t=0 时刻的海浪场。

    使用叠加法：η(x,y,t) = Σ Aᵢ * cos(kᵢ·r - ωᵢt + φᵢ)

    Args:
        spectrum: 波浪谱
        grid_points: 网格点列表

    Returns:
        初始海浪高度数组，shape: (n_points,)
    """
    n_points = len(grid_points)
    wave_height = np.zeros(n_points)

    for component in spectrum.components:
        # 波数向量（方向）
        k = component.wave_number
        direction_rad = math.radians(component.direction_deg)
        kx = k * math.sin(direction_rad)  # 东西方向
        ky = k * math.cos(direction_rad)  # 南北方向

        # 角频率
        omega = 2.0 * math.pi * component.frequency

        # 对每个网格点计算贡献
        for i, point in enumerate(grid_points):
            # 波数向量与位置向量的点积
            k_dot_r = kx * point.x + ky * point.y

            # 叠加波成分
            wave_height[i] += component.amplitude * math.cos(
                k_dot_r - omega * 0.0 + component.phase
            )

    return wave_height


def advance_wave_field(
    wave_height: np.ndarray,
    spectrum: WaveSpectrum,
    grid_points: List[GridPoint],
    dt: float,
    current_time: float,
) -> np.ndarray:
    """
    时间步进：推进一个时间步长。

    Args:
        wave_height: 当前时刻的海浪高度
        spectrum: 波浪谱
        grid_points: 网格点列表
        dt: 时间步长（秒）
        current_time: 当前时间（秒）

    Returns:
        下一时刻的海浪高度数组
    """
    n_points = len(grid_points)
    new_wave_height = np.zeros(n_points)

    for component in spectrum.components:
        # 波数向量
        k = component.wave_number
        direction_rad = math.radians(component.direction_deg)
        kx = k * math.sin(direction_rad)
        ky = k * math.cos(direction_rad)

        # 角频率
        omega = 2.0 * math.pi * component.frequency

        # 对每个网格点计算贡献
        for i, point in enumerate(grid_points):
            k_dot_r = kx * point.x + ky * point.y
            new_wave_height[i] += component.amplitude * math.cos(
                k_dot_r - omega * (current_time + dt) + component.phase
            )

    return new_wave_height


def simulate_area(
    region: Region,
    wind_config: WindConfig,
    spectrum_config: SpectrumConfig,
    discretization_config: DiscretizationConfig,
    time_config: TimeConfig,
) -> List[SimulationFrame]:
    """
    完整区域模拟流程。

    Args:
        region: 区域配置
        wind_config: 风场配置
        spectrum_config: 波浪谱配置
        discretization_config: 离散化配置
        time_config: 时间配置

    Returns:
        模拟时间序列帧列表
    """
    # 1. 创建网格
    grid_points = create_grid(region, discretization_config)

    # 2. 生成风场
    wind = create_wind_field(wind_config)

    # 3. 生成波浪谱
    spectrum = generate_spectrum(wind, spectrum_config)

    # 4. 初始化 t=0 海浪场
    initial_height = initialize_wave_field(spectrum, grid_points)

    # 5. 生成时间序列
    dt = time_config.dt_backend
    T_total = time_config.T_total
    times = np.arange(0, T_total + dt / 2, dt)  # 包含 t=0 和 T_total

    n_times = len(times)
    n_points = len(grid_points)

    # 存储所有时刻的海浪高度
    wave_heights = np.zeros((n_times, n_points))
    wave_heights[0] = initial_height

    # 6. 时间步进
    for t_idx in range(1, n_times):
        current_time = times[t_idx - 1]
        wave_heights[t_idx] = advance_wave_field(
            wave_heights[t_idx - 1],
            spectrum,
            grid_points,
            dt,
            current_time,
        )

    # 7. 转换为 SimulationFrame 列表
    frames = []
    for t_idx, time in enumerate(times):
        points = [
            WavePoint(
                lon=point.lon,
                lat=point.lat,
                wave_height=float(wave_heights[t_idx, i]),
            )
            for i, point in enumerate(grid_points)
        ]

        frames.append(
            SimulationFrame(time=float(time), region=region, points=points)
        )

    return frames


def create_wave_grid(
    region: Region,
    wind_config: WindConfig,
    spectrum_config: SpectrumConfig,
    discretization_config: DiscretizationConfig,
    time_config: TimeConfig,
) -> WaveGrid:
    """
    创建海浪高度网格（用于后续插值查询）。

    Args:
        region: 区域配置
        wind_config: 风场配置
        spectrum_config: 波浪谱配置
        discretization_config: 离散化配置
        time_config: 时间配置

    Returns:
        海浪高度网格对象
    """
    # 创建网格
    grid_points = create_grid(region, discretization_config)

    # 生成风场和波浪谱
    wind = create_wind_field(wind_config)
    spectrum = generate_spectrum(wind, spectrum_config)

    # 初始化并时间步进
    dt = time_config.dt_backend
    T_total = time_config.T_total
    times = np.arange(0, T_total + dt / 2, dt)

    n_times = len(times)
    n_points = len(grid_points)

    wave_heights = np.zeros((n_times, n_points))
    wave_heights[0] = initialize_wave_field(spectrum, grid_points)

    for t_idx in range(1, n_times):
        current_time = times[t_idx - 1]
        wave_heights[t_idx] = advance_wave_field(
            wave_heights[t_idx - 1],
            spectrum,
            grid_points,
            dt,
            current_time,
        )

    return WaveGrid(
        grid_points=grid_points,
        wave_heights=wave_heights,
        times=times,
    )
