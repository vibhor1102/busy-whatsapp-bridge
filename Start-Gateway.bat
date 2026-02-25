@ECHO OFF
REM Busy Whatsapp Bridge - Launcher (Bundled Python Edition)
REM Uses Python bundled with the application - no external Python needed!

SET "SCRIPT_DIR=%~dp0"
SET "VENV_PYTHON=%SCRIPT_DIR%venv\Scripts\python.exe"

IF EXIST "%VENV_PYTHON%" (
    REM Use bundled Python from virtual environment with tray icon by default
    "%VENV_PYTHON%" "%~dp0run.py" --tray %*
) ELSE (
    echo [ERROR] Virtual environment not found!
    echo.
    echo Please run setup-bundled.bat first to set up the application.
    echo.
    pause
    exit /b 1
)
