@ECHO OFF
REM ============================================================================
REM Busy Whatsapp Bridge - Development Launcher
REM One-file development workflow: builds dashboard if needed, then starts app
REM Enhanced logging for transparency and diagnostics
REM ============================================================================

SETLOCAL EnableDelayedExpansion

SET "SCRIPT_DIR=%~dp0"
SET "VENV_PYTHON=%SCRIPT_DIR%venv\Scripts\python.exe"
SET "DASHBOARD_DIR=%SCRIPT_DIR%dashboard-react"
SET "DASHBOARD_DIST=%DASHBOARD_DIR%\dist"
SET "NODE_MODULES=%DASHBOARD_DIR%\node_modules"
SET "CONFIG_DIR=%APPDATA%\BusyWhatsappBridge"
SET "CONFIG_FILE=%CONFIG_DIR%\conf.json"

REM Get current timestamp
for /f "tokens=2 delims==" %%a in ('wmic os get localdatetime /value') do set "DT=%%a"
set "TIMESTAMP=%DT:~8,2%:%DT:~10,2%:%DT:~12,2%"

REM Helper function to log with timestamp
call :log_header "Busy Whatsapp Bridge - Development Mode"
call :log_info "Script directory: %SCRIPT_DIR%"
call :log_info "Working directory: %CD%"
call :log_info "Python executable: %VENV_PYTHON%"
echo.

REM ============================================================================
REM Pre-flight Configuration Check
REM ============================================================================
call :log_step "PRE-FLIGHT" "Checking configuration and prerequisites"

REM Check if conf.json exists
call :log_info "Configuration file: %CONFIG_FILE%"
IF EXIST "%CONFIG_FILE%" (
    call :log_success "Configuration file exists"
    REM Try to parse basic info from it
    powershell -NoProfile -Command "try { $c=Get-Content '%CONFIG_FILE%'|ConvertFrom-Json; Write-Host '[CONFIG] Provider:' $c.whatsapp.provider } catch { Write-Host '[CONFIG] Unable to parse config' }" 2>nul
) ELSE (
    call :log_warning "Configuration file NOT FOUND - will be created on first run"
    call :log_info "You will need to edit %CONFIG_FILE% after first startup"
)
echo.

REM Check prerequisites
call :log_step "CHECK" "Verifying environment"

IF NOT EXIST "%VENV_PYTHON%" (
    call :log_error "Virtual environment not found at: %VENV_PYTHON%"
    call :log_info "Run setup-bundled.bat first to set up the environment."
    pause
    exit /b 1
)
call :log_success "Virtual environment found"

REM Check Node.js
where node >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    call :log_error "Node.js not found in PATH"
    call :log_info "Please install Node.js 18+ from https://nodejs.org/"
    pause
    exit /b 1
)
for /f "delims=" %%v in ('node --version 2^>nul') do set "NODE_VERSION=%%v"
call :log_success "Node.js found: %NODE_VERSION%"

REM Resolve npm command (supports missing npm.cmd)
call :resolve_npm
IF !ERRORLEVEL! NEQ 0 (
    call :log_error "npm not found in PATH or Node.js installation"
    call :log_info "Install npm or repair Node.js install from https://nodejs.org/"
    pause
    exit /b 1
)
call :log_success "npm found: !NPM_VERSION!"

REM Check Python version
for /f "delims=" %%v in ('"%VENV_PYTHON%" --version 2^>nul') do set "PYTHON_VERSION=%%v"
call :log_success "Python found: %PYTHON_VERSION%"
echo.

REM ============================================================================
REM Step 1: Check and Build Dashboard
REM ============================================================================
call :log_step "STEP 1/3" "Checking dashboard build status"

REM Check if dashboard needs building
SET "NEEDS_BUILD=0"

IF NOT EXIST "%DASHBOARD_DIST%" (
    call :log_info "Dashboard dist folder not found: %DASHBOARD_DIST%"
    SET "NEEDS_BUILD=1"
)
IF NOT EXIST "%DASHBOARD_DIST%\index.html" (
    call :log_info "Dashboard index.html not found"
    SET "NEEDS_BUILD=1"
)
IF NOT EXIST "%NODE_MODULES%" (
    call :log_info "Node modules not found"
    SET "NEEDS_BUILD=1"
)

