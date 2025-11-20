# Docker 部署说明

本项目支持使用 Docker 容器化部署，包含前端（Streamlit）和后端（FastAPI）两个服务。

## 目录结构

```
.
├── docker-compose.yml              # 主配置文件
├── docker-compose.dev.yml          # 开发环境配置
├── docker-compose.prod.yml         # 生产环境配置
├── .env.example                    # 环境变量模板
├── .dockerignore                   # Docker 忽略文件
├── docker-start.sh                 # Linux/macOS 启动脚本
├── docker-start.bat                # Windows 启动脚本
├── backend/
│   ├── Dockerfile                  # 后端 Dockerfile
│   └── .dockerignore               # 后端忽略文件
└── frontend/
    ├── Dockerfile                  # 前端 Dockerfile
    └── .dockerignore               # 前端忽略文件
```

## 快速开始

### 1. 配置环境变量（可选）

```bash
# 复制环境变量模板
cp .env.example .env

# 根据需要修改 .env 文件中的配置
```

**关键配置项**：
- `BACKEND_PORT`: 后端服务端口（默认: 8000）
- `FRONTEND_PORT`: 前端服务端口（默认: 8888）
- `FRONTEND_PROFILE`: 是否启用前端（默认: frontend，设置为空则只启动后端）
- `BACKEND_URL`: 前端连接后端地址（Docker 环境: http://backend:8000）

### 2. 使用启动脚本（推荐）

#### Linux/macOS

```bash
# 给脚本添加执行权限
chmod +x docker-start.sh

# 生产模式，启动所有服务
./docker-start.sh

# 开发模式，启动所有服务（支持热重载）
./docker-start.sh --dev

# 只启动后端服务
./docker-start.sh --backend-only

# 开发模式，只启动后端
./docker-start.sh --dev --backend-only

# 查看帮助
./docker-start.sh --help
```

#### Windows

```cmd
REM 生产模式，启动所有服务
docker-start.bat

REM 开发模式，启动所有服务
docker-start.bat --dev

REM 只启动后端服务
docker-start.bat --backend-only

REM 查看帮助
docker-start.bat --help
```

### 3. 直接使用 Docker Compose

```bash
# 生产模式：启动所有服务
docker-compose up -d

# 开发模式：启动所有服务（挂载代码目录，支持热重载）
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# 生产模式（带资源限制）
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 只启动后端服务
docker-compose up -d backend

# 启动后端 + 前端（使用 profile）
docker-compose --profile frontend up -d

# 禁用前端（如果 .env 中设置了 FRONTEND_PROFILE=""）
docker-compose up -d backend
```

## 访问服务

启动成功后，可以通过以下地址访问：

- **后端 API**: http://localhost:8000
- **前端界面**: http://localhost:8888（如果启用）
- **API 文档**: http://localhost:8000/docs

## 环境变量配置

所有配置通过 `.env` 文件管理（参考 `.env.example`）。

### 服务控制

- `FRONTEND_PROFILE`: 是否启用前端服务
  - 设置为 `frontend`（默认）：启用前端服务
  - 设置为空字符串 `""`：只启动后端服务

### 端口配置

- `BACKEND_PORT`: 后端服务端口（默认: `8000`）
- `FRONTEND_PORT`: 前端服务端口（默认: `8888`）

### 前端配置

- `BACKEND_URL`: 后端服务地址
  - Docker 环境：`http://backend:8000`（使用服务名）
  - 外部访问：`http://localhost:8000`

### 后端配置

- `LOG_LEVEL`: 日志级别（DEBUG, INFO, WARNING, ERROR，默认: INFO）
- `PYTHONUNBUFFERED`: 设置为 `1` 以实时查看日志（默认已设置）

## 部署模式

### 生产模式（默认）

