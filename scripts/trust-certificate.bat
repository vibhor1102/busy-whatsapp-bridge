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

set "TEMP_BASE=%TEMP%\bwb-dev-cert-%RANDOM%%RANDOM%"
set "PEM_FILE=%TEMP_BASE%.pem"
set "CER_FILE=%TEMP_BASE%.cer"

(
    echo -----BEGIN CERTIFICATE-----
    echo MIIDDjCCAfagAwIBAgIQHanaC/+zBLFL7Rg/EIdVATANBgkqhkiG9w0BAQsFADAfMR0wGwYDVQQDDBR2aWJob3IxMTAyIERldmVsb3BlcjAeFw0yNjAzMDQwNTQ3MTdaFw0zMTAzMDQwNTU3MTdaMB8xHTAbBgNVBAMMFHZpYmhvcjExMDIgRGV2ZWxvcGVyMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA7sR/xvNtqMJBHmb6ODhawGwmw8pPVleA9uhJydWWEH/X4xeqxrglH2YIXfkJYgzPByMq2WepQ4NfQ5Qd7UkuacYs4/TZUHvUGiTNSsI9+HD3j8Y+wtmcNVMiZc89MyxdKUY11EOpF6U3x6P06fvxaeqvwejxQLwwMdK4nryP7227kpZZ9Nqfj+tU4hYXKusNMmglQydkbuVYvuxDJFGqBzHwXiFIqREvAB+CIHp4Sh4NlrLGPkVXBNnS8khn/b0EMTPxzbnyJ5ssCtMXPBJOWS/EixAV0vU8uZG17dG0CqF2iwQk/4m4Bcn3qw9bYEjLYWMygeienN4lHnVrs+83iQIDAQABo0YwRDAOBgNVHQ8BAf8EBAMCB4AwEwYDVR0lBAwwCgYIKwYBBQUHAwMwHQYDVR0OBBYEFJBWLIvsVFluIohMw1ZAu/w+2f4dMA0GCSqGSIb3DQEBCwUAA4IBAQAqcqkndaVoKjIMlrr2pBuFv2sKwZ1qSV5HGOsS9+GKarUzOLbPccAmdn91XheNxcAevW/Opj3Lmeel5CO1DliLVceWI8m/HG5+mVQcV2IKt3QMhBLbgncsQF9flUfAMLiFeWMhcV3dIBJD1tCKTiLtcZYcRmLRsjU0XTS+UXMK7IHYnLrcq3nMcG46GTFRJfacI8mjZtCyoBK+fClWlGCxmNveTvrJ+QTDdJymfDSfjvkbVR5I/mZZFGGLut+oCfZglasA30c3qMqTAWQc2vXEudlrZlqoEGg2Tz56+mL3ga+CmgvrtHQAjSKwOGIzc+HFRJGqiDZU5zTb3psATAsG
    echo -----END CERTIFICATE-----
) > "%PEM_FILE%"

certutil -f -decode "%PEM_FILE%" "%CER_FILE%" >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Failed to prepare certificate file from embedded key.
    if exist "%PEM_FILE%" del /f /q "%PEM_FILE%" >nul 2>nul
    if exist "%CER_FILE%" del /f /q "%CER_FILE%" >nul 2>nul
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

if exist "%PEM_FILE%" del /f /q "%PEM_FILE%" >nul 2>nul
if exist "%CER_FILE%" del /f /q "%CER_FILE%" >nul 2>nul

pause
endlocal
