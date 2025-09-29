@echo off
echo ========================================
echo    AutoScreen Build Script
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.7+ and try again
    pause
    exit /b 1
)

echo [1/5] Checking Python installation...
python --version

echo.
echo [2/5] Installing/updating dependencies...
pip install -r requirements.txt
pip install pyinstaller

echo.
echo [3/5] Cleaning previous builds...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "__pycache__" rmdir /s /q "__pycache__"

echo.
echo [4/5] Building executable with PyInstaller...
pyinstaller autoscreen.spec

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    echo Check the error messages above
    pause
    exit /b 1
)

echo.
echo [5/5] Build completed successfully!
echo.
echo Executable location: dist\AutoScreen.exe
echo.
echo You can now distribute the entire 'dist' folder to users.
echo.
pause
