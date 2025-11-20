@echo off
REM Cleanup connections and restart backend
REM This script will kill backend processes and restart the server

echo ============================================================
echo Backend Cleanup and Restart Script
echo ============================================================
echo.

REM Step 1: Find backend processes (listening on port 8000)
echo Step 1: Finding backend processes...
echo.

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo Found backend process: PID %%a
    echo Killing process %%a...
    taskkill /F /PID %%a >nul 2>&1
    if errorlevel 1 (
        echo   Failed to kill PID %%a
    ) else (
        echo   Successfully killed PID %%a
    )
    echo.
)

REM Step 2: Wait a moment for cleanup
echo Step 2: Waiting for cleanup...
timeout /t 2 /nobreak >nul

REM Step 3: Show remaining connections
echo Step 3: Checking remaining connections on port 8000...
netstat -ano | findstr ":8000"
echo.

REM Step 4: Restart backend
echo Step 4: Starting backend server...
echo.
echo Starting uvicorn on port 8000...
echo Press Ctrl+C to stop the server
echo.

cd /d %~dp0
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

pause

