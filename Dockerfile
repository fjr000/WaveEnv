# 根目录 Dockerfile - 构建多阶段镜像
# 此 Dockerfile 主要用于参考，实际部署建议使用 docker-compose.yml

# 使用华为云镜像源代理的 Python 官方镜像
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.8-slim as base

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# ========== 后端构建阶段 ==========
FROM base as backend-build

WORKDIR /app/backend

# 复制后端依赖文件
COPY backend/pyproject.toml ./
COPY backend/requirements.txt* ./

# 安装后端依赖
RUN if [ -f requirements.txt ]; then \
        pip install --no-cache-dir -r requirements.txt; \
    else \
        pip install --no-cache-dir fastapi uvicorn[standard] pydantic pydantic-settings "numpy>=1.21.0,<1.24.0" httpx; \
    fi

# 复制后端代码
COPY backend/ .

# ========== 前端构建阶段 ==========
FROM base as frontend-build

WORKDIR /app/frontend

# 复制前端依赖文件
COPY frontend/requirements.txt* ./

# 安装前端依赖
RUN if [ -f requirements.txt ]; then \
        pip install --no-cache-dir -r requirements.txt; \
    else \
        pip install --no-cache-dir streamlit plotly numpy httpx; \
    fi

# 复制前端代码
COPY frontend/ .

# ========== 最终阶段（运行时） ==========
# 注意：此 Dockerfile 主要用于参考，实际推荐使用 docker-compose.yml 分别运行服务

FROM base as runtime

# 默认只运行后端，前端通过 docker-compose 单独运行
COPY --from=backend-build /app/backend /app/backend

WORKDIR /app/backend

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

