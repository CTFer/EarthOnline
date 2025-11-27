@echo off

REM Let's Encrypt Certificate Management Service Startup Script
REM Recommend to add this script to Windows Task Scheduler to run automatically at system startup

REM Check for administrator privileges
NET SESSION >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: This script must be run as administrator.
    echo Right-click and select "Run as administrator".
    pause
    exit /b 1
)

REM Set working directory to script's location
cd /d %~dp0

echo Current working directory: %CD%

REM Create logs directory if it doesn't exist
if not exist "%~dp0..\..\logs" (
    mkdir "%~dp0..\..\logs"
)

REM Log startup
@echo %date% %time% - Starting Certificate Management Service >> "%~dp0..\..\logs\certificate_service_start.log"

REM Check if Python is available
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: Python not found.
    pause
    exit /b 1
)

REM Check if certificate_manager.py exists
if not exist "certificate_manager.py" (
    echo ERROR: certificate_manager.py not found.
    pause
    exit /b 1
)

REM Check if certbot is available
where certbot >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo WARNING: Certbot not found.
)

echo Starting certificate service...
python certificate_manager.py start

REM Log service stop
@echo %date% %time% - Service stopped >> "%~dp0..\..\logs\certificate_service_start.log"
echo Service stopped, press any key to exit...
pause