"""
快速测试脚本 - 直接测试服务功能（不启动HTTP服务器）。
"""

import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

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


def test_basic_functions():
    """测试基础功能。"""
    print("=" * 60)
    print("测试基础功能")
    print("=" * 60)

    # 1. 测试风场创建
    print("\n1. 测试风场创建...")
    config = WindConfig(wind_speed=10.0, wind_direction_deg=270.0)
    wind = create_wind_field(config)
    print(f"   风速: {wind.wind_speed} m/s")
    print(f"   风向: {wind.wind_direction_deg}°")
    u, v = wind.get_wind_components()
    print(f"   风速分量: u={u:.2f}, v={v:.2f}")

    # 2. 测试波浪谱生成
    print("\n2. 测试波浪谱生成...")
    spectrum_config = SpectrumConfig(
        spectrum_model_type="PM", Hs=2.0, Tp=8.0
    )
    spectrum = generate_spectrum(wind, spectrum_config)
    print(f"   显著波高: {spectrum.Hs} m")
    print(f"   峰值周期: {spectrum.Tp} s")
    print(f"   波成分数量: {len(spectrum.components)}")

    # 3. 测试坐标转换
    print("\n3. 测试坐标转换...")
    origin_lon, origin_lat = 120.0, 35.0
    x, y = lonlat_to_xy(120.1, 35.0, origin_lon, origin_lat)
    print(f"   经纬度 (120.1, 35.0) -> 本地坐标 ({x:.2f}, {y:.2f})")

    # 4. 测试网格创建
    print("\n4. 测试网格创建...")
    region = Region(
        lon_min=120.0,
        lat_min=35.0,
        depth_min=10.0,
        lon_max=120.1,
        lat_max=35.1,
        depth_max=20.0,
    )
    discretization = DiscretizationConfig(dx=0.01, dy=0.01, max_points=100)
    grid_points = create_grid(region, discretization)
    print(f"   网格点数: {len(grid_points)}")
    print(f"   第一个点: lon={grid_points[0].lon:.4f}, lat={grid_points[0].lat:.4f}")

    # 5. 测试完整模拟流程
    print("\n5. 测试完整模拟流程...")
    time_config = TimeConfig(dt_backend=0.2, T_total=1.0)
    wind_config = WindConfig(wind_speed=10.0, wind_direction_deg=270.0)
    from app.services.simulation import simulate_area

    frames = simulate_area(
        region, wind_config, spectrum_config, discretization, time_config
    )
    print(f"   生成帧数: {len(frames)}")
    if len(frames) > 0:
        frame = frames[0]
        print(f"   第一帧时间: {frame.time}s")
        print(f"   第一帧点数: {len(frame.points)}")
        if len(frame.points) > 0:
            point = frame.points[0]
            print(f"   示例点海浪高度: {point.wave_height:.4f}m")

    print("\n" + "=" * 60)
    print("所有测试通过！")
    print("=" * 60)


if __name__ == "__main__":
    try:
        test_basic_functions()
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback

        traceback.print_exc()

