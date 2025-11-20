# -*- coding: utf-8 -*-
"""
API 客户端模块。

封装后端 FastAPI 服务的 HTTP 调用。
"""

import httpx
from typing import Dict, Optional, List


# 后端服务地址
BACKEND_URL = "http://localhost:8000"


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
        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            proxies=None,  # 禁用代理
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
        time_min: Optional[float] = None,
        time_max: Optional[float] = None,
        max_frames: int = 100,
    ) -> Dict:
        """
        获取模拟结果帧。

        Args:
            simulation_id: 模拟任务 ID
            time_min: 起始时间（秒）
            time_max: 结束时间（秒）
            max_frames: 最大帧数

        Returns:
            包含 frames 列表的字典

        Raises:
            httpx.HTTPStatusError: API 调用失败
            httpx.RequestError: 网络请求失败
        """
        params = {"max_frames": max_frames}
        if time_min is not None:
            params["time_min"] = time_min
        if time_max is not None:
            params["time_max"] = time_max

        response = self.client.get(
            f"{self.base_url}/api/simulation/{simulation_id}/frames",
            params=params,
        )
        response.raise_for_status()
        return response.json()

    def query_point(
        self,
        simulation_id: str,
        lon: float,
        lat: float,
        time: float,
    ) -> Dict:
        """
        单点查询。

        Args:
            simulation_id: 模拟任务 ID
            lon: 经度（度）
            lat: 纬度（度）
            time: 时间（秒）

        Returns:
            包含 wave_height 的字典

        Raises:
            httpx.HTTPStatusError: API 调用失败
            httpx.RequestError: 网络请求失败
        """
        request_data = {
            "simulation_id": simulation_id,
            "lon": lon,
            "lat": lat,
            "time": time,
        }

        response = self.client.post(
            f"{self.base_url}/api/query/point",
            json=request_data,
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

