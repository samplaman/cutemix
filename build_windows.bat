@echo off
REM ====================================================================
REM  CuteMix - Windows Standalone Executable Builder
REM  Packages CuteMix into dist\CuteMix.exe using PyInstaller
REM ====================================================================

setlocal
cd /d "%~dp0"

echo ====================================================================
echo   Building CuteMix Windows Standalone Release (x64)
echo ====================================================================
echo.

set PYTHON_CMD=python
if exist ".venv\Scripts\python.exe" (
    set PYTHON_CMD=.venv\Scripts\python.exe
)

%PYTHON_CMD% --version >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python not found! Please run setup_windows.bat first.
    pause
    exit /b 1
)

echo [1/3] Ensuring PyInstaller is installed...
%PYTHON_CMD% -m pip install --upgrade pyinstaller

echo.
echo [2/3] Building standalone executable with PyInstaller...
%PYTHON_CMD% -m PyInstaller cutemix.spec --clean --noconfirm
if %ERRORLEVEL% neq 0 (
    echo [ERROR] PyInstaller build failed!
    pause
    exit /b 1
)

echo.
echo [3/3] Packaging Release ZIP archive...
if exist "dist\CuteMix.exe" (
    powershell -Command "Compress-Archive -Path 'dist\CuteMix.exe', 'README.md', 'snapshots' -DestinationPath 'dist\CuteMix-Windows-x64.zip' -Force"
    echo.
    echo ====================================================================
    echo   BUILD SUCCESSFUL!
    echo   Standalone executable created at: dist\CuteMix.exe
    echo   Release ZIP created at:           dist\CuteMix-Windows-x64.zip
    echo ====================================================================
) else (
    echo [ERROR] dist\CuteMix.exe was not found.
)

echo.
pause
endlocal
