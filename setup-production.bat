@echo off
setlocal EnableDelayedExpansion

echo ================================================
echo Busy Whatsapp Bridge - Production Setup
echo ================================================
echo.

:: Check for Admin rights
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] This script requires Administrator privileges!
    echo Please right-click and select "Run as administrator"
    pause
    exit /b 1
)

:: Find 32-bit Python
set "PYTHON32="
set "PYTHON_PATHS=C:\Python39-32\python.exe C:\Python310-32\python.exe C:\Python311-32\python.exe C:\Python312-32\python.exe C:\Python313-32\python.exe"

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

echo [ERROR] 32-bit Python not found!
echo.
echo Please install Python 3.9-3.13 (32-bit) from:
echo https://www.python.org/downloads/windows/
echo.
echo Make sure to check "Add Python to PATH" during installation.
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
pip install -r requirements.txt
if errorLevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo      ✓ Dependencies installed
echo.

:: Create environment file
echo [4/6] Setting up configuration...
if exist ".env" (
    echo      .env file already exists
) else (
    copy .env.example .env >nul
    echo      ✓ Created .env from template
    echo      ⚠ IMPORTANT: Edit .env with your settings!
)
echo.

:: Create logs directory
echo [5/6] Creating log directory...
if not exist "logs" mkdir logs
echo      ✓ logs/ directory ready
echo.

:: Test database connectivity
echo [6/6] Testing database connection...
echo      Attempting to connect to database...

python -c "from app.database.connection import db; import sys; sys.exit(0 if db.test_connection() else 1)" 2>nul
if errorLevel 1 (
    echo      ⚠ Database connection failed (expected if not configured yet)
    echo        Please edit .env and set BDS_FILE_PATH
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
echo    notepad .env
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
