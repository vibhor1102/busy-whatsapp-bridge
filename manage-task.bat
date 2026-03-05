@ECHO OFF
SETLOCAL EnableDelayedExpansion

REM Busy Whatsapp Bridge - Task Scheduler Manager
REM Manages auto-start on login using Windows Task Scheduler

echo ================================================
echo Busy Whatsapp Bridge - Auto-Start Manager
echo ================================================
echo.

REM Save script directory
SET "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Find bundled Python
SET "PYTHON_EXE=%SCRIPT_DIR%venv\Scripts\python.exe"

IF NOT EXIST "%PYTHON_EXE%" (
    echo [ERROR] Virtual environment not found!
    echo Please run setup-bundled.bat first.
    pause
    exit /b 1
)

REM Non-interactive mode (for installer/scripts):
REM   manage-task.bat install|remove|status|start|stop
IF /I "%~1"=="install" GOTO cli_install
IF /I "%~1"=="remove" GOTO cli_remove
IF /I "%~1"=="status" GOTO cli_status
IF /I "%~1"=="start" GOTO cli_start
IF /I "%~1"=="stop" GOTO cli_stop

:menu
cls
echo ================================================
echo Busy Whatsapp Bridge - Auto-Start Manager
echo ================================================
echo.
echo This manages automatic startup on Windows login.
echo.
echo [1] Enable Auto-Start (Tray Mode)
echo     - Starts automatically when you log in
echo     - Shows system tray icon
echo.
echo [2] Disable Auto-Start
echo     - Stops automatic startup
echo     - Tray icon won't appear on login
echo.
echo [3] Check Status
echo     - Shows if auto-start is enabled
echo     - Shows current task state
echo.
echo [4] Start Now (Tray Mode)
echo     - Starts the application immediately
echo     - Tray icon appears right away
echo.
echo [5] Stop
echo     - Stops the running application
echo.
echo [6] Exit
echo.
echo ================================================
SET /P CHOICE="Select option [1-6]: "

IF "%CHOICE%"=="1" GOTO install
IF "%CHOICE%"=="2" GOTO remove
IF "%CHOICE%"=="3" GOTO status
IF "%CHOICE%"=="4" GOTO start_now
IF "%CHOICE%"=="5" GOTO stop
IF "%CHOICE%"=="6" GOTO end

echo Invalid option. Please try again.
timeout /t 2 >nul
goto menu

:install
echo.
echo Installing auto-start task...
echo This will enable the application to start automatically on login.
echo.
"%PYTHON_EXE%" -m app.task_scheduler install
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo [TIP] If installation failed, make sure you have admin rights.
    echo Right-click this batch file and select "Run as administrator".
)
echo.
pause
goto menu

:remove
echo.
echo Removing auto-start task...
echo This will disable automatic startup on login.
echo.
"%PYTHON_EXE%" -m app.task_scheduler remove
echo.
pause
goto menu

:status
echo.
"%PYTHON_EXE%" -m app.task_scheduler status
echo.
pause
goto menu

:start_now
echo.
echo Starting Busy Whatsapp Bridge (Tray Mode)...
echo.
"%PYTHON_EXE%" -m app.task_scheduler start
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo Trying alternative start method...
    echo.
    start "Busy Whatsapp Bridge" "%~dp0Start-Gateway.py"
    echo Started! The tray icon should appear in a few seconds.
)
echo.
pause
goto menu

:stop
echo.
echo Stopping Busy Whatsapp Bridge...
echo.
"%PYTHON_EXE%" -m app.task_scheduler stop
echo.
pause
goto menu

:end
echo.
echo Goodbye!
echo.
ENDLOCAL
exit /b 0

:cli_install
"%PYTHON_EXE%" -m app.task_scheduler install
SET "EXIT_CODE=%ERRORLEVEL%"
ENDLOCAL
exit /b %EXIT_CODE%

:cli_remove
"%PYTHON_EXE%" -m app.task_scheduler remove
SET "EXIT_CODE=%ERRORLEVEL%"
ENDLOCAL
exit /b %EXIT_CODE%

:cli_status
"%PYTHON_EXE%" -m app.task_scheduler status
SET "EXIT_CODE=%ERRORLEVEL%"
ENDLOCAL
exit /b %EXIT_CODE%

:cli_start
"%PYTHON_EXE%" -m app.task_scheduler start
SET "EXIT_CODE=%ERRORLEVEL%"
ENDLOCAL
exit /b %EXIT_CODE%

:cli_stop
"%PYTHON_EXE%" -m app.task_scheduler stop
SET "EXIT_CODE=%ERRORLEVEL%"
ENDLOCAL
exit /b %EXIT_CODE%
