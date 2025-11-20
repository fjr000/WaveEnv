"""
FastAPI 应用入口。
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.api.simulation import _cleanup_task_resources
from app.core.storage import task_storage
from app.schemas.data import SimulationStatus

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理器。
    
    处理应用启动和关闭事件。
    """
    # 启动时的逻辑（如果需要）
    logger.info("Starting backend server...")
    
    yield
    
    # 关闭时的逻辑
    logger.info("Shutting down backend server...")
    
    # 获取所有任务
    all_tasks = task_storage.list_tasks()
    
    # 停止所有运行中的任务
    running_tasks = [
        task for task in all_tasks 
        if task.status in (SimulationStatus.RUNNING, SimulationStatus.PENDING)
    ]
    
    if running_tasks:
        logger.info(f"Stopping {len(running_tasks)} running simulation tasks...")
        for task in running_tasks:
            try:
                # 标记任务为停止请求
                task.stop_requested = True
                task_storage.update_task(task)
                # 立即清理资源，释放内存
                _cleanup_task_resources(task)
                logger.info(f"Stopped and cleaned up simulation task: {task.simulation_id[:8]}...")
            except Exception as e:
                logger.error(f"Error stopping task {task.simulation_id}: {e}")
        
        # 等待一小段时间，让任务循环有机会退出
        await asyncio.sleep(0.5)
    
    logger.info("Backend server shutdown complete.")


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用实例。"""
    app = FastAPI(
        title="WaveEnv Backend",
        version="0.1.0",
        description="时变海浪环境模型后端服务",
        lifespan=lifespan,
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


