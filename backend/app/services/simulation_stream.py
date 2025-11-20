"""
区域海浪模拟服务（流式版本，异步）。

支持实时获取每个时间步的海浪高度场，使用外部时钟控制时间步进。
"""

import asyncio
import math
from typing import List, Optional

import numpy as np

from app.models.grid import GridPoint
from app.models.spectrum import WaveSpectrum
from app.schemas.base import (
    DiscretizationConfig,
    Region,
    SpectrumConfig,
    TimeConfig,
    WindConfig,
)
from app.schemas.data import SimulationFrame, WavePoint
from app.services.spectrum import generate_spectrum
from app.services.wind import create_wind_field
from app.utils.coordinate import create_grid

# 重力加速度（m/s²）
G = 9.81


class SimulationStepper:
    """
    模拟步进器类。
    
    内部维护模拟状态，每次调用 step() 方法计算并返回下一个时间步的帧。
    外部时钟负责定期调用 step() 方法，控制时间步进。
    """

    def __init__(
        self,
        region: Region,
        wind_config: WindConfig,
        spectrum_config: SpectrumConfig,
        discretization_config: DiscretizationConfig,
        time_config: TimeConfig,
    ):
        """
        初始化模拟步进器。

        Args:
            region: 区域配置
            wind_config: 风场配置
            spectrum_config: 波浪谱配置
            discretization_config: 离散化配置
            time_config: 时间配置
        """
        self.region = region
        self.time_config = time_config
        
        # 1. 创建网格
        self.grid_points = create_grid(region, discretization_config)

        # 2. 生成风场
        wind = create_wind_field(wind_config)

        # 3. 生成波浪谱
        self.spectrum = generate_spectrum(wind, spectrum_config)

        # 4. 初始化 t=0 海浪场
        self.current_wave_height = _initialize_wave_field(
            self.spectrum, self.grid_points
        )

        # 5. 时间配置
        self.dt = time_config.dt_backend
        self.time_limit = time_config.T_total  # None 表示无限制
        self.current_time = 0.0  # 当前时间（秒）

        # 6. 当前时间索引（0表示初始时刻，已计算）
        self.current_time_idx = 0
        
        # 7. 状态标记
        self.is_completed = False  # 达到时间上限或停止
        self.is_stopped = False  # 外部请求停止
        
        # 8. 预计算支持（用于流水线计算，减少延迟）
        self._next_frame_future: Optional[asyncio.Future] = None  # 预计算的下一帧和新的wave_height
        self._precompute_task: Optional[asyncio.Task] = None  # 预计算任务

    def step(self) -> Optional[SimulationFrame]:
        """
        执行一个时间步进，计算并返回下一个时间步的帧。
        
        每次调用代表过了一个时间步长（dt_backend）。
        首次调用返回初始时刻（t=0）的帧，后续调用返回逐步计算的帧。
        
        Returns:
            下一个时间步的 SimulationFrame，如果已完成则返回 None
        """
        # 如果已完成或被停止，返回 None
        if self.is_completed or self.is_stopped:
            return None

        # 如果是初始时刻，返回初始帧
        if self.current_time_idx == 0:
            frame = _create_frame(
                time=0.0,
                wave_height=self.current_wave_height,
                grid_points=self.grid_points,
                region=self.region,
            )
            self.current_time_idx += 1
            return frame

        # 计算下一时间步的时间
        next_time = self.current_time + self.dt

        # 如果存在时间上限且下一时刻超出范围，则结束
        if self.time_limit is not None and next_time > self.time_limit + 1e-9:
            self.is_completed = True
            return None

        # 计算下一个时间步
        current_time = self.current_time
        self.current_wave_height = _advance_wave_field(
            self.current_wave_height,
            self.spectrum,
            self.grid_points,
            self.dt,
            current_time,
        )

        # 创建并返回当前时间步的帧
        frame = _create_frame(
            time=next_time,
            wave_height=self.current_wave_height,
            grid_points=self.grid_points,
            region=self.region,
        )

        self.current_time = next_time
        self.current_time_idx += 1

        # 如果存在时间上限且已经达到，标记完成
        if (
            self.time_limit is not None
            and next_time >= self.time_limit - 1e-9
        ):
            self.is_completed = True

        return frame

    def get_total_steps(self) -> int:
        """获取总时间步数（包括初始时刻）。无限制时返回 math.inf。"""
        if self.time_limit is None:
            return math.inf
        return int(math.floor(self.time_limit / self.dt)) + 1

    def get_current_step(self) -> int:
        """获取当前已计算的步数（0表示还未开始，1表示已计算初始时刻）。"""
        return self.current_time_idx

    def stop(self) -> None:
        """外部请求停止模拟。"""
        self.is_stopped = True
        self.is_completed = True
        # 取消预计算任务
        if self._precompute_task is not None and not self._precompute_task.done():
            self._precompute_task.cancel()
    
    async def precompute_next_frame(self, loop: asyncio.AbstractEventLoop) -> None:
        """
        在后台预计算下一帧（异步）。
        
        这个方法在后台执行器中进行计算，完成后将结果存储在 _next_frame_future 中。
        预计算包括：计算下一时间步的 wave_height 和创建帧，但不更新 stepper 的状态。
        """
        if self.is_completed or self.is_stopped:
            return
        
        # 如果已经有预计算任务在运行，不重复启动
        if self._next_frame_future is not None and not self._next_frame_future.done():
            return
        
        # 创建 Future 用于存储预计算结果
        self._next_frame_future = loop.create_future()
        
        # 在后台执行器中计算下一帧
        def compute_frame():
            """同步计算函数，在后台线程中执行。"""
            try:
                # 如果已完成或被停止，返回 None
                if self.is_completed or self.is_stopped:
                    return None
                
                # 如果是初始时刻，计算第一个时间步
                if self.current_time_idx == 0:
                    # 初始帧已经返回，现在计算第一个时间步（t=dt）
                    next_time = self.dt
                else:
                    # 计算下一时间步的时间
                    next_time = self.current_time + self.dt
                
                # 如果存在时间上限且下一时刻超出范围，则结束
                if self.time_limit is not None and next_time > self.time_limit + 1e-9:
                    return None
                
                # 计算下一个时间步（使用当前的 current_wave_height 和 current_time）
                current_time = self.current_time if self.current_time_idx > 0 else 0.0
                new_wave_height = _advance_wave_field(
                    self.current_wave_height,
                    self.spectrum,
                    self.grid_points,
                    self.dt,
                    current_time,
                )
                
                # 创建并返回当前时间步的帧
                frame = _create_frame(
                    time=next_time,
                    wave_height=new_wave_height,
                    grid_points=self.grid_points,
                    region=self.region,
                )
                
                # 返回 (frame, new_wave_height) 元组，避免在 get_precomputed_frame 中重复计算
                return (frame, new_wave_height)
            except Exception as e:
                # 如果计算出错，返回 None
                print(f"预计算帧时出错: {e}")
                return None
        
        # 在后台执行器中运行计算
        async def run_compute():
            try:
                frame = await loop.run_in_executor(None, compute_frame)
                if not self._next_frame_future.cancelled():
                    self._next_frame_future.set_result(frame)
            except Exception as e:
                if not self._next_frame_future.cancelled():
                    self._next_frame_future.set_exception(e)
        
        # 启动预计算任务
        self._precompute_task = asyncio.create_task(run_compute())
    
    async def get_precomputed_frame(self) -> Optional["SimulationFrame"]:
        """
        获取预计算的下一帧（如果已准备好）。
        
        如果预计算已完成，返回帧并更新状态，然后立即开始预计算再下一帧。
        
        Returns:
            预计算的帧，如果未准备好或已完成则返回 None
        """
        if self._next_frame_future is None:
            return None
        
        # 等待预计算完成
        try:
            frame = await self._next_frame_future
        except asyncio.CancelledError:
            return None
        except Exception as e:
            print(f"获取预计算帧时出错: {e}")
            return None
        
        # 清空 Future，准备下一次预计算
        self._next_frame_future = None
        
        if frame is None:
            # 预计算返回 None，表示已完成
            self.is_completed = True
            return None
        
        # 预计算返回 (frame, new_wave_height) 元组
        frame, new_wave_height = frame
        
        # 更新状态：应用预计算的结果
        self.current_wave_height = new_wave_height  # 直接使用预计算的 wave_height，避免重复计算
        self.current_time = frame.time
        self.current_time_idx += 1
        
        # 如果存在时间上限且已经达到，标记完成
        if (
            self.time_limit is not None
            and self.current_time >= self.time_limit - 1e-9
        ):
            self.is_completed = True
        
        # 立即开始预计算再下一帧
        loop = asyncio.get_running_loop()
        await self.precompute_next_frame(loop)
        
        return frame


