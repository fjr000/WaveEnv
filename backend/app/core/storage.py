"""
任务存储模块。

使用内存存储模拟任务（后续可扩展为数据库）。
"""

from typing import Dict, List, Optional

from app.models.simulation import SimulationTask


class TaskStorage:
    """任务存储（内存）。"""

    def __init__(self):
        self._tasks: Dict[str, SimulationTask] = {}

    def add_task(self, task: SimulationTask) -> None:
        """添加任务。"""
        self._tasks[task.simulation_id] = task

    def get_task(self, simulation_id: str) -> Optional[SimulationTask]:
        """获取任务。"""
        return self._tasks.get(simulation_id)

    def update_task(self, task: SimulationTask) -> None:
        """更新任务。"""
        if task.simulation_id in self._tasks:
            self._tasks[task.simulation_id] = task

    def remove_task(self, simulation_id: str) -> None:
        """删除任务。"""
        if simulation_id in self._tasks:
            del self._tasks[simulation_id]

    def list_tasks(self) -> List[SimulationTask]:
        """列出所有任务。"""
        return list(self._tasks.values())


# 全局任务存储实例
task_storage = TaskStorage()

