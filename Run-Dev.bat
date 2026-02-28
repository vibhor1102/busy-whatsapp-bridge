@ECHO OFF
REM Busy Whatsapp Bridge - Development launcher
REM Automatically handles dashboard building and starts the application in tray mode.

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

echo.
echo ==========================================
echo Busy Whatsapp Bridge - Development Mode
echo ==========================================
echo.

REM Check and build dashboard if needed
echo [INFO] Checking dashboard build status...
"%VENV_PYTHON%" "%~dp0check-dashboard-build.py" --check >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [INFO] Dashboard not built or outdated. Building now...
    echo [INFO] This may take 1-2 minutes for first build...
    "%VENV_PYTHON%" "%~dp0check-dashboard-build.py" --build
    IF %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Dashboard build failed!
        echo [ERROR] Please check the errors above and try again.
        pause
        exit /b 1
    )
) ELSE (
    echo [INFO] Dashboard is ready.
)

echo.
echo [INFO] Stopping existing BusyWhatsappBridge background processes (if any)...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'BusyWhatsappBridge' -and $_.CommandLine -match 'run\.py|baileys-server\\server\.js|uvicorn app\.main:app' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; Write-Host ('[INFO] Stopped PID ' + $_.ProcessId) }"
echo [INFO] Clearing listeners on ports 3001/8000 (if any)...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ports = @(3001,8000); foreach($port in $ports){ Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue; Write-Host ('[INFO] Stopped port owner ' + $_ + ' on port ' + $port) } }"

timeout /t 2 /nobreak >nul

echo.
echo [INFO] Starting Busy Whatsapp Bridge in tray mode...
echo [INFO] Console will show logs. Tray icon will appear in system tray.
echo.
SET "BWB_DEV_CONSOLE_LOGS=1"
"%VENV_PYTHON%" "%~dp0run.py"

REM If we get here, the app has exited
echo.
echo [INFO] Application stopped.
pause
