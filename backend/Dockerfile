# 后端 Dockerfile
# 使用华为云镜像源代理的 Python 官方镜像
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.8-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 配置 apt 使用阿里云镜像源（Debian）
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's@http://deb.debian.org@http://mirrors.aliyun.com@g' /etc/apt/sources.list 2>/dev/null || \
    echo "deb http://mirrors.aliyun.com/debian/ bookworm main" > /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian/ bookworm-updates main" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian-security/ bookworm-security main" >> /etc/apt/sources.list

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 配置 pip 使用清华大学镜像源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn

# 复制依赖文件（构建上下文是项目根目录，需要包含 backend/ 前缀）
COPY backend/pyproject.toml ./
COPY backend/requirements.txt* ./

# 安装 Python 依赖（使用国内镜像源）
RUN if [ -f requirements.txt ]; then \
        pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn; \
    else \
        pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn \
            fastapi uvicorn[standard] pydantic "numpy>=1.21.0,<1.24.0"; \
    fi

# 复制应用代码（构建上下文是项目根目录，需要复制 backend 目录）
COPY backend/ .

# 暴露端口
EXPOSE 8000

# 健康检查（使用curl作为fallback，因为httpx可能未安装）
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=5).read()" || exit 1

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