async def simulate_area_stream(
    region: Region,
    wind_config: WindConfig,
    spectrum_config: SpectrumConfig,
    discretization_config: DiscretizationConfig,
    time_config: TimeConfig,
) -> "SimulationStepper":
    """
    创建并返回模拟步进器实例。
    
    外部时钟负责定期调用 step() 方法，每次调用代表过了一个时间步长。

    Args:
        region: 区域配置
        wind_config: 风场配置
        spectrum_config: 波浪谱配置
        discretization_config: 离散化配置
        time_config: 时间配置

    Returns:
        SimulationStepper 实例
    """
    return SimulationStepper(
        region=region,
        wind_config=wind_config,
        spectrum_config=spectrum_config,
        discretization_config=discretization_config,
        time_config=time_config,
    )


def _initialize_wave_field(
    spectrum: WaveSpectrum, grid_points: List[GridPoint]
) -> np.ndarray:
    """初始化 t=0 时刻的海浪场。"""
    n_points = len(grid_points)
    wave_height = np.zeros(n_points)

    for component in spectrum.components:
        k = component.wave_number
        direction_rad = math.radians(component.direction_deg)
        kx = k * math.sin(direction_rad)
        ky = k * math.cos(direction_rad)
        omega = 2.0 * math.pi * component.frequency

        for i, point in enumerate(grid_points):
            k_dot_r = kx * point.x + ky * point.y
            wave_height[i] += component.amplitude * math.cos(
                k_dot_r - omega * 0.0 + component.phase
            )

    return wave_height


