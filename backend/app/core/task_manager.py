"""
任务管理器。

提供任务的创建、获取、状态更新等功能。
"""

import uuid
from typing import Optional

from app.core.storage import task_storage
from app.models.simulation import SimulationTask
from app.schemas.base import (
    DiscretizationConfig,
    Region,
    SpectrumConfig,
    TimeConfig,
    WindConfig,
)
from app.schemas.data import SimulationStatus


def create_simulation_task(
    region: Region,
    wind_config: WindConfig,
    spectrum_config: SpectrumConfig,
    discretization_config: DiscretizationConfig,
    time_config: TimeConfig,
) -> str:
    """
    创建模拟任务。

    Args:
        region: 区域配置
        wind_config: 风场配置
        spectrum_config: 波浪谱配置
        discretization_config: 离散化配置
        time_config: 时间配置

    Returns:
        任务 ID
    """
    simulation_id = str(uuid.uuid4())

    task = SimulationTask(
        simulation_id=simulation_id,
        status=SimulationStatus.PENDING,
        region=region,
        wind_config=wind_config,
        spectrum_config=spectrum_config,
        discretization_config=discretization_config,
        time_config=time_config,
        wave_grid=None,
    )

    task_storage.add_task(task)
    return simulation_id


def get_simulation_task(simulation_id: str) -> Optional[SimulationTask]:
    """
    获取模拟任务。

    Args:
        simulation_id: 任务 ID

    Returns:
        任务对象，如果不存在则返回 None
    """
    return task_storage.get_task(simulation_id)


def update_task_status(
    simulation_id: str, status: SimulationStatus
) -> bool:
    """
    更新任务状态。

    Args:
        simulation_id: 任务 ID
        status: 新状态

    Returns:
        是否更新成功
    """
    task = task_storage.get_task(simulation_id)
    if task is None:
        return False

    task.status = status
    task_storage.update_task(task)
    return True

