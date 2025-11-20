"""
海浪演变网格可视化演示脚本（实时模式）。

使用后端模拟服务生成海浪高度场，使用真实时间时钟实时显示海浪的演变过程。
每个时间步按照 dt_backend 的真实时间间隔计算和显示。
"""

import sys
import os
import time

# 添加backend目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import matplotlib

# 尝试设置可用的GUI后端（Windows上优先使用TkAgg）
# 必须在导入pyplot之前设置
backends_to_try = ['TkAgg', 'Qt5Agg', 'Qt4Agg']
backend_set = False
backend_name_used = None

for backend_name in backends_to_try:
    try:
        matplotlib.use(backend_name, force=True)
        backend_set = True
        backend_name_used = backend_name
        break
    except Exception as e:
        continue

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

from app.services.simulation_stream import simulate_area_stream
from app.schemas.base import (
    Region,
    WindConfig,
    SpectrumConfig,
    DiscretizationConfig,
    TimeConfig,
)


def grid_points_to_2d_array(grid_points, wave_heights):
    """
    将网格点列表转换为2D数组。
    
    Args:
        grid_points: GridPoint列表
        wave_heights: 海浪高度数组，shape: (n_times, n_points) 或 (n_points,)
    
    Returns:
        (lon_grid, lat_grid, height_grid): 2D网格数组
    """
    # 提取唯一的经纬度值
    lons = sorted(set(p.lon for p in grid_points))
    lats = sorted(set(p.lat for p in grid_points))
    
    n_lon = len(lons)
    n_lat = len(lats)
    
    # 创建2D网格
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    
    # 创建经纬度到索引的映射
    lon_to_idx = {lon: i for i, lon in enumerate(lons)}
    lat_to_idx = {lat: i for i, lat in enumerate(lats)}
    
    # 判断wave_heights的维度
    if wave_heights.ndim == 1:
        # 单个时间步
        height_grid = np.zeros((n_lat, n_lon))
        for i, point in enumerate(grid_points):
            lon_idx = lon_to_idx[point.lon]
            lat_idx = lat_to_idx[point.lat]
            height_grid[lat_idx, lon_idx] = wave_heights[i]
    else:
        # 多个时间步
        n_times = wave_heights.shape[0]
        height_grid = np.zeros((n_times, n_lat, n_lon))
        for i, point in enumerate(grid_points):
            lon_idx = lon_to_idx[point.lon]
            lat_idx = lat_to_idx[point.lat]
            height_grid[:, lat_idx, lon_idx] = wave_heights[:, i]
    
    return lon_grid, lat_grid, height_grid


