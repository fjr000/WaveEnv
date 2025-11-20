# Streamlit 前端启动脚本 (PowerShell)
# 确保在 jobs 环境下运行

Write-Host "正在启动 Streamlit 前端..." -ForegroundColor Green
Write-Host ""

# 检查是否在 frontend 目录
if (-not (Test-Path "app.py")) {
    Write-Host "错误: 请在 frontend 目录下运行此脚本" -ForegroundColor Red
    exit 1
}

# 运行 Streamlit
streamlit run app.py --server.headless true

