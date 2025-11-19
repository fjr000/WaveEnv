"""
FastAPI 应用入口（结构占位）。

当前仅声明应用与路由挂载位置，不实现具体业务逻辑。
"""

from fastapi import FastAPI


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例。"""
    app = FastAPI(title="WaveEnv Backend", version="0.1.0")

    # TODO: 在此处挂载路由模块，例如：
    # from app.api import router as api_router
    # app.include_router(api_router, prefix="/api")

    return app


app = create_app()


