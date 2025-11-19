"""
代码验证脚本 - 检查代码逻辑和导入。
"""

import sys
from pathlib import Path

# 添加backend到路径
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

print("=" * 60)
print("代码验证测试")
print("=" * 60)
print()

errors = []
warnings = []

# 1. 测试所有模块导入
print("1. 测试模块导入...")
try:
    from app.schemas.base import (
        Region,
        WindConfig,
        SpectrumConfig,
        DiscretizationConfig,
        TimeConfig,
    )
    print("   ✓ Schema 导入成功")
except Exception as e:
    errors.append(f"Schema 导入失败: {e}")
    print(f"   ✗ Schema 导入失败: {e}")

try:
    from app.models.wind import WindField
    from app.models.spectrum import WaveSpectrum
    from app.models.grid import WaveGrid
    print("   ✓ Models 导入成功")
except Exception as e:
    errors.append(f"Models 导入失败: {e}")
    print(f"   ✗ Models 导入失败: {e}")

try:
    from app.services.wind import create_wind_field
    from app.services.spectrum import generate_spectrum
    from app.services.simulation import simulate_area
    from app.services.interpolation import query_point
    print("   ✓ Services 导入成功")
except Exception as e:
    errors.append(f"Services 导入失败: {e}")
    print(f"   ✗ Services 导入失败: {e}")

try:
    from app.utils.coordinate import create_grid, lonlat_to_xy
    from app.utils.numerical import bilinear_interpolation
    print("   ✓ Utils 导入成功")
except Exception as e:
    errors.append(f"Utils 导入失败: {e}")
    print(f"   ✗ Utils 导入失败: {e}")

try:
    from app.api.router import api_router
    print("   ✓ API 路由导入成功")
except Exception as e:
    errors.append(f"API 路由导入失败: {e}")
    print(f"   ✗ API 路由导入失败: {e}")

try:
    from app.main import app
    print("   ✓ 主应用导入成功")
except Exception as e:
    errors.append(f"主应用导入失败: {e}")
    print(f"   ✗ 主应用导入失败: {e}")

print()

# 2. 测试基本功能
if not errors:
    print("2. 测试基本功能...")
    try:
        # 创建配置
        wind_config = WindConfig(wind_speed=10.0, wind_direction_deg=270.0)
        spectrum_config = SpectrumConfig(spectrum_model_type="PM", Hs=2.0, Tp=8.0)
        region = Region(
            lon_min=120.0, lat_min=35.0, depth_min=10.0,
            lon_max=120.1, lat_max=35.1, depth_max=20.0
        )
        discretization = DiscretizationConfig(dx=0.01, dy=0.01, max_points=100)
        time_config = TimeConfig(dt_backend=0.2, T_total=1.0)

        # 测试风场
        wind = create_wind_field(wind_config)
        assert wind.wind_speed == 10.0
        print("   ✓ 风场创建成功")

        # 测试波浪谱
        spectrum = generate_spectrum(wind, spectrum_config)
        assert len(spectrum.components) > 0
        print(f"   ✓ 波浪谱生成成功 ({len(spectrum.components)} 个成分)")

        # 测试网格
        grid_points = create_grid(region, discretization)
        assert len(grid_points) > 0
        print(f"   ✓ 网格创建成功 ({len(grid_points)} 个点)")

        # 测试模拟（小规模）
        frames = simulate_area(region, wind_config, spectrum_config, discretization, time_config)
        assert len(frames) > 0
        print(f"   ✓ 模拟成功 ({len(frames)} 个时间帧)")

    except Exception as e:
        errors.append(f"功能测试失败: {e}")
        print(f"   ✗ 功能测试失败: {e}")
        import traceback
        traceback.print_exc()

print()

# 3. 总结
print("=" * 60)
if errors:
    print("❌ 发现错误:")
    for error in errors:
        print(f"   - {error}")
    print()
    print("请修复上述错误后重试。")
    sys.exit(1)
else:
    print("✅ 所有验证通过！")
    print()
    print("代码可以正常使用。")
    print("下一步：")
    print("  1. 启动服务: uvicorn app.main:app --reload")
    print("  2. 访问文档: http://127.0.0.1:8000/docs")
    print("  3. 运行测试: python quick_test.py")
print("=" * 60)


