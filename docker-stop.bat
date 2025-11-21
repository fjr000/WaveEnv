@echo off
REM Docker Stop Script (Windows)
REM This script ensures all containers and networks are properly stopped and removed
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM Check if Docker is available
docker ps >nul 2>&1
if errorlevel 1 (
    echo [WARN] Docker is not running or not available.
    echo This is OK if you just want to clean up stopped containers.
)

REM Check if .env exists to determine if frontend is enabled
set ENABLE_FRONTEND=false
if exist .env (
    findstr /C:"FRONTEND_PROFILE=frontend" .env >nul 2>&1
    if not errorlevel 1 (
        set ENABLE_FRONTEND=true
    )
    findstr /C:"FRONTEND_PROFILE=" .env | findstr /V /C:"FRONTEND_PROFILE=\"\"" >nul 2>&1
    if not errorlevel 1 (
        findstr /C:"FRONTEND_PROFILE=\"\"" .env >nul 2>&1
        if errorlevel 1 (
            set ENABLE_FRONTEND=true
        )
    )
)

echo [INFO] Stopping WaveEnv services...
echo.

REM Stop all containers (with profile if frontend was enabled)
if "%ENABLE_FRONTEND%"=="true" (
    echo [INFO] Stopping services with frontend profile...
    call docker-compose --profile frontend stop 2>nul
    call docker-compose --profile frontend rm -f 2>nul
) else (
    echo [INFO] Stopping backend service only...
    call docker-compose stop 2>nul
    call docker-compose rm -f 2>nul
)

REM Force remove any remaining containers by name
echo [INFO] Cleaning up any remaining containers...
for %%c in (waveenv-backend waveenv-frontend) do (
    docker stop %%c >nul 2>&1
    docker rm -f %%c >nul 2>&1
)

REM Remove network if it exists
echo [INFO] Removing network...
if "%ENABLE_FRONTEND%"=="true" (
    call docker-compose --profile frontend down 2>nul
) else (
    call docker-compose down 2>nul
)

REM Force remove network if it still exists
docker network rm waveenv_waveenv-network >nul 2>&1

REM Verify cleanup
echo [INFO] Verifying cleanup...
docker ps -a --filter name=waveenv --format "{{.Names}}" | findstr /V "^$" >nul 2>&1
if errorlevel 1 (
    echo [INFO] All containers removed successfully.
) else (
    echo [WARN] Some containers may still exist. Trying to remove...
    docker ps -a --filter name=waveenv --format "{{.Names}}" | (
        for /f "delims=" %%c in ('more') do (
            docker rm -f %%c >nul 2>&1
        )
    )
)

docker network ls --filter name=waveenv --format "{{.Name}}" | findstr /V "^$" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Network removed successfully.
) else (
    echo [WARN] Network may still exist.
)

echo.
echo [INFO] Cleanup complete!
echo.

endlocal

