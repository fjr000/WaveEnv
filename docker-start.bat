@echo off
REM Docker Startup Script (Windows)
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM Check if Docker is available
docker ps >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running or not available.
    echo Please start Docker Desktop and wait for it to be ready.
    echo.
    exit /b 1
)

REM Check .env file
if not exist .env (
    echo [WARN] .env file not found, creating from template...
    if exist .env.example (
        copy .env.example .env >nul
        echo [INFO] Created .env from .env.example
    ) else if exist env.example (
        copy env.example .env >nul
        echo [INFO] Created .env from env.example
    ) else (
        echo [WARN] Template file not found, creating default .env...
        (
            echo # WaveEnv Docker Environment Variables
            echo # Backend service port
            echo BACKEND_PORT=8000
            echo # Frontend service port
            echo FRONTEND_PORT=8888
            echo # Enable frontend service (set empty to disable)
            echo FRONTEND_PROFILE=frontend
            echo # Backend service URL (use service name in Docker)
            echo BACKEND_URL=http://backend:8000
            echo # Log level
            echo LOG_LEVEL=INFO
        ) > .env
        echo [INFO] Created default .env file, please modify as needed
    )
)

REM Default configuration
set MODE=prod
set ENABLE_FRONTEND=true
set COMPOSE_FILES=docker-compose.yml

REM Parse command line arguments
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
    echo Usage: %~nx0 [options]
    echo.
    echo Options:
    echo   --dev, --development      Development mode (mount code, enable hot reload)
    echo   --prod, --production      Production mode (default)
    echo   --backend-only            Start backend service only
    echo   --frontend                Enable frontend service (default)
    echo   --help                    Show this help message
    echo.
    echo Examples:
    echo   %~nx0                      # Production mode, start all services
    echo   %~nx0 --dev                # Development mode, start all services
    echo   %~nx0 --backend-only       # Start backend service only
    exit /b 0
)
if /i "%~1"=="-h" (
    goto :parse_args --help
)
echo [ERROR] Unknown parameter: %~1
echo Use --help to view help information
exit /b 1
:end_parse

REM Display configuration
echo [INFO] Mode: %MODE%
echo [INFO] Frontend enabled: %ENABLE_FRONTEND%

REM Check if Python 3.8-slim image exists (Huawei Cloud mirror)
set PYTHON_IMAGE=swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.8-slim
docker images %PYTHON_IMAGE% | findstr /C:"ddn-k8s" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Pulling Python 3.8-slim image from Huawei Cloud mirror...
    docker pull %PYTHON_IMAGE%
    if errorlevel 1 (
        echo [ERROR] Failed to pull Python 3.8-slim image from Huawei Cloud
        echo Please check network connection or mirror address
        exit /b 1
    )
)
REM Always create alias for compatibility
docker images python:3.8-slim | findstr /C:"python" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Creating image alias python:3.8-slim...
    docker tag %PYTHON_IMAGE% python:3.8-slim
)

REM Build and start services
if "%ENABLE_FRONTEND%"=="true" (
    echo [INFO] Starting all services - backend and frontend...
    call docker-compose -f !COMPOSE_FILES! --profile frontend up -d --build
) else (
    echo [INFO] Starting backend service only...
    call docker-compose -f !COMPOSE_FILES! up -d --build backend
)

REM Wait for services to start
echo [INFO] Waiting for services to start...
timeout /t 5 /nobreak >nul

REM Check service status
echo [INFO] Checking service status...
docker-compose -f docker-compose.yml ps

echo [INFO] Startup complete!
echo.
echo Access URLs:
if "%ENABLE_FRONTEND%"=="true" (
    echo   - Frontend: http://localhost:8888
)
echo   - Backend API: http://localhost:8000
echo   - API Docs: http://localhost:8000/docs
echo.
echo View logs: docker-compose logs -f
echo Stop services: docker-stop.bat
echo   (or manually: docker-compose down)

endlocal
