@echo off
echo ========================================
echo    AutoScreen User Package Creator
echo ========================================
echo.

set VERSION=2.1
set PACKAGE_DIR=AutoScreen_v%VERSION%_UserPackage

echo [1/7] Creating user package directory...
if exist "%PACKAGE_DIR%" rmdir /s /q "%PACKAGE_DIR%"
mkdir "%PACKAGE_DIR%"

echo.
echo [2/7] Building application...
call build.bat
if errorlevel 1 (
    echo ERROR: Application build failed!
    pause
    exit /b 1
)

echo.
echo [3/7] Copying application files...
xcopy "dist\*" "%PACKAGE_DIR%\AutoScreen\" /E /I /Y

echo.
echo [4/7] Copying documentation...
copy "README.md" "%PACKAGE_DIR%\" >nul
copy "README_USER.md" "%PACKAGE_DIR%\" >nul
copy "CUSTOM_FOLDER_GUIDE.md" "%PACKAGE_DIR%\" >nul
copy "GOOGLE_DRIVE_SETUP.md" "%PACKAGE_DIR%\" >nul
copy "GOOGLE_DRIVE_CREDENTIALS_SETUP.md" "%PACKAGE_DIR%\" >nul

echo.
echo [5/7] Copying setup helpers...
copy "setup_google_drive.bat" "%PACKAGE_DIR%\" >nul
copy "credentials_template.json" "%PACKAGE_DIR%\" >nul

echo.
echo [6/7] Creating user guide...
(
echo # AutoScreen v%VERSION% - Hướng dẫn sử dụng cho người dùng
echo.
echo Đã copy README_USER.md. Vui lòng đọc file đó để xem hướng dẫn chi tiết.
) > "%PACKAGE_DIR%\USER_GUIDE.md"

echo.
echo [7/7] Creating quick start script...
(
echo @echo off
echo echo Starting AutoScreen...
echo cd /d "%%~dp0"
echo start "" "AutoScreen\AutoScreen.exe"
) > "%PACKAGE_DIR%\Start_AutoScreen.bat"

echo.
echo ========================================
echo    User Package created successfully!
echo ========================================
echo.
echo Package location: %PACKAGE_DIR%\
echo.
echo Contents for users:
echo - AutoScreen\                    # Ứng dụng chính
echo - README_USER.md                # Hướng dẫn nhanh cho end user
echo - USER_GUIDE.md                 # Gợi ý nhanh
echo - setup_google_drive.bat        # Script thiết lập Google Drive
echo - credentials_template.json     # Template cho credentials
echo - [các file hướng dẫn khác]     # Tài liệu chi tiết
echo.
echo You can now zip this folder and distribute it to users.
echo.
pause
