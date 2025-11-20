"""
缓存保留策略测试。
"""

import asyncio
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
async def async_client():
    """异步测试客户端。"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_cache_retention_time(async_client):
    """测试缓存保留时间策略。"""
    request_data = {
        "region": {
            "lon_min": 120.0,
            "lat_min": 35.0,
            "depth_min": 10.0,
            "lon_max": 120.1,
            "lat_max": 35.1,
            "depth_max": 20.0,
        },
        "wind": {
            "wind_speed": 10.0,
            "wind_direction_deg": 270.0,
        },
        "spectrum": {
            "spectrum_model_type": "PM",
            "Hs": 2.0,
            "Tp": 8.0,
        },
        "discretization": {
            "dx": 0.02,
            "dy": 0.02,
            "max_points": 200,
        },
        "time": {
            "dt_backend": 0.1,  # 使用0.1秒的步长，加快测试
            "cache_retention_time": 1.0,  # 只保留最近1秒的帧
        },
    }

    # 创建模拟任务
    response = await async_client.post("/api/simulate/area", json=request_data)
    assert response.status_code == 201
    simulation_id = response.json()["simulation_id"]

    # 等待模拟运行一段时间，产生多个帧
    await asyncio.sleep(2.0)  # 等待2秒，应该产生约20个帧

    # 获取最新帧的时间范围
    frames_response = await async_client.get(f"/api/simulation/{simulation_id}/frames")
    assert frames_response.status_code == 200
    frames_data = frames_response.json()
    assert len(frames_data["frames"]) > 0

    latest_time = frames_data["frames"][-1]["time"]
    
    # 测试1: 查询最新帧（应该在缓存中）
    query_params = {
        "simulation_id": simulation_id,
        "lon": 120.05,
        "lat": 35.05,
        "time": latest_time,
    }
    query_response = await async_client.get("/api/query/point", params=query_params)
    assert query_response.status_code == 200, f"查询最新帧应该成功，但返回: {query_response.text}"

    # 测试2: 查询1秒前的帧（应该已被淘汰）
    old_time = latest_time - 1.5  # 1.5秒前，超出了1秒的保留时间
    query_params_old = {
        "simulation_id": simulation_id,
        "lon": 120.05,
        "lat": 35.05,
        "time": old_time,
    }
    query_response_old = await async_client.get("/api/query/point", params=query_params_old)
    assert query_response_old.status_code == 410, "查询已淘汰的帧应该返回 410 Gone"
    assert "缓存保留范围" in query_response_old.json()["detail"]

    # 测试3: 获取frames时，请求旧的时间范围（应该返回410）
    frames_response_old = await async_client.get(
        f"/api/simulation/{simulation_id}/frames",
        params={"time_min": old_time, "time_max": old_time + 0.1}
    )
    assert frames_response_old.status_code == 410, "获取已淘汰的帧应该返回 410 Gone"

    # 停止任务
    stop_response = await async_client.post(f"/api/simulation/{simulation_id}/stop")
    assert stop_response.status_code == 200


@pytest.mark.anyio
async def test_no_cache_limit(async_client):
    """测试不限制缓存的情况。"""
    request_data = {
        "region": {
            "lon_min": 120.0,
            "lat_min": 35.0,
            "depth_min": 10.0,
            "lon_max": 120.1,
            "lat_max": 35.1,
            "depth_max": 20.0,
        },
        "wind": {
            "wind_speed": 10.0,
            "wind_direction_deg": 270.0,
        },
        "spectrum": {
            "spectrum_model_type": "PM",
            "Hs": 2.0,
            "Tp": 8.0,
        },
        "discretization": {
            "dx": 0.02,
            "dy": 0.02,
            "max_points": 200,
        },
        "time": {
            "dt_backend": 0.1,
            "cache_retention_time": None,  # 不限制缓存
        },
    }

    # 创建模拟任务
    response = await async_client.post("/api/simulate/area", json=request_data)
    assert response.status_code == 201
    simulation_id = response.json()["simulation_id"]

    # 等待模拟运行
    await asyncio.sleep(1.5)

    # 获取所有帧
    frames_response = await async_client.get(f"/api/simulation/{simulation_id}/frames")
    assert frames_response.status_code == 200
    frames_data = frames_response.json()
    assert len(frames_data["frames"]) > 0

    # 查询最早的帧（应该仍然在缓存中，因为不限制）
    first_time = frames_data["frames"][0]["time"]
    query_params = {
        "simulation_id": simulation_id,
        "lon": 120.05,
        "lat": 35.05,
        "time": first_time,
    }
    query_response = await async_client.get("/api/query/point", params=query_params)
    assert query_response.status_code == 200, "不限制缓存时，查询早期帧应该成功"

    # 停止任务
    stop_response = await async_client.post(f"/api/simulation/{simulation_id}/stop")
    assert stop_response.status_code == 200

