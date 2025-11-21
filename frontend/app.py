# -*- coding: utf-8 -*-
"""
Streamlit 前端应用主文件。

时变海浪环境模型可视化界面。
"""

import streamlit as st
import numpy as np
import sys
import time
from pathlib import Path
from datetime import datetime
import httpx

# 添加当前目录到 Python 路径
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

from utils.api_client import APIClient, BACKEND_URL
from utils.data_converter import frames_to_grid_data, get_frame_at_time
from utils.visualization import create_heatmap, create_time_series_chart

# 创建 Session 级别的 API 客户端，实现连接复用且会话隔离
# 每个浏览器标签页（Session）拥有独立的连接池，互不干扰
def get_api_client():
    """获取当前 Session 的 API 客户端实例"""
    if "api_client" not in st.session_state:
        st.session_state.api_client = APIClient()
    return st.session_state.api_client

STATUS_LABELS = {
    "pending": "等待中",
    "running": "运行中",
    "paused": "已暂停",
    "stopped": "已停止",
    "completed": "已完成",
    "failed": "失败",
}

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
if "simulation_start_time" not in st.session_state:
    st.session_state.simulation_start_time = None  # 模拟启动时的真实时间戳
if "dt_frontend" not in st.session_state:
    st.session_state.dt_frontend = 1.0  # 前端显示间隔（秒）
if "needs_refresh" not in st.session_state:
    st.session_state.needs_refresh = False
if "simulation_completed" not in st.session_state:
    st.session_state.simulation_completed = False
if "data_changed" not in st.session_state:
    st.session_state.data_changed = False
if "_user_interaction" not in st.session_state:
    st.session_state._user_interaction = False
if "_query_button_clicked" not in st.session_state:
    st.session_state._query_button_clicked = False
if "_sync_button_clicked" not in st.session_state:
    st.session_state._sync_button_clicked = False
if "_prev_use_latest_frame" not in st.session_state:
    st.session_state._prev_use_latest_frame = False
if "_skip_chart_update" not in st.session_state:
    st.session_state._skip_chart_update = False
if "simulation_status" not in st.session_state:
    st.session_state.simulation_status = None
if "_control_button_clicked" not in st.session_state:
    st.session_state._control_button_clicked = False  # 控制按钮（暂停/恢复/停止）点击标记


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
        dt_backend = st.number_input("后端时间步长 (s)", value=0.2, step=0.1, format="%.2f", min_value=0.01, help="后端计算的时间步长")
        
        # 缓存配置
        st.subheader("💾 缓存配置")
        use_cache_limit = st.checkbox("启用帧缓存限制", value=False, help="限制内存中保留的帧数量，淘汰过期的旧帧")
        if use_cache_limit:
            cache_retention_time = st.number_input(
                "缓存保留时间 (s)", 
                value=60.0, 
                step=10.0, 
                format="%.1f", 
                min_value=1.0,
                help="保留最近 N 秒的帧数据，超过此时间的旧帧将被自动淘汰。None 表示不限制（可能占用大量内存）"
            )
        else:
            cache_retention_time = None
        
        # 前端显示参数
        st.subheader("📺 显示参数")
        dt_frontend = st.number_input("前端显示间隔 (s)", value=1.0, step=0.05, format="%.2f", min_value=0.01, help="前端图片显示的刷新间隔（秒），只影响图片显示频率，不影响单点查询响应速度")
        enable_chart = st.checkbox("启用实时等高线图", value=True, help="关闭后将不显示等高线图，可大幅提升界面响应速度，但仍可进行单点查询")

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
                "cache_retention_time": cache_retention_time,
            },
            "display": {
                "dt_frontend": dt_frontend,
                "enable_chart": enable_chart,
            },
        }

        return config


def check_backend_connection():
    """检查后端服务连接。"""
    import httpx
    import socket
    
    # 解析后端 URL
    url_part = BACKEND_URL.replace("http://", "").replace("https://", "")
    if ":" in url_part:
        host, port = url_part.split(":", 1)  # 只分割第一个冒号，避免 IPv6 问题
        try:
            port = int(port)
        except ValueError:
            port = 8000
    else:
        host = url_part
        port = 8000
    
    print(f"[连接检查] 尝试连接到后端: {BACKEND_URL} (host={host}, port={port})")
    
    # 先检查端口是否开放（仅当 host 是 localhost 或 127.0.0.1 时）
    # 在 Docker 环境中，使用服务名（如 "backend"）时，socket 检查不可靠
    if host in ("localhost", "127.0.0.1"):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()
            if result != 0:
                # 端口未开放
                print(f"[连接检查] ✗ 端口 {port} 未开放 (错误码: {result})")
                print(f"[连接检查] 提示: 请确保后端服务已启动，运行: cd backend && uvicorn app.main:app --reload")
                return False
            else:
                print(f"[连接检查] ✓ 端口 {port} 已开放")
        except Exception as e:
            # 如果端口检查失败，继续尝试 HTTP 请求
            print(f"[连接检查] 端口检查异常: {e}，继续尝试 HTTP 请求")
            pass
    
    # 尝试 HTTP 连接（禁用代理）
    try:
        # 使用连接池限制，避免创建过多连接
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
        with httpx.Client(
            timeout=5.0,  # 减少超时时间，更快失败
            follow_redirects=True,
            proxies=None,  # 禁用代理，避免 502 错误
            limits=limits,
            http2=False,  # 禁用 HTTP/2
        ) as client:
            # 先尝试健康检查端点（最简单）
            try:
                print(f"[连接检查] 尝试访问 /health 端点...")
                response = client.get(f"{BACKEND_URL}/health", timeout=3.0)
                if response.status_code == 200:
                    print(f"[连接检查] ✓ 后端连接成功 (HTTP {response.status_code})")
                    try:
                        health_data = response.json()
                        print(f"[连接检查] 健康状态: {health_data}")
                    except:
                        pass
                    return True
                else:
                    print(f"[连接检查] ✗ /health 返回非 200 状态: {response.status_code}")
                    return False
            except httpx.ConnectError as e:
                print(f"[连接检查] ✗ 连接错误: {e}")
                print(f"[连接检查] 提示: 无法连接到 {BACKEND_URL}，请检查：")
                print(f"[连接检查]   1. 后端服务是否已启动")
                print(f"[连接检查]   2. 端口 {port} 是否正确")
                print(f"[连接检查]   3. 防火墙是否阻止连接")
                # 如果健康检查失败，尝试根路径
                try:
                    print(f"[连接检查] 尝试访问根路径 / ...")
                    response = client.get(f"{BACKEND_URL}/", timeout=3.0)
                    if response.status_code == 200:
                        print(f"[连接检查] ✓ 后端连接成功 (通过根路径, HTTP {response.status_code})")
                        return True
                except httpx.ConnectError:
                    # 尝试使用 127.0.0.1 而不是 localhost
                    if "localhost" in BACKEND_URL:
                        try:
                            alt_url = BACKEND_URL.replace("localhost", "127.0.0.1")
                            print(f"[连接检查] 尝试使用 127.0.0.1 替代 localhost: {alt_url}")
                            response = client.get(f"{alt_url}/health", timeout=3.0)
                            if response.status_code == 200:
                                print(f"[连接检查] ✓ 后端连接成功 (使用 127.0.0.1, HTTP {response.status_code})")
                                return True
                        except Exception as alt_e:
                            print(f"[连接检查] ✗ 使用 127.0.0.1 也失败: {alt_e}")
            except httpx.TimeoutException as e:
                print(f"[连接检查] ✗ 连接超时: {e}")
                print(f"[连接检查] 提示: 后端服务可能未启动或响应缓慢")
            except httpx.RequestError as e:
                print(f"[连接检查] ✗ 请求错误: {e}")
            
            print(f"[连接检查] ✗ 所有连接尝试均失败")
            return False
    except Exception as e:
        # 调试信息
        print(f"[连接检查] ✗ 连接检查异常: {type(e).__name__}: {e}")
        import traceback
        print(f"[连接检查] 详细错误: {traceback.format_exc()}")
        return False


