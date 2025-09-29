@echo off
echo ========================================
echo    AutoScreen Installer Builder
echo ========================================
echo.

REM Check if Inno Setup is installed
where iscc >nul 2>&1
if errorlevel 1 (
    echo ERROR: Inno Setup is not installed or not in PATH
    echo Please install Inno Setup from: https://jrsoftware.org/isinfo.php
    echo And add it to your PATH
    pause
    exit /b 1
)

echo [1/4] Checking Inno Setup installation...
iscc /?

echo.
echo [2/4] Building application first...
call build.bat
if errorlevel 1 (
    echo ERROR: Application build failed!
    pause
    exit /b 1
)

echo.
echo [3/4] Creating installer directory...
if not exist "installer" mkdir "installer"

echo.
echo [4/4] Building installer with Inno Setup...
iscc installer.iss

if errorlevel 1 (
    echo.
    echo ERROR: Installer build failed!
    echo Check the error messages above
    pause
    exit /b 1
)

echo.
echo ========================================
echo    Build completed successfully!
echo ========================================
echo.
echo Installer location: installer\AutoScreen_Setup_v2.1.exe
echo.
echo You can now distribute this installer to users.
echo.
pause
