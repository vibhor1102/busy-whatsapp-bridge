@ECHO OFF
REM ============================================================================
REM Busy Whatsapp Bridge - Development Launcher
REM One-file development workflow: builds dashboard if needed, then starts app
REM ============================================================================

SETLOCAL EnableDelayedExpansion

SET "SCRIPT_DIR=%~dp0"
SET "VENV_PYTHON=%SCRIPT_DIR%venv\Scripts\python.exe"
SET "DASHBOARD_DIR=%SCRIPT_DIR%dashboard-react"
SET "DASHBOARD_DIST=%DASHBOARD_DIR%\dist"
SET "NODE_MODULES=%DASHBOARD_DIR%\node_modules"

REM Check prerequisites
IF NOT EXIST "%VENV_PYTHON%" (
    echo.
    echo [ERROR] Virtual environment not found at:
    echo   %VENV_PYTHON%
    echo.
    echo Run setup-bundled.bat first to set up the environment.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo Busy Whatsapp Bridge - Development Mode
echo ==========================================
echo.

REM ============================================================================
REM Step 1: Check and Build Dashboard
REM ============================================================================
echo [STEP 1/3] Checking dashboard build status...

REM Check if dashboard needs building
SET "NEEDS_BUILD=0"

IF NOT EXIST "%DASHBOARD_DIST%" SET "NEEDS_BUILD=1"
IF NOT EXIST "%DASHBOARD_DIST%\index.html" SET "NEEDS_BUILD=1"
IF NOT EXIST "%NODE_MODULES%" SET "NEEDS_BUILD=1"

IF "!NEEDS_BUILD!"=="1" (
    echo.
    echo [BUILD] Dashboard needs to be built.
    echo [BUILD] This may take 1-2 minutes for first build...
    echo.
    
    REM Check if npm is available
    where npm >nul 2>nul
    IF %ERRORLEVEL% NEQ 0 (
        echo [ERROR] npm not found. Please install Node.js from https://nodejs.org/
        echo [ERROR] Node.js 18+ is required.
        pause
        exit /b 1
    )
    
    REM Install dependencies if node_modules doesn't exist
    IF NOT EXIST "%NODE_MODULES%" (
        echo [BUILD] Installing npm dependencies...
        cd /d "%DASHBOARD_DIR%"
        call npm install
        IF %ERRORLEVEL% NEQ 0 (
            echo [ERROR] Failed to install npm dependencies!
            echo [ERROR] Check the error messages above.
            pause
            exit /b 1
        )
        echo [BUILD] Dependencies installed successfully.
        echo.
    )
    
    REM Build the dashboard - SHOW ALL OUTPUT
    echo [BUILD] Building dashboard for production...
    echo [BUILD] ==========================================
    cd /d "%DASHBOARD_DIR%"
    call npm run build
    SET "BUILD_RESULT=!ERRORLEVEL!"
    echo [BUILD] ==========================================
    
    IF !BUILD_RESULT! NEQ 0 (
        echo.
        echo [ERROR] Dashboard build failed with error code: !BUILD_RESULT!
        echo [ERROR] Please check the error messages above.
        echo.
        pause
        exit /b 1
    )
    echo.
    echo [BUILD] Dashboard built successfully!
) ELSE (
    echo [INFO] Dashboard is up to date.
)

echo.

REM ============================================================================
REM Step 2: Clean up existing processes
REM ============================================================================
echo [STEP 2/3] Stopping existing BusyWhatsappBridge processes...

REM Stop existing Python and Node processes related to BWB
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'BusyWhatsappBridge' -and ($_.CommandLine -match 'run\.py|baileys-server' -or $_.Name -match 'python|node') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; Write-Host ('[INFO] Stopped PID ' + $_.ProcessId) }" 2>nul

REM Clear ports 3001 (Baileys) and 8000 (FastAPI)
echo [INFO] Clearing ports 3001 and 8000...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ports = @(3001,8000); foreach($port in $ports){ Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue; Write-Host ('[INFO] Stopped process ' + $_ + ' on port ' + $port) } }" 2>nul

timeout /t 2 /nobreak >nul
echo.

REM ============================================================================
REM Step 3: Start Application
REM ============================================================================
echo [STEP 3/3] Starting Busy Whatsapp Bridge...
echo [INFO] Console will show logs. Tray icon will appear in system tray.
echo [INFO] Access dashboard at: http://localhost:8000/dashboard
echo.
echo Press Ctrl+C to stop the application
echo ==========================================
echo.

REM Set environment variable for console logging
SET "BWB_DEV_CONSOLE_LOGS=1"

REM Start the application
cd /d "%SCRIPT_DIR%"
"%VENV_PYTHON%" "%~dp0run.py"

REM If we get here, the app has exited
echo.
echo ==========================================
echo [INFO] Application stopped.
echo ==========================================
pause
