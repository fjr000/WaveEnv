"""
Pytest 配置文件。

提供全局的测试配置和 fixture。
"""

import sys
from pathlib import Path

# 添加 backend 目录到 Python 路径
backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

