@echo off
REM Cleanup script for unclosed connections on port 8000
REM This script will help identify and optionally clean up connections

echo ============================================================
echo Connection Cleanup Script
echo ============================================================
echo.

REM Check connections on port 8000
echo Checking connections on port 8000...
echo.

REM Show CLOSE_WAIT connections
echo CLOSE_WAIT connections:
netstat -ano | findstr "CLOSE_WAIT" | findstr ":8000"
echo.

REM Show FIN_WAIT_2 connections
echo FIN_WAIT_2 connections:
netstat -ano | findstr "FIN_WAIT_2" | findstr ":8000"
echo.

REM Show TIME_WAIT connections
echo TIME_WAIT connections:
netstat -ano | findstr "TIME_WAIT" | findstr ":8000"
echo.

REM Show all connections on port 8000
echo All connections on port 8000:
netstat -ano | findstr ":8000"
echo.

echo ============================================================
echo To kill a specific process, use:
echo   taskkill /F /PID [PID_NUMBER]
echo.
echo To kill all Python processes (CAUTION):
echo   taskkill /F /IM python.exe
echo ============================================================
echo.

pause

