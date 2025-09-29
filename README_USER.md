# AutoScreen – Hướng dẫn sử dụng cho Người Dùng Cuối (End User)

Bạn có thể dùng AutoScreen theo 2 cách: (1) cắm máy Android thật qua USB, hoặc (2) dùng máy ảo/emulator.

## ✅ Yêu cầu chung
- Windows 10/11 64-bit
- ADB (Android Debug Bridge)
  - Tải "platform-tools" từ Google, giải nén và thêm vào PATH
  - Hoặc đặt `adb.exe` cùng thư mục với ứng dụng

---

## 1) Dùng MÁY THẬT (USB)

### Bước 1: Chuẩn bị điện thoại
- Mở Developer Options → bật **USB Debugging**
- Kết nối điện thoại với PC bằng cáp tốt (data)
- Nếu điện thoại hỏi quyền "Allow USB debugging" → chọn Allow

### Bước 2: Kiểm tra ADB
```bat
adb devices
```
- Thấy 1 dòng có trạng thái `device` là OK
- Nếu `unauthorized`: rút ra, cắm lại, bấm Allow trên điện thoại

### Bước 3: Chạy AutoScreen
- Mở thư mục ứng dụng → chạy `AutoScreen\AutoScreen.exe`
- Chọn kênh/chi nhánh → nhấn "Bắt đầu chụp"
- Ảnh lưu trong `shots/<Kênh>/<Chi nhánh>/`

### Mẹo
- Nếu lướt nhanh → tăng Delay
- Nếu app nặng → bật tối ưu thiết bị (tắt animation)

---

## 2) Dùng MÁY ẢO (EMULATOR)
Hỗ trợ Android Emulator (AVD), BlueStacks, LDPlayer, Nox,… miễn là dùng được ADB.

### Cách A – Android Emulator (AVD – Android Studio)
1. Mở AVD → chạy 1 thiết bị ảo
2. Kiểm tra ADB:
```bat
adb devices
```
- Thấy `emulator-5554    device` là OK
3. Chạy `AutoScreen.exe` → thao tác như máy thật

### Cách B – BlueStacks / LDPlayer / Nox
- Bật chế độ ADB trong cài đặt emulator (nếu có)
- Kết nối ADB đến cổng của emulator (ví dụ BlueStacks 5555):
```bat
adb connect 127.0.0.1:5555
adb devices
```
- Thấy thiết bị `127.0.0.1:5555    device` là OK
- Chạy `AutoScreen.exe`

Lưu ý cho emulator:
- Mỗi emulator có cổng ADB khác nhau (thường 5555 / 62001 / 21503 …)
- Nếu `offline`: chạy `adb kill-server && adb start-server`, rồi `adb connect` lại

---

## 📂 Ảnh lưu ở đâu?
```
shots/<Kênh>/<Chi nhánh>/01_*.png, 02_*.png, ...
```
Bật “Tự động tiếp số ảnh” để không ghi đè ảnh cũ.

---

## 🔧 (Tuỳ chọn) Upload Google Drive
1. Chạy `setup_google_drive.bat`
2. Theo hướng dẫn trong `GOOGLE_DRIVE_CREDENTIALS_SETUP.md`
3. Tạo `credentials.json` riêng của bạn (không chia sẻ cho ai)
4. Xác thực lần đầu trong ứng dụng (tự sinh `token.json`)

---

## 🧰 Sự cố thường gặp
- Không thấy thiết bị: kiểm tra cáp/PATH, `adb devices`, driver USB
- `unauthorized`: mở khoá màn hình, bấm Allow trên điện thoại
- Emulator không hiện: dùng `adb connect HOST:PORT`, xem cài đặt ADB của emulator
- Không chụp/ảnh trùng: tăng Delay, điều chỉnh vùng vuốt (padding), tắt animation
- Google Drive lỗi: kiểm tra `credentials.json`, xóa `token.json` và xác thực lại

---

## 🚀 Khởi chạy nhanh
- Chạy `AutoScreen\AutoScreen.exe` hoặc `Start_AutoScreen.bat`
- Kết nối thiết bị (máy thật hoặc emulator)
- Chọn kênh/chi nhánh → Bắt đầu chụp

---

## 🧭 Tính năng chi tiết (theo giao diện)

### Khu vực chọn dữ liệu
- **Kênh**: Chọn ứng dụng đích (vd: ShopeeFood, GrabFood, …). Danh sách được lấy từ `channels_config.json`.
- **Chi nhánh**: Cửa hàng/điểm bán thuộc kênh. Có thể thêm/xoá/sửa trong mục Quản lý kênh.
- **Thư mục lưu**: Đường dẫn ảnh đầu ra. Mặc định `shots`. Nhấn "📁 Chọn" để thay đổi.

