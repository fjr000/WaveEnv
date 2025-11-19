"""
波浪谱模型服务。

根据风场生成波浪谱，支持 Pierson-Moskowitz (PM) 光谱。
"""

import math
import random

import numpy as np

from app.models.spectrum import WaveComponent, WaveSpectrum
from app.models.wind import WindField
from app.schemas.base import SpectrumConfig

# 重力加速度（m/s²）
G = 9.81

# Pierson-Moskowitz 光谱参数
PM_ALPHA = 0.0081
PM_BETA = 0.74


def generate_spectrum(
    wind: WindField, config: SpectrumConfig
) -> WaveSpectrum:
    """
    根据风场生成波浪谱。

    当前实现：Pierson-Moskowitz (PM) 光谱。

    Args:
        wind: 风场对象
        config: 波浪谱配置

    Returns:
        波浪谱对象
    """
    if config.spectrum_model_type == "PM":
        return _generate_pm_spectrum(wind, config)
    elif config.spectrum_model_type == "JONSWAP":
        raise NotImplementedError("JONSWAP spectrum not yet implemented")
    else:
        raise ValueError(
            f"Unknown spectrum model type: {config.spectrum_model_type}"
        )


def _generate_pm_spectrum(
    wind: WindField, config: SpectrumConfig
) -> WaveSpectrum:
    """
    生成 Pierson-Moskowitz 光谱。

    PM 光谱公式：
    S(ω) = (α * g²) / (ω⁵) * exp(-β * (ωₚ/ω)⁴)

    其中：
    - α = 0.0081
    - β = 0.74
    - ωₚ = 2π / Tp（峰值角频率）
    """
    # 峰值角频率
    omega_p = 2.0 * math.pi / config.Tp

    # 频率范围（Hz）
    freq_min = 0.1
    freq_max = 2.0
    n_freq = 50  # 频率离散点数

    # 方向范围
    main_direction = (
        config.main_wave_direction_deg
        if config.main_wave_direction_deg is not None
        else wind.wind_direction_deg
    )
    spread = config.directional_spread_deg
    n_dir = 16  # 方向离散点数

    # 生成频率数组
    frequencies = np.linspace(freq_min, freq_max, n_freq)
    df = frequencies[1] - frequencies[0] if len(frequencies) > 1 else 0.1

    # 生成方向数组（度）
    directions = np.linspace(
        main_direction - spread / 2.0,
        main_direction + spread / 2.0,
        n_dir,
    )

    components = []

    for freq in frequencies:
        omega = 2.0 * math.pi * freq  # 角频率

        # PM 光谱密度
        if omega > 0:
            S = (
                PM_ALPHA
                * G**2
                / (omega**5)
                * np.exp(-PM_BETA * (omega_p / omega) ** 4)
            )
        else:
            S = 0.0

        # 方向分布（余弦分布）
        for direction_deg in directions:
            # 计算方向权重（相对于主浪向）
            angle_diff = abs(direction_deg - main_direction)
            if angle_diff > spread / 2.0:
                continue

            # 余弦方向分布
            angle_rad = math.radians(angle_diff)
            dir_weight = math.cos(angle_rad) ** 2

            # 该频率-方向的能量
            energy = S * dir_weight * df * (spread / n_dir)

            # 计算振幅（从能量密度）
            # 能量密度 S(ω,θ) 与振幅的关系：A = sqrt(2 * S * dω * dθ)
            amplitude = math.sqrt(2.0 * energy) if energy > 0 else 0.0

            if amplitude > 1e-6:  # 忽略太小的振幅
                # 随机相位
                phase = random.uniform(0, 2 * math.pi)

                # 计算波数（深水波：k = ω² / g）
                k = omega**2 / G

                components.append(
                    WaveComponent(
                        frequency=freq,
                        direction_deg=direction_deg,
                        amplitude=amplitude,
                        phase=phase,
                        wave_number=k,
                    )
                )

    return WaveSpectrum(
        components=components,
        Hs=config.Hs,
        Tp=config.Tp,
        main_direction_deg=main_direction,
    )
