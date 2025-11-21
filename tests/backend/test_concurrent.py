"""
并发测试：多个模拟任务同时启动，测试各个接口的并发性能和响应时间。
"""

import asyncio
import time
from typing import List, Tuple

import pytest
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


async def create_simulation_task(
    client: AsyncClient,
    task_index: int,
    dt_backend: float = 0.1,
    cache_retention_time: float = None,
) -> Tuple[str, float]:
    """
    创建单个模拟任务，返回 (simulation_id, 响应时间)。

    Args:
        client: 异步客户端
        task_index: 任务索引（用于区分）
        dt_backend: 时间步长
        cache_retention_time: 缓存保留时间

    Returns:
        (simulation_id, 响应时间秒)
    """
    request_data = {
        "region": {
            "lon_min": 120.0 + task_index * 0.1,  # 每个任务使用不同的区域
            "lat_min": 35.0 + task_index * 0.1,
            "depth_min": 10.0,
            "lon_max": 120.1 + task_index * 0.1,
            "lat_max": 35.1 + task_index * 0.1,
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
            "dt_backend": dt_backend,
            "cache_retention_time": cache_retention_time,
        },
    }

    start_time = time.time()
    response = await client.post("/api/simulate/area", json=request_data)
    elapsed = time.time() - start_time

    assert response.status_code == 201, f"创建任务 {task_index} 失败: {response.text}"
    data = response.json()
    assert "simulation_id" in data
    assert data["status"] == "running"

    return data["simulation_id"], elapsed


@pytest.mark.anyio
async def test_concurrent_task_creation(async_client):
    """测试并发创建多个模拟任务。"""
    num_tasks = 5

    # 并发创建多个任务
    start_time = time.time()
    tasks = await asyncio.gather(
        *[create_simulation_task(async_client, i) for i in range(num_tasks)]
    )
    total_time = time.time() - start_time

    simulation_ids = [task[0] for task in tasks]
    response_times = [task[1] for task in tasks]

    print(f"\n并发创建 {num_tasks} 个任务:")
    print(f"  总耗时: {total_time:.3f} 秒")
    print(f"  平均响应时间: {sum(response_times) / len(response_times):.3f} 秒")
    print(f"  最大响应时间: {max(response_times):.3f} 秒")
    print(f"  最小响应时间: {min(response_times):.3f} 秒")

    # 验证所有任务都已创建
    assert len(simulation_ids) == num_tasks
    assert len(set(simulation_ids)) == num_tasks, "所有任务 ID 应该唯一"

    # 等待任务运行一段时间
    await asyncio.sleep(1.0)

    # 清理：停止所有任务
    stop_tasks = await asyncio.gather(
        *[async_client.post(f"/api/simulation/{sid}/stop") for sid in simulation_ids],
        return_exceptions=True
    )
    for i, result in enumerate(stop_tasks):
        if isinstance(result, Exception):
            print(f"停止任务 {i} 时出错: {result}")


@pytest.mark.anyio
async def test_concurrent_query_frames(async_client):
    """测试并发查询多个任务的帧数据。"""
    # 先创建多个任务
    num_tasks = 3
    create_tasks = await asyncio.gather(
        *[create_simulation_task(async_client, i) for i in range(num_tasks)]
    )
    simulation_ids = [task[0] for task in create_tasks]

    # 等待任务运行一段时间
    await asyncio.sleep(1.5)

    # 并发查询所有任务的帧数据（获取最新帧）
    async def query_frames(sid: str) -> Tuple[str, float, bool]:
        start_time = time.time()
        try:
            response = await async_client.get(f"/api/simulation/{sid}/frames", params={"time": -1})
            elapsed = time.time() - start_time
            success = response.status_code == 200
            return sid, elapsed, success
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"查询任务 {sid} 失败: {e}")
            return sid, elapsed, False

    start_time = time.time()
    query_results = await asyncio.gather(
        *[query_frames(sid) for sid in simulation_ids]
    )
    total_time = time.time() - start_time

    response_times = [r[1] for r in query_results]
    success_count = sum(1 for r in query_results if r[2])

    print(f"\n并发查询 {num_tasks} 个任务的帧数据:")
    print(f"  总耗时: {total_time:.3f} 秒")
    print(f"  平均响应时间: {sum(response_times) / len(response_times):.3f} 秒")
    print(f"  最大响应时间: {max(response_times):.3f} 秒")
    print(f"  成功率: {success_count}/{num_tasks}")

    assert success_count == num_tasks, "所有查询应该成功"

    # 清理
    await asyncio.gather(
        *[async_client.post(f"/api/simulation/{sid}/stop") for sid in simulation_ids],
        return_exceptions=True
    )