REM Check if source files are newer than dist (staleness detection)
IF "!NEEDS_BUILD!"=="0" (
    call :log_info "Checking if dashboard build is outdated..."
    powershell -NoProfile -Command "$dist=(Get-Item '%DASHBOARD_DIST%\index.html' -ErrorAction SilentlyContinue).LastWriteTime; if(-not $dist){exit 1}; $newer=Get-ChildItem '%DASHBOARD_DIR%\src' -Recurse -Include *.tsx,*.ts,*.css,*.html | Where-Object {$_.LastWriteTime -gt $dist}; if($newer){Write-Host $newer[0].Name; exit 1} else {exit 0}" 2>nul
    IF !ERRORLEVEL! NEQ 0 (
        call :log_info "Source files are newer than build"
        SET "NEEDS_BUILD=1"
    )
)

IF "!NEEDS_BUILD!"=="1" (
    call :log_info "Dashboard needs to be built (first time or missing files)"
    call :log_info "This may take 1-2 minutes for first build..."
    echo.
    
    REM Install dependencies if node_modules doesn't exist
    IF NOT EXIST "%NODE_MODULES%" (
        call :log_info "Installing npm dependencies in: %DASHBOARD_DIR%"
        cd /d "%DASHBOARD_DIR%"
        call :log_cmd "!NPM_CMD! install"
        call !NPM_CMD! install
        IF %ERRORLEVEL% NEQ 0 (
            call :log_error "Failed to install npm dependencies! (Exit code: %ERRORLEVEL%)"
            call :log_info "Check the error messages above for details."
            pause
            exit /b 1
        )
        call :log_success "Dependencies installed successfully"
        echo.
    )
    
    REM Build the dashboard - SHOW ALL OUTPUT
    call :log_info "Building dashboard for production..."
    call :log_info "Command: !NPM_CMD! run build"
    echo.
    cd /d "%DASHBOARD_DIR%"
    call !NPM_CMD! run build
    SET "BUILD_RESULT=!ERRORLEVEL!"
    
    IF !BUILD_RESULT! NEQ 0 (
        echo.
        call :log_error "Dashboard build failed with error code: !BUILD_RESULT!"
        call :log_info "Please check the error messages above."
        echo.
        pause
        exit /b 1
    )
    call :log_success "Dashboard built successfully!"
) ELSE (
    call :log_success "Dashboard is up to date"
)
echo.

REM ============================================================================
REM Step 2: Clean up existing processes
REM ============================================================================
call :log_step "STEP 2/3" "Stopping existing BusyWhatsappBridge processes"

REM Stop existing Python and Node processes related to BWB
call :log_info "Checking for existing BWB processes..."
powershell -NoProfile -ExecutionPolicy Bypass -Command "$count=0; Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'BusyWhatsappBridge' -and ($_.CommandLine -match 'run\.py|baileys-server' -or $_.Name -match 'python|node') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; $count++; Write-Host ('[STOPPED] PID ' + $_.ProcessId + ' - ' + $_.Name) }; if($count -eq 0) { Write-Host '[INFO] No existing BWB processes found' } else { Write-Host ('[INFO] Stopped ' + $count + ' process(es)') }" 2>nul

REM Clear ports 3001 (Baileys) and 8000 (FastAPI)
call :log_info "Checking ports 3001 (Baileys) and 8000 (FastAPI)..."
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ports = @(3001,8000); $found=$false; foreach($port in $ports){ $procs = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique; foreach($proc in $procs) { Stop-Process -Id $proc -Force -ErrorAction SilentlyContinue; $found=$true; Write-Host ('[STOPPED] Process ' + $proc + ' on port ' + $port) } }; if(-not $found) { Write-Host '[INFO] Ports are clear' }" 2>nul

timeout /t 2 /nobreak >nul
echo.

REM ============================================================================
REM Step 3: Start Application
REM ============================================================================
call :log_step "STEP 3/3" "Starting Busy Whatsapp Bridge"

call :log_info "Environment variables set:"
echo   - BWB_DEV_CONSOLE_LOGS=1
echo   - CONFIG_DIR=%CONFIG_DIR%
echo.
call :log_info "Services will start:"
echo   - Baileys Node.js server (port 3001)
echo   - FastAPI gateway (port 8000)
echo.
call :log_info "Access dashboard at: http://localhost:8000/dashboard"
call :log_info "Tray icon will appear in system tray"
echo.
call :log_info "Press Ctrl+C to stop the application"
call :log_separator
echo.

