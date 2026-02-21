@echo off
echo Starting Baileys WhatsApp Server
echo =================================
echo.

REM Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js not found in PATH
    echo Please install Node.js 18+ from https://nodejs.org/
    pause
    exit /b 1
)

REM Check if node_modules exists
if not exist baileys-server\node_modules (
    echo Installing Baileys dependencies...
    echo.
    cd baileys-server
    call npm install
    cd ..
    echo.
    echo Dependencies installed!
    echo.
)

echo Starting Baileys server on http://localhost:3001
echo QR Code page: http://localhost:3001/qr/page
echo.
echo Press Ctrl+C to stop
echo.

cd baileys-server
node server.js