@pytest.mark.anyio
async def test_concurrent_point_query(async_client):
    """测试并发查询多个任务的单点数据。"""
    # 先创建多个任务
    num_tasks = 4
    create_tasks = await asyncio.gather(
        *[create_simulation_task(async_client, i) for i in range(num_tasks)]
    )
    simulation_ids = [task[0] for task in create_tasks]

    # 等待任务运行一段时间
    await asyncio.sleep(1.5)

    # 并发查询所有任务的单点数据
    async def query_point(sid: str, query_index: int) -> Tuple[str, float, bool]:
        start_time = time.time()
        try:
            params = {
                "simulation_id": sid,
                "lon": 120.05 + query_index * 0.01,
                "lat": 35.05 + query_index * 0.01,
                "time": -1,  # 使用最新帧
            }
            response = await async_client.get("/api/query/point", params=params)
            elapsed = time.time() - start_time
            success = response.status_code == 200
            return sid, elapsed, success
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"查询任务 {sid} 单点失败: {e}")
            return sid, elapsed, False

    start_time = time.time()
    query_results = await asyncio.gather(
        *[query_point(sid, i) for i, sid in enumerate(simulation_ids)]
    )
    total_time = time.time() - start_time

    response_times = [r[1] for r in query_results]
    success_count = sum(1 for r in query_results if r[2])

    print(f"\n并发查询 {num_tasks} 个任务的单点数据:")
    print(f"  总耗时: {total_time:.3f} 秒")
    print(f"  平均响应时间: {sum(response_times) / len(response_times):.3f} 秒")
    print(f"  最大响应时间: {max(response_times):.3f} 秒")
    print(f"  成功率: {success_count}/{num_tasks}")

    assert success_count == num_tasks, "所有查询应该成功"

    # 清理
    await asyncio.gather(
        *[async_client.post(f"/api/simulation/{sid}/stop") for sid in simulation_ids],
        return_exceptions=True
    )


@pytest.mark.anyio
async def test_concurrent_control_operations(async_client):
    """测试并发控制操作（暂停/恢复/停止）。"""
    # 先创建多个任务
    num_tasks = 3
    create_tasks = await asyncio.gather(
        *[create_simulation_task(async_client, i) for i in range(num_tasks)]
    )
    simulation_ids = [task[0] for task in create_tasks]

    # 等待任务运行一段时间
    await asyncio.sleep(0.5)

    # 并发暂停所有任务
    async def pause_task(sid: str) -> Tuple[str, str, float, bool]:
        start_time = time.time()
        try:
            response = await async_client.post(f"/api/simulation/{sid}/clock/pause")
            elapsed = time.time() - start_time
            success = response.status_code == 200
            status = response.json().get("status", "unknown") if success else "error"
            return sid, status, elapsed, success
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"暂停任务 {sid} 失败: {e}")
            return sid, "error", elapsed, False

    start_time = time.time()
    pause_results = await asyncio.gather(
        *[pause_task(sid) for sid in simulation_ids]
    )
    pause_time = time.time() - start_time

    response_times = [r[2] for r in pause_results]
    success_count = sum(1 for r in pause_results if r[3])

    print(f"\n并发暂停 {num_tasks} 个任务:")
    print(f"  总耗时: {pause_time:.3f} 秒")
    print(f"  平均响应时间: {sum(response_times) / len(response_times):.3f} 秒")
    print(f"  成功率: {success_count}/{num_tasks}")

    assert success_count == num_tasks, "所有暂停操作应该成功"

    await asyncio.sleep(0.2)

    # 并发恢复所有任务
    async def resume_task(sid: str) -> Tuple[str, str, float, bool]:
        start_time = time.time()
        try:
            response = await async_client.post(f"/api/simulation/{sid}/clock/resume")
            elapsed = time.time() - start_time
            success = response.status_code == 200
            status = response.json().get("status", "unknown") if success else "error"
            return sid, status, elapsed, success
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"恢复任务 {sid} 失败: {e}")
            return sid, "error", elapsed, False

    start_time = time.time()
    resume_results = await asyncio.gather(
        *[resume_task(sid) for sid in simulation_ids]
    )
    resume_time = time.time() - start_time

    response_times = [r[2] for r in resume_results]
    success_count = sum(1 for r in resume_results if r[3])

    print(f"\n并发恢复 {num_tasks} 个任务:")
    print(f"  总耗时: {resume_time:.3f} 秒")
    print(f"  平均响应时间: {sum(response_times) / len(response_times):.3f} 秒")
    print(f"  成功率: {success_count}/{num_tasks}")

    assert success_count == num_tasks, "所有恢复操作应该成功"

    await asyncio.sleep(0.2)

    # 并发停止所有任务
    async def stop_task(sid: str) -> Tuple[str, str, float, bool]:
        start_time = time.time()
        try:
            response = await async_client.post(f"/api/simulation/{sid}/stop")
            elapsed = time.time() - start_time
            success = response.status_code == 200
            status = response.json().get("status", "unknown") if success else "error"
            return sid, status, elapsed, success
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"停止任务 {sid} 失败: {e}")
            return sid, "error", elapsed, False

    start_time = time.time()
    stop_results = await asyncio.gather(
        *[stop_task(sid) for sid in simulation_ids]
    )
    stop_time = time.time() - start_time

    response_times = [r[2] for r in stop_results]
    success_count = sum(1 for r in stop_results if r[3])

    print(f"\n并发停止 {num_tasks} 个任务:")
    print(f"  总耗时: {stop_time:.3f} 秒")
    print(f"  平均响应时间: {sum(response_times) / len(response_times):.3f} 秒")
    print(f"  成功率: {success_count}/{num_tasks}")

    assert success_count == num_tasks, "所有停止操作应该成功"


