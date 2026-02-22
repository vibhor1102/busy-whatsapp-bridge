@echo off
echo Busy WhatsApp Gateway
echo =====================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python 3.9+ from https://python.org/
    pause
    exit /b 1
)

REM Check/Install required packages
echo Checking packages...
python -c "import pystray" >nul 2>&1
if errorlevel 1 (
    echo Installing system tray support...
    python -m pip install pystray pillow --quiet
)

REM Check .env
if not exist .env (
    echo First run: Creating .env file...
    copy .env.example .env
    echo.
    echo IMPORTANT: Edit .env with your database path!
    notepad .env
    echo.
    echo Please run again after configuring .env
    pause
    exit /b 0
)

echo.
echo Starting Gateway Manager...
echo Left-click tray icon to open Dashboard
echo Right-click tray icon to control servers
echo.

python gateway-manager.py
