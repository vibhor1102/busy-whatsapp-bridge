@ECHO OFF
REM Busy Whatsapp Bridge - Development Launcher
REM 
REM This script is for development use only.
REM It runs the application with console output visible for debugging.
REM 
REM For production use, install the application and run BusyWhatsappBridge.exe
REM
REM Author: vibhor1102

SETLOCAL EnableDelayedExpansion

REM Get script directory
SET "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Check if virtual environment exists
SET "VENV_PYTHON=%SCRIPT_DIR%venv\Scripts\python.exe"

IF NOT EXIST "%VENV_PYTHON%" (
    echo [ERROR] Virtual environment not found!
    echo.
    echo Please run setup-bundled.bat first to set up the environment.
    echo.
    pause
    exit /b 1
)

echo ================================================
echo Busy Whatsapp Bridge - Development Mode
echo ================================================
echo.
echo Running with console output enabled...
echo Press Ctrl+C to stop
echo.

REM Run with tray icon but keep console window open
"%VENV_PYTHON%" "%~dp0Start-Gateway.py" --tray

ENDLOCAL