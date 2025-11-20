"""
基础功能测试。

测试核心服务模块的基本功能。
"""

import pytest
import numpy as np

from app.models.wind import WindField
from app.schemas.base import (
    DiscretizationConfig,
    Region,
    SpectrumConfig,
    TimeConfig,
    WindConfig,
)
from app.services.spectrum import generate_spectrum
from app.services.wind import create_wind_field
from app.utils.coordinate import create_grid, lonlat_to_xy


def test_wind_field_creation():
    """测试风场创建。"""
    config = WindConfig(wind_speed=10.0, wind_direction_deg=270.0)
    wind = create_wind_field(config)

    assert wind.wind_speed == 10.0
    assert wind.wind_direction_deg == 270.0
    assert wind.reference_height_m == 10.0


def test_wind_components():
    """测试风场分量计算。"""
    wind = WindField(
        wind_speed=10.0, wind_direction_deg=270.0, reference_height_m=10.0
    )
    u, v = wind.get_wind_components()

    # 270度应该是向西（负x方向）
    assert u < 0  # 西风
    assert abs(v) < 1e-6  # 南北分量应该接近0


def test_spectrum_generation():
    """测试波浪谱生成。"""
    wind = create_wind_field(WindConfig(wind_speed=10.0, wind_direction_deg=270.0))
    spectrum_config = SpectrumConfig(
        spectrum_model_type="PM", Hs=2.0, Tp=8.0
    )

    spectrum = generate_spectrum(wind, spectrum_config)

    assert spectrum.Hs == 2.0
    assert spectrum.Tp == 8.0
    assert len(spectrum.components) > 0


def test_coordinate_conversion():
    """测试坐标转换。"""
    origin_lon = 120.0
    origin_lat = 35.0

    # 测试经纬度转本地坐标
    x, y = lonlat_to_xy(120.1, 35.0, origin_lon, origin_lat)
    assert x > 0  # 向东应该是正x

    # 测试本地坐标转经纬度
    from app.utils.coordinate import xy_to_lonlat

    lon, lat = xy_to_lonlat(x, y, origin_lon, origin_lat)
    assert abs(lon - 120.1) < 0.01
    assert abs(lat - 35.0) < 0.01


def test_grid_creation():
    """测试网格创建。"""
    region = Region(
        lon_min=120.0,
        lat_min=35.0,
        depth_min=10.0,
        lon_max=120.1,
        lat_max=35.1,
        depth_max=20.0,
    )
    config = DiscretizationConfig(dx=0.01, dy=0.01, max_points=1000)

    grid_points = create_grid(region, config)

    assert len(grid_points) > 0
    assert len(grid_points) <= config.max_points

    # 检查网格点范围
    lons = [p.lon for p in grid_points]
    lats = [p.lat for p in grid_points]

    assert min(lons) >= region.lon_min
    assert max(lons) <= region.lon_max
    assert min(lats) >= region.lat_min
    assert max(lats) <= region.lat_max

