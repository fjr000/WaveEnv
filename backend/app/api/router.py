"""
API 路由主文件。

统一管理所有 API 路由。
"""

from fastapi import APIRouter

from app.api import query, simulation

api_router = APIRouter()

# 挂载子路由
api_router.include_router(simulation.router)
api_router.include_router(query.router)  # query 路由，包含查询相关接口


