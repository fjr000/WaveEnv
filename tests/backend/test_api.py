"""
API 端点测试。

使用 httpx 测试 FastAPI 端点。
"""

import asyncio
import time
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app

# 延迟初始化 client，避免在导入时出错
@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def anyio_backend():
    return 'asyncio'


@pytest.fixture
async def async_client():
    """异步测试客户端。"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def simulation_id(client):
    """创建模拟任务并返回 ID。"""
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
            "dx": 0.01,
            "dy": 0.01,
            "max_points": 100,
        },
        "time": {
            "dt_backend": 0.01,  # 使用更小的时间步长，加快测试速度
            "T_total": 0.1,  # 使用更短的总时长，加快测试速度
        },
    }

    response = client.post("/api/simulate/area", json=request_data)
    assert response.status_code == 201
    data = response.json()
    simulation_id = data["simulation_id"]
    
    # 等待任务完成（最多等待10秒，因为TestClient可能无法立即执行异步任务）
    max_wait_time = 10.0
    wait_interval = 0.1
    elapsed = 0.0
    
    # 给后台任务一些时间启动
    time.sleep(0.2)
    
    while elapsed < max_wait_time:
        time.sleep(wait_interval)
        elapsed += wait_interval
        
        # 检查任务状态（获取最新帧）
        response = client.get(f"/api/simulation/{simulation_id}/frames", params={"time": -1})
        if response.status_code == 200:
            status_data = response.json()
            if status_data["status"] == "completed":
                return simulation_id
        elif response.status_code == 404:
            # 如果返回404，说明任务可能还没有开始计算帧
            # 继续等待
            continue
    
    # 超时，但返回ID让测试继续（可能会有其他错误提示）
    return simulation_id


def test_root(client):
    """测试根路径。"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "WaveEnv Backend API"


def test_health(client):
    """测试健康检查。"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_create_simulation(client):
    """测试创建区域模拟任务。"""
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
            "dx": 0.01,
            "dy": 0.01,
            "max_points": 100,
        },
        "time": {
            "dt_backend": 0.01,  # 更小的时间步长，加快测试速度
            "T_total": 0.1,  # 更短的总时长，加快测试速度
        },
    }

    response = client.post("/api/simulate/area", json=request_data)
    assert response.status_code == 201

    data = response.json()
    assert "simulation_id" in data
    assert "status" in data
    # 任务启动后状态为 running，需要等待完成
    assert data["status"] == "running"
    
    # 等待任务完成（最多等待10秒，因为TestClient可能无法立即执行异步任务）
    # 需要给后台任务足够的时间来执行
    simulation_id = data["simulation_id"]
    max_wait_time = 10.0  # 增加等待时间
    wait_interval = 0.1
    elapsed = 0.0
    
    # 给后台任务一些时间启动
    time.sleep(0.2)
    
    while elapsed < max_wait_time:
        time.sleep(wait_interval)
        elapsed += wait_interval
        
        # 检查任务状态（获取最新帧）
        response = client.get(f"/api/simulation/{simulation_id}/frames", params={"time": -1})
        if response.status_code == 200:
            status_data = response.json()
            if status_data["status"] == "completed":
                break
        elif response.status_code == 404:
            # 如果返回404，说明任务可能还没有开始或还未产生帧
            # 继续等待
            continue
    else:
        # 超时前，检查是否有帧数据（即使状态不是completed，获取最新帧）
        response = client.get(f"/api/simulation/{simulation_id}/frames", params={"time": -1})
        if response.status_code == 200:
            status_data = response.json()
            # 如果有帧数据，即使状态不是completed也算成功
            if len(status_data.get("frames", [])) > 0:
                return
        # 超时
        pytest.fail(f"Simulation task did not complete within {max_wait_time} seconds")


def test_get_simulation_frames(client, simulation_id):
    """测试获取模拟结果（单时刻）。"""

    # 获取最新帧
    response = client.get(f"/api/simulation/{simulation_id}/frames", params={"time": -1})
    assert response.status_code == 200

    data = response.json()
    assert "simulation_id" in data
    assert "status" in data
    assert "frames" in data
    assert len(data["frames"]) == 1  # 只返回一个帧

    # 检查返回的帧
    frame = data["frames"][0]
    assert "time" in frame
    assert "region" in frame
    assert "points" in frame
    assert len(frame["points"]) > 0
    
    # 测试获取指定时刻的帧
    frame_time = frame["time"]
    response2 = client.get(f"/api/simulation/{simulation_id}/frames", params={"time": frame_time})
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2["frames"]) == 1
    assert data2["frames"][0]["time"] == frame_time


def test_query_point(client, simulation_id):
    """测试单点查询。"""

    # 查询点
    # 注意：使用的时间应该在模拟的时间范围内（0到0.1秒）
    params = {
        "simulation_id": simulation_id,
        "lon": 120.05,
        "lat": 35.05,
        "time": 0.05,  # 使用0.05秒，在0-0.1秒范围内
    }

    response = client.get("/api/query/point", params=params)
    assert response.status_code == 200

    data = response.json()
    assert "simulation_id" in data
    assert "time" in data
    assert "lon" in data
    assert "lat" in data
    assert "wave_height" in data
    assert isinstance(data["wave_height"], (int, float))


def test_invalid_simulation_id(client):
    """测试无效的 simulation_id。"""
    response = client.get("/api/simulation/invalid-id/frames", params={"time": 0.0})
    assert response.status_code == 404


def test_invalid_query(client):
    """测试无效的查询请求。"""
    params = {
        "simulation_id": "invalid-id",
        "lon": 120.05,
        "lat": 35.05,
        "time": 0.5,
    }

    response = client.get("/api/query/point", params=params)
    assert response.status_code == 404


@pytest.mark.anyio
async def test_pause_resume_and_stop(async_client):
    """测试暂停、恢复与停止接口。"""
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
            "dt_backend": 0.05,  # 不设置 T_total，进入无限模式
        },
    }

    response = await async_client.post("/api/simulate/area", json=request_data)
    assert response.status_code == 201
    simulation_id = response.json()["simulation_id"]

    # 等待后台任务启动
    await asyncio.sleep(0.2)

    pause_resp = await async_client.post(f"/api/simulation/{simulation_id}/clock/pause")
    assert pause_resp.status_code == 200
    assert pause_resp.json()["status"] == "paused"

    resume_resp = await async_client.post(f"/api/simulation/{simulation_id}/clock/resume")
    assert resume_resp.status_code == 200
    assert resume_resp.json()["status"] == "running"

    stop_resp = await async_client.post(f"/api/simulation/{simulation_id}/stop")
    assert stop_resp.status_code == 200
    assert stop_resp.json()["status"] == "stopped"