@pytest.mark.anyio
async def test_mixed_concurrent_operations(async_client):
    """测试混合并发操作：创建、查询、控制同时进行。"""
    # 第一阶段：并发创建多个任务
    num_tasks = 3
    print(f"\n=== 混合并发测试：{num_tasks} 个任务 ===")

    create_tasks = await asyncio.gather(
        *[create_simulation_task(async_client, i) for i in range(num_tasks)]
    )
    simulation_ids = [task[0] for task in create_tasks]
    print(f"创建了 {len(simulation_ids)} 个任务")

    await asyncio.sleep(1.0)

    # 第二阶段：同时进行多种操作
    async def query_operation(sid: str) -> Tuple[str, str, float]:
        start = time.time()
        response = await async_client.get(f"/api/simulation/{sid}/frames", params={"time": -1})
        return sid, "query_frames", time.time() - start

    async def point_operation(sid: str) -> Tuple[str, str, float]:
        start = time.time()
        params = {"simulation_id": sid, "lon": 120.05, "lat": 35.05, "time": -1}
        await async_client.get("/api/query/point", params=params)
        return sid, "query_point", time.time() - start

    async def pause_operation(sid: str) -> Tuple[str, str, float]:
        start = time.time()
        await async_client.post(f"/api/simulation/{sid}/clock/pause")
        return sid, "pause", time.time() - start

    # 为每个任务创建多种操作
    operations = []
    for sid in simulation_ids:
        operations.append(query_operation(sid))
        operations.append(point_operation(sid))
        operations.append(pause_operation(sid))

    start_time = time.time()
    results = await asyncio.gather(*operations)
    total_time = time.time() - start_time

    # 按操作类型统计
    operation_stats = {}
    for sid, op_type, elapsed in results:
        if op_type not in operation_stats:
            operation_stats[op_type] = []
        operation_stats[op_type].append(elapsed)

    print(f"\n混合并发操作结果:")
    print(f"  总操作数: {len(results)}")
    print(f"  总耗时: {total_time:.3f} 秒")
    for op_type, times in operation_stats.items():
        print(f"  {op_type}:")
        print(f"    平均响应时间: {sum(times) / len(times):.3f} 秒")
        print(f"    最大响应时间: {max(times):.3f} 秒")
        print(f"    最小响应时间: {min(times):.3f} 秒")

    # 清理
    await asyncio.gather(
        *[async_client.post(f"/api/simulation/{sid}/stop") for sid in simulation_ids],
        return_exceptions=True
    )


@pytest.mark.anyio
async def test_large_scale_concurrent(async_client):
    """大规模并发测试：创建更多任务并测试性能。"""
    num_tasks = 10
    print(f"\n=== 大规模并发测试：{num_tasks} 个任务 ===")

    # 并发创建
    start_time = time.time()
    create_tasks = await asyncio.gather(
        *[create_simulation_task(async_client, i, dt_backend=0.2) for i in range(num_tasks)],
        return_exceptions=True
    )
    create_time = time.time() - start_time

    # 过滤出成功创建的任务
    simulation_ids = []
    for i, task in enumerate(create_tasks):
        if isinstance(task, Exception):
            print(f"任务 {i} 创建失败: {task}")
        else:
            simulation_ids.append(task[0])

    success_count = len(simulation_ids)
    print(f"创建结果: {success_count}/{num_tasks} 成功，耗时 {create_time:.3f} 秒")

    assert success_count > 0, "至少应该成功创建一些任务"

    # 等待任务运行
    await asyncio.sleep(1.0)

    # 并发查询所有任务（获取最新帧）
    async def query_all(sid: str) -> Tuple[str, float]:
        start = time.time()
        await async_client.get(f"/api/simulation/{sid}/frames", params={"time": -1})
        return sid, time.time() - start

    start_time = time.time()
    query_results = await asyncio.gather(
        *[query_all(sid) for sid in simulation_ids],
        return_exceptions=True
    )
    query_time = time.time() - start_time

    # 统计查询结果
    query_times = [r[1] for r in query_results if not isinstance(r, Exception)]
    query_success = sum(1 for r in query_results if not isinstance(r, Exception))

    print(f"查询结果: {query_success}/{success_count} 成功，总耗时 {query_time:.3f} 秒")
    if query_times:
        print(f"  平均响应时间: {sum(query_times) / len(query_times):.3f} 秒")
        print(f"  最大响应时间: {max(query_times):.3f} 秒")

    # 清理
    await asyncio.gather(
        *[async_client.post(f"/api/simulation/{sid}/stop") for sid in simulation_ids],
        return_exceptions=True
    )

