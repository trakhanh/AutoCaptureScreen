@echo off
echo ========================================
echo    Google Drive Setup Helper
echo ========================================
echo.

echo This script will help you set up Google Drive integration.
echo.

REM Check if credentials.json already exists
if exist "credentials.json" (
    echo credentials.json already exists!
    echo.
    set /p choice="Do you want to replace it? (y/n): "
    if /i not "%choice%"=="y" (
        echo Setup cancelled.
        pause
        exit /b 0
    )
)

echo.
echo [1/3] Checking template file...
if not exist "credentials_template.json" (
    echo ERROR: credentials_template.json not found!
    echo Please make sure you're running this from the AutoScreen directory.
    pause
    exit /b 1
)

echo Template file found.

echo.
echo [2/3] Copying template...
copy "credentials_template.json" "credentials.json" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy template file!
    pause
    exit /b 1
)

echo Template copied to credentials.json

echo.
echo [3/3] Opening setup guide...
echo.
echo ========================================
echo    NEXT STEPS
echo ========================================
echo.
echo 1. Open GOOGLE_DRIVE_CREDENTIALS_SETUP.md for detailed instructions
echo 2. Go to Google Cloud Console: https://console.cloud.google.com/
echo 3. Create OAuth credentials and download the JSON file
echo 4. Replace the content of credentials.json with your downloaded file
echo 5. Run AutoScreen.exe and test Google Drive integration
echo.
echo Press any key to open the setup guide...
pause >nul

REM Try to open the markdown file
if exist "GOOGLE_DRIVE_CREDENTIALS_SETUP.md" (
    start "" "GOOGLE_DRIVE_CREDENTIALS_SETUP.md"
) else (
    echo Setup guide not found. Please read the documentation.
)

echo.
echo Setup helper completed!
echo Remember to replace credentials.json with your actual Google credentials.
pause
