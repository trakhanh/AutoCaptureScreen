# 📸 AutoScreen – Hướng dẫn sử dụng cho Người Dùng Cuối (End User)

Bạn có thể dùng AutoScreen theo 2 cách:  
(1) cắm máy Android thật qua USB, hoặc  
(2) dùng máy ảo/emulator.

---

## ✅ Yêu cầu chung
- Windows 10/11 64-bit  
- Python 3.9+  
- ADB (Android Debug Bridge)  
  - Tải "platform-tools" từ Google, giải nén và thêm vào PATH  
  - Hoặc đặt `adb.exe` cùng thư mục với ứng dụng  

---

## 🐍 Cách chạy AutoScreen

### Bước 1: Cài đặt môi trường
1. Mở **Command Prompt / PowerShell** tại thư mục chứa mã nguồn  
2. Cài thư viện cần thiết:
```bash
pip install -r requirements.txt
````

### Bước 2: Chạy giao diện

```bash
python AutoScreenGUI.py
```

Ứng dụng sẽ mở giao diện AutoScreen.

---

## 1) Dùng MÁY THẬT (USB)

### Bước 1: Chuẩn bị điện thoại

* Mở **Developer Options** → bật **USB Debugging**
* Kết nối điện thoại với PC bằng cáp **data** tốt
* Nếu điện thoại hỏi quyền *Allow USB debugging* → chọn **Allow**

### Bước 2: Kiểm tra ADB

```bat
adb devices
```

* Thấy 1 dòng có trạng thái `device` là OK
* Nếu `unauthorized`: rút ra, cắm lại, bấm **Allow** trên điện thoại

### Bước 3: Chạy AutoScreen

* Chạy `python AutoScreenGUI.py`
* Chọn kênh/chi nhánh → nhấn **Bắt đầu chụp**
* Ảnh lưu trong `shots/<Kênh>/<Chi nhánh>/`

---

## 2) Dùng MÁY ẢO (EMULATOR)

Hỗ trợ Android Emulator (AVD), BlueStacks, LDPlayer, Nox,… miễn là dùng được ADB.

### Cách A – Android Emulator (AVD – Android Studio)

1. Mở AVD → chạy 1 thiết bị ảo
2. Kiểm tra ADB:

```bat
adb devices
```

* Thấy `emulator-5554    device` là OK

3. Chạy `python AutoScreenGUI.py`

### Cách B – BlueStacks / LDPlayer / Nox

* Bật **ADB** trong cài đặt emulator (nếu có)
* Kết nối ADB đến cổng của emulator (ví dụ BlueStacks 5555):

```bat
adb connect 127.0.0.1:5555
adb devices
```

* Thấy thiết bị `127.0.0.1:5555    device` là OK
* Chạy `python AutoScreenGUI.py`

Lưu ý cho emulator:

* Mỗi emulator có cổng ADB khác nhau (thường 5555 / 62001 / 21503 …)
* Nếu `offline`: chạy `adb kill-server && adb start-server`, rồi `adb connect` lại

---

## 📂 Ảnh lưu ở đâu?

```
shots/<Kênh>/<Chi nhánh>/01_*.png, 02_*.png, ...
```

Bật **Tự động tiếp số ảnh** để không ghi đè ảnh cũ.

---

## 🔧 (Tuỳ chọn) Upload Google Drive

Xem phần [🔐 Hướng dẫn thiết lập Google Drive Credentials](#-hướng-dẫn-thiết-lập-google-drive-credentials) bên dưới.

---

## 🧰 Sự cố thường gặp

* Không thấy thiết bị: kiểm tra cáp/PATH, `adb devices`, driver USB
* `unauthorized`: mở khoá màn hình, bấm Allow trên điện thoại
* Emulator không hiện: dùng `adb connect HOST:PORT`, xem cài đặt ADB của emulator
* Không chụp/ảnh trùng: tăng Delay, chỉnh lại vuốt (padding), tắt animation
* Google Drive lỗi: kiểm tra `credentials.json`, xóa `token.json` và xác thực lại

---

## 🚀 Khởi chạy nhanh

```bash
pip install -r requirements.txt
python AutoScreenGUI.py
```

* Kết nối thiết bị (máy thật hoặc emulator)
* Chọn kênh/chi nhánh → Bắt đầu chụp

---

# 🔐 Hướng dẫn thiết lập Google Drive Credentials

## 📋 Tổng quan

Để sử dụng tính năng upload lên Google Drive, bạn cần tạo file `credentials.json` riêng cho tài khoản Google của mình.

---

## 🚀 Cách thiết lập

### Bước 1: Tạo Google Cloud Project

1. Truy cập [Google Cloud Console](https://console.cloud.google.com/)
2. Đăng nhập bằng tài khoản Google
3. Tạo project mới hoặc chọn project có sẵn

### Bước 2: Bật Google Drive API

1. Vào **APIs & Services** → **Library**
2. Tìm "Google Drive API"
3. Click **Enable**

### Bước 3: Tạo Credentials

1. Vào **APIs & Services** → **Credentials**
2. Chọn **Create Credentials** → **OAuth client ID**
3. Chọn **Desktop application**
4. Đặt tên: "AutoScreen"
5. Click **Create**

### Bước 4: Tải file credentials

1. Click icon download (⬇️) bên cạnh OAuth client ID vừa tạo
2. File tải về dạng `client_secret_xxx.json`
3. Đổi tên thành `credentials.json`
4. Copy file vào thư mục AutoScreen

### Bước 5: Cấu trúc thư mục

```
AutoScreen/
├── AutoScreenGUI.py
├── requirements.txt
├── credentials.json     ← File bạn cần tạo
├── token.json           ← Sinh tự động sau lần xác thực đầu tiên
├── drive_config.json    ← Cấu hình upload
└── ...
```

---

## 🔧 Cách sử dụng

### Lần đầu sử dụng:

1. Chạy `python AutoScreenGUI.py`
2. Vào **Settings** → **Google Drive**
3. Click **"Thiết lập Google Drive"**
4. Ứng dụng mở trình duyệt để xác thực
5. Đăng nhập và cấp quyền
6. Quay lại ứng dụng, Google Drive đã sẵn sàng!

### Các lần sau:

* Ứng dụng tự động dùng `token.json` đã lưu
* Không cần thiết lập lại

---

## ⚠️ Lưu ý quan trọng

### Bảo mật

* **KHÔNG** chia sẻ file `credentials.json`
* **KHÔNG** commit file này lên Git
* File chứa thông tin nhạy cảm của tài khoản Google

### Backup

* Lưu trữ `credentials.json` ở nơi an toàn
* Nếu mất file, cần tạo lại từ Google Cloud Console

### Troubleshooting

* Lỗi "Invalid credentials": kiểm tra lại `credentials.json`
* Lỗi "Access denied": chắc chắn Google Drive API đã được bật
* Lỗi "Token expired": xóa `token.json` và thiết lập lại

---

## 🎯 Template file credentials.json

```json
{
  "installed": {
    "client_id": "YOUR_CLIENT_ID_HERE",
    "project_id": "YOUR_PROJECT_ID_HERE", 
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "YOUR_CLIENT_SECRET_HERE",
    "redirect_uris": ["http://localhost"]
  }
}
```

---

## 📞 Hỗ trợ

Nếu gặp khó khăn trong quá trình thiết lập:

1. Kiểm tra `credentials.json` có đúng format JSON không
2. Đảm bảo Google Drive API đã được enable
3. Thử xóa `token.json` và thiết lập lại
4. Liên hệ team phát triển nếu cần

---

**Lưu ý**: Tính năng Google Drive là **tùy chọn**. Ứng dụng vẫn hoạt động bình thường nếu không thiết lập credentials.

```
