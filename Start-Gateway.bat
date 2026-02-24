@echo off
REM Busy Whatsapp Bridge - Launcher
REM This script runs the Python gateway directly for best visibility

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
    %PYTHON32% "%~dp0run.py" %*
) else (
    echo [WARNING] 32-bit Python not found, using default python
    echo Searched in C:
    echo   - C:\Python39-32 through C:\Python314-32
    echo   - %%LOCALAPPDATA%%\Programs\Python\Python39-32 through Python314-32
    echo.
    python "%~dp0run.py" %*
)
