@echo off
echo ================================================
echo Configure Windows Firewall
echo ================================================
echo.

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Administrator privileges required!
    echo Please right-click and select "Run as administrator"
    pause
    exit /b 1
)

echo [1/2] Adding HTTP rule (port 8000)...
netsh advfirewall firewall add rule name="Busy Whatsapp Bridge HTTP" dir=in action=allow protocol=TCP localport=8000
if errorLevel 1 (
    echo      [WARNING] Rule might already exist or error occurred
) else (
    echo      [OK] HTTP rule added
)
echo.

echo [2/2] Verifying rules...
netsh advfirewall firewall show rule name="Busy Whatsapp Bridge HTTP"
echo.

echo ================================================
echo Firewall Configuration Complete
echo ================================================
echo.
echo The following port is now open:
echo   - Port 8000 (HTTP) - API and Dashboard access
echo.
echo Security Recommendations:
echo   - Restrict access to specific IPs if possible
echo   - Use HTTPS in production
echo   - Consider using a reverse proxy (IIS/nginx)
echo.
pause
