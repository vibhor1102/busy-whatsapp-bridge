@ECHO OFF
REM Busy Whatsapp Bridge - Complete Build Orchestration
REM 
REM This script builds everything needed for a release:
REM   1. Builds the dashboard (npm run build)
REM   2. Builds the launcher EXE (PyInstaller)
REM   3. Builds the installer (Inno Setup)
REM 
REM Output: BusyWhatsappBridge-vX.X.X-Setup.exe
REM 
REM Author: vibhor1102

SETLOCAL EnableDelayedExpansion

echo ================================================
echo Busy Whatsapp Bridge - Complete Build
echo ================================================
echo.

REM Get script directory
SET "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Get version
SET "VENV_PYTHON=%SCRIPT_DIR%venv\Scripts\python.exe"
IF NOT EXIST "%VENV_PYTHON%" (
    echo [ERROR] Virtual environment not found! Run setup-bundled.bat first.
    pause
    exit /b 1
)
FOR /F "tokens=*" %%a IN ('"%VENV_PYTHON%" -c "from app.version import get_version; print(get_version())" 2^>nul') DO (
    SET "VERSION=%%a"
)

IF NOT DEFINED VERSION (
    echo [WARNING] Could not detect version, using 0.0.0-fallback
    SET "VERSION=0.0.0-fallback"
)

echo Building version: %VERSION%
echo.

REM ============================================================================
REM STEP 1: Build Dashboard
REM ============================================================================
echo [Step 1/4] Building dashboard...
echo.

IF NOT EXIST "dashboard-react\node_modules" (
    echo [INFO] Installing dashboard dependencies...
    cd dashboard-react
    call npm install
    IF ERRORLEVEL 1 (
        echo [ERROR] Failed to install dashboard dependencies!
        pause
        exit /b 1
    )
    cd ..
)

cd dashboard-react

echo Running npm run build...
call npm run build

IF ERRORLEVEL 1 (
    echo.
    echo [ERROR] Dashboard build failed!
    echo Check the errors above.
    pause
    exit /b 1
)

echo [OK] Dashboard built successfully
echo.

REM Verify dist folder exists
IF NOT EXIST "dist\index.html" (
    echo [ERROR] Dashboard build did not create dist/index.html!
    pause
    exit /b 1
)

cd ..

REM ============================================================================
REM STEP 2: Build Launcher EXE
REM ============================================================================
echo [Step 2/4] Building launcher EXE...
echo.

IF NOT EXIST "build-launcher-exe.py" (
    echo [ERROR] build-launcher-exe.py not found!
    pause
    exit /b 1
)

echo Running PyInstaller...
"%VENV_PYTHON%" build-launcher-exe.py

IF NOT EXIST "BusyWhatsappBridge.exe" (
    echo.
    echo [ERROR] EXE build failed! BusyWhatsappBridge.exe not found.
    pause
    exit /b 1
)

echo [OK] EXE built successfully
echo.

REM ============================================================================
REM STEP 3: Build Installer
REM ============================================================================
echo [Step 3/4] Building installer with Inno Setup...
echo.

IF NOT EXIST "build-installer.bat" (
    echo [ERROR] build-installer.bat not found!
    pause
    exit /b 1
)

echo Running Inno Setup...
call build-installer.bat

IF NOT EXIST "BusyWhatsappBridge-v%VERSION%-Setup.exe" (
    echo.
    echo [ERROR] Installer build failed!
    pause
    exit /b 1
)

echo [OK] Installer built successfully
echo.

REM ============================================================================
REM STEP 4: Verify Output
REM ============================================================================
echo [Step 4/4] Verifying build output...
echo.

SET "INSTALLER_FILE=BusyWhatsappBridge-v%VERSION%-Setup.exe"

IF EXIST "%INSTALLER_FILE%" (
    FOR %%A IN ("%INSTALLER_FILE%") DO (
        SET "SIZE=%%~zA"
    )
    
    echo ================================================
    echo BUILD COMPLETE!
    echo ================================================
    echo.
    echo Output file: %INSTALLER_FILE%
    echo Size: %SIZE% bytes
    echo.
    echo This installer includes:
    echo   - Python runtime (bundled)
    echo   - Application code
    echo   - Pre-built dashboard
    echo   - Baileys server
    echo   - All dependencies
    echo.
    echo Next steps:
    echo   1. Test the installer on a clean machine
    echo   2. Upload %INSTALLER_FILE% for distribution
    echo.
    echo Installation features:
    echo   [x] Desktop shortcut (default: enabled)
    echo   [x] Auto-start with Windows (default: enabled)
    echo   [x] System tray icon
    echo   [x] Start Menu entry
    echo   [x] Uninstaller
    echo   [x] Signed with developer certificate
    echo.
) ELSE (
    echo [ERROR] Output file not found!
    exit /b 1
)

ENDLOCAL
echo.
pause
