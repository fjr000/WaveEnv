"""
Streamlit 前端应用主文件。

时变海浪环境模型可视化界面。
"""

import streamlit as st

# 页面配置
st.set_page_config(
    page_title="WaveEnv - 时变海浪环境模型",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 标题
st.title("🌊 时变海浪环境模型系统")
st.markdown("---")

# 占位内容 - 待实现
st.info("🚧 Streamlit 前端正在开发中...")

st.markdown("""
### 功能规划

1. **区域模拟可视化**
   - 参数配置面板（风场、波浪谱、离散化、时间参数）
   - 区域地图显示
   - 海浪高度场动态渲染
   - 时间序列播放控制

2. **单点查询**
   - 地图点击查询
   - 手动输入坐标查询
   - 实时显示海浪高度

3. **参数管理**
   - 基础模式/高级模式切换
   - 参数预设保存与加载
   - 实时参数验证

### 技术架构

- **前端框架**: Streamlit
- **后端服务**: FastAPI (运行在独立服务中)
- **可视化**: Plotly / Matplotlib
- **地图**: Folium / Plotly Mapbox

---

**注意**: 当前为占位页面，完整功能将在后续迭代中实现。
""")

