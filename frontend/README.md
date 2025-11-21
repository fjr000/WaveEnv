# 前端应用（Frontend）

海浪环境模型前端应用，基于 **Streamlit** 实现，负责参数配置、区域可视化、动态渲染等交互功能。

## 📋 核心功能

- **区域模拟可视化**：展示给定区域的海浪高度场随时间变化
- **单点查询**：通过地图点击或输入经纬度坐标，查询该点的海浪高度
- **参数配置**：展示和调整风场、波浪谱模型及离散化参数等配置
- **实时监控**：支持使用 `time=-1` 获取最新帧，实现实时监控

## 🏗️ 技术栈

- **框架**: Streamlit
- **语言**: Python 3.8
- **可视化库**:
  - Plotly：交互式图表和地图
  - Matplotlib：静态图表
- **HTTP 客户端**: httpx（用于调用后端 FastAPI）

## 📁 目录结构

```
frontend/
├── app.py              # Streamlit 主应用文件
├── utils/              # 工具模块
│   ├── api_client.py   # API 客户端（与后端通信）
│   ├── data_converter.py # 数据转换工具
│   └── visualization.py # 可视化工具（图表、热力图）
├── requirements.txt    # Python 依赖
├── Dockerfile         # Docker 镜像构建文件
├── run.bat            # Windows 启动脚本
├── run.ps1            # PowerShell 启动脚本
└── README.md          # 本文件
```

## 🚀 快速开始

### 环境要求

- Python 3.8+
- pip 或 conda
- 后端服务已启动（默认 `http://localhost:8000`）

### 安装依赖

```bash
# 进入前端目录
cd frontend

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 启动应用

```bash
# 确保后端服务已启动（默认 http://localhost:8000）
# 在另一个终端启动后端：
# cd backend
# uvicorn app.main:app --reload

# 启动 Streamlit 前端
streamlit run app.py
```

应用将在 `http://localhost:8501` 启动。

### Windows 快速启动

```bash
# 使用批处理脚本
run.bat

# 或使用 PowerShell
.\run.ps1
```

## ⚙️ 配置

### 后端地址配置

前端通过环境变量或代码配置后端地址：

**方式一：环境变量（推荐）**

```bash
# Windows (PowerShell)
$env:BACKEND_URL="http://localhost:8000"
streamlit run app.py

# Linux/macOS
export BACKEND_URL="http://localhost:8000"
streamlit run app.py
```

**方式二：修改代码**

在 `app.py` 中修改 `BACKEND_URL` 配置：

```python
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
```

**Docker 环境**

在 Docker Compose 中，后端地址应为服务名：

```yaml
environment:
  - BACKEND_URL=http://backend:8000
```

## 🔌 与后端交互

前端通过以下 API 与后端交互：

### 1. 创建区域模拟任务

```python
POST /api/simulate/area
```

**请求体**：
```json
{
  "region": {...},
  "wind": {...},
  "spectrum": {...},
  "discretization": {...},
  "time": {
    "dt_backend": 0.2,
    "T_total": -1,
    "cache_retention_time": 60.0
  }
}
```

### 2. 获取模拟结果帧（单时刻）

```python
GET /api/query/simulation/{simulation_id}/frames?time={time}
```

**参数说明**：
- `time=-1`：获取最新帧（适用于实时监控）
- 其他值：获取指定时刻的数据

**示例**：
```python
# 获取最新帧
frames = api_client.get_frames(simulation_id, time=-1)

# 获取指定时刻的帧
frames = api_client.get_frames(simulation_id, time=0.6)
```

### 3. 单点查询

```python
POST /api/query/point
```

**请求体**：
```json
{
  "simulation_id": "...",
  "lon": 120.5,
  "lat": 35.2,
  "time": -1
}
```

**参数说明**：
- `time=-1`：查询最新帧的数据
- 其他值：查询指定时刻的数据

## 🎨 功能模块

### 1. 参数配置面板

- **区域设置**：经纬度范围、深度
- **风场参数**：风速、风向、参考高度
- **波浪谱参数**：
  - 模型类型（PM / JONSWAP）
  - 显著波高（Hs）
  - 峰值周期（Tp）
  - 主浪向、波向扩散
  - JONSWAP 参数（gamma）