def main():
    """主函数。"""
    # 性能分析：记录脚本开始时间
    script_start_time = time.time()
    
    # 标题
    st.title("🌊 时变海浪环境模型系统")
    st.markdown("---")

    # 检查后端连接（使用缓存，避免每次都检查）
    if "backend_checked" not in st.session_state:
        st.session_state.backend_checked = False
        st.session_state.backend_available = False
    
    if not st.session_state.backend_checked:
        # 直接检查，不使用spinner避免界面变白
        st.session_state.backend_available = check_backend_connection()
        st.session_state.backend_checked = True
    
    if not st.session_state.backend_available:
        st.error(
            f"⚠️ **无法连接到后端服务**\n\n"
            f"**后端地址**: `{BACKEND_URL}`\n\n"
            "**请按以下步骤排查：**\n\n"
            "### 1. 检查后端服务是否启动\n"
            "```bash\n"
            "cd backend\n"
            "uvicorn app.main:app --reload\n"
            "```\n\n"
            "### 2. 验证后端服务\n"
            f"- 在浏览器中访问 `{BACKEND_URL}/docs` 查看 API 文档\n"
            f"- 访问 `{BACKEND_URL}/health` 查看健康状态\n"
            f"- 如果无法访问，说明后端服务未启动或端口不正确\n\n"
            "### 3. 检查配置\n"
            "- 如果使用 Docker，确保后端容器正在运行\n"
            "- 如果后端在不同端口，请设置环境变量：\n"
            "  ```bash\n"
            "  export BACKEND_URL=http://localhost:你的端口\n"
            "  ```\n"
            "- 或修改 `frontend/utils/api_client.py` 中的 `BACKEND_URL`\n\n"
            "### 4. 查看控制台日志\n"
            "- 查看浏览器控制台（F12）是否有连接错误信息\n"
            "- 查看 Streamlit 终端是否有 `[连接检查]` 日志\n\n"
            "### 5. 常见问题\n"
            "- **防火墙阻止**：检查防火墙是否允许访问后端端口\n"
            "- **端口被占用**：检查是否有其他程序占用后端端口\n"
            "- **Docker 网络**：如果使用 Docker，确保前端和后端在同一网络中"
        )
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🔄 重新检查连接", type="primary"):
                st.session_state.backend_checked = False
                st.rerun()
        with col2:
            if st.button("🔍 详细诊断", help="显示详细的连接诊断信息"):
                st.session_state.show_connection_diagnostics = True
                st.rerun()
        with col3:
            if st.button("⏭️ 跳过检查（继续使用）"):
                st.session_state.backend_available = True
                st.session_state.backend_checked = True
                st.rerun()
        
        # 显示详细诊断信息
        if st.session_state.get("show_connection_diagnostics", False):
            import os
            with st.expander("🔍 连接诊断详情", expanded=True):
                st.code(f"""
后端 URL: {BACKEND_URL}
环境变量 BACKEND_URL: {os.getenv('BACKEND_URL', '未设置')}

诊断步骤：
1. 检查环境变量...
2. 解析 URL...
3. 尝试连接...
                """, language="text")
                
                # 执行详细诊断
                import socket
                url_part = BACKEND_URL.replace("http://", "").replace("https://", "")
                if ":" in url_part:
                    host, port = url_part.split(":")
                    port = int(port)
                else:
                    host = url_part
                    port = 8000
                
                st.write(f"**解析结果**: host=`{host}`, port=`{port}`")
                
                # 测试端口
                if host in ("localhost", "127.0.0.1"):
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(2)
                        result = sock.connect_ex((host, port))
                        sock.close()
                        if result == 0:
                            st.success(f"✓ 端口 {port} 已开放")
                        else:
                            st.error(f"✗ 端口 {port} 未开放（错误码: {result}）")
                    except Exception as e:
                        st.warning(f"端口检查异常: {e}")
                
                # 测试 HTTP 连接
                try:
                    with httpx.Client(timeout=5.0) as client:
                        try:
                            response = client.get(f"{BACKEND_URL}/health")
                            st.success(f"✓ HTTP 连接成功: {response.status_code}")
                            st.json(response.json())
                        except httpx.ConnectError as e:
                            st.error(f"✗ HTTP 连接失败: {e}")
                        except Exception as e:
                            st.error(f"✗ HTTP 请求异常: {e}")
                except Exception as e:
                    st.error(f"✗ 创建 HTTP 客户端失败: {e}")
                
                if st.button("关闭诊断"):
                    st.session_state.show_connection_diagnostics = False
                    st.rerun()
        
        st.stop()

    # 参数配置
    config = render_parameter_config()

    # 开始模拟按钮
    with st.sidebar:
        st.markdown("---")
        if st.button("🚀 开始模拟", type="primary", use_container_width=True):
            # 直接执行，不使用spinner避免界面变白阻塞
            try:
                api_client = get_api_client()
                
                # 检查当前 Session 是否有正在运行的仿真任务
                # 只停止当前 Session 自己的任务，不影响其他 Session
                current_simulation_id = st.session_state.get("simulation_id")
                if current_simulation_id:
                    try:
                        # 检查当前任务的状态
                        frames_response = api_client.get_frames(
                            current_simulation_id,
                            time=-1,
                            timeout=2.0,
                        )
                        current_status = frames_response.get("status", "unknown")
                        
                        # 如果当前任务正在运行，先停止它
                        if current_status in ("running", "paused"):
                            st.info(f"检测到当前 Session 有运行中的任务 ({current_simulation_id[:8]}...)，正在停止...")
                            try:
                                api_client.stop_simulation(current_simulation_id, timeout=3.0)
                                st.success("已停止当前 Session 的任务")
                            except Exception as stop_error:
                                st.warning(f"停止当前任务时出错: {stop_error}，继续创建新任务...")
                            
                            # 清空当前 Session 的状态
                            st.session_state.simulation_id = None
                            st.session_state.frames = []
                            st.session_state.simulation_status = None
                            st.session_state.is_playing = False
                            
                            # 等待一小段时间，确保任务已停止
                            time.sleep(0.5)
                    except Exception as check_error:
                        # 如果检查失败（可能是任务不存在），继续创建新任务
                        st.info("当前 Session 没有运行中的任务，创建新任务...")
                
                # 创建新的模拟任务
                response = api_client.create_simulation(
                    region=config["region"],
                    wind=config["wind"],
                    spectrum=config["spectrum"],
                    discretization=config["discretization"],
                    time_config=config["time"],
                )

                st.session_state.simulation_id = response["simulation_id"]
                st.session_state.simulation_status = response.get("status", "running")
                
                # 记录模拟启动的真实时间戳（作为基础时间）
                st.session_state.simulation_start_time = time.time()
                st.session_state.dt_frontend = config["display"]["dt_frontend"]
                st.session_state.enable_chart = config["display"]["enable_chart"]
                
                st.success(f"模拟任务创建成功！ID: {response['simulation_id'][:8]}...")
                
                # 自动开始播放（实时显示）
                st.session_state.is_playing = True
                st.session_state.current_time_idx = 0
                st.session_state.last_play_time = None  # 初始化最后刷新时间

                # 尝试获取初始帧（t=0），如果还没有则等待
                # 添加重试机制，因为后端生成初始帧需要一些时间
                initial_frame_obtained = False
                max_retries = 5
                retry_delay = 0.5  # 每次重试等待 0.5 秒
                
                for retry in range(max_retries):
                    try:
                        frames_response = api_client.get_frames(
                            st.session_state.simulation_id,
                            time=0.0,  # 获取初始帧
                            timeout=2.0,  # 短超时，避免长时间阻塞
                        )
                        
                        if frames_response.get("frames") and len(frames_response["frames"]) > 0:
                            initial_frame = frames_response["frames"][0]
                            st.session_state.frames = [initial_frame]
                            
                            # 转换为网格数据（如果启用图表）
                            if st.session_state.enable_chart:
                                (
                                    st.session_state.lon_grid,
                                    st.session_state.lat_grid,
                                    st.session_state.height_grid,
                                    st.session_state.times,
                                ) = frames_to_grid_data(st.session_state.frames)
                                st.session_state.current_time_idx = 0
                            
                            initial_frame_obtained = True
                            st.success(f"获取到初始帧")
                            break
                    except httpx.HTTPStatusError as e:
                        if e.response.status_code == 404:
                            # 404 表示帧还没有生成，等待后重试
                            if retry < max_retries - 1:
                                time.sleep(retry_delay)
                                continue
                            else:
                                # 最后一次重试失败，设置空frames，后续会自动获取
                                st.session_state.frames = []
                                st.info("模拟任务已创建，等待初始帧生成...（这可能需要几秒钟）")
                                break
                        else:
                            # 其他 HTTP 错误，抛出异常
                            raise
                    except Exception as e:
                        # 其他异常，如果是最后一次重试则优雅处理
                        if retry < max_retries - 1:
                            time.sleep(retry_delay)
                            continue
                        else:
                            st.warning(f"获取初始帧时出错: {e}，后续会自动重试...")
                            st.session_state.frames = []
                            break
                
                if not initial_frame_obtained:
                    # 如果所有重试都失败，设置空frames，后续会自动获取
                    st.session_state.frames = []
                    st.info("模拟任务已创建，等待初始帧生成...（这可能需要几秒钟）")

                # api_client.close()  # 不再关闭，因为使用全局单例复用连接

            except Exception as e:
                st.error(f"模拟失败: {str(e)}")
                st.session_state.simulation_id = None
                st.session_state.frames = []
                st.session_state.simulation_status = None

    # 主内容区
    # 如果有模拟任务，即使还没有帧数据，也显示界面
    if st.session_state.simulation_id:
        # ===== 用户交互检测（必须在所有逻辑之前） =====
        # 检查是否是由用户交互触发的（复选框、按钮等）
        # 使用多个来源检测用户交互：
        # 1. 已有的_user_interaction标记
        # 2. 检查复选框状态是否变化（在复选框创建前）
        prev_use_latest = st.session_state.get("_prev_use_latest_frame", st.session_state.get("use_latest_frame", False))
        
        # 检查查询按钮是否被点击（通过检查session_state中是否设置了标记）
        # 注意：不要在这里清除标记，应该在脚本末尾清除，以确保整个脚本运行期间都能检测到
        query_button_clicked = st.session_state.get("_query_button_clicked", False)
        
        # 检查同步时间按钮是否被点击
        sync_button_clicked = st.session_state.get("_sync_button_clicked", False)
        
        # 检查控制按钮是否被点击
        control_button_clicked = st.session_state.get("_control_button_clicked", False)
        
        # 综合判断是否为用户交互
        is_user_interaction = (
            st.session_state.get("_user_interaction", False) or
            query_button_clicked or
            sync_button_clicked or
            bool(control_button_clicked)  # 控制按钮点击也算用户交互
        )
        
        # 如果检测到用户交互，完全跳过自动刷新逻辑
        if is_user_interaction:
            # 完全跳过自动刷新逻辑，直接到显示部分
            skip_auto_refresh = True
            st.session_state._skip_chart_update = True  # 标记跳过图表更新
            # 调试日志
            if query_button_clicked:
                print(f"[DEBUG] 查询按钮点击，跳过自动刷新")
        else:
            skip_auto_refresh = False
            st.session_state._skip_chart_update = False  # 允许图表更新
        
        # ===== 自动刷新逻辑（只在非用户交互时执行） =====
        # 即使没有帧数据，也要尝试获取
        auto_refresh_start = time.time()
        current_real_time = time.time()  # 提前定义，避免作用域问题
        
        if not skip_auto_refresh and st.session_state.simulation_start_time is not None:
            print(f"[性能分析] 进入自动刷新逻辑")
            # 确保播放状态为True（自动实时显示）
            if not st.session_state.is_playing:
                st.session_state.is_playing = True
            
            # 在播放状态下，持续刷新以更新画面（非用户交互时）
            if st.session_state.is_playing:
                # 计算当前真实时间与启动时间的差值
                current_real_time = time.time()
                real_time_elapsed = current_real_time - st.session_state.simulation_start_time
                
                # 计算模拟时间：应该基于已生成的帧数，而不是真实时间
                # 因为后端计算需要时间，真实时间会超过模拟时间
                if st.session_state.times is not None and len(st.session_state.times) > 0:
                    # 使用最后一帧的时间作为当前模拟时间（最准确）
                    simulation_time = st.session_state.times[-1]
                else:
                    # 如果还没有帧，使用真实时间作为估算
                    simulation_time = real_time_elapsed
                
                # 从后端获取最新帧（因为后端在流式计算中，可能会有新帧产生）
                # 使用更智能的更新策略：根据刷新间隔调整检查频率
                check_for_new_frames = False
                if "last_frame_check_time" not in st.session_state:
                    st.session_state.last_frame_check_time = None
                
                # 计算检查间隔（至少2秒，但不超过5秒，避免频繁请求导致阻塞）
                # dt_frontend 只用于控制图片显示的刷新频率，不影响单点查询
                # 增加最小间隔到2秒，减少请求频率，避免阻塞
                check_interval = min(max(st.session_state.dt_frontend * 5, 2.0), 5.0)
                
                if st.session_state.last_frame_check_time is None:
                    # 首次检查
                    check_for_new_frames = True
                    st.session_state.last_frame_check_time = current_real_time
                else:
                    # 根据配置的刷新间隔检查新帧
                    elapsed_since_last_check = current_real_time - st.session_state.last_frame_check_time
                    if elapsed_since_last_check >= check_interval:
                        check_for_new_frames = True
                        st.session_state.last_frame_check_time = current_real_time
                
                if check_for_new_frames:
                    try:
                        # 使用非阻塞方式获取帧数据（快速超时，避免长时间阻塞）
                        frame_fetch_start = time.time()
                        api_client = get_api_client()
                        # 获取最新帧（用于图片显示）
                        # 使用独立的短超时（5秒），避免阻塞单点查询操作
                        # 注意：这个操作只用于图片显示刷新，不影响单点查询
                        # 进一步减少超时时间，确保不会长时间阻塞
                        frames_response = api_client.get_frames(
                            st.session_state.simulation_id,
                            time=-1,  # 获取最新帧
                            timeout=5.0,  # 5秒超时（从8秒减少到5秒），避免长时间阻塞
                        )
                        frame_fetch_time = time.time() - frame_fetch_start
                        print(f"[性能分析] 获取帧数据耗时: {frame_fetch_time*1000:.2f} ms")
                        
                        # 检查模拟状态
                        simulation_status = frames_response.get("status", "unknown")
                        st.session_state.simulation_status = simulation_status
                        # 根据状态调整本地控制逻辑
                        if simulation_status in ("completed", "stopped"):
                            if not st.session_state.get("simulation_completed", False):
                                st.session_state.simulation_completed = True
                                st.session_state.is_playing = False
                        elif simulation_status == "paused":
                            st.session_state.is_playing = False
                            st.session_state.simulation_completed = False
                        elif simulation_status == "running":
                            st.session_state.simulation_completed = False
                        
                        # 更新frames列表（如果有了新的帧）
                        if frames_response.get("frames") and len(frames_response["frames"]) > 0:
                            new_frame = frames_response["frames"][0]  # 只返回一个帧
                            new_frame_time = new_frame.get("time", 0)
                            
                            # 检查是否有新的帧（通过比较时间）
                            has_new_frame = True
                            if st.session_state.frames and len(st.session_state.frames) > 0:
                                latest_frame_time = st.session_state.frames[-1].get("time", -1)
                                if new_frame_time <= latest_frame_time:
                                    # 没有新帧，不需要更新
                                    has_new_frame = False
                            
                            if has_new_frame:
                                # 有新帧，添加到frames列表
                                if st.session_state.frames is None:
                                    st.session_state.frames = []
                                st.session_state.frames.append(new_frame)
                                
                                # 优化：只在有新帧时才转换数据，但限制最大帧数避免内存问题
                                # 限制保留的帧数，只保留最近的 N 帧（如最近100帧），避免内存和性能问题
                                max_frames_to_keep = 100
                                if len(st.session_state.frames) > max_frames_to_keep:
                                    # 保留最近的帧
                                    st.session_state.frames = st.session_state.frames[-max_frames_to_keep:]
                                
                                # 重新转换为网格数据（这个操作可能较耗时）
                                # 只有启用图表时才需要转换，否则跳过以提升性能
                                if st.session_state.get("enable_chart", True):
                                    # 使用try-except包装，确保转换失败不影响其他功能
                                    # 添加超时保护：如果转换时间过长，放弃本次更新
                                    try:
                                        import time as time_module
                                        convert_start_time = time_module.time()
                                        
                                        (
                                            st.session_state.lon_grid,
                                            st.session_state.lat_grid,
                                            st.session_state.height_grid,
                                            st.session_state.times,
                                        ) = frames_to_grid_data(st.session_state.frames)
                                        
                                        convert_time = time_module.time() - convert_start_time
                                        # 记录数据转换耗时
                                        print(f"[性能分析] frames_to_grid_data转换耗时: {convert_time*1000:.2f} ms ({convert_time:.3f} 秒)")
                                        if convert_time > 2.0:
                                            print(f"[警告] 数据转换耗时过长: {convert_time:.2f} 秒，考虑优化或减少帧数")
                                        
                                        # 标记有数据变化，需要刷新
                                        st.session_state.data_changed = True
                                    except Exception as convert_error:
                                        # 转换失败，但不影响界面响应
                                        print(f"帧数据转换失败: {convert_error}")
                                        st.session_state.data_changed = False
                                else:
                                    # 图表禁用时，跳过数据转换，大幅提升性能
                                    st.session_state.data_changed = False
                            else:
                                # 帧没有变化，不需要刷新
                                st.session_state.data_changed = False
                        else:
                            # 没有帧数据，不需要刷新
                            st.session_state.data_changed = False
                    except (httpx.TimeoutException, httpx.RequestError) as e:
                        # 如果获取失败（超时或网络错误），继续使用已有的frames，不影响界面响应
                        st.session_state.data_changed = False
                        # 静默失败，不中断用户体验（图片显示刷新失败不影响单点查询）
                        pass
                    except Exception as e:
                        # 其他异常也静默处理，不影响界面响应
                        st.session_state.data_changed = False
                        pass
                else:
                    # 本次未检查，标记为未变化
                    st.session_state.data_changed = False
                
                # 记录自动刷新总耗时
                auto_refresh_time = time.time() - auto_refresh_start
                if auto_refresh_time > 0.1:  # 只记录超过100ms的
                    print(f"[性能分析] 自动刷新逻辑总耗时: {auto_refresh_time*1000:.2f} ms")
        else:
            if skip_auto_refresh:
                print(f"[性能分析] 跳过自动刷新逻辑（用户交互）")
                
                # 根据模拟时间找到对应的帧索引
                # 使用最后一帧的时间作为当前模拟时间（最准确，因为这是后端实际生成的）
                if st.session_state.times is not None and len(st.session_state.times) > 0:
                    # 直接使用最后一帧的时间作为当前模拟时间
                    # 这样可以确保模拟时间与后端实际生成的帧时间一致
                    current_simulation_time = st.session_state.times[-1]
                    
                    # 保存之前的帧索引，用于检测变化
                    previous_time_idx = st.session_state.current_time_idx
                    
                    # 当前帧索引应该是最新帧（最后一帧）
                    new_time_idx = len(st.session_state.times) - 1
                    st.session_state.current_time_idx = new_time_idx
                    
                    # 检查是否需要刷新（根据dt_frontend配置刷新一次）
                    # 智能刷新策略：只在有实际变化时才刷新，减少不必要的重绘
                    # 注意：dt_frontend 只控制图片显示的刷新频率，不影响单点查询
                    should_refresh = False
                    
                    # 如果模拟已完成，停止刷新
                    if st.session_state.get("simulation_completed", False):
                        # 模拟已完成，不需要继续刷新
                        should_refresh = False
                    elif st.session_state.last_play_time is None:
                        # 首次刷新，需要rerun来初始化
                        st.session_state.last_play_time = current_real_time
                        should_refresh = True
                    else:
                        elapsed_since_last_refresh = current_real_time - st.session_state.last_play_time
                        # 使用配置的前端刷新间隔（至少1秒，最大5秒，避免过于频繁）
                        # dt_frontend 只用于控制图片显示的刷新频率，不影响单点查询
                        # 增加最小间隔到1秒，减少刷新频率，避免界面卡顿
                        refresh_interval = min(max(st.session_state.dt_frontend * 3, 1.0), 5.0)
                        
                        if elapsed_since_last_refresh >= refresh_interval:
                            # 检查数据是否有变化或帧索引是否变化
                            data_changed = st.session_state.get("data_changed", False)
                            frame_index_changed = new_time_idx != previous_time_idx
                            
                            if data_changed or frame_index_changed:
                                # 只有当数据变化或帧索引变化时才刷新
                                st.session_state.last_play_time = current_real_time
                                should_refresh = True
                            else:
                                # 数据没有变化，更新时间但不刷新，节省资源
                                st.session_state.last_play_time = current_real_time
                                should_refresh = False
                    
                    # 设置刷新标记（仅在需要时）
                    # 添加防抖：如果上次刷新时间太近，跳过本次刷新
                    if should_refresh:
                        # 检查上次刷新时间，避免过于频繁
                        if "last_rerun_time" not in st.session_state:
                            st.session_state.last_rerun_time = 0
                        
                        time_since_last_rerun = current_real_time - st.session_state.last_rerun_time
                        min_rerun_interval = 1.0  # 至少间隔1秒才能再次rerun，避免频繁刷新导致阻塞
                        
                        if time_since_last_rerun >= min_rerun_interval:
                            st.session_state.needs_refresh = True
                            st.session_state.last_rerun_time = current_real_time
                        else:
                            # 太频繁，跳过本次刷新，避免阻塞
                            st.session_state.needs_refresh = False
                    else:
                        # 不需要刷新，清除标记
                        st.session_state.needs_refresh = False
        

        # 显示实时状态信息（始终显示，即使没有数据）
        if st.session_state.simulation_id:
            # 实时状态栏
            status_col1, status_col2, status_col3 = st.columns([2, 1, 1])
            with status_col1:
                status_key = st.session_state.get("simulation_status", "unknown")
                status_label = STATUS_LABELS.get(status_key, "未知")
                
                # 计算实时信息
                # 直接使用最新帧的时间，确保与后端实际生成的最新帧时间一致
                if st.session_state.times is not None and len(st.session_state.times) > 0:
                    # 始终使用最后一帧的时间作为当前模拟时间（最准确）
                    current_time = st.session_state.times[-1]
                    # 同步更新 current_time_idx 到最新帧，保持一致性
                    st.session_state.current_time_idx = len(st.session_state.times) - 1
                    
                    if st.session_state.simulation_start_time is not None:
                        real_time_elapsed = time.time() - st.session_state.simulation_start_time
                    else:
                        real_time_elapsed = 0.0
                    
                    if status_key == "running":
                        st.info(f"🟢 实时运行中 | 模拟时间: {current_time:.2f} s | 真实时间: {real_time_elapsed:.2f} s | 状态: {status_label}")
                    elif status_key == "paused":
                        st.warning(f"⏸️ 已暂停 | 模拟时间: {current_time:.2f} s | 状态: {status_label}")
                    elif status_key in ("completed", "stopped"):
                        st.success(f"✅ 模拟完成 | 最终时间: {current_time:.2f} s | 状态: {status_label}")
                    else:
                        st.info(f"⏳ {status_label} | 模拟时间: {current_time:.2f} s")
                else:
                    st.info(f"⏳ {status_label} | 等待数据...")
            
            with status_col2:
                if st.session_state.times is not None:
                    st.metric("总帧数", len(st.session_state.times))
                else:
                    st.metric("总帧数", 0)
            
            with status_col3:
                if st.session_state.simulation_id:
                    st.metric("任务ID", st.session_state.simulation_id[:8] + "...")

        # 显示可视化
        col1, col2 = st.columns([3, 1])

        with col1:
            # 显示可视化图表（使用Plotly等高线图，支持高度查询）
            # 检查是否启用图表
            if not st.session_state.get("enable_chart", True):
                # 图表已禁用，显示提示信息
                st.info("📊 实时等高线图已禁用（可在左侧参数配置中启用）\n\n✅ 单点查询功能仍然可用")
            # 检查是否有帧数据
            elif st.session_state.frames and len(st.session_state.frames) > 0 and st.session_state.times is not None and len(st.session_state.times) > 0:
                # 直接使用最新帧的数据，确保与后端实际生成的最新帧一致
                current_time = st.session_state.times[-1]
                current_height = st.session_state.height_grid[-1]
                # 同步更新 current_time_idx 到最新帧
                st.session_state.current_time_idx = len(st.session_state.times) - 1

                # 使用占位符避免全页面刷新
                if "chart_placeholder" not in st.session_state:
                    st.session_state.chart_placeholder = st.empty()
                
                # 只在非用户交互时创建/更新图表，避免阻塞
                # 用户交互时（复选框、查询等），图表保持不变，不重新渲染
                skip_chart_update = st.session_state.get("_skip_chart_update", False)
                
                # 添加图表更新防抖：避免过于频繁的图表重绘
                if not skip_chart_update:
                    # 检查是否需要更新图表（避免每次rerun都重绘）
                    chart_needs_update = False
                    if "last_chart_update_time" not in st.session_state:
                        chart_needs_update = True
                        st.session_state.last_chart_update_time = time.time()
                    else:
                        elapsed_since_chart_update = time.time() - st.session_state.last_chart_update_time
                        # 图表更新间隔至少0.5秒，避免过于频繁重绘导致卡顿
                        if elapsed_since_chart_update >= 0.5:
                            chart_needs_update = True
                            st.session_state.last_chart_update_time = time.time()
                    
                    if chart_needs_update:
                        try:
                            # 添加图表创建超时保护
                            import time as time_module
                            chart_start_time = time_module.time()
                            
                            # 创建等高线图（使用Contour，支持hover查询高度）
                            fig = create_heatmap(
                                st.session_state.lon_grid,
                                st.session_state.lat_grid,
                                current_height,
                                current_time,
                                use_fast_mode=False,  # 使用Contour等高线图，支持hover查询
                            )
                            
                            chart_create_time = time_module.time() - chart_start_time
                            # 如果图表创建时间超过1秒，记录警告
                            if chart_create_time > 1.0:
                                print(f"警告：图表创建耗时 {chart_create_time:.2f} 秒")
                            
                            # 在占位符中更新图表，避免全页面刷新
                            with st.session_state.chart_placeholder.container():
                                st.plotly_chart(
                                    fig, 
                                    use_container_width=True,
                                    key="heatmap_main",  # 使用固定的key，让Streamlit自动处理更新
                                    # 保持交互性以支持hover查询
                                    config={
                                        "displayModeBar": True,  # 显示工具栏
                                        "staticPlot": False,  # 保持交互性
                                    }
                                )
                        except Exception as chart_error:
                            # 图表更新失败时，不影响其他功能
                            print(f"图表更新失败: {chart_error}")
                # 用户交互时，不更新图表，避免阻塞（图表保持原样）
            else:
                # 还没有数据时显示占位符
                if "chart_placeholder" not in st.session_state:
                    st.session_state.chart_placeholder = st.empty()
                with st.session_state.chart_placeholder.container():
                    st.info("等待模拟数据...")

        with col2:
            st.subheader("📊 数据信息")
            if st.session_state.times is not None and len(st.session_state.times) > 0:
                # 直接使用最新帧的时间，确保与后端实际生成的最新帧时间一致
                current_time = st.session_state.times[-1]
                # 同步更新 current_time_idx 到最新帧
                st.session_state.current_time_idx = len(st.session_state.times) - 1
                
                # 如果图表已启用，显示高度信息；否则只显示时间
                if (st.session_state.get("enable_chart", True) and 
                    st.session_state.height_grid is not None and 
                    len(st.session_state.height_grid) > 0):
                    current_height = st.session_state.height_grid[-1]
                    st.metric("当前时间", f"{current_time:.2f} s")
                    st.metric("最大高度", f"{np.max(current_height):.4f} m")
                    st.metric("最小高度", f"{np.min(current_height):.4f} m")
                    st.metric("平均高度", f"{np.mean(current_height):.4f} m")
                else:
                    st.metric("当前时间", f"{current_time:.2f} s")
                    st.info("图表已禁用，高度信息不可用")
            else:
                st.info("暂无数据")
                
            st.markdown("### ⏯️ 控制")
            st.markdown("*模拟运行时可以随时操作*")
            
            # 控制按钮的回调函数（在回调中直接执行逻辑，立即生效）
            def on_pause_click():
                """暂停按钮点击回调 - 立即执行暂停逻辑"""
                print(f"[DEBUG] 暂停按钮 on_click 回调执行 - 立即执行逻辑")
                st.session_state._user_interaction = True
                st.session_state._skip_chart_update = True
                st.session_state._control_button_clicked = "pause"
                st.session_state.needs_refresh = False
                
                # 在回调中直接执行暂停逻辑
                try:
                    api_client = get_api_client()
                    resp = api_client.pause_clock(
                        st.session_state.simulation_id,
                        timeout=3.0,
                    )
                    st.session_state.simulation_status = resp.get("status", "paused")
                    st.session_state.is_playing = False
                    print(f"[DEBUG] 暂停逻辑执行成功")
                except httpx.TimeoutException:
                    st.session_state._pause_error = "TimeoutException"
                except httpx.RequestError:
                    st.session_state._pause_error = "RequestError"
                except Exception as e:
                    st.session_state._pause_error = str(e)
            
            def on_resume_click():
                """恢复按钮点击回调 - 立即执行恢复逻辑"""
                st.session_state._user_interaction = True
                st.session_state._skip_chart_update = True
                st.session_state._control_button_clicked = "resume"
                st.session_state.needs_refresh = False
                
                # 在回调中直接执行恢复逻辑
                try:
                    api_client = get_api_client()
                    resp = api_client.resume_clock(
                        st.session_state.simulation_id,
                        timeout=3.0,
                    )
                    st.session_state.simulation_status = resp.get("status", "running")
                    st.session_state.is_playing = True
                    st.session_state.simulation_completed = False
                    st.session_state.last_play_time = None
                except httpx.TimeoutException:
                    st.session_state._resume_error = "TimeoutException"
                except httpx.RequestError:
                    st.session_state._resume_error = "RequestError"
                except Exception as e:
                    st.session_state._resume_error = str(e)
            
            def on_stop_click():
                """停止按钮点击回调 - 立即执行停止逻辑"""
                st.session_state._user_interaction = True
                st.session_state._skip_chart_update = True
                st.session_state._control_button_clicked = "stop"
                st.session_state.needs_refresh = False
                
                # 在回调中直接执行停止逻辑
                try:
                    api_client = get_api_client()
                    resp = api_client.stop_simulation(
                        st.session_state.simulation_id,
                        timeout=3.0,
                    )
                    st.session_state.simulation_status = resp.get("status", "stopped")
                    st.session_state.is_playing = False
                    st.session_state.simulation_completed = True
                except httpx.TimeoutException:
                    st.session_state._stop_error = "TimeoutException"
                except httpx.RequestError:
                    st.session_state._stop_error = "RequestError"
                except Exception as e:
                    st.session_state._stop_error = str(e)
            
            control_pause, control_resume, control_stop = st.columns(3)
            with control_pause:
                st.button(
                    "⏸️ 暂停", 
                    use_container_width=True, 
                    key="pause_clock_btn",
                    on_click=on_pause_click
                )
                # 显示错误信息（如果有）
                if st.session_state.get("_pause_error"):
                    error = st.session_state._pause_error
                    st.session_state._pause_error = None  # 清除错误
                    if "Timeout" in error or "timeout" in error.lower():
                        st.error("⏱️ 暂停操作超时，请稍后重试。")
                    elif "RequestError" in error or "网络" in error:
                        st.error("🌐 网络错误: 无法连接到后端服务。")
                    else:
                        st.error(f"暂停失败: {error}")
                # 清除标记（如果操作已完成）
                if st.session_state.get("_control_button_clicked") == "pause":
                    st.session_state._control_button_clicked = False
                    st.session_state._user_interaction = False
                    st.session_state._skip_chart_update = False
            
            with control_resume:
                st.button(
                    "▶️ 恢复", 
                    use_container_width=True, 
                    key="resume_clock_btn",
                    on_click=on_resume_click
                )
                # 显示错误信息（如果有）
                if st.session_state.get("_resume_error"):
                    error = st.session_state._resume_error
                    st.session_state._resume_error = None  # 清除错误
                    if "Timeout" in error or "timeout" in error.lower():
                        st.error("⏱️ 恢复操作超时，请稍后重试。")
                    elif "RequestError" in error or "网络" in error:
                        st.error("🌐 网络错误: 无法连接到后端服务。")
                    else:
                        st.error(f"恢复失败: {error}")
                # 清除标记（如果操作已完成）
                if st.session_state.get("_control_button_clicked") == "resume":
                    st.session_state._control_button_clicked = False
                    st.session_state._user_interaction = False
                    st.session_state._skip_chart_update = False
            
            with control_stop:
                st.button(
                    "⏹️ 停止", 
                    use_container_width=True, 
                    key="stop_sim_btn",
                    on_click=on_stop_click
                )
                # 显示错误信息（如果有）
                if st.session_state.get("_stop_error"):
                    error = st.session_state._stop_error
                    st.session_state._stop_error = None  # 清除错误
                    if "Timeout" in error or "timeout" in error.lower():
                        st.error("⏱️ 停止操作超时，请稍后重试。")
                    elif "RequestError" in error or "网络" in error:
                        st.error("🌐 网络错误: 无法连接到后端服务。")
                    else:
                        st.error(f"停止失败: {error}")
                # 清除标记（如果操作已完成）
                if st.session_state.get("_control_button_clicked") == "stop":
                    st.session_state._control_button_clicked = False
                    st.session_state._user_interaction = False
                    st.session_state._skip_chart_update = False

        # 单点查询（独立于播放状态，随时可查询）
        st.markdown("---")
        st.subheader("📍 单点查询")
        st.markdown("*模拟运行时可以随时进行查询操作*")

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
            # 添加"使用最新帧"选项
            if "use_latest_frame" not in st.session_state:
                st.session_state.use_latest_frame = False
            
            # 使用复选框（Streamlit会自动处理状态变化）
            use_latest = st.checkbox(
                "使用最新帧",
                value=st.session_state.use_latest_frame,
                key="use_latest_frame_checkbox",
                help="勾选后使用最新帧（time=-1）进行查询",
            )
            
            # 检查复选框值是否变化（用户点击了）
            prev_use_latest = st.session_state.get("_prev_use_latest_frame", st.session_state.get("use_latest_frame", False))
            if use_latest != prev_use_latest:
                # 用户点击了复选框，标记为用户交互，避免触发自动刷新
                st.session_state._user_interaction = True
                st.session_state.use_latest_frame = use_latest
                # 保存之前的值，用于下次检测
                st.session_state._prev_use_latest_frame = prev_use_latest
            else:
                # 值没有变化，正常更新状态
                st.session_state.use_latest_frame = use_latest
                # 保存当前值
                st.session_state._prev_use_latest_frame = use_latest
            
            col_time, col_btn = st.columns([3, 1])
            with col_time:
                # 如果使用最新帧，禁用时间输入框
                query_time = st.number_input(
                    "时间 (s)",
                    value=st.session_state.query_time if not use_latest else -1.0,
                    step=0.1,
                    format="%.2f",
                    key="query_time_input",
                    disabled=use_latest,
                )
                if not use_latest:
                    st.session_state.query_time = query_time
                else:
                    st.session_state.query_time = -1.0  # 使用 -1 表示最新帧
            with col_btn:
                # 同步时间按钮的回调函数
                def on_sync_time_click():
                    """同步时间按钮点击回调"""
                    st.session_state._sync_button_clicked = True
                    st.session_state._user_interaction = True
                    st.session_state._skip_chart_update = True
                    st.session_state.needs_refresh = False
                    st.session_state.use_latest_frame = False
                    # 同步当前播放时间（使用最新帧的时间）
                    if st.session_state.times is not None and len(st.session_state.times) > 0:
                        # 直接使用最新帧的时间，确保与后端实际生成的最新帧时间一致
                        current_time = st.session_state.times[-1]
                        st.session_state.query_time = float(current_time)
                        # 同步更新 current_time_idx 到最新帧
                        st.session_state.current_time_idx = len(st.session_state.times) - 1
                
                st.button(
                    "📌", 
                    help="使用当前播放时间", 
                    key="sync_time_btn",
                    on_click=on_sync_time_click
                )

        # 查询按钮的回调函数（在按钮点击时立即执行，早于脚本主体）
        def on_query_click():
            """查询按钮点击回调，立即设置标记避免自动刷新"""
            st.session_state._query_button_clicked = True
            st.session_state._user_interaction = True
            st.session_state._skip_chart_update = True
            st.session_state.needs_refresh = False
        
        query_button_col1, query_button_col2 = st.columns([1, 4])
        with query_button_col1:
            # 使用 on_click 回调，确保标记在脚本开头就能检测到
            query_clicked = st.button(
                "🔍 查询", 
                type="primary", 
                use_container_width=True,
                on_click=on_query_click,
                key="query_button"
            )
            
            if query_clicked:
                # 按钮被点击，执行查询逻辑
                print(f"\n{'='*60}")
                print(f"[性能分析] 查询按钮点击 - 开始")
                total_start = time.time()
                
                # 检查 simulation_id 是否存在
                if not st.session_state.simulation_id:
                    st.error("❌ **查询失败**：当前没有活动的模拟任务\n\n请先创建模拟任务后再进行查询。")
                    st.session_state.query_result = None
                else:
                    # 单点查询使用独立的短超时，确保快速响应
                    # 查询操作不应该受显示间隔影响
                    # 使用 spinner 显示查询进度，但不阻塞其他操作
                    try:
                        query_time_value = -1.0 if st.session_state.use_latest_frame else st.session_state.query_time
                        
                        # 使用全局单例 API 客户端，实现连接复用
                        # 查询操作完全独立，不受显示刷新逻辑影响
                        print(f"[性能分析] 准备查询参数耗时: {(time.time() - total_start)*1000:.2f} ms")
                        
                        api_start = time.time()
                        api_client = get_api_client()
                        result = api_client.query_point(
                                simulation_id=st.session_state.simulation_id,
                                lon=query_lon,
                                lat=query_lat,
                                time=query_time_value,
                                timeout=3.0,  # 3秒超时，确保快速响应（从5秒减少到3秒）
                            )
                        api_time = time.time() - api_start
                        print(f"[性能分析] API查询耗时: {api_time*1000:.2f} ms ({api_time:.3f} 秒)")
                        
                        result_start = time.time()
                        st.session_state.query_result = result
                        result_time = time.time() - result_start
                        print(f"[性能分析] 保存结果耗时: {result_time*1000:.2f} ms")
                        
                        total_time = time.time() - total_start
                        print(f"[性能分析] 查询总耗时: {total_time*1000:.2f} ms ({total_time:.3f} 秒)")
                        print(f"{'='*60}\n")
                        
                        # 查询成功，不显示额外消息，避免界面闪烁
                    except httpx.TimeoutException:
                        print(f"[性能分析] 查询超时")
                        print(f"{'='*60}\n")
                        # 查询超时，显示友好的错误提示
                        st.error("⏱️ 查询超时，请稍后重试。如果问题持续，请检查后端服务状态。")
                        st.session_state.query_result = None
                    except httpx.HTTPStatusError as e:
                        print(f"[性能分析] HTTP错误: {e.response.status_code}")
                        print(f"{'='*60}\n")
                        # HTTP 错误（如 404, 500 等）
                        # 尝试获取后端返回的详细错误信息
                        try:
                            error_detail = e.response.json().get("detail", "")
                        except:
                            error_detail = e.response.text if hasattr(e.response, 'text') else ""
                        
                        error_msg = f"查询失败: HTTP {e.response.status_code}"
                        if e.response.status_code == 404:
                            error_detail_lower = error_detail.lower()
                            if "not found" in error_detail_lower and "has no results" not in error_detail_lower:
                                # 任务确实不存在
                                error_msg += f"\n\n**原因**：模拟任务不存在（ID: {st.session_state.simulation_id[:8]}...）\n\n"
                                error_msg += "**可能的原因**：\n"
                                error_msg += "1. 任务已被停止或清理\n"
                                error_msg += "2. 后端服务重启，任务丢失\n"
                                error_msg += "3. 任务 ID 不正确\n\n"
                                error_msg += "**解决方案**：请重新创建模拟任务"
                            elif "is running" in error_detail_lower or "is paused" in error_detail_lower:
                                # 任务正在运行/暂停，但还没有数据
                                error_msg += f"\n\n**原因**：模拟任务正在运行，但还没有生成任何结果数据\n\n"
                                error_msg += "**说明**：这是正常情况，任务刚创建时需要几秒钟来生成第一帧数据\n\n"
                                error_msg += "**解决方案**：\n"
                                error_msg += "1. 等待 3-5 秒后重试\n"
                                error_msg += "2. 检查状态栏确认任务是否正在运行\n"
                                error_msg += "3. 如果长时间无数据，请检查后端日志"
                            elif "no results" in error_detail_lower:
                                # 任务存在但没有数据（其他状态）
                                error_msg += f"\n\n**原因**：模拟任务还没有生成任何结果数据\n\n"
                                error_msg += "**解决方案**：请等待几秒钟后重试，或检查模拟任务是否正在运行"
                            else:
                                error_msg += f"\n\n**详细信息**：{error_detail}"
                        elif e.response.status_code == 410:
                            error_msg += f"\n\n**原因**：请求的时间已超出缓存保留范围\n\n"
                            error_msg += f"**详细信息**：{error_detail}\n\n"
                            error_msg += "**解决方案**：请使用最新帧（勾选'使用最新帧'）或查询更近的时间点"
                        else:
                            error_msg += f"\n\n**详细信息**：{error_detail}"
                        
                        st.error(error_msg)
                        st.session_state.query_result = None
                    except httpx.RequestError as e:
                        print(f"[性能分析] 网络错误: {e}")
                        print(f"{'='*60}\n")
                        # 网络请求错误（连接失败等）
                        st.error(f"🌐 网络错误: 无法连接到后端服务。请检查后端是否正常运行。")
                        st.session_state.query_result = None
                    except Exception as e:
                        print(f"[性能分析] 其他异常: {e}")
                        print(f"{'='*60}\n")
                        # 其他异常
                        st.error(f"查询失败: {str(e)}")
                        st.session_state.query_result = None

        # 显示查询结果（使用容器，避免触发不必要的刷新）
        if "query_result_placeholder" not in st.session_state:
            st.session_state.query_result_placeholder = st.empty()
        
        with st.session_state.query_result_placeholder.container():
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

    # 在脚本末尾统一处理刷新
    # 彻底避免用户交互时的刷新阻塞和过于频繁的刷新
    # 检查是否为用户交互（复选框、按钮点击等）
    # 注意：暂停、恢复、停止按钮也会设置 _user_interaction，确保不会在按钮操作时刷新
    
    # 性能分析：记录脚本执行到此处的时间
    script_elapsed = time.time() - script_start_time
    if st.session_state.get("_query_button_clicked", False):
        print(f"[性能分析] 脚本执行到末尾耗时: {script_elapsed*1000:.2f} ms ({script_elapsed:.3f} 秒)")
    
    # 检查控制按钮是否点击（暂停/恢复/停止）
    # 注意：按钮的实际执行逻辑在脚本中间（920-1020行），这里只负责禁止自动刷新
    # _control_button_clicked 现在是一个字符串（"pause"/"resume"/"stop"），表示哪个按钮被点击
    control_button_clicked = st.session_state.get("_control_button_clicked", False)
    if control_button_clicked:
        # 标记已检测到控制按钮点击，禁止自动刷新
        # 标记会在按钮逻辑执行后清除（见按钮逻辑部分）
        pass
    
    # 检查其他用户交互
    is_user_interaction_end = (
        st.session_state.get("_user_interaction", False) or
        st.session_state.get("_query_button_clicked", False) or
        st.session_state.get("_sync_button_clicked", False) or
        st.session_state.get("_skip_chart_update", False) or
        bool(control_button_clicked)  # 控制按钮点击也算用户交互
    )
    
    # 如果用户交互标记存在，强制禁止刷新
    if is_user_interaction_end:
        st.session_state.needs_refresh = False
    
    # 只有在非用户交互且需要刷新时才rerun
    # 添加额外的防抖检查，避免过于频繁的rerun
    if st.session_state.get("needs_refresh", False) and not is_user_interaction_end:
        # 再次检查时间间隔，确保不会过于频繁
        current_time_check = time.time()
        if "last_rerun_time" not in st.session_state:
            st.session_state.last_rerun_time = 0
        
        time_since_last_rerun = current_time_check - st.session_state.last_rerun_time
        min_rerun_interval = 1.0  # 至少间隔1秒才能再次rerun，避免频繁刷新导致阻塞
        
        if time_since_last_rerun >= min_rerun_interval:
            st.session_state.needs_refresh = False
            st.session_state.last_rerun_time = current_time_check
            # 非用户交互时，可以刷新
            st.rerun()
        else:
            # 太频繁，跳过本次刷新
            st.session_state.needs_refresh = False
    else:
        # 用户交互时，清除所有刷新标记，绝不rerun
        st.session_state.needs_refresh = False
        
        # 重要：只在脚本结束时清除用户交互标记
        # 如果检测到查询按钮点击，清除标记，表示本次交互已完成
        if st.session_state.get("_query_button_clicked", False):
            st.session_state._query_button_clicked = False
        if st.session_state.get("_sync_button_clicked", False):
            st.session_state._sync_button_clicked = False
        
        # 清除用户交互标记（下次运行时恢复自动刷新）
        st.session_state._user_interaction = False
        st.session_state._skip_chart_update = False
        # 用户交互时绝不rerun，让Streamlit自然结束，避免界面阻塞


if __name__ == "__main__":
    main()
