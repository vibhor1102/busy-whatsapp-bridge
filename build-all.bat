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
SET "NO_PAUSE=%BUILD_NO_PAUSE%"

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
    call :maybe_pause
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
SET "RELEASE_TAG=v%VERSION%"

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
    call :maybe_pause
    exit /b 1
)
echo [OK] Inno Setup found: %ISCC%

REM Check other prerequisites
IF NOT EXIST "python\python.exe" (
    echo [ERROR] Bundled Python not found!
    call :maybe_pause
    exit /b 1
)

where gh >nul 2>nul
IF ERRORLEVEL 1 (
    echo [ERROR] GitHub CLI ^(gh^) not found!
    call :attention "Install GitHub CLI or remove release publishing from this build."
    call :maybe_pause
    exit /b 1
)

gh auth status >nul 2>nul
IF ERRORLEVEL 1 (
    echo [ERROR] GitHub CLI is not signed in!
    call :attention "Run: gh auth login"
    call :maybe_pause
    exit /b 1
)

SET "GIT_STATUS_SIZE=0"
git status --porcelain > "%TEMP%\busy_git_status.txt" 2>nul
FOR %%A IN ("%TEMP%\busy_git_status.txt") DO SET "GIT_STATUS_SIZE=%%~zA"
IF NOT "%GIT_STATUS_SIZE%"=="0" (
    echo [ERROR] Git working tree is not clean!
    del "%TEMP%\busy_git_status.txt" 2>nul
    call :attention "Commit or stash your changes before running build-all.bat."
    call :maybe_pause
    exit /b 1
)
del "%TEMP%\busy_git_status.txt" 2>nul

git rev-parse -q --verify "refs\tags\%RELEASE_TAG%" >nul 2>nul
IF NOT ERRORLEVEL 1 (
    echo [ERROR] Tag %RELEASE_TAG% already exists locally!
    call :attention "Bump version.json or delete the tag manually if you intend to rebuild that version."
    call :maybe_pause
    exit /b 1
)

SET "REMOTE_TAG_EXISTS="
FOR /F "delims=" %%I IN ('git ls-remote --tags origin "refs/tags/%RELEASE_TAG%" 2^>nul') DO SET "REMOTE_TAG_EXISTS=1"
IF DEFINED REMOTE_TAG_EXISTS (
    echo [ERROR] Tag %RELEASE_TAG% already exists on origin!
    call :attention "This version is already tagged remotely. Bump version.json for the next release."
    call :maybe_pause
    exit /b 1
)

gh release view "%RELEASE_TAG%" >nul 2>nul
IF NOT ERRORLEVEL 1 (
    echo [ERROR] GitHub release %RELEASE_TAG% already exists!
    call :attention "Bump version.json for a new release, or manage the existing release manually on GitHub."
    call :maybe_pause
    exit /b 1
)

echo [OK] Prerequisites met
echo.

REM ============================================================================
REM STEP 1: Build Dashboard
REM ============================================================================
echo [Step 1/6] Building dashboard...
echo.

echo [INFO] Syncing dashboard package version...
"%VENV_PYTHON%" "scripts\sync_dashboard_version.py"
IF ERRORLEVEL 1 (
    echo [ERROR] Failed to sync dashboard version!
    call :maybe_pause
    exit /b 1
)