- **离散化参数**：dx, dy, max_points
- **时间参数**：
  - `dt_backend`：后端计算步长（默认 0.2s）
  - `T_total`：总仿真时长（`-1` 或 `null` 表示无限制）
  - `cache_retention_time`：缓存保留时间

### 2. 可视化区域

- **地图显示**：使用 Plotly 显示区域地图
- **海浪高度场热力图**：动态展示海浪高度分布
- **时间序列播放控制**：
  - 播放/暂停
  - 时间滑块选择特定时刻
  - 使用 `time=-1` 自动获取最新帧
- **颜色映射（colorbar）**：浪高与颜色的对应关系

### 3. 单点查询

- **地图点击查询**：点击地图上的点进行查询
- **手动输入坐标查询**：输入经纬度进行查询
- **时间选择**：
  - 使用最新帧（`time=-1`）
  - 使用指定时刻
- **实时显示查询结果**：显示查询点的海浪高度和实际查询时间

### 4. 模拟任务管理

- **创建任务**：根据当前参数创建新的模拟任务
- **任务状态**：显示任务状态（pending, running, completed, failed）
- **结果展示**：展示模拟结果的时间序列

## 🔧 开发指南

### 状态管理

Streamlit 应用使用 `st.session_state` 管理状态：

```python
# 初始化状态
if 'simulation_id' not in st.session_state:
    st.session_state.simulation_id = None

# 更新状态
st.session_state.simulation_id = "new-id"
```

### API 客户端使用

```python
from utils.api_client import APIClient

# 创建 API 客户端
with APIClient() as api_client:
    # 创建模拟任务
    response = api_client.create_simulation(...)
    
    # 获取帧（单时刻）
    frames = api_client.get_frames(simulation_id, time=-1)
    
    # 单点查询
    result = api_client.query_point(
        simulation_id=simulation_id,
        lon=120.5,
        lat=35.2,
        time=-1
    )
```

### 可视化

```python
from utils.visualization import create_heatmap, create_time_series_chart

# 创建热力图
fig = create_heatmap(points, region)

# 创建时间序列图
fig = create_time_series_chart(data)
```

### 开发注意事项

- ✅ Streamlit 应用是状态化的，使用 `st.session_state` 管理状态
- ✅ 后端 API 调用使用异步 httpx 客户端
- ✅ 大数据量可视化时注意性能优化
- ✅ 遵循 Streamlit 最佳实践，合理使用缓存（`@st.cache_data`）
- ✅ 接口只支持单时刻查询，如需多时刻需多次调用
- ✅ 使用 `time=-1` 获取最新帧，适用于实时监控

## 🐳 Docker 部署

使用 Docker Compose 可以快速部署，详见根目录 `docker-compose.yml`。

**Docker Compose 配置**：

```yaml
frontend:
  build: ./frontend
  ports:
    - "8888:8501"
  environment:
    - BACKEND_URL=http://backend:8000
  profiles:
    - frontend
```

**启动**：

```bash
# Windows
docker-start.bat --frontend

# Linux/macOS
./docker-start.sh --frontend
```

服务启动后访问：`http://localhost:8888`

## 📚 相关文档

- **需求文档**: `docs/需求文档V1.md`
- **接口文档**: `docs/接口文档.yaml`
- **项目主文档**: `README.md`
- **后端文档**: `../backend/README.md`

## 🔗 与后端通信

- **通信协议**: HTTP REST API
- **数据格式**: JSON
- **后端地址**: 通过环境变量 `BACKEND_URL` 配置（默认 `http://localhost:8000`）
- **错误处理**: 使用 `httpx` 的异常处理机制，捕获 `HTTPStatusError` 和 `RequestError`

## 💡 使用技巧

### 实时监控

使用 `time=-1` 可以获取最新帧，实现实时监控：

```python
# 获取最新帧
frames = api_client.get_frames(simulation_id, time=-1)
```

### 无限制运行

设置 `T_total=-1` 或 `null` 可以让模拟无限制运行：

```python
time_config = {
    "dt_backend": 0.2,
    "T_total": -1,  # 无限制运行
    "cache_retention_time": 60.0  # 只保留最近 60 秒的帧
}
```

### 缓存优化

使用 `cache_retention_time` 控制内存使用：

```python
time_config = {
    "dt_backend": 0.2,
    "T_total": -1,
    "cache_retention_time": 60.0  # 只保留最近 60 秒的帧
}
```
