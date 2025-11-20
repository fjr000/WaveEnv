@echo off
REM Streamlit 前端启动脚本
REM 确保在 jobs 环境下运行

echo 正在启动 Streamlit 前端...
echo.

REM 检查是否在 frontend 目录
if not exist "app.py" (
    echo 错误: 请在 frontend 目录下运行此脚本
    pause
    exit /b 1
)

REM 运行 Streamlit
streamlit run app.py --server.headless true

pause