REM Set environment variable for console logging
SET "BWB_DEV_CONSOLE_LOGS=1"

REM Display the exact command being executed
call :log_cmd "\"%VENV_PYTHON%\" \"%SCRIPT_DIR%run.py\""
cd /d "%SCRIPT_DIR%"

REM Start the application with real-time output
echo.
"%VENV_PYTHON%" "%SCRIPT_DIR%run.py"
SET "APP_EXIT_CODE=%ERRORLEVEL%"

REM If we get here, the app has exited
echo.
call :log_separator
IF %APP_EXIT_CODE% NEQ 0 (
    call :log_error "Application exited with code: %APP_EXIT_CODE%"
    call :log_info "Check the logs above for error details"
) ELSE (
    call :log_success "Application stopped normally"
)
call :log_separator
exit /b %APP_EXIT_CODE%

REM Should never reach here, but just in case
exit /b 0

REM ============================================================================
REM Logging Helper Functions
REM ============================================================================
:log_header
    echo.
    echo ==========================================
    echo %~1
    echo ==========================================
    goto :eof

:log_separator
    echo ==========================================
    goto :eof

:log_timestamp
    for /f "tokens=2 delims==" %%a in ('wmic os get localdatetime /value') do set "DT=%%a"
    set "NOW=%DT:~8,2%:%DT:~10,2%:%DT:~12,2%"
    echo [%NOW%]
    goto :eof

:log_info
    for /f "tokens=2 delims==" %%a in ('wmic os get localdatetime /value') do set "DT=%%a"
    echo [%DT:~8,2%:%DT:~10,2%:%DT:~12,2%] [INFO] %~1
    goto :eof

:log_success
    for /f "tokens=2 delims==" %%a in ('wmic os get localdatetime /value') do set "DT=%%a"
    echo [%DT:~8,2%:%DT:~10,2%:%DT:~12,2%] [OK] %~1
    goto :eof

:log_warning
    for /f "tokens=2 delims==" %%a in ('wmic os get localdatetime /value') do set "DT=%%a"
    echo [%DT:~8,2%:%DT:~10,2%:%DT:~12,2%] [WARN] %~1
    goto :eof

:log_error
    for /f "tokens=2 delims==" %%a in ('wmic os get localdatetime /value') do set "DT=%%a"
    echo [%DT:~8,2%:%DT:~10,2%:%DT:~12,2%] [ERROR] %~1
    goto :eof

:log_step
    for /f "tokens=2 delims==" %%a in ('wmic os get localdatetime /value') do set "DT=%%a"
    echo.
    echo [%DT:~8,2%:%DT:~10,2%:%DT:~12,2%] [%~1] %~2
    goto :eof

:log_cmd
    for /f "tokens=2 delims==" %%a in ('wmic os get localdatetime /value') do set "DT=%%a"
    echo [%DT:~8,2%:%DT:~10,2%:%DT:~12,2%] [CMD] %~1
    goto :eof

:resolve_npm
    set "NPM_CMD=npm"
    set "NPM_VERSION="
    for /f "delims=" %%v in ('npm --version 2^>nul') do set "NPM_VERSION=%%v"
    if defined NPM_VERSION exit /b 0

    set "NODE_PATH="
    for /f "delims=" %%p in ('where node 2^>nul') do (
        if not defined NODE_PATH set "NODE_PATH=%%p"
    )
    if not defined NODE_PATH exit /b 1

    set "NODE_DIR="
    for %%d in ("!NODE_PATH!") do set "NODE_DIR=%%~dpd"
    if not defined NODE_DIR exit /b 1

    set "NPM_CLI=!NODE_DIR!node_modules\npm\bin\npm-cli.js"
    if exist "!NPM_CLI!" (
        set "NPM_CMD=node ""!NPM_CLI!"""
        for /f "delims=" %%v in ('node "!NPM_CLI!" --version 2^>nul') do set "NPM_VERSION=%%v"
        if defined NPM_VERSION exit /b 0
    )

    exit /b 1
