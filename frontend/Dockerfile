# 前端 Dockerfile
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    STREAMLIT_SERVER_PORT=8888 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件（如果有）
COPY requirements.txt* ./

# 安装 Python 依赖
RUN if [ -f requirements.txt ]; then \
        pip install --no-cache-dir -r requirements.txt; \
    else \
        pip install --no-cache-dir streamlit plotly numpy httpx; \
    fi

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8888

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import socket; s=socket.socket(); s.settimeout(5); result=s.connect_ex(('localhost', 8888)); s.close(); exit(0 if result==0 else 1)"

# 启动命令
CMD ["streamlit", "run", "app.py", "--server.port=8888", "--server.address=0.0.0.0"]

