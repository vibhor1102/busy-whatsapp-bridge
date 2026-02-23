@echo off
echo ================================================
echo Busy Whatsapp Bridge - Test Suite
echo ================================================
echo.

REM Check if .env file exists
if not exist .env (
    echo [WARNING] .env file not found!
    echo Please configure your environment first.
    pause
    exit /b 1
)

echo Running API tests...
echo.

REM Run with 32-bit Python if available
if exist "C:\Python39-32\python.exe" (
    C:\Python39-32\python.exe tests\test_webhook.py --url http://localhost:8000
) else if exist "C:\Python310-32\python.exe" (
    C:\Python310-32\python.exe tests\test_webhook.py --url http://localhost:8000
) else if exist "C:\Python311-32\python.exe" (
    C:\Python311-32\python.exe tests\test_webhook.py --url http://localhost:8000
) else (
    python tests\test_webhook.py --url http://localhost:8000
)

echo.
pause
