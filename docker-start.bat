@echo off
REM Docker 启动脚本 (Windows)

setlocal enabledelayedexpansion

REM 检查 .env 文件
if not exist .env (
    echo [WARN] .env 文件不存在，尝试从模板创建...
    if exist .env.example (
        copy .env.example .env >nul
        echo [INFO] 已从 .env.example 创建 .env 文件
    ) else if exist env.example (
        copy env.example .env >nul
        echo [INFO] 已从 env.example 创建 .env 文件
    ) else (
        echo [WARN] 模板文件不存在，创建默认 .env 文件...
        (
            echo # WaveEnv Docker 环境变量配置
            echo # 后端服务端口
            echo BACKEND_PORT=8000
            echo # 前端服务端口
            echo FRONTEND_PORT=8888
            echo # 是否启用前端服务（设置为空字符串则只启动后端）
            echo FRONTEND_PROFILE=frontend
            echo # 后端服务地址（Docker环境使用服务名）
            echo BACKEND_URL=http://backend:8000
            echo # 日志级别
            echo LOG_LEVEL=INFO
        ) > .env
        echo [INFO] 已创建默认 .env 文件，请根据需要修改配置
    )
)

REM 默认配置
set MODE=prod
set ENABLE_FRONTEND=true
set COMPOSE_FILES=docker-compose.yml

REM 解析命令行参数
:parse_args
if "%~1"=="" goto end_parse
if /i "%~1"=="--dev" (
    set MODE=dev
    set COMPOSE_FILES=!COMPOSE_FILES! -f docker-compose.dev.yml
    shift
    goto parse_args
)
if /i "%~1"=="--development" (
    set MODE=dev
    set COMPOSE_FILES=!COMPOSE_FILES! -f docker-compose.dev.yml
    shift
    goto parse_args
)
if /i "%~1"=="--prod" (
    set MODE=prod
    set COMPOSE_FILES=!COMPOSE_FILES! -f docker-compose.prod.yml
    shift
    goto parse_args
)
if /i "%~1"=="--production" (
    set MODE=prod
    set COMPOSE_FILES=!COMPOSE_FILES! -f docker-compose.prod.yml
    shift
    goto parse_args
)
if /i "%~1"=="--backend-only" (
    set ENABLE_FRONTEND=false
    shift
    goto parse_args
)
if /i "%~1"=="--no-frontend" (
    set ENABLE_FRONTEND=false
    shift
    goto parse_args
)
if /i "%~1"=="--frontend" (
    set ENABLE_FRONTEND=true
    shift
    goto parse_args
)
if /i "%~1"=="--help" (
    echo 用法: %~nx0 [选项]
    echo.
    echo 选项:
    echo   --dev, --development      开发模式（挂载代码目录，启用热重载）
    echo   --prod, --production      生产模式（默认）
    echo   --backend-only            只启动后端服务
    echo   --frontend                启用前端服务（默认）
    echo   --help                    显示此帮助信息
    echo.
    echo 示例:
    echo   %~nx0                      # 生产模式，启动所有服务
    echo   %~nx0 --dev                # 开发模式，启动所有服务
    echo   %~nx0 --backend-only       # 只启动后端服务
    exit /b 0
)
if /i "%~1"=="-h" (
    goto :parse_args --help
)
echo [ERROR] 未知参数: %~1
echo 使用 --help 查看帮助信息
exit /b 1
:end_parse

REM 显示配置信息
echo [INFO] 启动模式: %MODE%
echo [INFO] 启用前端: %ENABLE_FRONTEND%

REM 构建并启动服务
if "%ENABLE_FRONTEND%"=="true" (
    echo [INFO] 启动所有服务（后端 + 前端）...
    docker-compose -f %COMPOSE_FILES% up -d --build
) else (
    echo [INFO] 只启动后端服务...
    docker-compose -f %COMPOSE_FILES% up -d --build backend
)

REM 等待服务启动
echo [INFO] 等待服务启动...
timeout /t 5 /nobreak >nul

REM 检查服务状态
echo [INFO] 检查服务状态...
docker-compose -f docker-compose.yml ps

echo [INFO] 启动完成！
echo.
echo 访问地址:
if "%ENABLE_FRONTEND%"=="true" (
    echo   - 前端界面: http://localhost:8888
)
echo   - 后端 API: http://localhost:8000
echo   - API 文档: http://localhost:8000/docs
echo.
echo 查看日志: docker-compose logs -f
echo 停止服务: docker-compose down

endlocal

