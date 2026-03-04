@ECHO OFF
REM Busy Whatsapp Bridge - Complete Build Orchestration
REM 
REM This is the ONLY script you need to run to produce a release.
REM It builds everything and creates the installer EXE.
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

REM ============================================================================
REM STEP 0: Detect Version and Check Prerequisites
REM ============================================================================

SET "VENV_PYTHON=%SCRIPT_DIR%venv\Scripts\python.exe"
IF NOT EXIST "%VENV_PYTHON%" (
    echo [ERROR] Virtual environment not found! Run setup-bundled.bat first.
    pause
    exit /b 1
)

REM Read version from version.json via Python (reliable, no quoting issues)
SET "VERSION="
"%VENV_PYTHON%" -c "import json; print(json.load(open('version.json'))['version'])" > "%TEMP%\busy_version.txt" 2>nul
SET /P VERSION=<"%TEMP%\busy_version.txt"
DEL "%TEMP%\busy_version.txt" 2>nul

IF NOT DEFINED VERSION (
    echo [WARNING] Could not detect version, using 0.0.0
    SET "VERSION=0.0.0"
)

echo Building version: %VERSION%
echo.

REM Check for Inno Setup early (fail fast)
SET "ISCC="
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
echo [OK] Inno Setup found: %ISCC%

REM Check other prerequisites
IF NOT EXIST "python\python.exe" (
    echo [ERROR] Bundled Python not found!
    pause
    exit /b 1
)
echo [OK] Prerequisites met
echo.

REM ============================================================================
REM STEP 1: Build Dashboard
REM ============================================================================
echo [Step 1/5] Building dashboard...
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
echo [Step 2/5] Building launcher EXE...
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
REM STEP 3: Prepare Staging Directory
REM ============================================================================
echo [Step 3/5] Preparing staging directory (release_dist)...
echo.

SET "DIST_DIR=%SCRIPT_DIR%release_dist"
IF EXIST "%DIST_DIR%" rd /s /q "%DIST_DIR%"
mkdir "%DIST_DIR%"

REM --- Directories (robocopy, with exit code handling) ---
echo   Copying app...
robocopy "app" "%DIST_DIR%\app" /E /XD __pycache__ /XF *.pyc /NFL /NDL /NJH /NJS /nc /ns /np
IF %ERRORLEVEL% GEQ 8 ( echo [ERROR] Failed to copy app & exit /b 1 )

echo   Copying bundled Python...
robocopy "python" "%DIST_DIR%\python" /E /NFL /NDL /NJH /NJS /nc /ns /np
IF %ERRORLEVEL% GEQ 8 ( echo [ERROR] Failed to copy python & exit /b 1 )

echo   Copying Baileys server...
robocopy "baileys-server" "%DIST_DIR%\baileys-server" /E /XD auth logs /NFL /NDL /NJH /NJS /nc /ns /np
IF %ERRORLEVEL% GEQ 8 ( echo [ERROR] Failed to copy baileys-server & exit /b 1 )

REM Install baileys node_modules if missing
IF NOT EXIST "baileys-server\node_modules" (
    echo   Installing Baileys dependencies...
    cd baileys-server
    call npm install --production
    IF ERRORLEVEL 1 (
        echo [ERROR] Failed to install Baileys dependencies!
        exit /b 1
    )
    cd ..
)

echo   Copying virtual environment...
robocopy "venv" "%DIST_DIR%\venv" /E /XD __pycache__ /XF *.pyc /NFL /NDL /NJH /NJS /nc /ns /np
IF %ERRORLEVEL% GEQ 8 ( echo [ERROR] Failed to copy venv & exit /b 1 )

echo   Copying dashboard dist...
robocopy "dashboard-react\dist" "%DIST_DIR%\dashboard-react\dist" /E /NFL /NDL /NJH /NJS /nc /ns /np
IF %ERRORLEVEL% GEQ 8 ( echo [ERROR] Failed to copy dashboard & exit /b 1 )

REM --- Root files (using a manifest approach) ---
echo   Copying root files...

REM Core executables and scripts (REQUIRED - fail if missing)
FOR %%F IN (
    BusyWhatsappBridge.exe
    run.py
    Start-Gateway.py
    setup.py
    uninstall.py
    manage-task.bat
    configure-firewall.bat
    app.ico
    conf.json.example
    requirements.txt
    version.json
    LICENSE
) DO (
    IF EXIST "%%F" (
        copy "%%F" "%DIST_DIR%\" >nul
    ) ELSE (
        echo [ERROR] Required file missing: %%F
        pause
        exit /b 1
    )
)

REM Documentation files (OPTIONAL - skip if missing)
FOR %%F IN (
    README.md
    USER-GUIDE.md
    INSTALL.md
    CHANGELOG.md
) DO (
    IF EXIST "%%F" copy "%%F" "%DIST_DIR%\" >nul
)

echo [OK] Staging directory prepared
echo.

REM ============================================================================
REM STEP 4: Build Installer (Inno Setup)
REM ============================================================================
echo [Step 4/5] Building installer...
echo This may take a few minutes...
echo.

"%ISCC%" /DMyAppVersion=%VERSION% "installer.iss"

IF ERRORLEVEL 1 (
    echo.
    echo [ERROR] Installer build failed!
    pause
    exit /b 1
)

SET "INSTALLER_FILE=BusyWhatsappBridge-v%VERSION%-Setup.exe"

IF NOT EXIST "%INSTALLER_FILE%" (
    echo [ERROR] Installer file not created!
    pause
    exit /b 1
)

echo [OK] Installer built successfully
echo.

REM ============================================================================
REM STEP 5: Sign and Verify
REM ============================================================================
echo [Step 5/5] Signing and verifying...
echo.

REM Sign the installer
echo Signing installer...
powershell.exe -ExecutionPolicy Bypass -File "scripts\manage-signing.ps1" -Action sign -File "%INSTALLER_FILE%" 2>nul
IF ERRORLEVEL 1 (
    echo [WARNING] Signing failed, but installer was created successfully.
)
echo.

REM Report
FOR %%A IN ("%INSTALLER_FILE%") DO SET "SIZE=%%~zA"

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

ENDLOCAL
echo.
pause
