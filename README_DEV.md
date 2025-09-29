# AutoScreen – Hướng dẫn cho Developer (Chạy & Sử dụng)

Tài liệu này dành cho developer muốn chạy và kiểm thử AutoScreen trực tiếp từ source.

## 🧱 Môi trường
- Windows 10/11 (khuyến nghị)
- Python 3.7+
- pip
- ADB (Android Debug Bridge) đã cài và trong PATH

## ⚙️ Cài đặt dependencies
```bash
pip install -r requirements.txt
```

## ▶️ Chạy ứng dụng
### GUI (khuyến nghị)
```bash
python AutoscreenGUI.py
```
- Kết nối thiết bị Android (USB Debugging) hoặc emulator
- Chọn kênh/chi nhánh → Bắt đầu chụp
- Ảnh sẽ lưu vào `shots/<Kênh>/<Chi nhánh>/`

### CLI (nâng cao)
```bash
# Ví dụ nhanh
python Autoscreen.py --channel shopeefood --branch BC

# Liệt kê kênh có sẵn
python Autoscreen.py --list-channels

# Quản lý kênh/chi nhánh (menu dòng lệnh)
python Autoscreen.py --manage

# Ví dụ tham số nâng cao
python Autoscreen.py \
  --channel grabfood --branch LBB \
  --shots 50 --delay 2.0 \
  --padding-top 0.15 --padding-bottom 0.85
```

## 📱 Kết nối thiết bị
### Máy thật (USB)
- Bật Developer Options → USB Debugging
- Cắm cáp USB, chạy:
```bash
adb devices
```
- Thấy trạng thái `device` là OK. Nếu `unauthorized` → bấm Allow trên điện thoại

### Máy ảo (emulator)
- Android Emulator (AVD): chạy AVD → `adb devices` thấy `emulator-5554`
- BlueStacks/LDPlayer/Nox: bật ADB → kết nối theo cổng
```bash
adb connect 127.0.0.1:5555
adb devices
```

## 🔐 Google Drive (tùy chọn cho dev)
- Không commit `credentials.json`/`token.json`
- Tạo theo `GOOGLE_DRIVE_CREDENTIALS_SETUP.md`
- Đặt `credentials.json` cạnh source hoặc thư mục chạy
- Xác thực lần đầu, `token.json` sẽ được tạo

## 🧩 Các file cấu hình chính
- `channels_config.json`: Kênh/chi nhánh mặc định
- `gui_settings.json`: Lưu cài đặt GUI gần nhất
- `drive_config.json`: Cấu hình upload Google Drive

## 🧪 Mẹo kiểm thử
- Bật “Tự động tiếp số ảnh” để tránh ghi đè
- Tăng `--delay` nếu app tải chậm
- Điều chỉnh `--padding-top/bottom` cho vùng lướt phù hợp từng app
- Tắt animation trên thiết bị để chụp nhanh hơn

## 🧰 Troubleshooting nhanh
- `adb devices` không thấy thiết bị: kiểm tra driver/cáp, PATH
- Trạng thái `offline/unauthorized`: `adb kill-server && adb start-server`, cắm lại
- Không chụp được: tăng delay, xem log trong terminal, đảm bảo quyền màn hình
- Google Drive lỗi: kiểm tra `credentials.json`, xóa `token.json` rồi xác thực lại

## 📞 Hỗ trợ
- Đọc `README_USER.md` cho hướng dẫn end user
- Mô tả rõ vấn đề, kèm log/ảnh chụp màn hình khi cần hỗ trợ
