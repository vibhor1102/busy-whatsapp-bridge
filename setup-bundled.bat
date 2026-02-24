@ECHO OFF
SETLOCAL EnableDelayedExpansion

echo ================================================
echo Busy Whatsapp Bridge - Setup
echo ================================================
echo.

REM Save script directory and change to it
SET "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo Setting up Busy Whatsapp Bridge with bundled Python...
echo Directory: %SCRIPT_DIR%
echo.

REM Check for bundled Python
IF NOT EXIST "python\python.exe" (
    echo [ERROR] Bundled Python not found!
    echo Expected: %SCRIPT_DIR%python\python.exe
    echo.
    echo This is a bundled distribution. Python should be included.
    echo Please download the complete release package.
    pause
    exit /b 1
)

echo [OK] Found bundled Python
echo.

REM Check for virtual environment
IF NOT EXIST "venv\Scripts\python.exe" (
    echo [1/4] Creating virtual environment...
    python\Scripts\virtualenv.exe venv --python=python\python.exe
    IF ERRORLEVEL 1 (
        echo [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo      Virtual environment created
) ELSE (
    echo [1/4] Virtual environment already exists
)
echo.

REM Install dependencies
echo [2/4] Checking dependencies...
IF NOT EXIST "venv\Lib\site-packages\fastapi" (
    echo      Installing dependencies (this may take a few minutes)...
    venv\Scripts\pip.exe install -r requirements.txt --no-warn-script-location
    IF ERRORLEVEL 1 (
        echo [ERROR] Failed to install dependencies!
        pause
        exit /b 1
    )
    echo      Dependencies installed
) ELSE (
    echo      Dependencies already installed
)
echo.

REM Setup configuration
echo [3/4] Setting up configuration...

REM Get AppData path
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v LOCALAPPDATA 2^>nul ^| findstr "LOCALAPPDATA"') do set "LOCALAPPDATA=%%b"
IF NOT DEFINED LOCALAPPDATA SET "LOCALAPPDATA=%USERPROFILE%\AppData\Local"

SET "CONFIG_DIR=%LOCALAPPDATA%\BusyWhatsappBridge"
SET "CONFIG_FILE=%CONFIG_DIR%\conf.json"

IF EXIST "%CONFIG_FILE%" (
    echo      Configuration already exists at:
    echo        %CONFIG_FILE%
) ELSE (
    IF NOT EXIST "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"
    copy conf.json.example "%CONFIG_FILE%" >nul
    echo      Created configuration file:
    echo        %CONFIG_FILE%
    echo.
    echo      IMPORTANT: Edit this file with your settings!
    echo        - database.bds_file_path
    echo        - whatsapp credentials
)
echo.

REM Run AppData migration if old data exists
echo [4/4] Checking for existing data...
IF EXIST "data\messages.db" (
    echo      Found old data in Program Files.
    echo      Migrating to AppData...
    venv\Scripts\python.exe migrate-to-appdata.py --auto
    echo      Migration complete!
) ELSE (
    IF EXIST "%CONFIG_DIR%\data\messages.db" (
        echo      Data already in AppData
    ) ELSE (
        echo      No existing data found
    )
)
echo.

REM Create desktop shortcuts
echo Creating shortcuts...
venv\Scripts\python.exe Create-Desktop-Shortcut.py
echo.

REM Final status
echo ================================================
echo Setup Complete!
echo ================================================
echo.
echo Your Busy Whatsapp Bridge is ready to use!
echo.
echo Quick Start:
echo   1. Edit configuration: notepad "%CONFIG_FILE%"
echo   2. Start manually: Start-Gateway.bat --tray
echo   3. Enable auto-start: manage-task.bat
echo.
echo All data is stored in: %CONFIG_DIR%
echo.
echo Would you like to enable auto-start on login?
echo This will start the application automatically when you log in.
echo.
SET /P AUTO_START="Enable auto-start? [Y/n]: "
IF /I "%AUTO_START%"=="Y" (
    echo.
    venv\Scripts\python.exe -m app.task_scheduler install
    echo.
    echo Auto-start enabled! The application will start on next login.
)

echo.
echo Setup complete!
echo.
echo Press any key to exit...
pause >nul
ENDLOCAL
exit /b 0
