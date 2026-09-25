@echo off
REM ====================================================================
REM  CuteMix - MOTU PCIe-424 + 24i Mixer Console Launcher (Windows)
REM ====================================================================

setlocal
cd /d "%~dp0"

REM 1. Check for Python virtual environment in .venv
if exist ".venv\Scripts\python.exe" (
    echo [CuteMix] Launching with virtual environment .venv ...
    ".venv\Scripts\python.exe" app.py %*
    goto END
)

REM 2. Check for system Python
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [CuteMix] Launching with system Python ...
    python app.py %*
    goto END
)

echo [CuteMix ERROR] Python not found in PATH!
echo Please install Python 3.9+ from https://www.python.org/
echo Ensure "Add Python to PATH" is checked during installation.
pause

:END
endlocal
