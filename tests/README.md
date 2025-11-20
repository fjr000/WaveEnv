## 测试（tests）说明

本目录用于存放后端测试用例。

### 目录结构

```
tests/
├── conftest.py              # Pytest 全局配置（路径设置等）
├── backend/                 # 后端测试
│   ├── __init__.py
│   ├── test_basic.py        # 基础功能测试
│   └── test_api.py          # API 端点测试
├── frontend/                # 前端测试（预留，当前为空）
│   └── __init__.py
└── integration/             # 集成测试（预留，当前为空）
    └── __init__.py
```

### 测试文件说明

#### `test_basic.py` - 基础功能测试

测试核心服务模块的基本功能：

- `test_wind_field_creation()` - 测试风场创建
- `test_wind_components()` - 测试风场分量计算
- `test_spectrum_generation()` - 测试波浪谱生成
- `test_coordinate_conversion()` - 测试坐标转换（经纬度 ↔ 本地坐标）
- `test_grid_creation()` - 测试网格创建

#### `test_api.py` - API 端点测试

使用 FastAPI TestClient 测试 API 端点：

- `test_root()` - 测试根路径
- `test_health()` - 测试健康检查
- `test_create_simulation()` - 测试创建区域模拟任务
- `test_get_simulation_frames()` - 测试获取模拟结果
- `test_query_point()` - 测试单点查询
- `test_invalid_simulation_id()` - 测试无效 ID 处理
- `test_invalid_query()` - 测试无效查询处理

### 运行测试

#### 从项目根目录运行（推荐）

```bash
# 进入项目根目录
cd /path/to/WaveEnv

# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/backend/test_basic.py
pytest tests/backend/test_api.py

# 运行特定测试函数
pytest tests/backend/test_basic.py::test_wind_field_creation

# 显示详细输出
pytest -v

# 显示覆盖率
pytest --cov=backend/app --cov-report=html
```

#### 从 backend 目录运行

```bash
# 进入 backend 目录
cd backend

# 运行测试（pytest.ini 已配置路径）
pytest
```

### 测试要求

- **Python**: 3.8+
- **pytest**: 测试框架
- **依赖**: 需要安装后端依赖（`pip install -e backend/` 或 `pip install -r backend/requirements.txt`）

### 测试命名规范

- 测试文件命名：`test_*.py`
- 测试函数命名：`test_*`
- 测试类命名：`Test*`

### 注意事项

1. **路径配置**: `tests/conftest.py` 已自动配置 Python 路径，测试文件无需手动添加路径设置
2. **测试隔离**: 每个测试应该独立，不依赖其他测试的执行顺序
3. **API 测试**: `test_api.py` 使用 FastAPI TestClient，无需启动实际服务器
4. **清理**: 已删除无用的测试文件（`quick_test.py`, `manual_test.py`），仅保留正式的 pytest 测试

### 已删除的文件

以下文件已被删除，功能已由正式的 pytest 测试覆盖：

- `backend/quick_test.py` - 快速测试脚本（功能由 `test_basic.py` 覆盖）
- `tests/backend/manual_test.py` - 手动测试脚本（功能由 `test_api.py` 覆盖）
