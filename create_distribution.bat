@echo off
echo ========================================
echo    AutoScreen Distribution Creator
echo ========================================
echo.

set VERSION=2.1
set DIST_DIR=AutoScreen_v%VERSION%_Distribution

echo [1/6] Creating distribution directory...
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
mkdir "%DIST_DIR%"

echo.
echo [2/6] Building application...
call build.bat
if errorlevel 1 (
    echo ERROR: Application build failed!
    pause
    exit /b 1
)

echo.
echo [3/6] Copying application files...
xcopy "dist\*" "%DIST_DIR%\AutoScreen\" /E /I /Y

echo.
echo [4/6] Copying documentation...
copy "README.md" "%DIST_DIR%\"
copy "CUSTOM_FOLDER_GUIDE.md" "%DIST_DIR%\"
copy "GOOGLE_DRIVE_SETUP.md" "%DIST_DIR%\"
copy "PACKAGING_GUIDE.md" "%DIST_DIR%\"

echo.
echo [5/6] Creating user guide...
(
echo # AutoScreen v%VERSION% - Hướng dẫn sử dụng
echo.
echo ## 🚀 Cài đặt nhanh
echo.
echo 1. **Chạy ứng dụng**: Double-click `AutoScreen\AutoScreen.exe`
echo 2. **Cài đặt ADB**: Tải và cài đặt Android Debug Bridge
echo 3. **Kết nối thiết bị**: Bật USB Debugging trên Android
echo 4. **Bắt đầu sử dụng**: Chọn kênh và chi nhánh, nhấn "Bắt đầu chụp"
echo.
echo ## 📋 Yêu cầu hệ thống
echo.
echo - Windows 10/11 ^(64-bit^)
echo - ADB ^(Android Debug Bridge^)
echo - Thiết bị Android với USB Debugging
echo.
echo ## 📁 Cấu trúc thư mục
echo.
echo ```
echo AutoScreen/
echo ├── AutoScreen.exe          # Ứng dụng chính
echo ├── _internal/              # Thư viện hệ thống
echo ├── shots/                  # Thư mục lưu ảnh
echo └── [các file config]       # File cấu hình
echo ```
echo.
echo ## 🔧 Troubleshooting
echo.
echo ### Lỗi "Không thấy thiết bị"
echo - Kiểm tra USB Debugging đã bật
echo - Chạy `adb devices` trong Command Prompt
echo.
echo ### Lỗi "Không thể chụp ảnh"
echo - Kiểm tra quyền Screen Capture
echo - Thử khởi động lại ADB
echo.
echo ## 📞 Hỗ trợ
echo.
echo Nếu gặp vấn đề, hãy đọc file README.md để biết thêm chi tiết.
echo.
echo ---
echo **Phiên bản**: %VERSION%
echo **Ngày tạo**: %DATE%
) > "%DIST_DIR%\USER_GUIDE.md"

echo.
echo [6/6] Creating batch file for easy launch...
(
echo @echo off
echo cd /d "%%~dp0"
echo start "" "AutoScreen\AutoScreen.exe"
) > "%DIST_DIR%\Start_AutoScreen.bat"

echo.
echo ========================================
echo    Distribution created successfully!
echo ========================================
echo.
echo Location: %DIST_DIR%\
echo.
echo Contents:
echo - AutoScreen\          # Ứng dụng chính
echo - USER_GUIDE.md        # Hướng dẫn sử dụng
echo - README.md            # Tài liệu đầy đủ
echo - Start_AutoScreen.bat # Script khởi chạy
echo.
echo You can now zip this folder and distribute it to users.
echo.
pause
