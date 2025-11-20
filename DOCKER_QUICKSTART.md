# Docker 快速启动指南

## 快速开始

### 1. 配置环境（可选）

```bash
cp .env.example .env
# 编辑 .env 文件
```

### 2. 启动服务

#### 使用启动脚本（推荐）

**Linux/macOS:**
```bash
chmod +x docker-start.sh

# 生产模式，启动所有服务
./docker-start.sh

# 开发模式
./docker-start.sh --dev

# 只启动后端
./docker-start.sh --backend-only
```

**Windows:**
```cmd
REM 生产模式，启动所有服务
docker-start.bat

REM 开发模式
docker-start.bat --dev

REM 只启动后端
docker-start.bat --backend-only
```

#### 直接使用 Docker Compose

```bash
# 启动所有服务（默认启用前端）
docker-compose up -d

# 只启动后端
docker-compose up -d backend

# 开发模式
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# 生产模式（带资源限制）
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 3. 访问服务

- **后端 API**: http://localhost:8000
- **前端界面**: http://localhost:8888
- **API 文档**: http://localhost:8000/docs

### 4. 常用命令

```bash
# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重启服务
docker-compose restart
```

## 环境变量说明

编辑 `.env` 文件可以配置：

- `BACKEND_PORT`: 后端端口（默认: 8000）
- `FRONTEND_PORT`: 前端端口（默认: 8888）
- `FRONTEND_PROFILE`: 是否启用前端（默认: frontend，设置为空则只启动后端）
- `BACKEND_URL`: 前端连接后端地址（默认: http://backend:8000）
- `LOG_LEVEL`: 日志级别（默认: INFO）

## 更多信息

查看 `README.Docker.md` 获取详细文档。

