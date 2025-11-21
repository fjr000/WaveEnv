# 后端服务（Backend）

海浪环境模型后端服务，基于 **Python + FastAPI** 实现，负责海浪物理模型模拟、区域计算、单点查询等核心功能。

## 📋 核心功能

- **区域海浪模拟**：根据输入的区域（矩形经纬度范围 + 深度）、风场参数和波浪谱参数，生成时变海浪高度场
- **单点查询**：基于区域模拟结果，通过空间双线性插值和时间线性插值，查询任意点的海浪高度
- **风场模型管理**：支持固定风场模型（当前版本），后续可扩展为时变风场
- **波浪谱模型管理**：支持 Pierson-Moskowitz (PM) 和 JONSWAP 光谱模型
- **模拟任务管理**：创建、查询、管理模拟任务状态

## 🏗️ 技术栈

- **框架**: FastAPI
- **语言**: Python 3.8
- **数据验证**: Pydantic
- **ASGI 服务器**: Uvicorn
- **数值计算**: NumPy

## 📁 目录结构

```
backend/
├── app/
│   ├── api/              # API 路由层
│   │   ├── simulation.py # 区域模拟接口
│   │   ├── query.py      # 单点查询接口
│   │   └── router.py     # 路由汇总
│   ├── core/             # 核心配置与基础设施
│   │   ├── config.py     # 应用配置
│   │   ├── storage.py    # 数据存储管理
│   │   └── task_manager.py # 任务管理
│   ├── models/           # 内部领域模型
│   │   ├── grid.py       # 网格模型
│   │   ├── simulation.py # 模拟任务模型
│   │   ├── spectrum.py   # 波浪谱模型
│   │   └── wind.py       # 风场模型
│   ├── schemas/          # Pydantic 请求/响应模型
│   │   ├── api.py        # API Schema
│   │   ├── base.py       # 基础配置 Schema
│   │   └── data.py       # 数据 Schema
│   ├── services/         # 业务服务层
│   │   ├── simulation.py # 模拟服务
│   │   ├── simulation_stream.py # 流式模拟服务
│   │   ├── spectrum.py   # 波浪谱服务
│   │   ├── wind.py       # 风场服务
│   │   └── interpolation.py # 插值服务
│   ├── utils/            # 工具函数
│   │   ├── coordinate.py # 坐标转换
│   │   └── numerical.py  # 数值计算
│   └── main.py           # 应用入口
├── pyproject.toml        # Python 项目配置
├── requirements.txt      # 依赖列表
├── Dockerfile           # Docker 镜像构建文件
└── README.md            # 本文件
```

## 🚀 快速开始

### 环境要求

- Python 3.8+
- pip 或 conda

### 安装依赖

```bash
# 进入后端目录
cd backend

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -e .
# 或
pip install -r requirements.txt
```

### 启动服务

```bash
# 开发模式（自动重载）
uvicorn app.main:app --reload

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

服务将在 `http://localhost:8000` 启动。

### 访问文档

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

## 🔌 API 接口

### 核心接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/simulate/area` | 创建区域模拟任务 |
| `GET` | `/api/query/simulation/{simulation_id}/frames?time={time}` | 获取指定时刻的模拟结果帧（单时刻） |
| `POST` | `/api/query/point` | 单点查询 |

### 接口说明

#### 1. 创建区域模拟任务

```bash
POST /api/simulate/area
```

**请求体**：
```json
{
  "region": {
    "lon_min": 120.0,
    "lat_min": 30.0,
    "depth_min": 10.0,
    "lon_max": 120.5,
    "lat_max": 30.5,
    "depth_max": 20.0
  },
  "wind": {
    "wind_speed": 10.0,
    "wind_direction_deg": 270.0
  },
  "spectrum": {
    "spectrum_model_type": "PM",
    "Hs": 2.0,
    "Tp": 8.0
  },
  "discretization": {
    "dx": 0.01,
    "dy": 0.01,
    "max_points": 40000
  },
  "time": {
    "dt_backend": 0.2,
    "T_total": -1,
    "cache_retention_time": 60.0
  }
}
```

**响应**：
```json
{
  "simulation_id": "abcd-1234",
  "status": "running"
}
```

#### 2. 获取模拟结果帧（单时刻）

```bash
GET /api/query/simulation/{simulation_id}/frames?time={time}
```

