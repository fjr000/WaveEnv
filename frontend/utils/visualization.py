# -*- coding: utf-8 -*-
"""
可视化模块。

使用 Plotly 生成海浪高度场可视化图表。
"""

import numpy as np
from typing import Tuple, Optional
import plotly.graph_objects as go


def create_heatmap(
    lon_grid: np.ndarray,
    lat_grid: np.ndarray,
    height_grid: np.ndarray,
    time: float,
    title: str = None,
    use_fast_mode: bool = True,
) -> go.Figure:
    """
    创建海浪高度场热力图。

    Args:
        lon_grid: 经度网格 (n_lat, n_lon)
        lat_grid: 纬度网格 (n_lat, n_lon)
        height_grid: 海浪高度场 (n_lat, n_lon) - 单帧数据
        time: 当前时间（秒）
        title: 图表标题
        use_fast_mode: 是否使用快速模式（简化渲染，提升性能）

    Returns:
        Plotly Figure 对象
    """
    # 计算高度范围
    vmin = float(np.nanmin(height_grid))
    vmax = float(np.nanmax(height_grid))

    # 提取坐标轴数据（只提取一次，避免重复计算）
    x_data = lon_grid[0, :] if lon_grid.ndim == 2 else lon_grid
    y_data = lat_grid[:, 0] if lat_grid.ndim == 2 else lat_grid

    if use_fast_mode:
        # 快速模式：使用Heatmap代替Contour，减少计算量
        fig = go.Figure(
            data=go.Heatmap(
                x=x_data,
                y=y_data,
                z=height_grid,
                colorscale="Viridis",
                colorbar=dict(
                    title=dict(
                        text="海浪高度 (m)",
                        font=dict(size=12),
                    ),
                ),
                hovertemplate=(
                    "经度: %{x:.4f}°<br>"
                    "纬度: %{y:.4f}°<br>"
                    "海浪高度: %{z:.4f} m<extra></extra>"
                ),
                # 禁用平滑处理以提升性能
                zsmooth=False,
            )
        )
    else:
        # 标准模式：使用Contour等高线图（支持hover查询高度）
    fig = go.Figure(
        data=go.Contour(
                x=x_data,
                y=y_data,
            z=height_grid,
            colorscale="Viridis",
            colorbar=dict(
                title=dict(
                    text="海浪高度 (m)",
                    font=dict(size=12),
                ),
            ),
            contours=dict(
                    showlines=True,  # 显示等高线
                    showlabels=True,  # 显示等高线标签
                labelfont=dict(size=10),
            ),
            hovertemplate=(
                "经度: %{x:.4f}°<br>"
                "纬度: %{y:.4f}°<br>"
                "海浪高度: %{z:.4f} m<extra></extra>"
            ),
                ncontours=20,  # 等高线数量
        )
    )

    # 设置标题
    if title is None:
        title = f"海浪高度场 - t = {time:.2f} s"
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=16, color="black"),
            x=0.5,
            xanchor="center",
        ),
        xaxis_title="经度 (°)",
        yaxis_title="纬度 (°)",
        width=800,
        height=600,
        margin=dict(l=60, r=60, t=80, b=60),
        # 禁用某些交互以提升性能
        dragmode=False,
    )

    return fig


def update_heatmap_data(
    fig: go.Figure,
    height_grid: np.ndarray,
    time: float,
    title: str = None,
) -> go.Figure:
    """
    更新现有热力图的数据（比重新创建更快）。

    Args:
        fig: 现有的Plotly Figure对象
        height_grid: 新的海浪高度场 (n_lat, n_lon)
        time: 当前时间（秒）
        title: 图表标题

    Returns:
        更新后的Plotly Figure对象
    """
    # 更新数据
    if len(fig.data) > 0:
        fig.data[0].z = height_grid
    
    # 更新标题
    if title is None:
        title = f"海浪高度场 - t = {time:.2f} s"
    fig.update_layout(title_text=title)

    return fig


def create_time_series_chart(
    times: np.ndarray,
    wave_heights: np.ndarray,
    point_label: str = "查询点",
) -> go.Figure:
    """
    创建时间序列图表。

    Args:
        times: 时间数组
        wave_heights: 海浪高度数组
        point_label: 点的标签

    Returns:
        Plotly Figure 对象
    """
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=times,
            y=wave_heights,
            mode="lines+markers",
            name=point_label,
            line=dict(color="blue", width=2),
            marker=dict(size=4),
            hovertemplate=(
                "时间: %{x:.2f} s<br>"
                "海浪高度: %{y:.4f} m<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        title=dict(
            text=f"{point_label} 海浪高度时间序列",
            font=dict(size=16),
            x=0.5,
            xanchor="center",
        ),
        xaxis_title="时间 (s)",
        yaxis_title="海浪高度 (m)",
        width=800,
        height=400,
        margin=dict(l=60, r=60, t=80, b=60),
        hovermode="x unified",
    )

    return fig

