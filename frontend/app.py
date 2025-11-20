# -*- coding: utf-8 -*-
"""
Streamlit 前端应用主文件。

时变海浪环境模型可视化界面。
"""

import streamlit as st
import numpy as np
import sys
from pathlib import Path

# 添加当前目录到 Python 路径
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from utils.api_client import APIClient, BACKEND_URL
from utils.data_converter import frames_to_grid_data, get_frame_at_time
from utils.visualization import create_heatmap, create_time_series_chart

# 页面配置
st.set_page_config(
    page_title="WaveEnv - 时变海浪环境模型",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 初始化 session_state
if "simulation_id" not in st.session_state:
    st.session_state.simulation_id = None
if "frames" not in st.session_state:
    st.session_state.frames = []
if "lon_grid" not in st.session_state:
    st.session_state.lon_grid = None
if "lat_grid" not in st.session_state:
    st.session_state.lat_grid = None
if "height_grid" not in st.session_state:
    st.session_state.height_grid = None
if "times" not in st.session_state:
    st.session_state.times = None
if "current_time_idx" not in st.session_state:
    st.session_state.current_time_idx = 0
if "is_playing" not in st.session_state:
    st.session_state.is_playing = False
if "query_result" not in st.session_state:
    st.session_state.query_result = None
if "query_lon" not in st.session_state:
    st.session_state.query_lon = 120.25
if "query_lat" not in st.session_state:
    st.session_state.query_lat = 30.25
if "query_time" not in st.session_state:
    st.session_state.query_time = 0.0
if "last_play_time" not in st.session_state:
    st.session_state.last_play_time = None


def render_parameter_config():
    """渲染参数配置侧边栏。"""
    with st.sidebar:
        st.header("⚙️ 参数配置")

        # 基础/高级模式切换
        mode = st.radio("配置模式", ["基础", "高级"], horizontal=True)

        # 区域配置
        st.subheader("📍 区域设置")
        lon_min = st.number_input("最小经度 (°)", value=120.0, step=0.1, format="%.4f")
        lon_max = st.number_input("最大经度 (°)", value=120.5, step=0.1, format="%.4f")
        lat_min = st.number_input("最小纬度 (°)", value=30.0, step=0.1, format="%.4f")
        lat_max = st.number_input("最大纬度 (°)", value=30.5, step=0.1, format="%.4f")
        depth_min = st.number_input("最小深度 (m)", value=50.0, step=1.0, format="%.1f")
        depth_max = st.number_input("最大深度 (m)", value=100.0, step=1.0, format="%.1f")

        # 风场参数
        st.subheader("💨 风场参数")
        wind_speed = st.slider("风速 (m/s)", 0.0, 40.0, 10.0, step=0.5)
        wind_direction_deg = st.slider("风向 (°)", 0.0, 360.0, 270.0, step=1.0)
        if mode == "高级":
            reference_height_m = st.number_input("参考高度 (m)", value=10.0, step=0.1)
        else:
            reference_height_m = 10.0

        # 波浪谱参数
        st.subheader("🌊 波浪谱参数")
        spectrum_model_type = st.selectbox("光谱模型", ["PM", "JONSWAP"], index=0)
        Hs = st.slider("显著波高 (m)", 0.0, 15.0, 2.0, step=0.1)
        Tp = st.slider("峰值周期 (s)", 2.0, 20.0, 8.0, step=0.1)
        if mode == "高级":
            main_wave_direction_deg = st.number_input(
                "主浪向 (°)", value=None, step=1.0, help="留空则使用风向"
            )
            directional_spread_deg = st.slider("方向扩散 (°)", 5.0, 90.0, 30.0, step=1.0)
            if spectrum_model_type == "JONSWAP":
                gamma = st.slider("峰锐系数", 1.0, 7.0, 3.3, step=0.1)
            else:
                gamma = 3.3
        else:
            main_wave_direction_deg = None
            directional_spread_deg = 30.0
            gamma = 3.3

        # 离散化参数
        st.subheader("📐 离散化参数")
        dx = st.number_input("经度间隔 (°)", value=0.05, step=0.01, format="%.3f", min_value=0.001)
        dy = st.number_input("纬度间隔 (°)", value=0.05, step=0.01, format="%.3f", min_value=0.001)
        max_points = st.number_input("最大点数", value=5000, step=100, min_value=100)

        # 时间参数
        st.subheader("⏱️ 时间参数")
        dt_backend = st.number_input("时间步长 (s)", value=0.2, step=0.1, format="%.2f", min_value=0.01)
        T_total = st.number_input("总时长 (s)", value=10.0, step=1.0, format="%.1f", min_value=0.1)

        # 构建配置字典
        config = {
            "region": {
                "lon_min": lon_min,
                "lon_max": lon_max,
                "lat_min": lat_min,
                "lat_max": lat_max,
                "depth_min": depth_min,
                "depth_max": depth_max,
            },
            "wind": {
                "wind_speed": wind_speed,
                "wind_direction_deg": wind_direction_deg,
                "reference_height_m": reference_height_m,
            },
            "spectrum": {
                "spectrum_model_type": spectrum_model_type,
                "Hs": Hs,
                "Tp": Tp,
                "main_wave_direction_deg": main_wave_direction_deg,
                "directional_spread_deg": directional_spread_deg,
                "gamma": gamma,
            },
            "discretization": {
                "dx": dx,
                "dy": dy,
                "max_points": max_points,
            },
            "time": {
                "dt_backend": dt_backend,
                "T_total": T_total,
            },
        }

        return config


def check_backend_connection():
    """检查后端服务连接。"""
    import httpx
    import socket
    
    # 先检查端口是否开放
    try:
        url_part = BACKEND_URL.replace("http://", "").replace("https://", "")
        if ":" in url_part:
            host, port = url_part.split(":")
            port = int(port)
        else:
            host = url_part
            port = 8000
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(("127.0.0.1", port))
        sock.close()
        if result != 0:
            # 端口未开放
            return False
    except Exception:
        # 如果端口检查失败，继续尝试 HTTP 请求
        pass
    
    # 尝试 HTTP 连接（禁用代理）
    try:
        with httpx.Client(
            timeout=10.0,
            follow_redirects=True,
            proxies=None,  # 禁用代理，避免 502 错误
        ) as client:
            # 先尝试根路径
            try:
                response = client.get(f"{BACKEND_URL}/", timeout=5.0)
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if "message" in data:
                            return True
                    except:
                        # 如果不是 JSON，也认为连接成功（状态码 200）
                        return True
            except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError):
                # 尝试使用 127.0.0.1 而不是 localhost
                try:
                    alt_url = BACKEND_URL.replace("localhost", "127.0.0.1")
                    response = client.get(f"{alt_url}/", timeout=5.0)
                    if response.status_code == 200:
                        return True
                except:
                    pass
            
            # 如果根路径失败，尝试健康检查端点
            try:
                response = client.get(f"{BACKEND_URL}/health", timeout=5.0)
                if response.status_code == 200:
                    return True
            except:
                pass
            
            return False
    except Exception as e:
        # 调试信息
        print(f"Backend connection check error: {type(e).__name__}: {e}")
        return False


