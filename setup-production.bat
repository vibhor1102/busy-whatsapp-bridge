@echo off
setlocal EnableDelayedExpansion

echo ================================================
echo Busy Whatsapp Bridge - Production Setup
echo ================================================
echo.

:: Save script directory and change to it (running as admin changes cwd to System32)
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

:: Check for Admin rights
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] This script requires Administrator privileges!
    echo Please right-click and select "Run as administrator"
    pause
    exit /b 1
)

:: Make sure we're in the script directory
cd /d "%SCRIPT_DIR%"

:: Find 32-bit Python
set "PYTHON32="
set "PYTHON_PATHS=C:\Python39-32\python.exe C:\Python310-32\python.exe C:\Python311-32\python.exe C:\Python312-32\python.exe C:\Python313-32\python.exe C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python39-32\python.exe C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python310-32\python.exe C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311-32\python.exe C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python312-32\python.exe C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313-32\python.exe C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python314-32\python.exe"

for %%P in (%PYTHON_PATHS%) do (
    if exist "%%P" (
        set "PYTHON32=%%P"
        goto :found_python
    )
)

:: Check registry for 32-bit Python
for /f "tokens=2*" %%a in ('reg query "HKLM\SOFTWARE\Python\PythonCore" /s /f "InstallPath" 2^>nul ^| findstr "InstallPath"') do (
    if exist "%%b\python.exe" (
        "%%b\python.exe" -c "import struct; exit(0 if struct.calcsize('P') * 8 == 32 else 1)" 2>nul
        if !errorLevel! equ 0 (
            set "PYTHON32=%%b\python.exe"
            goto :found_python
        )
    )
)

:: Check user-specific Python installations in AppData
for /f "tokens=2*" %%a in ('reg query "HKCU\SOFTWARE\Python\PythonCore" /s /f "InstallPath" 2^>nul ^| findstr "InstallPath"') do (
    if exist "%%b\python.exe" (
        "%%b\python.exe" -c "import struct; exit(0 if struct.calcsize('P') * 8 == 32 else 1)" 2>nul
        if !errorLevel! equ 0 (
            set "PYTHON32=%%b\python.exe"
            goto :found_python
        )
    )
)

echo [ERROR] 32-bit Python not found!
echo.
echo Please install Python 3.13 (32-bit) from:
echo https://www.python.org/downloads/windows/
echo.
echo IMPORTANT: Python 3.14 is NOT recommended as many packages lack pre-built wheels.
echo Please use Python 3.13 for best compatibility.
echo.
echo During installation:
echo   - Choose "Install Now" (no need to add to PATH)
echo   - The script will find Python automatically
echo   - Recommended path: C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python313-32\
pause
exit /b 1

:found_python
echo [OK] Found 32-bit Python: %PYTHON32%
echo.

:: Verify it's 32-bit
%PYTHON32% -c "import struct; print(struct.calcsize('P') * 8)" | findstr "32" >nul
if errorLevel 1 (
    echo [ERROR] Python is not 32-bit!
    pause
    exit /b 1
)

echo [OK] Verified 32-bit architecture
echo.

:: Create virtual environment
echo [1/6] Creating virtual environment...
if exist "venv" (
    echo      Virtual environment already exists
) else (
    %PYTHON32% -m venv venv
    if errorLevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo      ✓ Virtual environment created
)
echo.

:: Activate virtual environment
call venv\Scripts\activate.bat
if errorLevel 1 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)

:: Upgrade pip
echo [2/6] Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1
echo      ✓ Pip upgraded
echo.

:: Install dependencies
echo [3/6] Installing dependencies (this may take a few minutes)...
echo      (If this fails, you may need Microsoft Visual C++ Build Tools)
echo      Download from: https://aka.ms/vs/17/release/vs_BuildTools.exe
echo.
pip install -r requirements.txt
if errorLevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo      ✓ Dependencies installed
echo.

:: Create configuration file
echo [4/6] Setting up configuration...

:: Get AppData path
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v LOCALAPPDATA 2^>nul ^| findstr "LOCALAPPDATA"') do set "LOCALAPPDATA=%%b"
if not defined LOCALAPPDATA set "LOCALAPPDATA=%USERPROFILE%\AppData\Local"

set "CONFIG_DIR=%LOCALAPPDATA%\BusyWhatsappBridge"
set "CONFIG_FILE=%CONFIG_DIR%\conf.json"

if exist "%CONFIG_FILE%" (
    echo      conf.json already exists at %CONFIG_FILE%
) else (
    if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"
    copy conf.json.example "%CONFIG_FILE%" >nul
    echo      ✓ Created conf.json at %CONFIG_FILE%
    echo      ⚠ IMPORTANT: Edit conf.json with your settings!
)
echo.

:: Logs directory (in AppData)
echo [5/6] Log directory setup...
echo      ✓ Logs will be stored in: %LOCALAPPDATA%\BusyWhatsappBridge\logs
echo.

:: Test database connectivity
echo [6/6] Testing database connection...
echo      Attempting to connect to database...

python -c "from app.database.connection import db; import sys; sys.exit(0 if db.test_connection() else 1)" 2>nul
if errorLevel 1 (
    echo      ⚠ Database connection failed (expected if not configured yet)
    echo        Please edit conf.json and set database.bds_file_path
) else (
    echo      ✓ Database connection successful
)
echo.

:: Final status
echo ================================================
echo Setup Complete!
echo ================================================
echo.
echo Next steps:
echo.
echo 1. Configure the application:
echo    notepad "%LOCALAPPDATA%\BusyWhatsappBridge\conf.json"
echo.
echo 2. Install as Windows Service:
echo    manage-service.bat
echo    or: python app\service_wrapper.py install
echo.
echo 3. Start the service:
echo    manage-service.bat start
echo    or: python app\service_wrapper.py start
echo.
echo 4. Test the API:
echo    run-tests.bat
echo.
echo 5. Configure Busy Software:
echo    URL: http://localhost:8000/api/v1/send-invoice
echo        ?phone={MobileNo}
echo        ^&msg={Message}
echo        ^&pdf_url={AttachmentURL}
echo.
echo Documentation:
echo    - README.md for full documentation
echo    - INSTALL.md for detailed installation guide
echo    - QUICKSTART.md for quick reference
echo.
pause