def create_wave_animation():
    """创建海浪演变动画。"""
    
    # 配置参数
    region = Region(
        lon_min=120.0,
        lat_min=30.0,
        depth_min=50.0,
        lon_max=120.5,
        lat_max=30.5,
        depth_max=100.0,
    )
    
    wind_config = WindConfig(
        wind_speed=15.0,  # 风速 15 m/s
        wind_direction_deg=270.0,  # 西风
        reference_height_m=10.0,
    )
    
    spectrum_config = SpectrumConfig(
        spectrum_model_type="PM",
        Hs=2.5,  # 显著波高 2.5m
        Tp=8.0,  # 峰值周期 8s
        main_wave_direction_deg=270.0,  # 主浪向与风向一致
        directional_spread_deg=30.0,  # 方向扩散 30度
    )
    
    discretization_config = DiscretizationConfig(
        dx=0.05,  # 经度间隔 0.05度（增大间隔以减少点数，加快速度）
        dy=0.05,  # 纬度间隔 0.05度
        max_points=5000,  # 最大点数（减少点数）
    )
    
    time_config = TimeConfig(
        dt_backend=0.2,  # 时间步长 500ms（增大步长）
        T_total=10.0,  # 总时长 10秒（减少总时长）
    )
    
    print("开始生成海浪模拟数据...")
    print(f"区域: 经度 [{region.lon_min}, {region.lon_max}], "
          f"纬度 [{region.lat_min}, {region.lat_max}]")
    print(f"风速: {wind_config.wind_speed} m/s, 风向: {wind_config.wind_direction_deg}°")
    total_time_text = (
        f"{time_config.T_total} s" if time_config.T_total is not None else "∞"
    )
    print(f"显著波高: {spectrum_config.Hs} m, 峰值周期: {spectrum_config.Tp} s")
    print(f"时间步长: {time_config.dt_backend} s, 总时长: {total_time_text}")
    print()
    
    print("正在初始化模拟步进器...")
    sys.stdout.flush()
    
    # 使用异步流式模拟，创建步进器实例
    try:
        import asyncio
        
        # 创建事件循环（如果是同步环境，创建新循环）
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # 异步创建步进器
        stepper = loop.run_until_complete(
            simulate_area_stream(
            region=region,
            wind_config=wind_config,
            spectrum_config=spectrum_config,
            discretization_config=discretization_config,
            time_config=time_config,
        )
        )
        
        total_steps = stepper.get_total_steps()
        print(f"✓ 步进器初始化完成")
        print(f"  网格点数: {len(stepper.grid_points)}")
        total_time_text = (
            f"{time_config.T_total} s" if time_config.T_total is not None else "∞"
        )
        print(f"  总时间步数: {total_steps}")
        print(f"  时间步长: {time_config.dt_backend} s")
        print(f"  总时长: {total_time_text}")
        print()
        
    except Exception as e:
        print(f"❌ 模拟初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        return
    
    # 创建自定义颜色映射（蓝色到白色到绿色，模拟海洋）
    colors = ['#000080', '#0000CD', '#4169E1', '#87CEEB', '#E0F6FF', 
              '#FFFFFF', '#90EE90', '#228B22', '#006400']
    n_bins = 256
    cmap = LinearSegmentedColormap.from_list('ocean', colors, N=n_bins)
    
    # 检查matplotlib后端
    print("正在检查matplotlib后端...")
    current_backend = matplotlib.get_backend()
    print(f"使用matplotlib后端: {current_backend}")
    
    if current_backend.lower() == 'agg':
        print("⚠️  警告: 当前使用的是非交互式后端(agg)，无法实时更新！")
        print("请尝试安装GUI后端: pip install PyQt5 或确保tkinter可用")
        print("将使用静态显示模式...")
        _show_static_mode(stepper, cmap, time_config)
        return
    
    # 启用交互模式
    plt.ion()
    
    try:
        # 创建单个图形窗口
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # 初始化变量
        lon_grid = None
        lat_grid = None
        vmin = None
        vmax = None
        cbar = None
        frame_count = 0
        
        print("开始实时动画显示（使用真实时间时钟）...")
        print("提示: 关闭窗口或按Ctrl+C停止")
        print()
        
        # 获取初始帧（t=0）
        first_frame = stepper.step()
        if first_frame is None:
            print("❌ 无法获取初始帧")
            return
        
        # 初始化网格和颜色范围
        lon_grid, lat_grid, height_grid_2d = _frame_to_2d_array(first_frame)
        vmin = height_grid_2d.min()
        vmax = height_grid_2d.max()
        
        # 动态更新颜色范围（初始值）
        vmin_init = vmin
        vmax_init = vmax
        
        print(f"初始网格尺寸: {height_grid_2d.shape[0]} x {height_grid_2d.shape[1]}")
        print(f"初始高度范围: [{vmin:.3f}, {vmax:.3f}] 米")
        print()
            
        # 真实时间循环
        dt = time_config.dt_backend  # 使用真实时间步长
        start_time = time.time()  # 记录开始时间（真实时间）
        last_real_time = start_time  # 上一帧的真实时间
        
        # 显示初始帧
        cbar = _update_display(
            ax, lon_grid, lat_grid, height_grid_2d,
            first_frame.time, cmap, vmin, vmax, cbar
        )
        plt.tight_layout()
        fig.canvas.draw()
        fig.canvas.flush_events()
        frame_count += 1
        
        real_time_elapsed = time.time() - start_time
        print(f"t = {first_frame.time:.2f} s | 真实时间: {real_time_elapsed:.2f} s")
        
        # 真实时间循环：按照 dt_backend 的时间间隔调用 step()
        # 使用当前时间与上一帧时间的差值来控制时间步进
        while not stepper.is_completed:
            # 记录当前真实时间
            current_real_time = time.time()
            
            # 计算从上一次到现在经过的真实时间
            elapsed_since_last = current_real_time - last_real_time
            
            # 如果经过的时间小于 dt，则等待剩余的间隔
            if elapsed_since_last < dt:
                sleep_time = dt - elapsed_since_last
                time.sleep(sleep_time)
                # 更新当前时间（包括睡眠后的时间）
                current_real_time = time.time()
            
            # 如果经过的时间已经超过 dt，则不休眠，立即计算下一帧
            # 这样可以确保即使计算超时也不会累积延迟
            
            # 更新上一帧的真实时间
            last_real_time = current_real_time
            
            # 调用 step() 方法，计算下一个时间步
            frame = stepper.step()
            
            if frame is None:
                # 如果没有帧返回，说明已完成
                break
            
            # 转换为2D数组
            lon_grid, lat_grid, height_grid_2d = _frame_to_2d_array(frame)
            
            # 动态更新颜色范围（使用滑动窗口或当前所有帧的最小/最大值）
            current_min = height_grid_2d.min()
            current_max = height_grid_2d.max()
            vmin = min(vmin, current_min) if vmin is not None else current_min
            vmax = max(vmax, current_max) if vmax is not None else current_max
            
            # 更新显示
            cbar = _update_display(
                ax, lon_grid, lat_grid, height_grid_2d,
                frame.time, cmap, vmin, vmax, cbar
            )
            
            plt.tight_layout()
            fig.canvas.draw()
            fig.canvas.flush_events()
            frame_count += 1
            
            # 计算真实时间流逝
            real_time_elapsed = current_real_time - start_time
            
            # 显示进度
            progress = stepper.get_current_step() / total_steps * 100
            print(
                f"\rt = {frame.time:.2f} s | "
                f"真实时间: {real_time_elapsed:.2f} s | "
                f"进度: {progress:.1f}% | "
                f"高度: [{current_min:.3f}, {current_max:.3f}] m",
                end='', flush=True
            )
            
            # 检查窗口是否关闭
            if not plt.get_fignums():
                print("\n窗口已关闭")
                break
        
        total_real_time = time.time() - start_time
        print(f"\n✓ 实时动画完成")
        print(f"  总帧数: {frame_count}")
        if time_config.T_total is not None:
            print(f"  模拟时间: {time_config.T_total:.2f} s")
            print(f"  真实时间: {total_real_time:.2f} s")
            print(f"  时间加速比: {time_config.T_total / total_real_time:.2f}x")
        else:
            print("  模拟时间: ∞ (无限制模式)")
            print(f"  真实时间: {total_real_time:.2f} s")
        
        # 保持窗口打开
        print("\n窗口将保持打开，按Enter键关闭...")
        plt.ioff()  # 关闭交互模式
        plt.show(block=True)
        
    except KeyboardInterrupt:
        print("\n\n动画已中断")
        plt.ioff()
    except Exception as e:
        print(f"\n❌ 实时动画失败: {e}")
        import traceback
        traceback.print_exc()
        plt.ioff()


def _frame_to_2d_array(frame):
    """
    将单个帧转换为2D网格数组。
    
    Args:
        frame: SimulationFrame对象
    
    Returns:
        (lon_grid, lat_grid, height_grid): 2D网格数组
    """
    grid_points = frame.points
    wave_heights = np.array([p.wave_height for p in grid_points])
    
    # 提取唯一的经纬度值
    lons = sorted(set(p.lon for p in grid_points))
    lats = sorted(set(p.lat for p in grid_points))
    
    n_lon = len(lons)
    n_lat = len(lats)
    
    # 创建2D网格
    lon_grid, lat_grid = np.meshgrid(lons, lats)
    
    # 创建经纬度到索引的映射
    lon_to_idx = {lon: i for i, lon in enumerate(lons)}
    lat_to_idx = {lat: i for i, lat in enumerate(lats)}
    
    # 创建高度网格
    height_grid = np.zeros((n_lat, n_lon))
    point_dict = {(p.lon, p.lat): p.wave_height for p in grid_points}
    
    for i, lon in enumerate(lons):
        for j, lat in enumerate(lats):
            if (lon, lat) in point_dict:
                height_grid[j, i] = point_dict[(lon, lat)]
    
    return lon_grid, lat_grid, height_grid


def _update_display(ax, lon_grid, lat_grid, height_grid, current_time, cmap, vmin, vmax, cbar):
    """
    更新显示内容。
    
    Args:
        ax: matplotlib axes对象
        lon_grid: 经度网格
        lat_grid: 纬度网格
        height_grid: 高度网格（2D）
        current_time: 当前时间
        cmap: 颜色映射
        vmin: 最小高度
        vmax: 最大高度
        cbar: 颜色条对象（如果已创建）
    """
    # 清除之前的图形元素
    ax.clear()
    
    # 绘制等高线填充
    im = ax.contourf(
        lon_grid, lat_grid, height_grid,
        levels=50,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        extend='both'
    )
    
    # 添加等高线
    ax.contour(
        lon_grid, lat_grid, height_grid,
        levels=20,
        colors='black',
        alpha=0.3,
        linewidths=0.5
    )
    
    # 设置标题和标签
    ax.set_xlabel('经度 (°)', fontsize=12)
    ax.set_ylabel('纬度 (°)', fontsize=12)
    ax.set_title(
        f'海浪演变（实时） - t = {current_time:.2f} s | '
        f'最大: {height_grid.max():.3f} m, '
        f'最小: {height_grid.min():.3f} m',
        fontsize=14, fontweight='bold'
    )
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # 添加或更新颜色条
    if cbar is None:
        # 第一次创建颜色条
        cbar = plt.colorbar(im, ax=ax, label='海浪高度 (米)', shrink=0.8)
    else:
        # 更新颜色条：由于 ax.clear() 清除了之前的图像，需要重新创建 colorbar
        # 移除旧的 colorbar
        try:
            cbar.remove()
        except Exception:
            pass  # 如果移除失败，忽略
        # 创建新的 colorbar
        cbar = plt.colorbar(im, ax=ax, label='海浪高度 (米)', shrink=0.8)
    
    # 设置颜色条的范围（通过 mappable 对象）
    if hasattr(cbar, 'mappable') and cbar.mappable is not None:
        cbar.mappable.set_clim(vmin, vmax)
    
    return cbar


def _show_static_mode(stepper, cmap, time_config):
    """静态模式：先计算所有帧，然后显示"""
    print("\n使用静态模式（先计算所有帧，然后显示）...")
    
    # 收集所有帧
    frames = []
    frame = stepper.step()  # 获取初始帧
    if frame is None:
        print("❌ 无法获取初始帧")
        return
    
    frames.append(frame)
    print(f"  已获取帧 1: t = {frame.time:.2f} s")
    
    # 计算所有帧
    while not stepper.is_completed:
        time.sleep(0.001)  # 短暂延迟，避免占用太多CPU
        frame = stepper.step()
        if frame is None:
            break
        frames.append(frame)
        if len(frames) % 10 == 0:
            print(f"  已获取帧 {len(frames)}: t = {frame.time:.2f} s")
    
    print(f"✓ 所有帧计算完成，共 {len(frames)} 帧")
    
    # 转换为2D网格
    times = [f.time for f in frames]
    wave_heights_list = [[p.wave_height for p in f.points] for f in frames]
    wave_heights = np.array(wave_heights_list)
    
    lon_grid, lat_grid, height_grid = grid_points_to_2d_array(
        frames[0].points, 
        wave_heights
    )
    
    # 计算颜色范围
    vmin = height_grid.min()
    vmax = height_grid.max()
    
    # 显示静态图像
    _show_static_images(lon_grid, lat_grid, height_grid, np.array(times), cmap, vmin, vmax, len(frames))


def _show_static_images(lon_grid, lat_grid, height_grid, times, cmap, vmin, vmax, n_times):
    """回退方案：显示静态图像"""
    print("\n使用静态图像显示...")
    try:
        # 选择要显示的时间步
        time_indices_to_show = [
            0,
            n_times // 4,
            n_times // 2,
            3 * n_times // 4,
            n_times - 1
        ]
        time_indices_to_show = [idx for idx in time_indices_to_show if idx < n_times]
        
        n_plots = len(time_indices_to_show)
        cols = min(3, n_plots)
        rows = (n_plots + cols - 1) // cols
        
        fig, axes = plt.subplots(rows, cols, figsize=(15, 5 * rows))
        if n_plots == 1:
            axes = [axes]
        else:
            axes = axes.flatten() if hasattr(axes, 'flatten') else axes
        
        for plot_idx, time_idx in enumerate(time_indices_to_show):
            ax = axes[plot_idx]
            im = ax.contourf(
                lon_grid, lat_grid, height_grid[time_idx],
                levels=50, cmap=cmap, vmin=vmin, vmax=vmax, extend='both'
            )
            ax.contour(lon_grid, lat_grid, height_grid[time_idx],
                      levels=20, colors='black', alpha=0.3, linewidths=0.5)
            ax.set_xlabel('经度 (°)', fontsize=10)
            ax.set_ylabel('纬度 (°)', fontsize=10)
            ax.set_title(
                f't = {times[time_idx]:.2f} s\n'
                f'最大: {height_grid[time_idx].max():.3f} m, '
                f'最小: {height_grid[time_idx].min():.3f} m',
                fontsize=11, fontweight='bold'
            )
            ax.grid(True, alpha=0.3, linestyle='--')
            if plot_idx == 0:
                plt.colorbar(im, ax=ax, label='海浪高度 (米)', shrink=0.8)
        
        for idx in range(n_plots, len(axes)):
            axes[idx].set_visible(False)
        
        plt.tight_layout()
        output_file = 'wave_visualization.png'
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"✓ 图像已保存到: {output_file}")
        plt.show(block=True)
    except Exception as e:
        print(f"静态显示也失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("=" * 60)
    print("海浪演变可视化演示")
    print("=" * 60)
    print(f"Python版本: {sys.version.split()[0]}")
    print(f"NumPy版本: {np.__version__}")
    print(f"Matplotlib版本: {matplotlib.__version__}")
    print(f"Matplotlib后端: {matplotlib.get_backend()}")
    
    # 检查后端是否支持GUI
    backend = matplotlib.get_backend()
    if backend.lower() in ['agg', 'svg', 'pdf', 'ps']:
        print("\n⚠️  警告: 当前后端不支持GUI显示！")
        print("尝试安装GUI后端:")
        print("  - Windows/Linux: pip install PyQt5")
        print("  - 或确保tkinter可用 (Windows通常已包含)")
        print("=" * 60)
    else:
        print("✓ GUI后端可用")
        print("=" * 60)
    print()
    
    try:
        create_wave_animation()
    except KeyboardInterrupt:
        print("\n\n动画已中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        print("\n" + "=" * 60)
        print("故障排除提示:")
        print("=" * 60)
        print("1. 检查matplotlib后端:")
        print("   python -c \"import matplotlib; print(matplotlib.get_backend())\"")
        print("2. 安装GUI后端:")
        print("   pip install PyQt5")
        print("3. 测试matplotlib显示:")
        print("   python -c \"import matplotlib.pyplot as plt; plt.plot([1,2,3]); plt.show()\"")
        print("4. 如果使用Jupyter/IDE，可能需要:")
        print("   %matplotlib qt  # 在Jupyter中")
        print("=" * 60)