IF NOT EXIST "dashboard-react\node_modules" (
    echo [INFO] Installing dashboard dependencies...
    cd dashboard-react
    call npm ci
    IF ERRORLEVEL 1 (
        echo [WARNING] npm ci failed, falling back to npm install...
        call npm install
    )
    IF ERRORLEVEL 1 (
        echo [ERROR] Failed to install dashboard dependencies!
        call :maybe_pause
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
    call :maybe_pause
    exit /b 1
)

echo [OK] Dashboard built successfully
echo.

REM Verify dist folder exists
IF NOT EXIST "dist\index.html" (
    echo [ERROR] Dashboard build did not create dist/index.html!
    call :maybe_pause
    exit /b 1
)

cd ..

REM ============================================================================
REM STEP 2: Build Launcher EXE
REM ============================================================================
echo [Step 2/6] Building launcher EXE...
echo.

IF NOT EXIST "build-launcher-exe.py" (
    echo [ERROR] build-launcher-exe.py not found!
    call :maybe_pause
    exit /b 1
)

echo Running PyInstaller...
IF EXIST "BusyWhatsappBridge.exe" del /f /q "BusyWhatsappBridge.exe" >nul 2>nul
"%VENV_PYTHON%" build-launcher-exe.py
IF ERRORLEVEL 1 (
    echo.
    echo [ERROR] EXE build command failed.
    call :maybe_pause
    exit /b 1
)

IF NOT EXIST "BusyWhatsappBridge.exe" (
    echo.
    echo [ERROR] EXE build failed! BusyWhatsappBridge.exe not found.
    call :maybe_pause
    exit /b 1
)

echo [OK] EXE built successfully
echo.

REM ============================================================================
REM STEP 3: Prepare Staging Directory
REM ============================================================================
echo [Step 3/6] Preparing staging directory (release_dist)...
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

REM Install baileys node_modules if missing
IF NOT EXIST "baileys-server\node_modules" (
    echo   Installing Baileys dependencies...
    cd baileys-server
    call npm ci --omit=dev
    IF ERRORLEVEL 1 (
        echo   [WARNING] npm ci failed, falling back to npm install --production...
        call npm install --production
    )
    IF ERRORLEVEL 1 (
        echo [ERROR] Failed to install Baileys dependencies!
        exit /b 1
    )
    cd ..
)

echo   Copying Baileys server...
robocopy "baileys-server" "%DIST_DIR%\baileys-server" /E /XD auth logs /NFL /NDL /NJH /NJS /nc /ns /np
IF %ERRORLEVEL% GEQ 8 ( echo [ERROR] Failed to copy baileys-server & exit /b 1 )

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
        call :maybe_pause
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
echo [Step 4/6] Building installer...
echo This may take a few minutes...
echo.

"%ISCC%" /DMyAppVersion=%VERSION% "installer.iss"

IF ERRORLEVEL 1 (
    echo.
    echo [ERROR] Installer build failed!
    call :maybe_pause
    exit /b 1
)

SET "INSTALLER_FILE=BusyWhatsappBridge-v%VERSION%-Setup.exe"

IF NOT EXIST "%INSTALLER_FILE%" (
    echo [ERROR] Installer file not created!
    call :maybe_pause
    exit /b 1
)

echo [OK] Installer built successfully
echo.

REM ============================================================================
REM STEP 5: Sign and Verify
REM ============================================================================
echo [Step 5/6] Signing and verifying...
echo.

REM Sign the installer
echo Signing installer...
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "scripts\manage-signing.ps1" -Action sign -File "%INSTALLER_FILE%"
IF ERRORLEVEL 1 (
    echo [ERROR] Signing failed. Aborting release build.
    call :maybe_pause
    exit /b 1
)
echo.

echo Verifying installer signature...
"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "$s = Get-AuthenticodeSignature '%INSTALLER_FILE%'; if ($s.SignatureType -eq 'None' -or -not $s.SignerCertificate) { exit 1 } else { exit 0 }"
IF ERRORLEVEL 1 (
    echo [ERROR] Signature verification failed. Installer is not signed.
    call :maybe_pause
    exit /b 1
)
echo [OK] Installer signature verified
echo.

REM ============================================================================
REM STEP 6: Create Git Tag and GitHub Release
REM ============================================================================
echo [Step 6/6] Publishing GitHub release...
echo.

git tag "%RELEASE_TAG%"
IF ERRORLEVEL 1 (
    echo [ERROR] Failed to create git tag %RELEASE_TAG%!
    call :attention "Create and push the tag manually if you still want to publish this release."
    call :maybe_pause
    exit /b 1
)

git push origin "%RELEASE_TAG%"
IF ERRORLEVEL 1 (
    echo [ERROR] Failed to push git tag %RELEASE_TAG%!
    call :attention "Push the tag manually, then create the GitHub release by hand if needed."
    call :maybe_pause
    exit /b 1
)

gh release create "%RELEASE_TAG%" "%INSTALLER_FILE%" --title "%RELEASE_TAG%" --generate-notes --latest
IF ERRORLEVEL 1 (
    echo [ERROR] Failed to create GitHub release %RELEASE_TAG%!
    call :attention "The tag was pushed. Finish the release manually on GitHub or with gh release create."
    call :maybe_pause
    exit /b 1
)

echo [OK] GitHub release published
echo.

REM Report
FOR %%A IN ("%INSTALLER_FILE%") DO SET "SIZE=%%~zA"

echo ================================================
echo BUILD COMPLETE!
echo ================================================
echo.
echo Output file: %INSTALLER_FILE%
echo Size: %SIZE% bytes
echo Release tag: %RELEASE_TAG%
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
echo   2. Verify the GitHub release page and download asset
echo.

echo.
call :maybe_pause
ENDLOCAL
exit /b 0

:maybe_pause
IF /I "%NO_PAUSE%"=="1" goto :eof
IF /I "%CI%"=="true" goto :eof
pause
goto :eof

:attention
powershell -NoProfile -NonInteractive -Command "Write-Host ''; Write-Host '*** ACTION REQUIRED ***' -ForegroundColor Yellow; Write-Host '%~1' -ForegroundColor Red; Write-Host ''"
goto :eof
