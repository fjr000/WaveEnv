# 时变海浪环境模型系统 (WaveEnv)

一个基于物理模型的海浪环境模拟与可视化系统，支持对指定区域内的海浪高度进行时变模拟、查询与可视化展示。

## 📋 项目简介

本系统实现了一个**时变海浪环境模型**，采用前后端分离架构：

- **后端**：基于 Python + FastAPI，负责海浪物理模型模拟、区域计算、单点查询等核心功能
- **前端**：基于 Streamlit，负责参数配置、区域可视化、动态渲染等交互功能
- **模型**：支持风场模型（当前为固定风场）与波浪谱模型（Pierson-Moskowitz / JONSWAP）的组合

### 核心功能

- 🌊 **区域海浪模拟**：给定矩形区域（经纬度范围 + 深度），结合风场与波浪谱参数，生成时变海浪高度场
- 📍 **单点查询**：基于区域模拟结果，通过空间双线性插值查询任意点的海浪高度
- ⚙️ **参数配置**：支持风场、波浪谱、离散化等参数的前端配置与实时调整
- 🎨 **可视化展示**：动态渲染海浪高度场，支持时间序列播放与交互查询

## 🏗️ 项目结构

```
WaveEnv/
├── backend/              # 后端服务（Python + FastAPI）
│   ├── app/
│   │   ├── api/         # API 路由层
│   │   ├── core/        # 核心配置与启动逻辑
│   │   ├── models/      # 内部领域模型
│   │   ├── schemas/     # Pydantic 请求/响应模型
│   │   ├── services/    # 业务服务（风场、波浪谱、模拟、插值）
│   │   └── utils/       # 通用工具函数
│   ├── pyproject.toml   # Python 项目配置
│   └── README.md        # 后端说明文档
│
├── frontend/            # 前端应用（Streamlit）
│   ├── app.py           # Streamlit 主应用文件
│   ├── requirements.txt # 前端依赖
│   └── README.md        # 前端说明文档
│
├── tests/               # 测试目录
│   ├── backend/         # 后端单元测试与 API 测试
│   ├── frontend/        # 前端组件与页面测试
│   └── integration/     # 前后端集成测试
│
├── docs/                # 项目文档
│   ├── 需求文档V1.md    # 需求文档（完整版）
│   ├── 接口文档.yaml    # OpenAPI 接口定义
│   └── README.md        # 文档目录说明
│
├── docker-compose.yml   # Docker Compose 配置
├── docker-start.bat     # Windows 启动脚本
├── docker-start.sh      # Linux/macOS 启动脚本
├── docker-stop.bat      # Windows 停止脚本
├── docker-stop.sh       # Linux/macOS 停止脚本
├── README.Docker.md     # Docker 部署详细文档
├── .gitignore           # Git 忽略规则
└── README.md            # 本文件
```

## 🚀 快速开始

### 环境要求

- **Python**: 3.8（后端和前端）
- **Git**: 用于版本管理

### 后端开发

```bash
# 进入后端目录
cd backend

# 安装依赖（推荐使用虚拟环境）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e .

# 启动服务（开发模式）
uvicorn app.main:app --reload
```

服务将在 `http://localhost:8000` 启动，API 文档可访问 `http://localhost:8000/docs`。

### 前端开发

```bash
# 进入前端目录
cd frontend

# 安装依赖（推荐使用虚拟环境）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 启动 Streamlit 应用
streamlit run app.py
```

应用将在 `http://localhost:8501` 启动。

> **注意**：前端通过 HTTP 调用后端 FastAPI 服务，请确保后端服务已启动（默认 `http://localhost:8000`）。

### Docker 部署（推荐）

使用 Docker Compose 可以快速部署整个系统，详见 [README.Docker.md](README.Docker.md)。

**快速启动**：

```bash
# Windows
docker-start.bat

# Linux/macOS
chmod +x docker-start.sh
./docker-start.sh
```

**停止服务**：

```bash
# Windows
docker-stop.bat

# Linux/macOS
chmod +x docker-stop.sh
./docker-stop.sh
```

服务启动后：
- 前端：`http://localhost:8888`
- 后端 API：`http://localhost:8000`
- API 文档：`http://localhost:8000/docs`

## 📚 文档说明

项目文档统一存放在 `docs/` 目录：

- **`需求文档V1.md`**：完整的需求文档，包含系统架构、功能需求、参数说明、接口定义等
- **`接口文档.yaml`**：OpenAPI 3.0 格式的接口定义，包含请求/响应 Schema

更多技术文档（如物理模型说明、架构设计等）也将存放在 `docs/` 目录中。

> **快速查阅**：需求文档包含快速导航，可快速定位到感兴趣的章节。

## 🔧 技术栈

### 后端

- **框架**: FastAPI
- **语言**: Python 3.8
- **数据验证**: Pydantic
- **ASGI 服务器**: Uvicorn

### 前端

- **框架**: Streamlit
- **语言**: Python 3.8
- **可视化**: Plotly / Matplotlib / Folium
- **HTTP 客户端**: httpx（用于调用后端 API）

### 开发工具

- **版本控制**: Git
- **代码质量**: ruff, mypy（后端）
- **测试**: pytest（后端）

## 📝 项目状态

- ✅ 项目结构搭建完成
- ✅ 后端业务逻辑实现完成
- ✅ 后端 API 接口实现完成
- ✅ Streamlit 前端功能实现完成
- ✅ 可视化组件开发完成
- ✅ Docker 容器化部署支持
- ✅ 单元测试和集成测试完成

## 🤝 贡献指南

1. 遵循项目目录结构与命名规范
2. 代码遵循 Python PEP 8 规范
3. 前后端统一使用 Python 虚拟环境管理依赖
4. 提交前运行测试与代码检查

## 📄 许可证

待定

---

**核心文档**：请参考 `docs/需求文档V1.md` 了解项目需求与实现方向（文档包含快速导航，便于快速查阅）。
