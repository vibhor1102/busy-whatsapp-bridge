@echo off
echo Busy Whatsapp Bridge - Desktop Shortcut Creator
echo =================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    pause
    exit /b 1
)

REM Run the shortcut creator
echo Creating desktop shortcut...
python "%~dp0Create-Desktop-Shortcut.py"

exit /b %errorlevel%
