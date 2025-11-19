"""
FastAPI 应用入口。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例。"""
    app = FastAPI(
        title="WaveEnv Backend",
        version="0.1.0",
        description="时变海浪环境模型后端服务",
    )

    # 配置 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 开发环境允许所有来源，生产环境应限制
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 挂载 API 路由
    app.include_router(api_router, prefix="/api")

    @app.get("/", tags=["root"])
    async def root():
        """根路径。"""
        return {
            "message": "WaveEnv Backend API",
            "version": "0.1.0",
            "docs": "/docs",
        }

    @app.get("/health", tags=["health"])
    async def health():
        """健康检查。"""
        return {"status": "healthy"}

    return app


app = create_app()