**参数说明**：
- `simulation_id`（路径参数）：模拟任务 ID
- `time`（查询参数，必填）：
  - `time=-1`：获取最新帧
  - 其他值：获取指定时刻的数据（返回最接近的帧）

**响应**：
```json
{
  "simulation_id": "abcd-1234",
  "status": "running",
  "frames": [
    {
      "time": 0.2,
      "region": {...},
      "points": [
        {"lon": 120.1, "lat": 30.1, "wave_height": 1.5},
        ...
      ]
    }
  ]
}
```

#### 3. 单点查询

```bash
POST /api/query/point
```

**请求体**：
```json
{
  "simulation_id": "abcd-1234",
  "lon": 120.5,
  "lat": 35.2,
  "time": -1
}
```

**参数说明**：
- `time=-1`：查询最新帧的数据
- 其他值：查询指定时刻的数据

**响应**：
```json
{
  "simulation_id": "abcd-1234",
  "time": 0.6,
  "lon": 120.5,
  "lat": 35.2,
  "wave_height": 1.23
}
```

> **注意**：响应中的 `time` 为实际查询时间（如果请求中 `time=-1`，则返回最新帧的实际时间）

## ⚙️ 配置参数

### 时间参数

- **`dt_backend`**：后端计算时间步长（秒）
  - 默认值：0.2（200ms）
  - 必须 > 0
  - 每隔一个 `dt_backend` 生成一帧

- **`T_total`**：总仿真时长（秒）
  - `null` 或 `-1`：无限制持续运行
  - 正数：指定总时长（必须 > 0）

- **`cache_retention_time`**：缓存保留时间（秒）
  - `null`：保留所有历史帧
  - 正数：只保留最近 N 秒的帧，超过此时间的旧帧将被自动淘汰

### 风场参数

- **`wind_speed`**：风速（m/s），默认 10.0
- **`wind_direction_deg`**：风向（度，0°=北向，顺时针增加），默认 270.0
- **`reference_height_m`**：参考高度（m），默认 10.0

### 波浪谱参数

- **`spectrum_model_type`**：模型类型（"PM" / "JONSWAP"），默认 "PM"
- **`Hs`**：显著波高（m），默认 2.0
- **`Tp`**：峰值周期（s），默认 8.0
- **`main_wave_direction_deg`**：主浪向（度）
- **`directional_spread_deg`**：波向扩散（度），默认 30.0
- **`gamma`**：JONSWAP 峰锐系数（仅 JONSWAP），默认 3.3

### 离散化参数

- **`dx`**：经度方向离散间隔（度），默认 0.01
- **`dy`**：纬度方向离散间隔（度），默认 0.01
- **`max_points`**：最大离散点数量，默认 40000

## 🔧 开发指南

### 架构设计

- **API 层**（`app/api/`）：只做参数校验，不包含业务逻辑
- **服务层**（`app/services/`）：核心业务逻辑实现
- **模型层**（`app/models/`）：内部领域模型
- **Schema 层**（`app/schemas/`）：API 请求/响应验证

### 开发注意事项

- ✅ 使用 Pydantic 进行数据验证
- ✅ API 路由层只做参数校验，业务逻辑放在 services 层
- ✅ 遵循 FastAPI 最佳实践
- ✅ 注意 CORS 配置（已在 `app/main.py` 中配置为允许所有来源，生产环境应限制）
- ✅ 接口只支持单时刻查询，如需多时刻需多次调用
- ✅ 使用 `time=-1` 获取最新帧，适用于实时监控

### 运行测试

```bash
# 安装测试依赖
pip install pytest pytest-asyncio httpx

# 运行测试
pytest tests/backend/
```

## 🐳 Docker 部署

使用 Docker Compose 可以快速部署，详见根目录 `docker-compose.yml`。

```bash
# 构建镜像
docker build -t waveenv-backend ./backend

# 运行容器
docker run -p 8000:8000 waveenv-backend
```

## 📚 相关文档

- **需求文档**: `docs/需求文档V1.md`
- **接口文档**: `docs/接口文档.yaml`
- **项目主文档**: `README.md`

## 🔗 与前端集成

后端通过 REST API 为前端（Streamlit）提供服务。前端通过 HTTP 请求调用后端接口。

默认配置：
- 后端地址：`http://localhost:8000`
- 前端地址：`http://localhost:8501`
- 数据格式：JSON
