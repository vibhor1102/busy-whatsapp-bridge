@echo off
echo ================================================
echo Busy Whatsapp Bridge - Service Manager
echo ================================================
echo.

set "PYTHON=C:\Python39-32\python.exe"

if not exist "%PYTHON%" (
    echo [ERROR] 32-bit Python not found at %PYTHON%
    echo Please install Python 3.9+ 32-bit or update this script path
    pause
    exit /b 1
)

if not exist ".env" (
    echo [ERROR] .env file not found!
    echo Please copy .env.example to .env and configure it
    pause
    exit /b 1
)

if "%~1"=="" goto :menu
set "COMMAND=%~1"
goto :execute

:menu
cls
echo.
echo ================================================
echo Service Management Menu
echo ================================================
echo.
echo [1] Install Service (Auto-start)
echo [2] Start Service
echo [3] Stop Service
echo [4] Restart Service
echo [5] Check Status
echo [6] Remove Service
echo [7] View Logs
echo [8] Test Database Connection
echo [9] Exit
echo.
set /p "CHOICE=Select option (1-9): "

if "%CHOICE%"=="1" set "COMMAND=install"
if "%CHOICE%"=="2" set "COMMAND=start"
if "%CHOICE%"=="3" set "COMMAND=stop"
if "%CHOICE%"=="4" set "COMMAND=restart"
if "%CHOICE%"=="5" set "COMMAND=status"
if "%CHOICE%"=="6" set "COMMAND=remove"
if "%CHOICE%"=="7" set "COMMAND=logs"
if "%CHOICE%"=="8" set "COMMAND=test-db"
if "%CHOICE%"=="9" exit /b 0

:execute
if "%COMMAND%"=="install" goto :install
if "%COMMAND%"=="start" goto :start
if "%COMMAND%"=="stop" goto :stop
if "%COMMAND%"=="restart" goto :restart
if "%COMMAND%"=="status" goto :status
if "%COMMAND%"=="remove" goto :remove
if "%COMMAND%"=="logs" goto :logs
if "%COMMAND%"=="test-db" goto :test-db
echo [ERROR] Unknown command: %COMMAND%
pause
goto :menu

:install
echo.
echo Installing service...
%PYTHON% app\service_wrapper.py install
echo.
echo Service installed. Starting now...
%PYTHON% app\service_wrapper.py start
echo.
echo [TIP] Service will auto-start on Windows boot
pause
goto :menu

:start
echo.
echo Starting service...
%PYTHON% app\service_wrapper.py start
echo.
echo API available at: http://localhost:8000
echo Documentation: http://localhost:8000/docs
pause
goto :menu

:stop
echo.
echo Stopping service...
%PYTHON% app\service_wrapper.py stop
echo.
epause
goto :menu

:restart
echo.
echo Restarting service...
%PYTHON% app\service_wrapper.py restart
echo.
echo API available at: http://localhost:8000
pause
goto :menu

:status
echo.
%PYTHON% app\service_wrapper.py status
echo.
pause
goto :menu

:remove
echo.
echo WARNING: This will remove the Windows service
echo.
set /p "CONFIRM=Are you sure? (yes/no): "
if /i not "%CONFIRM%"=="yes" goto :menu

echo.
echo Stopping service first...
%PYTHON% app\service_wrapper.py stop 2>nul
echo.
echo Removing service...
%PYTHON% app\service_wrapper.py remove
echo.
pause
goto :menu

:logs
echo.
if exist "logs\service.log" (
    echo Showing last 50 log lines...
    echo.
    powershell -Command "Get-Content logs\service.log -Tail 50"
) else (
    echo No log file found at logs\service.log
    echo.
    echo Checking Windows Event Log...
    powershell -Command "Get-WinEvent -FilterHashtable @{LogName='Application'; ID=0} -MaxEvents 20 | Where-Object {$_.Message -like '*BusyWhatsappBridge*'} | Format-Table TimeCreated, LevelDisplayName, Message -Wrap"
)
echo.
pause
goto :menu

:test-db
echo.
echo Testing database connection...
%PYTHON% -c "from app.database.connection import db; print('Connection successful!' if db.test_connection() else 'Connection failed!')"
echo.
pause
goto :menu
