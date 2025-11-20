# -*- coding: utf-8 -*-
"""
可视化模块。

使用 Plotly 生成海浪高度场可视化图表。
"""

import plotly.graph_objects as go
import numpy as np
from typing import Tuple


def create_heatmap(
    lon_grid: np.ndarray,
    lat_grid: np.ndarray,
    height_grid: np.ndarray,
    time: float,
    title: str = None,
) -> go.Figure:
    """
    创建海浪高度场热力图。

    Args:
        lon_grid: 经度网格 (n_lat, n_lon)
        lat_grid: 纬度网格 (n_lat, n_lon)
        height_grid: 海浪高度场 (n_lat, n_lon) - 单帧数据
        time: 当前时间（秒）
        title: 图表标题

    Returns:
        Plotly Figure 对象
    """
    # 计算高度范围
    vmin = float(np.nanmin(height_grid))
    vmax = float(np.nanmax(height_grid))

    # 创建热力图
    fig = go.Figure(
        data=go.Contour(
            x=lon_grid[0, :],  # 第一行的经度值
            y=lat_grid[:, 0],  # 第一列的纬度值
            z=height_grid,
            colorscale="Viridis",
            colorbar=dict(
                title=dict(
                    text="海浪高度 (m)",
                    font=dict(size=12),
                ),
            ),
            contours=dict(
                showlines=True,
                showlabels=True,
                labelfont=dict(size=10),
            ),
            hovertemplate=(
                "经度: %{x:.4f}°<br>"
                "纬度: %{y:.4f}°<br>"
                "海浪高度: %{z:.4f} m<extra></extra>"
            ),
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
    )

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

