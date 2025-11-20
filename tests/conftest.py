"""
Pytest 配置文件。

提供全局的测试配置和 fixture。
"""

import sys
from pathlib import Path

# 获取项目根目录
project_root = Path(__file__).parent.parent

# 添加 backend 目录到 Python 路径（让测试可以导入 app 模块）
backend_path = project_root / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# 确保 backend 目录是当前工作目录的一部分
# 这样导入 'app' 模块时能正确找到
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

