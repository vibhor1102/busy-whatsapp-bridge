@ECHO OFF
REM Busy Whatsapp Bridge - Development launcher
REM Tray mode is mandatory. Any stale BusyWhatsappBridge background processes
REM are stopped first, then app is launched in tray mode.

SET "SCRIPT_DIR=%~dp0"
SET "VENV_PYTHON=%SCRIPT_DIR%venv\Scripts\python.exe"

IF NOT EXIST "%VENV_PYTHON%" (
    echo [ERROR] Virtual environment not found at:
    echo   %VENV_PYTHON%
    echo.
    echo Run setup-bundled.bat first.
    pause
    exit /b 1
)

echo [INFO] Stopping existing BusyWhatsappBridge background processes (if any)...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'BusyWhatsappBridge' -and $_.CommandLine -match 'run\\.py|baileys-server\\\\server\\.js|uvicorn app\\.main:app' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; Write-Host ('[INFO] Stopped PID ' + $_.ProcessId) }"
echo [INFO] Clearing listeners on ports 3001/8000 (if any)...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ports = @(3001,8000); foreach($port in $ports){ Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue; Write-Host ('[INFO] Stopped port owner PID ' + $_ + ' on ' + $port) } }"

timeout /t 2 /nobreak >nul

echo [INFO] Starting Busy Whatsapp Bridge in tray mode...
SET "BWB_DEV_CONSOLE_LOGS=1"
"%VENV_PYTHON%" "%~dp0run.py"