```bash
# 使用默认配置
docker-compose up -d

# 或使用生产配置（包含资源限制）
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

**特点**：
- 不挂载代码目录，使用镜像内代码
- 包含资源限制（CPU、内存）
- 优化性能配置

### 开发模式

```bash
# 使用开发配置（挂载代码目录，支持热重载）
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# 或使用启动脚本
./docker-start.sh --dev
```

**特点**：
- 挂载代码目录，修改代码后自动重载
- 启用调试日志
- 后端支持 `--reload` 自动重载
- 前端支持文件监听

### 自定义配置

可以通过 `docker-compose.override.yml` 添加自定义配置（不会被 Git 跟踪）：

```bash
# 复制示例文件
cp docker-compose.override.yml.example docker-compose.override.yml

# 编辑配置，docker-compose 会自动读取
```

## 常用命令

### 查看服务状态

```bash
# 查看所有服务状态
docker-compose ps

# 查看服务详细信息
docker-compose ps -a
```

### 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend

# 查看最近 100 行日志
docker-compose logs --tail=100 -f
```

### 服务控制

```bash
# 停止所有服务
docker-compose down

# 停止并删除卷（谨慎使用）
docker-compose down -v

# 重启服务
docker-compose restart

# 重启特定服务
docker-compose restart backend
docker-compose restart frontend
```

### 进入容器

```bash
# 进入后端容器
docker exec -it waveenv-backend bash

# 进入前端容器
docker exec -it waveenv-frontend bash
```

### 重新构建

```bash
# 重新构建所有镜像
docker-compose build --no-cache

# 重新构建特定服务
docker-compose build --no-cache backend

# 构建并启动
docker-compose up -d --build
```

## 健康检查

两个服务都配置了健康检查：

- **后端**: 每30秒检查 `/health` 端点
- **前端**: 每30秒检查端口是否可访问

查看健康状态：
```bash
# 查看容器健康状态
docker inspect waveenv-backend | grep -A 10 Health
docker inspect waveenv-frontend | grep -A 10 Health
```

## 故障排查

### 查看容器日志

```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs backend
docker-compose logs frontend

# 实时查看日志
docker-compose logs -f backend
```

### 常见问题

1. **端口已被占用**
   - 修改 `.env` 文件中的 `BACKEND_PORT` 或 `FRONTEND_PORT`
   - 或停止占用端口的进程

2. **前端无法连接后端**
   - 检查 `BACKEND_URL` 环境变量是否正确
   - Docker 环境应使用服务名：`http://backend:8000`
   - 确保后端服务已启动并健康

3. **容器启动失败**
   - 查看日志：`docker-compose logs <service-name>`
   - 检查镜像是否构建成功：`docker images`
   - 检查依赖是否正确安装

4. **代码修改不生效（开发模式）**
   - 确保使用了 `docker-compose.dev.yml` 配置
   - 检查 volumes 挂载是否正确
   - 重启容器：`docker-compose restart`

5. **服务无法访问**
   - 检查端口映射是否正确
   - 检查防火墙设置
   - 检查容器是否正常运行：`docker-compose ps`

### 清理资源

```bash
# 停止并删除容器
docker-compose down

# 删除镜像
docker rmi waveenv-backend waveenv-frontend

# 清理未使用的资源
docker system prune -a
```

## 生产部署建议

1. **环境变量**：使用 `.env` 文件管理配置，不要提交到 Git
2. **资源限制**：使用 `docker-compose.prod.yml` 配置资源限制
3. **反向代理**：使用 Nginx 作为反向代理，配置 HTTPS
4. **日志收集**：配置日志收集系统（如 ELK、Loki）
5. **监控告警**：配置监控系统（如 Prometheus + Grafana）
6. **数据持久化**：如有数据需要持久化，配置 volumes
7. **备份策略**：制定容器和数据的备份策略
8. **安全扫描**：定期扫描镜像安全漏洞

## 示例：完整部署流程

```bash
# 1. 克隆项目
git clone <repository-url>
cd WaveEnv

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，根据需要修改配置

# 3. 启动服务（生产模式）
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 4. 检查服务状态
docker-compose ps

# 5. 查看日志
docker-compose logs -f

# 6. 访问服务
# - 前端: http://localhost:8888
# - 后端 API: http://localhost:8000
# - API 文档: http://localhost:8000/docs
```