def main():
    """主函数。"""
    # 标题
    st.title("🌊 时变海浪环境模型系统")
    st.markdown("---")

    # 检查后端连接（使用缓存，避免每次都检查）
    if "backend_checked" not in st.session_state:
        st.session_state.backend_checked = False
        st.session_state.backend_available = False
    
    if not st.session_state.backend_checked:
        with st.spinner("正在检查后端连接..."):
            st.session_state.backend_available = check_backend_connection()
            st.session_state.backend_checked = True
    
    if not st.session_state.backend_available:
        st.error(
            f"⚠️ 无法连接到后端服务 ({BACKEND_URL})\n\n"
            "请确保后端服务已启动：\n"
            "```bash\n"
            "cd backend\n"
            "uvicorn app.main:app --reload\n"
            "```\n\n"
            "**故障排除：**\n"
            "1. 检查后端是否在 `http://localhost:8000` 运行\n"
            "2. 在浏览器中访问 `http://localhost:8000/docs` 确认后端正常\n"
            "3. 检查防火墙设置\n"
            "4. 如果后端在不同端口，请修改 `frontend/utils/api_client.py` 中的 `BACKEND_URL`"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 重新检查连接", type="primary"):
                st.session_state.backend_checked = False
                st.rerun()
        with col2:
            if st.button("⏭️ 跳过检查（继续使用）"):
                st.session_state.backend_available = True
                st.session_state.backend_checked = True
                st.rerun()
        
        st.stop()

    # 参数配置
    config = render_parameter_config()

    # 开始模拟按钮
    with st.sidebar:
        st.markdown("---")
        if st.button("🚀 开始模拟", type="primary", use_container_width=True):
            with st.spinner("正在创建模拟任务..."):
                try:
                    api_client = APIClient()
                    response = api_client.create_simulation(
                        region=config["region"],
                        wind=config["wind"],
                        spectrum=config["spectrum"],
                        discretization=config["discretization"],
                        time_config=config["time"],
                    )

                    st.session_state.simulation_id = response["simulation_id"]
                    st.success(f"模拟任务创建成功！ID: {response['simulation_id'][:8]}...")

                    # 获取模拟结果
                    with st.spinner("正在获取模拟结果..."):
                        frames_response = api_client.get_frames(
                            st.session_state.simulation_id,
                            max_frames=100,
                        )
                        st.session_state.frames = frames_response["frames"]

                        # 转换为网格数据
                        if st.session_state.frames:
                            (
                                st.session_state.lon_grid,
                                st.session_state.lat_grid,
                                st.session_state.height_grid,
                                st.session_state.times,
                            ) = frames_to_grid_data(st.session_state.frames)
                            st.session_state.current_time_idx = 0
                            st.success(f"获取到 {len(st.session_state.frames)} 个时间帧")

                    api_client.close()

                except Exception as e:
                    st.error(f"模拟失败: {str(e)}")
                    st.session_state.simulation_id = None
                    st.session_state.frames = []

    # 主内容区
    if st.session_state.simulation_id and st.session_state.frames:
        # 控制面板
        st.subheader("🎮 控制面板")
        control_col1, control_col2, control_col3, control_col4 = st.columns([1, 1, 1, 3])

        with control_col1:
            # 使用 key 确保按钮状态正确
            play_pause_key = "play_pause_btn"
            if st.button("▶️ 播放" if not st.session_state.is_playing else "⏸️ 暂停", key=play_pause_key):
                st.session_state.is_playing = not st.session_state.is_playing
                # 如果停止播放，清除播放时间记录
                if not st.session_state.is_playing:
                    st.session_state.last_play_time = None
                st.rerun()

        with control_col2:
            # 使用 key 确保按钮响应
            reset_key = "reset_btn"
            if st.button("⏹️ 重置", key=reset_key):
                st.session_state.current_time_idx = 0
                st.session_state.is_playing = False
                st.session_state.last_play_time = None
                st.rerun()

        with control_col3:
            play_speed = st.selectbox("播放速度", [0.5, 1.0, 2.0, 5.0], index=1)

        # 播放状态显示（不在这里更新索引，避免画面不显示）
        if st.session_state.is_playing:
            progress = (st.session_state.current_time_idx + 1) / len(st.session_state.times)
            st.progress(progress, text=f"播放中... {st.session_state.current_time_idx + 1}/{len(st.session_state.times)} (速度: {play_speed}x)")

        # 显示可视化
        col1, col2 = st.columns([3, 1])

        with col1:
            # 时间滑块
            if st.session_state.times is not None and len(st.session_state.times) > 0:
                # 如果正在播放，禁用滑块（避免冲突）
                time_idx = st.slider(
                    "时间",
                    0,
                    len(st.session_state.times) - 1,
                    st.session_state.current_time_idx,
                    key="time_slider",
                    disabled=st.session_state.is_playing,  # 播放时禁用滑块
                )
                
                # 如果不在播放状态，允许滑块控制
                if not st.session_state.is_playing:
                    if time_idx != st.session_state.current_time_idx:
                        st.session_state.current_time_idx = time_idx
                        st.rerun()
                # 如果正在播放，强制使用 session_state 中的索引（滑块会自动跟随更新）

                # 使用当前索引获取数据
                current_time = st.session_state.times[st.session_state.current_time_idx]
                current_height = st.session_state.height_grid[st.session_state.current_time_idx]

                # 创建热力图
                fig = create_heatmap(
                    st.session_state.lon_grid,
                    st.session_state.lat_grid,
                    current_height,
                    current_time,
                )
                st.plotly_chart(fig, use_container_width=True, key=f"heatmap_{st.session_state.current_time_idx}")

        with col2:
            st.subheader("📊 信息")
            if st.session_state.simulation_id:
                st.metric("模拟ID", st.session_state.simulation_id[:8] + "...")
            if st.session_state.times is not None:
                st.metric("当前时间", f"{current_time:.2f} s")
                st.metric("总帧数", len(st.session_state.times))
                st.metric("最大高度", f"{np.max(current_height):.4f} m")
                st.metric("最小高度", f"{np.min(current_height):.4f} m")

        # 单点查询（独立于播放状态）
        st.markdown("---")
        st.subheader("📍 单点查询")

        query_col1, query_col2, query_col3 = st.columns([1, 1, 1])
        with query_col1:
            query_lon = st.number_input(
                "经度 (°)", 
                value=st.session_state.query_lon, 
                step=0.01, 
                format="%.4f",
                key="query_lon_input"
            )
            st.session_state.query_lon = query_lon
        with query_col2:
            query_lat = st.number_input(
                "纬度 (°)", 
                value=st.session_state.query_lat, 
                step=0.01, 
                format="%.4f",
                key="query_lat_input"
            )
            st.session_state.query_lat = query_lat
        with query_col3:
            # 查询时间独立于播放时间，但提供快捷按钮
            col_time, col_btn = st.columns([3, 1])
            with col_time:
                query_time = st.number_input(
                    "时间 (s)",
                    value=st.session_state.query_time,
                    step=0.1,
                    format="%.2f",
                    key="query_time_input"
                )
                st.session_state.query_time = query_time
            with col_btn:
                if st.button("📌", help="使用当前播放时间", key="sync_time_btn"):
                    st.session_state.query_time = float(current_time)
                    st.rerun()

        query_button_col1, query_button_col2 = st.columns([1, 4])
        with query_button_col1:
            if st.button("🔍 查询", type="primary", use_container_width=True):
                try:
                    api_client = APIClient()
                    result = api_client.query_point(
                        st.session_state.simulation_id,
                        query_lon,
                        query_lat,
                        query_time,
                    )
                    st.session_state.query_result = result
                    api_client.close()
                    st.rerun()
                except Exception as e:
                    st.error(f"查询失败: {str(e)}")

        # 显示查询结果
        if st.session_state.query_result:
            result = st.session_state.query_result
            st.success(
                f"✅ 查询成功！\n\n"
                f"**位置**: ({result['lon']:.4f}°, {result['lat']:.4f}°)\n\n"
                f"**时间**: {result['time']:.2f} s\n\n"
                f"**海浪高度**: {result['wave_height']:.4f} m"
            )

    else:
        # 未开始模拟时的提示
        st.info("👈 请在左侧配置参数并点击「开始模拟」按钮")


if __name__ == "__main__":
    main()
