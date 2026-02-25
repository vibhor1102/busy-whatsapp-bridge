@ECHO OFF
REM Busy Whatsapp Bridge - Launcher (Bundled Python Edition)
REM Uses Python bundled with the application - no external Python needed!

SET "SCRIPT_DIR=%~dp0"
SET "VENV_PYTHON=%SCRIPT_DIR%venv\Scripts\python.exe"

IF EXIST "%VENV_PYTHON%" (
    echo [INFO] Cleaning previous BusyWhatsappBridge processes...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'BusyWhatsappBridge' -and $_.CommandLine -match 'run\\.py|baileys-server\\\\server\\.js|uvicorn app\\.main:app' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    powershell -NoProfile -ExecutionPolicy Bypass -Command "$ports = @(3001,8000); foreach($port in $ports){ Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue } }"
    echo [INFO] Starting Busy Whatsapp Bridge in mandatory tray mode...
    "%VENV_PYTHON%" "%~dp0run.py"
) ELSE (
    echo [ERROR] Virtual environment not found!
    echo.
    echo Please run setup-bundled.bat first to set up the application.
    echo.
    pause
    exit /b 1
)
