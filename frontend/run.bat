@echo off
REM Streamlit Frontend Startup Script
REM Make sure running in jobs environment

echo Starting Streamlit frontend...
echo.

REM Check if in frontend directory
if not exist "app.py" (
    echo Error: Please run this script in the frontend directory
    pause
    exit /b 1
)

REM Try multiple ports to find available one (starting from 8888)
set PORT=8888
set FOUND=0

:check_port
netstat -ano | findstr ":%PORT%" >nul 2>&1
if %errorlevel% neq 0 (
    set FOUND=1
    goto :port_found
)

REM Port is occupied, try next one
if %PORT% equ 8888 (
    set PORT=8889
    goto :check_port
) else if %PORT% equ 8889 (
    set PORT=8890
    goto :check_port
) else if %PORT% equ 8890 (
    set PORT=8501
    goto :check_port
) else if %PORT% equ 8501 (
    set PORT=8502
    goto :check_port
) else (
    echo Error: Cannot find available port, please close programs using these ports
    pause
    exit /b 1
)

:port_found
if %FOUND% equ 0 (
    echo Error: Cannot find available port
    pause
    exit /b 1
)

echo Using port %PORT% to start Streamlit...
echo Access URL: http://localhost:%PORT%
echo.
echo Tips: If startup fails, try:
echo   1. Run this script as administrator
echo   2. Check firewall settings or specify port manually
echo   3. Close programs using the port
echo.

REM Run Streamlit with specified port and address
streamlit run app.py --server.headless true --server.port %PORT% --server.address localhost

pause



