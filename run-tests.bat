@echo off
echo ================================================
echo Busy Whatsapp Bridge - Test Suite
echo ================================================
echo.

REM Check for conf.json in AppData
set "CONFIG_FILE=%LOCALAPPDATA%\BusyWhatsappBridge\conf.json"
if not exist "%CONFIG_FILE%" (
    echo [WARNING] conf.json not found at %CONFIG_FILE%!
    echo Please configure your environment first.
    pause
    exit /b 1
)

echo Running API tests...
echo.

REM Find 32-bit Python
set "PYTHON32="

REM Check common installation paths
if exist "C:\Python39-32\python.exe" set "PYTHON32=C:\Python39-32\python.exe"
if exist "C:\Python310-32\python.exe" set "PYTHON32=C:\Python310-32\python.exe"
if exist "C:\Python311-32\python.exe" set "PYTHON32=C:\Python311-32\python.exe"
if exist "C:\Python312-32\python.exe" set "PYTHON32=C:\Python312-32\python.exe"
if exist "C:\Python313-32\python.exe" set "PYTHON32=C:\Python313-32\python.exe"

REM Check user-specific installations in AppData
if exist "%LOCALAPPDATA%\Programs\Python\Python39-32\python.exe" set "PYTHON32=%LOCALAPPDATA%\Programs\Python\Python39-32\python.exe"
if exist "%LOCALAPPDATA%\Programs\Python\Python310-32\python.exe" set "PYTHON32=%LOCALAPPDATA%\Programs\Python\Python310-32\python.exe"
if exist "%LOCALAPPDATA%\Programs\Python\Python311-32\python.exe" set "PYTHON32=%LOCALAPPDATA%\Programs\Python\Python311-32\python.exe"
if exist "%LOCALAPPDATA%\Programs\Python\Python312-32\python.exe" set "PYTHON32=%LOCALAPPDATA%\Programs\Python\Python312-32\python.exe"
if exist "%LOCALAPPDATA%\Programs\Python\Python313-32\python.exe" set "PYTHON32=%LOCALAPPDATA%\Programs\Python\Python313-32\python.exe"
if exist "%LOCALAPPDATA%\Programs\Python\Python314-32\python.exe" set "PYTHON32=%LOCALAPPDATA%\Programs\Python\Python314-32\python.exe"

if defined PYTHON32 (
    echo Using 32-bit Python: %PYTHON32%
    %PYTHON32% tests\test_webhook.py --url http://localhost:8000
) else (
    echo [WARNING] 32-bit Python not found, using default python
    echo Searched in C:\Python39-32 through C:\Python314-32
    echo and %%LOCALAPPDATA%%\Programs\Python\Python39-32 through Python314-32
    echo.
    python tests\test_webhook.py --url http://localhost:8000
)

echo.
pause
