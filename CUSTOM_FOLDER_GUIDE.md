# Hướng dẫn sử dụng Custom Folder Mapping

## Tổng quan

Tính năng Custom Folder Mapping cho phép bạn upload ảnh trực tiếp vào các folder có sẵn trên Google Drive thay vì tạo cấu trúc folder mới. Điều này rất hữu ích khi bạn đã có 4 folder đại diện cho 4 chi nhánh và muốn upload trực tiếp vào đó.

## Khi nào sử dụng Custom Folder Mapping?

### ✅ Sử dụng khi:
- Bạn đã có các folder có sẵn trên Google Drive cho từng chi nhánh
- Muốn upload trực tiếp vào folder chi nhánh mà không cần phân chia theo kênh
- Tên file ảnh đã chứa thông tin kênh (ví dụ: `01_LBB_Shopee.png`)
- Muốn tổ chức file theo cách riêng của bạn

### ❌ Không sử dụng khi:
- Muốn tạo cấu trúc folder tự động theo ngày/kênh/chi nhánh
- Chưa có folder có sẵn trên Drive
- Muốn phân chia rõ ràng theo từng kênh

## Cách thiết lập

### Bước 1: Chuẩn bị folder trên Google Drive

1. Tạo 4 folder trên Google Drive cho 4 chi nhánh:
   ```
   📁 Luỹ Bán Bích
   📁 Lê Văn Thọ  
   📁 Bàu Cát
   📁 Phạm Viết Chánh
   ```

2. Ghi nhớ tên chính xác của các folder (phân biệt hoa thường)

### Bước 2: Cấu hình trong ứng dụng

1. Mở ứng dụng và chuyển sang tab "☁️ Drive"
2. Đảm bảo đã xác thực Google Drive thành công
3. **Cấu hình folder gốc**:
   - Nhập tên folder hoặc Folder ID vào ô "Folder gốc"
   - Tích "✅ Dùng ID" nếu bạn nhập Folder ID (khuyến nghị)
   - Bỏ tích "Dùng ID" nếu bạn nhập tên folder
4. Tích chọn "✅ Sử dụng folder tùy chỉnh cho chi nhánh"
5. Click nút "🗂️ Cấu hình folder"

### Bước 3: Thiết lập mapping

Trong dialog "Cấu hình Folder Tùy chỉnh":

#### Option 1: Thiết lập nhanh (Khuyến nghị)
1. Click "🚀 Thiết lập nhanh"
2. Ứng dụng sẽ tự động tìm folder có tên trùng với tên chi nhánh
3. Xác nhận kết quả

#### Option 2: Thiết lập thủ công
1. Chọn chi nhánh trong danh sách
2. Click "✏️ Chỉnh sửa"
3. Nhập **tên folder** hoặc **Folder ID**:
   - Tên folder: `Luỹ Bán Bích`
   - Folder ID: `1ABCxyz123...` (copy từ URL Google Drive)

### Bước 4: Kiểm tra và lưu

1. Click "🧪 Test mapping" để kiểm tra
2. Đảm bảo tất cả chi nhánh hiển thị "✅ OK"
3. Click "💾 Lưu" để hoàn tất

## Cấu trúc folder kết quả

### Với Custom Mapping (Đã bật):
```
Google Drive/
├── Luỹ Bán Bích/
│   ├── 01_LBB_Shopee.png
│   ├── 02_LBB_Grab.png
│   └── 03_LBB_XanhSM.png
├── Lê Văn Thọ/
│   ├── 01_LVT_Shopee.png
│   └── 02_LVT_Grab.png
├── Bàu Cát/
└── Phạm Viết Chánh/
```

### Với cấu trúc mặc định (Chưa bật):
```
Google Drive/
└── AutoScreen Photos/
    └── 2024-01-15/
        ├── ShopeeFood/
        │   ├── Luỹ Bán Bích/
        │   │   └── 01_LBB_Shopee.png
        │   └── Bàu Cát/
        └── GrabFood/
            └── Luỹ Bán Bích/
                └── 01_LBB_Grab.png
```

## Lấy Folder ID từ Google Drive

### Cách 1: Từ URL (Khuyến nghị)
1. Mở folder trên Google Drive web
2. Copy URL: `https://drive.google.com/drive/folders/1ABCxyz123...`
3. Folder ID là phần sau `/folders/`: `1ABCxyz123...`
4. Paste Folder ID vào ô "Folder gốc" và tích "✅ Dùng ID"

