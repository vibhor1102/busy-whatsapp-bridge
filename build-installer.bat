@ECHO OFF
SETLOCAL EnableDelayedExpansion

echo ================================================
echo Busy Whatsapp Bridge - Installer Builder
echo ================================================
echo.

REM Get script directory
SET "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Check for Inno Setup
SET "ISCC="

REM Check common Inno Setup locations
IF EXIST "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    SET "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)
IF EXIST "C:\Program Files\Inno Setup 6\ISCC.exe" (
    SET "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"
)
IF EXIST "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" (
    SET "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
)

IF NOT DEFINED ISCC (
    echo [ERROR] Inno Setup 6 not found!
    echo.
    echo Please install Inno Setup 6 from:
    echo https://jrsoftware.org/isdl.php
    echo.
    pause
    exit /b 1
)

echo [OK] Found Inno Setup: %ISCC%
echo.

REM Verify required directories exist
echo Checking prerequisites...

IF NOT EXIST "app\" (
    echo [ERROR] app\ directory not found!
    exit /b 1
)

IF NOT EXIST "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found!
    echo Please run setup-bundled.bat first.
    exit /b 1
)

IF NOT EXIST "python\python.exe" (
    echo [ERROR] Bundled Python not found!
    exit /b 1
)

IF NOT EXIST "LICENSE" (
    echo [ERROR] LICENSE file not found!
    exit /b 1
)

IF NOT EXIST "BusyWhatsappBridge.exe" (
    echo [WARNING] BusyWhatsappBridge.exe not found!
    echo Building launcher EXE first...
    echo.
    python build-launcher-exe.py
    IF NOT EXIST "BusyWhatsappBridge.exe" (
        echo [ERROR] Failed to build launcher EXE!
        exit /b 1
    )
)

echo [OK] All prerequisites met
echo.

REM Get version from app/version.py
echo Detecting version...
FOR /F "tokens=*" %%a IN ('python -c "from app.version import get_version; print(get_version())" 2^>nul') DO (
    SET "VERSION=%%a"
)

IF NOT DEFINED VERSION (
    echo [WARNING] Could not detect version, using 0.0.1
    SET "VERSION=0.0.1"
)

echo [OK] Version: %VERSION%
echo.

REM Build the installer
echo Building installer...
echo This may take a few minutes...
echo.

"%ISCC%" "installer.iss"

IF ERRORLEVEL 1 (
    echo.
    echo [ERROR] Installer build failed!
    pause
    exit /b 1
)

REM Check if installer was created
SET "INSTALLER_EXE=BusyWhatsappBridge-v%VERSION%-Setup.exe"

IF EXIST "%INSTALLER_EXE%" (
    echo.
    echo ================================================
    echo SUCCESS!
    echo ================================================
    echo.
    echo Installer created: %INSTALLER_EXE%
    
    FOR %%A IN ("%INSTALLER_EXE%") DO (
        SET "SIZE=%%~zA"
    )
    
    echo Size: %SIZE% bytes
    echo.
    echo This is a self-contained installer that includes:
    echo   - Python runtime
    echo   - Virtual environment with all dependencies
    echo   - Application code
    echo   - Baileys server
    echo   - Dashboard files
    echo.
    echo Users just need to download this one file and run it!
    echo.
    echo To test:
    echo   1. Copy %INSTALLER_EXE% to a test machine
    echo   2. Run it
    echo   3. Follow the installation wizard
    echo   4. Launch from Start Menu
    echo.
) ELSE (
    echo.
    echo [ERROR] Installer file not created!
    echo Check build output for errors.
    pause
    exit /b 1
)

ENDLOCAL
exit /b 0
