# 🔐 Hướng dẫn thiết lập Google Drive Credentials

## 📋 Tổng quan

Để sử dụng tính năng upload lên Google Drive, bạn cần tạo file `credentials.json` riêng cho tài khoản Google của mình.

## 🚀 Cách thiết lập

### Bước 1: Tạo Google Cloud Project

1. Truy cập [Google Cloud Console](https://console.cloud.google.com/)
2. Đăng nhập bằng tài khoản Google của bạn
3. Tạo project mới hoặc chọn project có sẵn

### Bước 2: Bật Google Drive API

1. Vào **APIs & Services** → **Library**
2. Tìm kiếm "Google Drive API"
3. Click **Enable**

### Bước 3: Tạo Credentials

1. Vào **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Chọn **Desktop application**
4. Đặt tên: "AutoScreen"
5. Click **Create**

### Bước 4: Tải file credentials

1. Click vào icon download (⬇️) bên cạnh OAuth client ID vừa tạo
2. File sẽ được tải về với tên như `client_secret_xxx.json`
3. Đổi tên file thành `credentials.json`
4. Copy file vào thư mục AutoScreen

### Bước 5: Cấu trúc thư mục

```
AutoScreen/
├── AutoScreen.exe
├── credentials.json          ← File này bạn cần tạo
├── token.json               ← Sẽ được tạo tự động
├── drive_config.json        ← Cấu hình upload
└── ...
```

## 🔧 Cách sử dụng

### Lần đầu sử dụng:
1. Chạy AutoScreen.exe
2. Vào **Settings** → **Google Drive**
3. Click **"Thiết lập Google Drive"**
4. Ứng dụng sẽ mở trình duyệt để xác thực
5. Đăng nhập và cấp quyền
6. Quay lại ứng dụng, Google Drive đã sẵn sàng!

### Các lần sau:
- Ứng dụng sẽ tự động sử dụng `token.json` đã lưu
- Không cần thiết lập lại

## ⚠️ Lưu ý quan trọng

### Bảo mật:
- **KHÔNG** chia sẻ file `credentials.json` với ai khác
- **KHÔNG** commit file này lên Git
- File này chứa thông tin nhạy cảm của tài khoản Google

### Backup:
- Lưu trữ `credentials.json` ở nơi an toàn
- Nếu mất file, cần tạo lại từ Google Cloud Console

### Troubleshooting:
- Nếu lỗi "Invalid credentials": Kiểm tra file `credentials.json` có đúng format không
- Nếu lỗi "Access denied": Kiểm tra Google Drive API đã được enable chưa
- Nếu lỗi "Token expired": Xóa `token.json` và thiết lập lại

## 🎯 Template file

Nếu bạn muốn tạo file `credentials.json` thủ công, sử dụng template này:

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

## 📞 Hỗ trợ

Nếu gặp khó khăn trong quá trình thiết lập:
1. Kiểm tra file `credentials.json` có đúng format JSON không
2. Đảm bảo Google Drive API đã được enable
3. Thử xóa `token.json` và thiết lập lại
4. Liên hệ team phát triển nếu cần hỗ trợ

---

**Lưu ý**: Tính năng Google Drive là tùy chọn. Ứng dụng vẫn hoạt động bình thường nếu không thiết lập credentials.