def _advance_wave_field(
    wave_height: np.ndarray,
    spectrum: WaveSpectrum,
    grid_points: List[GridPoint],
    dt: float,
    current_time: float,
) -> np.ndarray:
    """
    时间步进：推进一个时间步长。
    
    Args:
        wave_height: 当前时刻的海浪高度
        spectrum: 波浪谱
        grid_points: 网格点列表
        dt: 时间步长（秒）
        current_time: 当前时间（秒）
    
    Returns:
        下一时刻的海浪高度数组
    """
    n_points = len(grid_points)
    new_wave_height = np.zeros(n_points)

    for component in spectrum.components:
        k = component.wave_number
        direction_rad = math.radians(component.direction_deg)
        kx = k * math.sin(direction_rad)
        ky = k * math.cos(direction_rad)
        omega = 2.0 * math.pi * component.frequency

        for i, point in enumerate(grid_points):
            k_dot_r = kx * point.x + ky * point.y
            new_wave_height[i] += component.amplitude * math.cos(
                k_dot_r - omega * (current_time + dt) + component.phase
            )

    return new_wave_height


def _create_frame(
    time: float,
    wave_height: np.ndarray,
    grid_points: List[GridPoint],
    region: Region,
) -> SimulationFrame:
    """创建单个时间步的帧。"""
    points = [
        WavePoint(
            lon=point.lon,
            lat=point.lat,
            wave_height=float(wave_height[i]),
        )
        for i, point in enumerate(grid_points)
    ]

    return SimulationFrame(time=float(time), region=region, points=points)


