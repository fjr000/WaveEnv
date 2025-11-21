# -*- coding: utf-8 -*-
"""
API 客户端模块。

封装后端 FastAPI 服务的 HTTP 调用。
"""

import httpx
from typing import Dict, Optional, List


# 后端服务地址（可通过环境变量配置，Docker环境下使用服务名）
import os
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


class APIClient:
    """后端 API 客户端。"""

    def __init__(self, base_url: str = BACKEND_URL):
        """
        初始化 API 客户端。

        Args:
            base_url: 后端服务基础 URL
        """
        self.base_url = base_url
        # 配置客户端，禁用代理避免 502 错误
        # 使用连接池复用连接，减少连接数
        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            proxies=None,  # 禁用代理
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),  # 限制连接数
            http2=False,  # 禁用 HTTP/2，避免连接问题
        )

    def create_simulation(
        self,
        region: Dict,
        wind: Dict,
        spectrum: Dict,
        discretization: Dict,
        time_config: Dict,
    ) -> Dict:
        """
        创建区域模拟任务。

        Args:
            region: 区域配置
            wind: 风场配置
            spectrum: 波浪谱配置
            discretization: 离散化配置
            time_config: 时间配置

        Returns:
            包含 simulation_id 和 status 的字典

        Raises:
            httpx.HTTPStatusError: API 调用失败
            httpx.RequestError: 网络请求失败
        """
        request_data = {
            "region": region,
            "wind": wind,
            "spectrum": spectrum,
            "discretization": discretization,
            "time": time_config,
        }

        response = self.client.post(
            f"{self.base_url}/api/simulate/area",
            json=request_data,
        )
        response.raise_for_status()
        return response.json()

    def get_frames(
        self,
        simulation_id: str,
        time: float,
        timeout: float = 10.0,
    ) -> Dict:
        """
        获取模拟结果帧（单时刻）。

        Args:
            simulation_id: 模拟任务 ID
            time: 指定时间（秒），相对于 t=0 的偏移。time=-1 表示最新帧
            timeout: 请求超时时间（秒），默认 10.0 秒

        Returns:
            包含 frames 列表的字典（只包含一个帧）

        Raises:
            httpx.HTTPStatusError: API 调用失败
            httpx.RequestError: 网络请求失败
            httpx.TimeoutException: 请求超时
        """
        params = {"time": time}

        # 使用持久化客户端实现连接复用
        response = self.client.get(
            f"{self.base_url}/api/query/simulation/{simulation_id}/frames",
            params=params,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    def query_point(
        self,
        simulation_id: str,
        lon: float,
        lat: float,
        time: float,
        timeout: float = 5.0,
    ) -> Dict:
        """
        单点查询（独立于显示刷新，使用独立超时）。

        Args:
            simulation_id: 模拟任务 ID
            lon: 经度（度）
            lat: 纬度（度）
            time: 时间（秒），time=-1 表示最新帧
            timeout: 查询超时时间（秒），默认 5.0 秒，确保快速响应

        Returns:
            包含 wave_height 的字典

        Raises:
            httpx.HTTPStatusError: API 调用失败
            httpx.RequestError: 网络请求失败
            httpx.TimeoutException: 请求超时
        """
        params = {
            "simulation_id": simulation_id,
            "lon": lon,
            "lat": lat,
            "time": time,
        }

        # 使用持久化的客户端实现连接复用，大幅提升性能（从 1.2秒 降至 14ms）
        # 注意：self.client 已经在 __init__ 中创建，支持连接池和 keep-alive
        response = self.client.get(
            f"{self.base_url}/api/query/point",
            params=params,
            timeout=timeout,  # 单独设置超时，不影响全局配置
        )
        response.raise_for_status()
        return response.json()

    def pause_clock(self, simulation_id: str, timeout: float = 3.0) -> Dict:
        """
        暂停指定模拟任务的时钟（使用独立短超时，确保快速响应）。
        
        Args:
            simulation_id: 模拟任务 ID
            timeout: 请求超时时间（秒），默认 3.0 秒
        
        Returns:
            包含状态信息的字典
        
        Raises:
            httpx.HTTPStatusError: API 调用失败
            httpx.RequestError: 网络请求失败
            httpx.TimeoutException: 请求超时
        """
        # 使用持久化客户端实现连接复用
        response = self.client.post(
            f"{self.base_url}/api/simulation/{simulation_id}/clock/pause",
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    def resume_clock(self, simulation_id: str, timeout: float = 3.0) -> Dict:
        """
        恢复指定模拟任务的时钟（使用独立短超时，确保快速响应）。
        
        Args:
            simulation_id: 模拟任务 ID
            timeout: 请求超时时间（秒），默认 3.0 秒
        
        Returns:
            包含状态信息的字典
        
        Raises:
            httpx.HTTPStatusError: API 调用失败
            httpx.RequestError: 网络请求失败
            httpx.TimeoutException: 请求超时
        """
        # 使用持久化客户端实现连接复用
        response = self.client.post(
            f"{self.base_url}/api/simulation/{simulation_id}/clock/resume",
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    def stop_simulation(self, simulation_id: str, timeout: float = 3.0) -> Dict:
        """
        停止指定模拟任务（使用独立短超时，确保快速响应）。
        
        Args:
            simulation_id: 模拟任务 ID
            timeout: 请求超时时间（秒），默认 3.0 秒
        
        Returns:
            包含状态信息的字典
        
        Raises:
            httpx.HTTPStatusError: API 调用失败
            httpx.RequestError: 网络请求失败
            httpx.TimeoutException: 请求超时
        """
        # 使用持久化客户端实现连接复用
        response = self.client.post(
            f"{self.base_url}/api/simulation/{simulation_id}/stop",
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    def list_simulations(self, status: Optional[str] = None) -> Dict:
        """
        获取所有仿真任务列表。
        
        Args:
            status: 可选的状态过滤器（如 "running", "paused" 等）
        
        Returns:
            包含任务列表的字典
        """
        params = {}
        if status:
            params["status"] = status
        
        response = self.client.get(
            f"{self.base_url}/api/query/simulations",
            params=params
        )
        response.raise_for_status()
        return response.json()

    def stop_all_simulations(self) -> Dict:
        """停止所有运行中的仿真任务。"""
        response = self.client.post(
            f"{self.base_url}/api/simulations/stop-all"
        )
        response.raise_for_status()
        return response.json()

    def close(self):
        """关闭 HTTP 客户端。"""
        self.client.close()

    def __enter__(self):
        """上下文管理器入口。"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口。"""
        self.close()