### Cách 2: Từ ứng dụng
1. Sử dụng tính năng "Thiết lập nhanh"
2. Ứng dụng sẽ tự động tìm và lấy Folder ID

### Tại sao nên dùng Folder ID?
- ✅ **Không tạo folder trùng**: Tránh tạo nhiều folder cùng tên
- ✅ **Chính xác 100%**: Không phụ thuộc vào tên folder (hoa thường, dấu cách)
- ✅ **Nhanh hơn**: Không cần tìm kiếm folder theo tên
- ✅ **Ổn định**: Folder ID không thay đổi khi đổi tên folder

## Troubleshooting

### ❌ "Folder ID không hợp lệ"
- **Nguyên nhân**: Folder đã bị xóa hoặc không có quyền truy cập
- **Giải pháp**: Kiểm tra folder có tồn tại, đảm bảo quyền truy cập

### ❌ "Không tìm thấy folder có tên: XXX"
- **Nguyên nhân**: Tên folder không chính xác (phân biệt hoa thường)
- **Giải pháp**: Kiểm tra tên folder chính xác trên Google Drive

### ❌ Upload vẫn tạo cấu trúc folder mới
- **Nguyên nhân**: Chưa bật "Sử dụng folder tùy chỉnh cho chi nhánh"
- **Giải pháp**: Tích chọn option này trong tab Drive

### ❌ Tạo nhiều folder cùng tên
- **Nguyên nhân**: Sử dụng tên folder thay vì Folder ID
- **Giải pháp**: Chuyển sang sử dụng Folder ID và tích "✅ Dùng ID"

### ⚠️ File upload vào sai folder
- **Nguyên nhân**: Mapping sai chi nhánh
- **Giải pháp**: Kiểm tra lại mapping bằng "Test mapping"

## Tips sử dụng hiệu quả

### 1. Đặt tên folder rõ ràng
```
✅ Tốt: "Luỹ Bán Bích", "Bàu Cát"
❌ Tránh: "LBB", "CN1", "Branch_1"
```

### 2. Tổ chức file trong folder
- Tất cả ảnh của chi nhánh vào cùng 1 folder
- Tên file đã chứa thông tin kênh: `01_LBB_Shopee.png`
- Không cần tạo subfolder theo kênh

### 3. Backup định kỳ
- Export danh sách mapping để backup
- Lưu Folder ID vào file text riêng
- Test mapping định kỳ để đảm bảo hoạt động

### 4. Quản lý quyền truy cập
- Đảm bảo tài khoản Google có quyền edit folder
- Không chia sẻ folder với người khác khi đang upload
- Kiểm tra dung lượng Google Drive thường xuyên

## Ví dụ cấu hình hoàn chỉnh

### Cấu hình sử dụng Folder ID (Khuyến nghị)
```json
{
  "use_custom_mapping": true,
  "use_root_folder_id": true,
  "root_folder_name": "1XYZabc789_RootFolder_ID",
  "create_channel_folders": false,
  "create_branch_folders": false,
  "create_date_folders": false,
  "custom_folder_mapping": {
    "LBB": "1ABCxyz123_LuyBanBich_FolderID",
    "LVT": "1DEFabc456_LeVanTho_FolderID", 
    "BC": "1GHIdef789_BauCat_FolderID",
    "PVC": "1JKLghi012_PhamVietChanh_FolderID"
  }
}
```

### Cấu hình sử dụng tên folder
```json
{
  "use_custom_mapping": true,
  "use_root_folder_id": false,
  "root_folder_name": "AutoScreen Photos",
  "create_channel_folders": false,
  "create_branch_folders": false,
  "create_date_folders": false,
  "custom_folder_mapping": {
    "LBB": "1ABCxyz123_LuyBanBich_FolderID",
    "LVT": "1DEFabc456_LeVanTho_FolderID", 
    "BC": "1GHIdef789_BauCat_FolderID",
    "PVC": "1JKLghi012_PhamVietChanh_FolderID"
  }
}
```

**Lưu ý**: Ngay cả khi sử dụng tên folder cho root, vẫn nên dùng Folder ID cho mapping chi nhánh để đảm bảo chính xác.
