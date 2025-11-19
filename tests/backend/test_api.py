"""
API 端点测试。

使用 httpx 测试 FastAPI 端点。
"""

import sys
from pathlib import Path

# 添加 backend 目录到路径
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import pytest
from fastapi.testclient import TestClient

from app.main import app

# 延迟初始化 client，避免在导入时出错
@pytest.fixture
def client():
    return TestClient(app)


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
            "dt_backend": 0.2,
            "T_total": 1.0,
        },
    }

    response = client.post("/api/simulate/area", json=request_data)
    assert response.status_code == 201
    data = response.json()
    return data["simulation_id"]


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
            "dt_backend": 0.2,
            "T_total": 1.0,  # 短时间用于测试
        },
    }

    response = client.post("/api/simulate/area", json=request_data)
    assert response.status_code == 201

    data = response.json()
    assert "simulation_id" in data
    assert "status" in data
    assert data["status"] == "completed"


def test_get_simulation_frames(client, simulation_id):
    """测试获取模拟结果。"""

    # 获取结果
    response = client.get(f"/api/simulation/{simulation_id}/frames")
    assert response.status_code == 200

    data = response.json()
    assert "simulation_id" in data
    assert "status" in data
    assert "frames" in data
    assert len(data["frames"]) > 0

    # 检查第一帧
    frame = data["frames"][0]
    assert "time" in frame
    assert "region" in frame
    assert "points" in frame
    assert len(frame["points"]) > 0


def test_query_point(client, simulation_id):
    """测试单点查询。"""

    # 查询点
    request_data = {
        "simulation_id": simulation_id,
        "lon": 120.05,
        "lat": 35.05,
        "time": 0.5,
    }

    response = client.post("/api/query/point", json=request_data)
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
    response = client.get("/api/simulation/invalid-id/frames")
    assert response.status_code == 404


def test_invalid_query(client):
    """测试无效的查询请求。"""
    request_data = {
        "simulation_id": "invalid-id",
        "lon": 120.05,
        "lat": 35.05,
        "time": 0.5,
    }

    response = client.post("/api/query/point", json=request_data)
    assert response.status_code == 404

