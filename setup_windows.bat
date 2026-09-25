@echo off
REM ====================================================================
REM  CuteMix - Windows Automated Setup Script
REM  Installs virtual environment and required dependencies (PySide6)
REM ====================================================================

setlocal
cd /d "%~dp0"

echo ====================================================================
echo   Setting up CuteMix for Windows Desktop (MOTU PCIe-424 + 24i)
echo ====================================================================
echo.

where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please download and install Python 3.9+ from https://www.python.org/
    echo Make sure to check the box "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo [1/3] Creating virtual environment (.venv)...
python -m venv .venv
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)

echo [2/3] Upgrading pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip

echo [3/3] Installing dependencies (PySide6, zeroconf)...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [WARNING] requirements.txt install had issues. Attempting PySide6 direct install...
    ".venv\Scripts\python.exe" -m pip install PySide6
)

echo.
echo ====================================================================
echo   Setup completed successfully!
echo   Double-click 'run.bat' to launch CuteMix.
echo ====================================================================
echo.
pause
endlocal
