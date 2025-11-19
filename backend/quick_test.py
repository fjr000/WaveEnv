"""
快速测试 - 验证核心功能是否正常工作。
"""

print("开始测试...")

try:
    # 测试导入
    print("1. 测试模块导入...")
    from app.schemas.base import Region, WindConfig, SpectrumConfig
    from app.services.wind import create_wind_field
    print("   ✓ 导入成功")

    # 测试风场
    print("2. 测试风场创建...")
    wind_config = WindConfig(wind_speed=10.0, wind_direction_deg=270.0)
    wind = create_wind_field(wind_config)
    assert wind.wind_speed == 10.0
    print("   ✓ 风场创建成功")

    # 测试波浪谱
    print("3. 测试波浪谱生成...")
    from app.services.spectrum import generate_spectrum
    spectrum_config = SpectrumConfig(spectrum_model_type="PM", Hs=2.0, Tp=8.0)
    spectrum = generate_spectrum(wind, spectrum_config)
    assert len(spectrum.components) > 0
    print(f"   ✓ 波浪谱生成成功，包含 {len(spectrum.components)} 个波成分")

    # 测试坐标转换
    print("4. 测试坐标转换...")
    from app.utils.coordinate import lonlat_to_xy
    x, y = lonlat_to_xy(120.1, 35.0, 120.0, 35.0)
    assert x > 0
    print(f"   ✓ 坐标转换成功: ({x:.2f}, {y:.2f})")

    # 测试网格创建
    print("5. 测试网格创建...")
    from app.schemas.base import DiscretizationConfig
    from app.utils.coordinate import create_grid
    region = Region(
        lon_min=120.0, lat_min=35.0, depth_min=10.0,
        lon_max=120.1, lat_max=35.1, depth_max=20.0
    )
    discretization = DiscretizationConfig(dx=0.01, dy=0.01, max_points=100)
    grid_points = create_grid(region, discretization)
    assert len(grid_points) > 0
    print(f"   ✓ 网格创建成功，包含 {len(grid_points)} 个点")

    # 测试完整模拟
    print("6. 测试完整模拟流程...")
    from app.schemas.base import TimeConfig
    from app.services.simulation import simulate_area
    time_config = TimeConfig(dt_backend=0.2, T_total=1.0)
    frames = simulate_area(region, wind_config, spectrum_config, discretization, time_config)
    assert len(frames) > 0
    print(f"   ✓ 模拟成功，生成 {len(frames)} 个时间帧")
    if len(frames[0].points) > 0:
        print(f"   ✓ 第一帧包含 {len(frames[0].points)} 个点，海浪高度范围: "
              f"{min(p.wave_height for p in frames[0].points):.4f} ~ "
              f"{max(p.wave_height for p in frames[0].points):.4f} m")

    print("\n" + "="*60)
    print("所有测试通过！✓")
    print("="*60)

except ImportError as e:
    print(f"\n❌ 导入错误: {e}")
    print("请确保已安装依赖: pip install -e .")
except AssertionError as e:
    print(f"\n❌ 断言失败: {e}")
except Exception as e:
    print(f"\n❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()


