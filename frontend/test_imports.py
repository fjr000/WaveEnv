"""
测试导入脚本。

用于验证所有模块是否可以正常导入。
"""

import sys
from pathlib import Path

# 添加当前目录到 Python 路径
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

print("测试模块导入...")
print(f"Python 路径: {sys.path[:3]}...")
print()

try:
    print("1. 导入 streamlit...")
    import streamlit as st
    print(f"   ✓ streamlit {st.__version__}")
except ImportError as e:
    print(f"   ✗ 导入失败: {e}")
    sys.exit(1)

try:
    print("2. 导入 numpy...")
    import numpy as np
    print(f"   ✓ numpy {np.__version__}")
except ImportError as e:
    print(f"   ✗ 导入失败: {e}")
    sys.exit(1)

try:
    print("3. 导入 utils.api_client...")
    from utils.api_client import APIClient, BACKEND_URL
    print(f"   ✓ APIClient (后端地址: {BACKEND_URL})")
except ImportError as e:
    print(f"   ✗ 导入失败: {e}")
    sys.exit(1)

try:
    print("4. 导入 utils.data_converter...")
    from utils.data_converter import frames_to_grid_data, get_frame_at_time
    print("   ✓ data_converter")
except ImportError as e:
    print(f"   ✗ 导入失败: {e}")
    sys.exit(1)

try:
    print("5. 导入 utils.visualization...")
    from utils.visualization import create_heatmap, create_time_series_chart
    print("   ✓ visualization")
except ImportError as e:
    print(f"   ✗ 导入失败: {e}")
    sys.exit(1)

print()
print("=" * 50)
print("✓ 所有模块导入成功！")
print("=" * 50)
print()
print("可以运行: streamlit run app.py")