### ⚙️ Cài đặt nâng cao
- **Số ảnh**: Số ảnh tối đa sẽ chụp trong một phiên.
- **Delay (s)**: Thời gian chờ giữa hai lần chụp. Tăng nếu app tải chậm để tránh chụp mờ/trùng.
- **Vuốt (ms)**: Thời lượng thao tác vuốt để kéo nội dung. Số lớn → vuốt lâu hơn (khoảng di chuyển xa hơn).
- **Trên (padding-top)**: Vị trí bắt đầu vuốt theo tỉ lệ màn hình (0.00–1.00). Ví dụ 0.22 = bắt đầu từ 22% chiều cao.
- **Dưới (padding-bottom)**: Vị trí kết thúc vuốt theo tỉ lệ màn hình. Ví dụ 0.18 = kết thúc ở 82% (1 - 0.18).
- **Thử lại**: Khi phát hiện ảnh trùng (có thể là hết nội dung), app sẽ vuốt thêm tối đa N lần để xác nhận.
- **Tối ưu thiết bị**: Tự động tắt animation trên thiết bị (qua ADB) nhằm tăng ổn định/tốc độ thao tác.
- **Tiếp số ảnh**: Nếu thư mục đã có ảnh `01_*.png, 02_*.png, …` thì sẽ tự tiếp tục từ số lớn nhất, không ghi đè.

Mẹo thiết lập nhanh:
- App nhẹ, nội dung ngắn: Delay ~1.0–1.2s, Vuốt 450–600ms, Trên 0.20–0.25, Dưới 0.15–0.20
- App nặng, load chậm: Delay 1.5–2.0s, Vuốt 600–800ms, Thử lại 3–4

### 💾 Preset
- **💾 Lưu preset**: Lưu toàn bộ thiết lập hiện tại (kênh/chi nhánh/parameters) thành file `.json` để tái sử dụng.
- **📂 Tải preset**: Chọn file preset `.json` đã lưu để áp dụng nhanh.
- **🔄 Reset**: Trả về thông số mặc định (không xoá preset đã lưu).

### 🎛️ Nút điều khiển
- **▶ Bắt đầu chụp**: Bắt đầu phiên chụp. Nút **⏹ Dừng** sẽ được bật trong khi chạy.
- **⏹ Dừng**: Kết thúc phiên chụp ngay lập tức (an toàn cho thiết bị).
- **⚙ Quản lý kênh**: Mở giao diện quản lý:
  - Thêm kênh mới (key + tên hiển thị)
  - Thêm/xoá/sửa chi nhánh
  - Copy toàn bộ chi nhánh từ kênh A sang kênh B
  - Dùng chuột phải (context menu) hoặc double-click để thao tác nhanh
- **🔧 Sắp xếp file**: Tự động gom/sắp xếp ảnh về đúng cấu trúc chuẩn `shots/<Kênh>/<Chi nhánh>/...` và chuẩn hoá tên nếu cần.
- **🔄 Làm mới**: Nạp lại danh sách kênh/chi nhánh từ `channels_config.json` (hữu ích sau khi vừa chỉnh sửa).
- **📁 Mở thư mục**: Mở thư mục kết quả hiện tại. Chỉ khả dụng khi đã có ảnh đầu tiên.

### 📊 Tiến trình & thống kê
- **Trạng thái**: Hiển thị trạng thái gần nhất (Sẵn sàng/Đang chụp/Đã dừng/Hoàn tất/…)
- **Timer**: Tổng thời gian chạy thực tế của phiên.
- **Thanh tiến trình**: Tiến độ theo số ảnh đã chụp / số ảnh đặt trước.
- Có thể kèm tốc độ ước tính (ảnh/phút) trong khu vực Log tuỳ phiên bản.

### 🗂️ Tabs
- **📝 Log**: Hiển thị từng bước thao tác (kết nối ADB, chụp, lưu file, upload Drive…). Rất hữu ích để chẩn đoán lỗi.
- **🖼️ Xem**: Xem ảnh mới chụp gần nhất; có nút **🔍 Phóng to** để mở ảnh full-size.

### ☁️ Google Drive (tuỳ chọn)
- Cần `credentials.json` cá nhân và xác thực lần đầu → tạo `token.json` tự động.
- Cấu trúc upload mặc định (tuỳ cấu hình trong `drive_config.json`):
  - Thư mục gốc: "AutoScreen Photos"
  - Có thể tạo thư mục theo kênh/chi nhánh/ngày (bật/tắt qua cấu hình)
- Khu vực Log sẽ hiển thị tiến trình upload và lỗi (nếu có). Nếu upload không chạy, kiểm tra lại credentials/token hoặc kết nối mạng.

---

## 📞 Hỗ trợ
- Gửi ảnh chụp màn hình, nội dung Log, và phiên bản Windows/thiết bị khi cần hỗ trợ để xử lý nhanh hơn.
