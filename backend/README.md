## 后端（backend）说明

本目录为**海浪环境模型后端服务**，使用 **Python + FastAPI** 实现，负责：

- 区域海浪模拟（矩形经纬度范围 + 深度）
- 单点海浪高度查询（基于区域结果进行空间双线性插值）
- 风场模型、波浪谱模型管理与组合

### 目录结构

- `app/`：后端应用主包
  - `api/`：接口与路由层，只做协议与参数校验，不写复杂业务逻辑
  - `core/`：全局配置、应用启动、依赖注入等核心设施
  - `models/`：内部领域模型（非对外 Schema）
  - `schemas/`：Pydantic 模型（请求 / 响应 / 配置）
  - `services/`：业务服务，包括风场、波浪谱、区域模拟、插值等
  - `utils/`：通用工具函数

### 运行方式

#### 1. 安装依赖

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

#### 2. 启动服务

```bash
# 开发模式（自动重载）
uvicorn app.main:app --reload

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

服务将在 `http://localhost:8000` 启动。

- API 文档（Swagger UI）: `http://localhost:8000/docs`
- 替代文档（ReDoc）: `http://localhost:8000/redoc`

### API 接口

主要接口包括：

- `POST /api/simulate/area` - 创建区域模拟任务
- `GET /api/simulation/{simulation_id}/frames` - 获取模拟结果帧
- `POST /api/query/point` - 单点查询

详细接口文档请参考 `docs/接口文档.yaml` 或访问 Swagger 文档。

### 前端集成

后端通过 REST API 为前端（Streamlit）提供服务。前端通过 HTTP 请求调用后端接口。

### 开发注意事项

- 使用 Pydantic 进行数据验证
- API 路由层只做参数校验，业务逻辑放在 services 层
- 遵循 FastAPI 最佳实践
- 注意 CORS 配置（已在 `app/main.py` 中配置为允许所有来源，生产环境应限制）


