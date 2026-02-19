@echo off
echo ================================================
echo Busy WhatsApp Gateway - Server Startup
echo ================================================
echo.

REM Check if .env file exists
if not exist .env (
    echo [WARNING] .env file not found!
    echo Creating from template...
    copy .env.example .env
    echo Please edit .env file with your configuration before running.
    pause
    exit /b 1
)

echo Starting server on http://localhost:8000
echo.
echo API Documentation: http://localhost:8000/docs
echo Health Check: http://localhost:8000/api/v1/health
echo.

REM Run with 32-bit Python if available
if exist "C:\Python39-32\python.exe" (
    echo Using 32-bit Python at C:\Python39-32\python.exe
    C:\Python39-32\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
) else if exist "C:\Python310-32\python.exe" (
    echo Using 32-bit Python at C:\Python310-32\python.exe
    C:\Python310-32\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
) else if exist "C:\Python311-32\python.exe" (
    echo Using 32-bit Python at C:\Python311-32\python.exe
    C:\Python311-32\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
) else (
    echo Using default Python (ensure it's 32-bit for ODBC compatibility)
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
)

pause
