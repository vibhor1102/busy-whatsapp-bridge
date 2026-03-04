@echo off
setlocal
echo ============================================================
echo Trusted Developer Certificate Installer
echo ============================================================
echo.

:: Check for administrative privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] This script must be run as Administrator!
    echo.
    echo Please right-click this file and select "Run as Administrator".
    echo.
    pause
    exit /b 1
)

set "CER_FILE=%~dp0vibhor1102-dev.cer"

if not exist "%CER_FILE%" (
    echo [ERROR] Certificate file not found: %CER_FILE%
    echo Make sure you are running this from the distribution folder.
    pause
    exit /b 1
)

echo Installing certificate: %CER_FILE%
echo This will allow Windows to trust Busy Whatsapp Bridge.
echo.

:: Import certificate to Trusted Root Certification Authorities (Local Machine)
certutil -addstore -f "Root" "%CER_FILE%"

if %errorLevel% equ 0 (
    echo.
    echo SUCCESS: The certificate has been installed.
    echo You can now install and run Busy Whatsapp Bridge without Smart App Control blocks.
    echo.
) else (
    echo.
    echo [ERROR] Failed to install certificate. Error code: %errorLevel%
)

pause
endlocal
