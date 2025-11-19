"""
手动测试脚本。

用于快速测试API功能，不依赖pytest。
"""

import json
import sys
from pathlib import Path

# 添加backend到路径
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import requests

BASE_URL = "http://127.0.0.1:8000"


def test_root():
    """测试根路径。"""
    print("测试根路径...")
    response = requests.get(f"{BASE_URL}/")
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    print()


def test_health():
    """测试健康检查。"""
    print("测试健康检查...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    print()


def test_create_simulation():
    """测试创建区域模拟任务。"""
    print("测试创建区域模拟任务...")
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

    response = requests.post(
        f"{BASE_URL}/api/simulate/area", json=request_data
    )
    print(f"状态码: {response.status_code}")
    if response.status_code == 201:
        data = response.json()
        print(f"模拟ID: {data['simulation_id']}")
        print(f"状态: {data['status']}")
        print()
        # 存储到模块变量，供其他测试使用
        test_create_simulation.simulation_id = data["simulation_id"]
    else:
        print(f"错误: {response.text}")
        print()
        test_create_simulation.simulation_id = None


def test_get_frames():
    """测试获取模拟结果。"""
    # 如果没有 simulation_id，先创建一个
    if not hasattr(test_create_simulation, 'simulation_id') or test_create_simulation.simulation_id is None:
        test_create_simulation()
    
    simulation_id = test_create_simulation.simulation_id
    if simulation_id is None:
        print("无法获取 simulation_id，跳过测试")
        return
    
    print(f"测试获取模拟结果 (ID: {simulation_id})...")
    response = requests.get(f"{BASE_URL}/api/simulation/{simulation_id}/frames")
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"状态: {data['status']}")
        print(f"帧数: {len(data['frames'])}")
        if len(data["frames"]) > 0:
            frame = data["frames"][0]
            print(f"第一帧时间: {frame['time']}")
            print(f"第一帧点数: {len(frame['points'])}")
            if len(frame["points"]) > 0:
                point = frame["points"][0]
                print(f"示例点: lon={point['lon']}, lat={point['lat']}, height={point['wave_height']:.4f}")
    else:
        print(f"错误: {response.text}")
    print()


def test_query_point():
    """测试单点查询。"""
    # 如果没有 simulation_id，先创建一个
    if not hasattr(test_create_simulation, 'simulation_id') or test_create_simulation.simulation_id is None:
        test_create_simulation()
    
    simulation_id = test_create_simulation.simulation_id
    if simulation_id is None:
        print("无法获取 simulation_id，跳过测试")
        return
    
    print(f"测试单点查询 (ID: {simulation_id})...")
    request_data = {
        "simulation_id": simulation_id,
        "lon": 120.05,
        "lat": 35.05,
        "time": 0.5,
    }

    response = requests.post(f"{BASE_URL}/api/query/point", json=request_data)
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"查询结果:")
        print(f"  位置: ({data['lon']}, {data['lat']})")
        print(f"  时间: {data['time']}s")
        print(f"  海浪高度: {data['wave_height']:.4f}m")
    else:
        print(f"错误: {response.text}")
    print()


if __name__ == "__main__":
    print("=" * 60)
    print("开始手动测试 API")
    print("=" * 60)
    print()

    try:
        # 测试基础端点
        test_root()
        test_health()

        # 测试模拟功能
        test_create_simulation()
        if hasattr(test_create_simulation, 'simulation_id') and test_create_simulation.simulation_id:
            test_get_frames()
            test_query_point()

        print("=" * 60)
        print("测试完成！")
        print("=" * 60)

    except requests.exceptions.ConnectionError:
        print("错误: 无法连接到服务器")
        print("请确保服务已启动: uvicorn app.main:app --reload")
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


