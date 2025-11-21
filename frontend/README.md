## 前端（frontend）说明

本目录为**海浪环境模型前端应用**，使用 **Streamlit** 实现，负责：

- 区域模拟可视化：展示给定区域的海浪高度场随时间变化
- 单点查询：通过地图点击或输入经纬度坐标，查询该点的海浪高度
- 参数配置：展示和调整风场、波浪谱模型及离散化参数等配置

### 技术栈

- **框架**: Streamlit
- **语言**: Python 3.8
- **可视化库**:
  - Plotly：交互式图表和地图
  - Matplotlib：静态图表
  - Folium：地理地图可视化
- **HTTP 客户端**: httpx（用于调用后端 FastAPI）

### 目录结构

```
frontend/
├── app.py              # Streamlit 主应用文件
├── requirements.txt    # Python 依赖
└── README.md          # 本文件
```

### 运行方式

#### 1. 安装依赖

```bash
# 进入前端目录
cd frontend

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

#### 2. 启动应用

```bash
# 确保后端服务已启动（默认 http://localhost:8000）
# 在另一个终端启动后端：
# cd backend
# uvicorn app.main:app --reload

# 启动 Streamlit 前端
streamlit run app.py
```

应用将在 `http://localhost:8501` 启动。

### 配置

前端通过 HTTP 调用后端 API，默认后端地址为 `http://localhost:8000`。

如需修改后端地址，可在 `app.py` 中修改 `BACKEND_URL` 配置。

### 功能模块（规划）

1. **参数配置面板**
   - 区域设置（经纬度范围、深度）
   - 风场参数（风速、风向）
   - 波浪谱参数（模型类型、显著波高、峰值周期等）
   - 离散化参数（dx, dy, max_points）
   - 时间参数（dt_backend, T_total）

2. **可视化区域**
   - 地图显示（使用 Folium 或 Plotly Mapbox）
   - 海浪高度场热力图
   - 时间序列播放控制
   - 颜色映射（colorbar）

3. **单点查询**
   - 地图点击查询
   - 手动输入坐标查询
   - 实时显示查询结果

4. **结果管理**
   - 模拟任务列表
   - 结果下载
   - 历史记录

### 开发注意事项

- Streamlit 应用是状态化的，使用 `st.session_state` 管理状态
- 后端 API 调用使用异步 httpx 客户端
- 大数据量可视化时注意性能优化
- 遵循 Streamlit 最佳实践，合理使用缓存（`@st.cache_data`）

### 与后端交互

前端通过以下 API 与后端交互：

- `POST /api/simulate/area` - 创建区域模拟任务
- `GET /api/simulation/{simulation_id}/frames?time={time}` - 获取指定时刻的模拟结果帧（单时刻）
- `POST /api/query/point` - 单点查询

详细接口文档请参考 `docs/接口文档.yaml` 或访问后端 Swagger 文档 `http://localhost:8000/docs`。
