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

REM Parse command line arguments (simplified)
if not "%1"=="" (
    if /i "%1"=="--dev" set MODE=dev
    if /i "%1"=="--development" set MODE=dev
    if /i "%1"=="--prod" set MODE=prod
    if /i "%1"=="--production" set MODE=prod
    if /i "%1"=="--backend-only" set ENABLE_FRONTEND=false
    if /i "%1"=="--no-frontend" set ENABLE_FRONTEND=false
    if /i "%1"=="--frontend" set ENABLE_FRONTEND=true
    if /i "%1"=="--help" goto show_help
    if /i "%1"=="-h" goto show_help
)

REM Continue with startup
goto start_services

:show_help
echo Usage: %~nx0 [options]
echo.
echo Options:
echo   --dev, --development      Development mode
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

:start_services

REM Display configuration
echo [INFO] Mode: %MODE%
echo [INFO] Frontend enabled: %ENABLE_FRONTEND%

REM Check if Python 3.8-slim image exists (Huawei Cloud mirror)
set "PYTHON_IMAGE=swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.8-slim"
docker images "%PYTHON_IMAGE%" | findstr /C:"ddn-k8s" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Pulling Python 3.8-slim image from Huawei Cloud mirror...
    docker pull "%PYTHON_IMAGE%"
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
    docker tag "%PYTHON_IMAGE%" python:3.8-slim
)

REM Build and start services
echo [INFO] Building images (this may take a few minutes on first run)...
if "%ENABLE_FRONTEND%"=="true" (
    echo [INFO] Building all services - backend and frontend...
    docker-compose -f docker-compose.yml --profile frontend build
    echo.
    REM Verify images were built successfully
    docker images waveenv-backend --format "{{.Repository}}:{{.Tag}}" | findstr /C:"waveenv-backend" >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Backend image was not created!
        echo Please check the build logs above for errors.
        pause
        exit /b 1
    )
    docker images waveenv-frontend --format "{{.Repository}}:{{.Tag}}" | findstr /C:"waveenv-frontend" >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Frontend image was not created!
        echo Please check the build logs above for errors.
        pause
        exit /b 1
    )
    echo [SUCCESS] Build completed successfully!
    echo.
    echo [INFO] Starting all services - backend and frontend...
    docker-compose -f docker-compose.yml --profile frontend up -d
    if errorlevel 1 (
        echo [ERROR] Service startup failed!
        echo.
        echo Please run diagnostic script for details:
        echo   docker-diagnose.bat
        echo.
        echo Or check container logs:
        echo   docker logs waveenv-backend
        echo   docker logs waveenv-frontend
        pause
        exit /b 1
    )
) else (
    echo [INFO] Building backend service only...
    docker-compose -f docker-compose.yml build backend
    echo.
    REM Verify image was built successfully
    docker images waveenv-backend --format "{{.Repository}}:{{.Tag}}" | findstr /C:"waveenv-backend" >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Backend image was not created!
        echo Please check the build logs above for errors.
        pause
        exit /b 1
    )
    echo [SUCCESS] Backend build completed successfully!
    echo.
    echo [INFO] Starting backend service only...
    docker-compose -f docker-compose.yml up -d backend
    if errorlevel 1 (
        echo [ERROR] Backend service startup failed!
        echo.
        echo Please check container logs:
        echo   docker logs waveenv-backend
        echo.
        echo Or check if container exists:
        echo   docker ps -a --filter "name=waveenv-backend"
        pause
        exit /b 1
    )
)

REM Wait for services to start (increased wait time for health checks)
echo [INFO] Waiting for services to start (waiting for health checks)...
timeout /t 10 /nobreak >nul

REM Check service status
echo [INFO] Checking service status...
docker-compose -f docker-compose.yml ps

REM Check backend container health status
docker inspect waveenv-backend --format="{{.State.Health.Status}}" 2>nul | findstr /C:"healthy" >nul
if errorlevel 1 (
    echo [WARN] Backend container may not have passed health check
    echo [INFO] View backend logs: docker logs waveenv-backend
    echo [INFO] Run diagnostic script: docker-diagnose.bat
)

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
