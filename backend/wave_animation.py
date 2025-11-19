"""
海浪演变网格可视化演示脚本。

使用后端模拟服务生成海浪高度场，并显示多个时间步的静态图像展示海浪的演变过程。
"""

import sys
import os

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

from app.services.simulation import simulate_area
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
    print(f"显著波高: {spectrum_config.Hs} m, 峰值周期: {spectrum_config.Tp} s")
    print(f"时间步长: {time_config.dt_backend} s, 总时长: {time_config.T_total} s")
    print()
    
    print("正在运行模拟（流式模式，实时获取结果）...")
    sys.stdout.flush()
    
    # 使用流式模拟，实时获取每个时间步的结果
    frames = []
    grid_points = None
    wave_heights_list = []
    times_list = []
    
    try:
        # 使用流式模拟生成器
        frame_generator = simulate_area_stream(
            region=region,
            wind_config=wind_config,
            spectrum_config=spectrum_config,
            discretization_config=discretization_config,
            time_config=time_config,
        )
        
        print("开始接收实时数据...")
        for frame_idx, frame in enumerate(frame_generator):
            frames.append(frame)
            
            # 第一次获取网格点信息
            if grid_points is None:
                grid_points = frame.points
                n_points = len(grid_points)
                print(f"  网格点数: {n_points}")
            
            # 提取当前时间步的海浪高度
            times_list.append(frame.time)
            wave_heights_list.append([p.wave_height for p in frame.points])
            
            # 每10个时间步显示一次进度
            if frame_idx % 10 == 0 or frame_idx == 0:
                print(f"  已接收时间步 {frame_idx+1}: t = {frame.time:.2f} s", flush=True)
        
        n_times = len(frames)
        print(f"✓ 模拟完成，共生成 {n_times} 个时间帧")
        sys.stdout.flush()
        
        # 转换为numpy数组
        times = np.array(times_list)
        wave_heights = np.array(wave_heights_list)
        
    except Exception as e:
        print(f"❌ 模拟失败: {e}")
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        return
    
    # 转换为2D网格
    print("正在转换网格数据...")
    try:
        lon_grid, lat_grid, height_grid = grid_points_to_2d_array(
            frames[0].points, 
            wave_heights
        )
        
        print(f"✓ 网格尺寸: {height_grid.shape[1]} x {height_grid.shape[2]}")
    except Exception as e:
        print(f"❌ 网格转换失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 计算颜色范围（使用所有时间步的最小值和最大值）
    try:
        vmin = height_grid.min()
        vmax = height_grid.max()
        print(f"✓ 海浪高度范围: [{vmin:.3f}, {vmax:.3f}] 米")
    except Exception as e:
        print(f"❌ 计算颜色范围失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 创建自定义颜色映射（蓝色到白色到绿色，模拟海洋）
    colors = ['#000080', '#0000CD', '#4169E1', '#87CEEB', '#E0F6FF', 
              '#FFFFFF', '#90EE90', '#228B22', '#006400']
    n_bins = 256
    cmap = LinearSegmentedColormap.from_list('ocean', colors, N=n_bins)
    
    # 使用交互模式实时更新显示
    print("\n正在创建实时更新图像...")
    current_backend = matplotlib.get_backend()
    print(f"使用matplotlib后端: {current_backend}")
    
    if current_backend.lower() == 'agg':
        print("⚠️  警告: 当前使用的是非交互式后端(agg)，无法实时更新！")
        print("请尝试安装GUI后端: pip install PyQt5 或确保tkinter可用")
        print("将改为保存静态图像...")
        # 回退到静态显示
        _show_static_images(lon_grid, lat_grid, height_grid, times, cmap, vmin, vmax, n_times)
        return
    
    # 启用交互模式
    plt.ion()
    
    try:
        # 创建单个图形窗口
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # 初始化图像
        im = None
        contour_lines = None
        cbar = None
        
        print("开始实时更新显示...")
        print("提示: 关闭窗口或按Ctrl+C停止")
        print()
        
        # 实时更新循环
        import time
        update_interval = 0.1  # 更新间隔（秒）
        
        for time_idx in range(n_times):
            # 清除之前的图形元素
            ax.clear()
            
            # 绘制等高线填充
            im = ax.contourf(
                lon_grid, lat_grid, height_grid[time_idx],
                levels=50,
                cmap=cmap,
                vmin=vmin,
                vmax=vmax,
                extend='both'
            )
            
            # 添加等高线
            contour_lines = ax.contour(
                lon_grid, lat_grid, height_grid[time_idx],
                levels=20,
                colors='black',
                alpha=0.3,
                linewidths=0.5
            )
            
            # 设置标题和标签
            ax.set_xlabel('经度 (°)', fontsize=12)
            ax.set_ylabel('纬度 (°)', fontsize=12)
            ax.set_title(
                f'海浪演变 - t = {times[time_idx]:.2f} s | '
                f'最大: {height_grid[time_idx].max():.3f} m, '
                f'最小: {height_grid[time_idx].min():.3f} m',
                fontsize=14, fontweight='bold'
            )
            ax.grid(True, alpha=0.3, linestyle='--')
            
            # 添加颜色条（只在第一次添加）
            if cbar is None:
                cbar = plt.colorbar(im, ax=ax, label='海浪高度 (米)', shrink=0.8)
            
            # 更新显示
            plt.tight_layout()
            fig.canvas.draw()
            fig.canvas.flush_events()
            
            # 显示进度
            if time_idx % 5 == 0 or time_idx == n_times - 1:
                progress = (time_idx + 1) / n_times * 100
                print(f"\r进度: {progress:.1f}% | t = {times[time_idx]:.2f} s", end='', flush=True)
            
            # 控制更新速度
            time.sleep(update_interval)
            
            # 检查窗口是否关闭
            if not plt.get_fignums():
                print("\n窗口已关闭")
                break
        
        print("\n✓ 实时更新完成")
        
        # 保持窗口打开
        print("窗口将保持打开，按Enter键关闭...")
        plt.ioff()  # 关闭交互模式
        plt.show(block=True)
        
    except KeyboardInterrupt:
        print("\n\n更新已中断")
        plt.ioff()
    except Exception as e:
        print(f"\n❌ 实时更新失败: {e}")
        import traceback
        traceback.print_exc()
        plt.ioff()
        # 回退到静态显示
        _show_static_images(lon_grid, lat_grid, height_grid, times, cmap, vmin, vmax, n_times)


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

