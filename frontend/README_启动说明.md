# Streamlit 前端启动说明

## 环境要求

- Python 3.8+
- 已激活虚拟环境（jobs）
- 已安装依赖：`pip install -r requirements.txt`

## 配置问题修复

### 问题 1: CORS 配置冲突
- ✅ 已修复：`enableXsrfProtection = false`（避免与 CORS 冲突）

### 问题 2: 权限错误
- ✅ 已修复：使用项目本地配置 `.streamlit/config.toml`
- ✅ 已添加：`headless = true` 避免浏览器自动打开

### 问题 3: 导入路径问题
- ✅ 已修复：在 `app.py` 中添加了路径设置

## 启动方式

### 方式一：使用启动脚本（推荐）

**Windows (CMD):**
```cmd
cd frontend
run.bat
```

**Windows (PowerShell):**
```powershell
cd frontend
.\run.ps1
```

### 方式二：直接运行

```bash
cd frontend
streamlit run app.py
```

### 方式三：测试导入

在启动前，可以先测试导入是否正常：
```bash
cd frontend
python test_imports.py
```

## 配置说明

当前配置（`.streamlit/config.toml`）：
- ✅ 端口：8501
- ✅ 地址：localhost
- ✅ CORS：启用
- ✅ XSRF 保护：禁用（避免冲突）
- ✅ 无头模式：启用（不自动打开浏览器）
- ✅ 使用统计：禁用

## 启动步骤

1. **确保后端服务已启动**
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

2. **启动前端服务**
   ```bash
   cd frontend
   streamlit run app.py
   ```

3. **访问应用**
   - 浏览器自动打开，或手动访问：`http://localhost:8501`

## 常见问题

### 问题：无法连接到后端
- 检查后端服务是否在 `http://localhost:8000` 运行
- 检查防火墙设置

### 问题：配置警告
- 如果看到 CORS 相关警告，可以忽略（已修复）
- 配置已优化为兼容模式

