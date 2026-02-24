@ECHO OFF
SETLOCAL EnableDelayedExpansion

echo ================================================
echo Busy Whatsapp Bridge - Build Release Package
echo ================================================
echo.

SET "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Check if we have the bundled Python
IF NOT EXIST "python\python.exe" (
    echo [ERROR] Bundled Python not found!
    echo.
    echo This build script assumes you have already:
    echo   1. Downloaded Python embeddable (python-3.13.1-embed-win32.zip)
    echo   2. Extracted it to 'python/' directory
    echo   3. Created python313._pth configuration
    echo   4. Installed pip and virtualenv
    echo   5. Created venv with all dependencies
    echo.
    echo Run setup-bundled.bat first to prepare the environment.
    pause
    exit /b 1
)

REM Get version from git or use default
FOR /F "tokens=*" %%a IN ('git describe --tags --always 2^>nul') DO SET "VERSION=%%a"
IF NOT DEFINED VERSION SET "VERSION=v1.0.0"

echo Building release package: BusyWhatsappBridge-%VERSION%.zip
echo.

REM Create release directory
SET "RELEASE_DIR=%TEMP%\BusyWhatsappBridge-Release"
IF EXIST "%RELEASE_DIR%" rmdir /s /q "%RELEASE_DIR%"
mkdir "%RELEASE_DIR%"

echo [1/5] Copying application files...
xcopy /s /e /q /y /i "app" "%RELEASE_DIR%\app\" >nul
xcopy /s /e /q /y /i "baileys-server" "%RELEASE_DIR%\baileys-server\" >nul
xcopy /s /e /q /y /i "python" "%RELEASE_DIR%\python\" >nul
xcopy /s /e /q /y /i "venv" "%RELEASE_DIR%\venv\" >nul
xcopy /s /e /q /y /i "dashboard" "%RELEASE_DIR%\dashboard\" >nul 2>nul

echo [2/5] Copying configuration and docs...
copy "*.bat" "%RELEASE_DIR%\" >nul
copy "*.py" "%RELEASE_DIR%\" >nul
copy "*.md" "%RELEASE_DIR%\" >nul
copy "*.txt" "%RELEASE_DIR%\" >nul
copy "conf.json.example" "%RELEASE_DIR%\" >nul

echo [3/5] Copying documentation...
IF EXIST "docs" xcopy /s /e /q /y /i "docs" "%RELEASE_DIR%\docs\" >nul
IF EXIST "tests" xcopy /s /e /q /y /i "tests" "%RELEASE_DIR%\tests\" >nul

echo [4/5] Creating distribution package...
cd /d "%TEMP%"

REM Create zip file using PowerShell
powershell -Command "Compress-Archive -Path 'BusyWhatsappBridge-Release\*' -DestinationPath 'BusyWhatsappBridge-%VERSION%.zip' -Force"

IF ERRORLEVEL 1 (
    echo [ERROR] Failed to create zip file!
    pause
    exit /b 1
)

REM Move to project directory
move /y "BusyWhatsappBridge-%VERSION%.zip" "%SCRIPT_DIR%" >nul

echo [5/5] Cleaning up...
rmdir /s /q "%RELEASE_DIR%"

echo.
echo ================================================
echo Build Complete!
echo ================================================
echo.
echo Release package created:
echo   BusyWhatsappBridge-%VERSION%.zip
echo.
echo Package size:
dir /-C "BusyWhatsappBridge-%VERSION%.zip" | findstr "BusyWhatsappBridge"
echo.
echo Distribution includes:
echo   - Python 3.13.1 (32-bit) embeddable
echo   - Virtual environment with all dependencies
echo   - Baileys server (Node.js required separately)
echo   - All application code
echo   - Documentation
echo.
echo Installation for end users:
echo   1. Extract BusyWhatsappBridge-%VERSION%.zip
echo   2. Run setup-bundled.bat
echo   3. Done!
echo.

ENDLOCAL
exit /b 0
