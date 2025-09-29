import os
import io
import json
import threading
import queue
from datetime import datetime
from pathlib import Path

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload
    from googleapiclient.errors import HttpError
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False

class GoogleDriveUploader:
    """Class để quản lý upload ảnh lên Google Drive theo từng chi nhánh"""
    
    # Scope cho Google Drive API
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    
    def __init__(self, credentials_file="credentials.json", token_file="token.json"):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self.upload_queue = queue.Queue()
        self.is_uploading = False
        self.upload_thread = None
        self.log_callback = None
        self.progress_callback = None
        self.completion_callback = None
        
        # Cấu hình upload
        self.auto_upload = False
        self.create_date_folders = True
        self.create_branch_folders = True
        self.create_channel_folders = True  # Tùy chọn tạo folder theo kênh
        self.root_folder_name = "AutoScreen Photos"
        self.root_folder_id = None
        self.use_root_folder_id = False  # Sử dụng folder ID thay vì tên cho root folder
        self.custom_folder_mapping = {}  # Mapping tùy chỉnh folder cho từng chi nhánh
        self.use_custom_mapping = False  # Sử dụng mapping tùy chỉnh thay vì cấu trúc mặc định
        
        # Thống kê
        self.upload_stats = {
            'total_uploaded': 0,
            'total_failed': 0,
            'current_session': 0,
            'last_upload_time': None
        }
    
    def is_available(self):
        """Kiểm tra xem Google Drive API có sẵn không"""
        return GOOGLE_DRIVE_AVAILABLE
    
    def set_callbacks(self, log_callback=None, progress_callback=None, completion_callback=None):
        """Đặt các callback functions"""
        self.log_callback = log_callback
        self.progress_callback = progress_callback
        self.completion_callback = completion_callback
    
    def log_message(self, message):
        """Ghi log message"""
        if self.log_callback:
            self.log_callback(f"📤 {message}")
        else:
            print(f"Drive Upload: {message}")
    
    def authenticate(self):
        """Xác thực với Google Drive API"""
        if not self.is_available():
            raise Exception("Google Drive API không có sẵn. Vui lòng cài đặt: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
        
        creds = None
        
        # Kiểm tra token đã lưu
        if os.path.exists(self.token_file):
            try:
                creds = Credentials.from_authorized_user_file(self.token_file, self.SCOPES)
            except Exception as e:
                self.log_message(f"Lỗi đọc token: {e}")
        
        # Nếu không có credentials hợp lệ, yêu cầu xác thực
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    self.log_message(f"Lỗi làm mới token: {e}")
                    creds = None
            
            if not creds:
                if not os.path.exists(self.credentials_file):
                    raise Exception(f"Không tìm thấy file credentials: {self.credentials_file}")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Lưu credentials cho lần sử dụng tiếp theo
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('drive', 'v3', credentials=creds)
        self.log_message("✅ Đã xác thực thành công với Google Drive")
        return True
    
    def create_folder(self, folder_name, parent_id=None):
        """Tạo folder trên Google Drive"""
        try:
            # Kiểm tra xem folder đã tồn tại chưa
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            if parent_id:
                query += f" and parents in '{parent_id}'"
            else:
                query += " and 'root' in parents"
            
            results = self.service.files().list(q=query, fields="files(id, name)").execute()
            items = results.get('files', [])
            
            if items:
                # Folder đã tồn tại
                return items[0]['id']
            
            # Tạo folder mới
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_id:
                folder_metadata['parents'] = [parent_id]
            
            folder = self.service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = folder.get('id')
            
            self.log_message(f"📁 Đã tạo folder: {folder_name}")
            return folder_id
            
        except HttpError as e:
            self.log_message(f"❌ Lỗi tạo folder '{folder_name}': {e}")
            return None
    
    def get_or_create_folder_structure(self, channel_name, branch_name):
        """Tạo cấu trúc thư mục cho kênh và chi nhánh"""
        try:
            # Nếu sử dụng custom mapping, upload trực tiếp vào folder đã map
            if self.use_custom_mapping and branch_name in self.custom_folder_mapping:
                folder_id = self.custom_folder_mapping[branch_name]
                # Kiểm tra folder có tồn tại không
                if self._check_folder_exists(folder_id):
                    self.log_message(f"📁 Sử dụng custom mapping: {branch_name} -> {folder_id}")
                    return folder_id
                else:
                    self.log_message(f"❌ Folder ID không hợp lệ cho chi nhánh {branch_name}: {folder_id}")
                    return None
            
            # Nếu không dùng custom mapping, tạo cấu trúc folder thông thường
            self.log_message(f"📂 Tạo cấu trúc folder thông thường cho {channel_name}/{branch_name}")
            
            # Tạo hoặc sử dụng root folder
            if not self.root_folder_id:
                if self.use_root_folder_id:
                    # Sử dụng root_folder_name như là folder ID
                    self.root_folder_id = self.root_folder_name
                    if not self._check_folder_exists(self.root_folder_id):
                        self.log_message(f"❌ Root folder ID không hợp lệ: {self.root_folder_id}")
                        return None
                    else:
                        self.log_message(f"📁 Sử dụng root folder ID: {self.root_folder_id}")
                else:
                    # Tạo folder mới theo tên
                    self.root_folder_id = self.create_folder(self.root_folder_name)
                    if not self.root_folder_id:
                        return None
            
            current_folder_id = self.root_folder_id
            
            # Tạo folder theo ngày nếu được bật
            if self.create_date_folders:
                date_folder = datetime.now().strftime("%Y-%m-%d")
                current_folder_id = self.create_folder(date_folder, current_folder_id)
                if not current_folder_id:
                    return None
            
            # Tạo folder kênh nếu được bật
            if self.create_channel_folders:
                current_folder_id = self.create_folder(channel_name, current_folder_id)
                if not current_folder_id:
                    return None
            
            # Tạo folder chi nhánh nếu được bật
            if self.create_branch_folders:
                current_folder_id = self.create_folder(branch_name, current_folder_id)
            
            return current_folder_id
            
        except Exception as e:
            self.log_message(f"❌ Lỗi tạo cấu trúc folder: {e}")
            return None
    
    def _check_folder_exists(self, folder_id):
        """Kiểm tra folder có tồn tại trên Google Drive không"""
        try:
            self.service.files().get(fileId=folder_id).execute()
            return True
        except:
            return False
    
    def upload_file(self, file_path, folder_id=None, custom_name=None):
        """Upload một file lên Google Drive"""
        try:
            if not os.path.exists(file_path):
                self.log_message(f"❌ File không tồn tại: {file_path}")
                return False
            
            filename = custom_name or os.path.basename(file_path)
            
            # Kiểm tra file đã tồn tại chưa
            query = f"name='{filename}' and trashed=false"
            if folder_id:
                query += f" and parents in '{folder_id}'"
            
            results = self.service.files().list(q=query, fields="files(id, name)").execute()
            items = results.get('files', [])
            
            if items:
                self.log_message(f"⚠️ File đã tồn tại: {filename}")
                return True  # Coi như thành công
            
            # Chuẩn bị metadata
            file_metadata = {'name': filename}
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            # Upload file
            with open(file_path, 'rb') as f:
                media = MediaIoBaseUpload(
                    io.BytesIO(f.read()),
                    mimetype='image/png',
                    resumable=True
                )
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            if file_id:
                self.upload_stats['total_uploaded'] += 1
                self.upload_stats['current_session'] += 1
                self.upload_stats['last_upload_time'] = datetime.now()
                self.log_message(f"✅ Đã upload: {filename}")
                return True
            else:
                self.upload_stats['total_failed'] += 1
                self.log_message(f"❌ Upload thất bại: {filename}")
                return False
                
        except HttpError as e:
            self.upload_stats['total_failed'] += 1
            self.log_message(f"❌ Lỗi upload '{filename}': {e}")
            return False
        except Exception as e:
            self.upload_stats['total_failed'] += 1
            self.log_message(f"❌ Lỗi không xác định upload '{filename}': {e}")
            return False
    
    def add_to_upload_queue(self, file_path, channel_name, branch_name, custom_name=None):
        """Thêm file vào hàng đợi upload"""
        upload_item = {
            'file_path': file_path,
            'channel_name': channel_name,
            'branch_name': branch_name,
            'custom_name': custom_name,
            'timestamp': datetime.now()
        }
        self.upload_queue.put(upload_item)
    
    def start_upload_worker(self):
        """Bắt đầu worker thread để xử lý upload queue"""
        if self.is_uploading:
            return
        
        self.is_uploading = True
        self.upload_stats['current_session'] = 0
        self.upload_thread = threading.Thread(target=self._upload_worker, daemon=True)
        self.upload_thread.start()
        self.log_message("🚀 Bắt đầu upload worker")
    
    def stop_upload_worker(self):
        """Dừng upload worker"""
        self.is_uploading = False
        if self.upload_thread and self.upload_thread.is_alive():
            self.upload_thread.join(timeout=5)
        self.log_message("⏹ Đã dừng upload worker")
    
    def _upload_worker(self):
        """Worker thread xử lý upload queue"""
        while self.is_uploading:
            try:
                # Lấy item từ queue với timeout
                upload_item = self.upload_queue.get(timeout=1)
                
                # Xác thực nếu cần
                if not self.service:
                    if not self.authenticate():
                        self.log_message("❌ Không thể xác thực Google Drive")
                        continue
                
                # Tạo cấu trúc folder
                folder_id = self.get_or_create_folder_structure(
                    upload_item['channel_name'], 
                    upload_item['branch_name']
                )
                
                if folder_id:
                    # Upload file
                    success = self.upload_file(
                        upload_item['file_path'],
                        folder_id,
                        upload_item['custom_name']
                    )
                    
                    # Callback progress
                    if self.progress_callback:
                        self.progress_callback(success, upload_item)
                else:
                    self.log_message(f"❌ Không thể tạo folder cho {upload_item['channel_name']}/{upload_item['branch_name']}")
                
                self.upload_queue.task_done()
                
            except queue.Empty:
                # Timeout - kiểm tra nếu queue rỗng thì dừng
                if self.upload_queue.empty():
                    self.log_message("📤 Queue rỗng, dừng upload worker")
                    break
                continue
            except Exception as e:
                self.log_message(f"❌ Lỗi trong upload worker: {e}")
        
        # Đặt flag về False khi worker kết thúc
        self.is_uploading = False
        self.log_message("📤 Upload worker đã hoàn thành")
        
        # Callback khi hoàn thành
        if self.completion_callback:
            self.completion_callback(self.upload_stats)
    
    def upload_folder_contents(self, folder_path, channel_name, branch_name, file_pattern=None):
        """Upload toàn bộ nội dung của một folder"""
        if not os.path.exists(folder_path):
            self.log_message(f"❌ Folder không tồn tại: {folder_path}")
            return
        
        files_added = 0
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            
            # Kiểm tra pattern nếu có
            if file_pattern and not file_pattern.match(filename):
                continue
            
            if os.path.isfile(file_path) and filename.lower().endswith('.png'):
                self.add_to_upload_queue(file_path, channel_name, branch_name)
                files_added += 1
        
        self.log_message(f"📤 Đã thêm {files_added} file vào hàng đợi upload")
        return files_added
    
    def get_upload_status(self):
        """Lấy trạng thái upload"""
        return {
            'is_uploading': self.is_uploading,
            'queue_size': self.upload_queue.qsize(),
            'stats': self.upload_stats.copy()
        }
    
    def reset_upload_stats(self):
        """Reset thống kê upload"""
        self.upload_stats = {
            'total_uploaded': 0,
            'total_failed': 0,
            'current_session': 0,
            'last_upload_time': None
        }
        self.save_config()
        self.log_message("🔄 Đã reset thống kê upload")
    
    def configure_upload(self, auto_upload=None, create_date_folders=None, 
                        create_branch_folders=None, create_channel_folders=None,
                        root_folder_name=None, use_custom_mapping=None, use_root_folder_id=None):
        """Cấu hình các tùy chọn upload"""
        if auto_upload is not None:
            self.auto_upload = auto_upload
        if create_date_folders is not None:
            self.create_date_folders = create_date_folders
        if create_branch_folders is not None:
            self.create_branch_folders = create_branch_folders
        if create_channel_folders is not None:
            self.create_channel_folders = create_channel_folders
        if root_folder_name is not None:
            self.root_folder_name = root_folder_name
            self.root_folder_id = None  # Reset để tạo lại folder
        if use_custom_mapping is not None:
            self.use_custom_mapping = use_custom_mapping
        if use_root_folder_id is not None:
            self.use_root_folder_id = use_root_folder_id
            self.root_folder_id = None  # Reset để tạo lại folder
    
    def set_custom_folder_mapping(self, mapping_dict):
        """
        Thiết lập mapping tùy chỉnh folder cho từng chi nhánh
        mapping_dict: {branch_code: folder_id_or_name}
        """
        self.custom_folder_mapping = mapping_dict.copy()
        self.log_message(f"📁 Đã thiết lập custom folder mapping cho {len(mapping_dict)} chi nhánh")
    
    def add_custom_folder_mapping(self, branch_code, folder_id_or_name):
        """Thêm mapping cho một chi nhánh"""
        self.custom_folder_mapping[branch_code] = folder_id_or_name
        self.log_message(f"📁 Đã thêm mapping: {branch_code} -> {folder_id_or_name}")
    
    def remove_custom_folder_mapping(self, branch_code):
        """Xóa mapping cho một chi nhánh"""
        if branch_code in self.custom_folder_mapping:
            del self.custom_folder_mapping[branch_code]
            self.log_message(f"🗑️ Đã xóa mapping cho chi nhánh: {branch_code}")
    
    def get_folder_id_by_name(self, folder_name, parent_id=None):
        """Tìm folder ID theo tên"""
        try:
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            if parent_id:
                query += f" and parents in '{parent_id}'"
            
            results = self.service.files().list(q=query, fields="files(id, name)").execute()
            items = results.get('files', [])
            
            if items:
                return items[0]['id']
            return None
        except Exception as e:
            self.log_message(f"❌ Lỗi tìm folder '{folder_name}': {e}")
            return None
    
    def setup_branch_folders_from_names(self, branch_folder_names, parent_folder_id=None):
        """
        Thiết lập mapping từ danh sách tên folder có sẵn trên Drive
        branch_folder_names: {branch_code: folder_name}
        """
        mapping = {}
        
        # Xác định parent folder
        if parent_folder_id:
            parent_id = parent_folder_id
        else:
            # Sử dụng root folder đã được thiết lập
            if not self.root_folder_id:
                if self.use_root_folder_id:
                    self.root_folder_id = self.root_folder_name
                    if not self._check_folder_exists(self.root_folder_id):
                        self.log_message(f"❌ Root folder ID không hợp lệ: {self.root_folder_id}")
                        return {}
                else:
                    self.root_folder_id = self.create_folder(self.root_folder_name)
                    if not self.root_folder_id:
                        return {}
            parent_id = self.root_folder_id
        
        self.log_message(f"🔍 Tìm folder chi nhánh trong parent folder ID: {parent_id}")
        
        for branch_code, folder_name in branch_folder_names.items():
            # Tìm folder theo tên trong parent folder
            folder_id = self.get_folder_id_by_name(folder_name, parent_id)
            
            if folder_id:
                mapping[branch_code] = folder_id
                self.log_message(f"✅ Tìm thấy {branch_code} -> {folder_name} (ID: {folder_id})")
            else:
                # Tạo folder mới nếu không tìm thấy
                folder_id = self.create_folder(folder_name, parent_id)
                if folder_id:
                    mapping[branch_code] = folder_id
                    self.log_message(f"➕ Tạo mới {branch_code} -> {folder_name} (ID: {folder_id})")
                else:
                    self.log_message(f"❌ Không thể tạo folder cho {branch_code}: {folder_name}")
        
        if mapping:
            self.set_custom_folder_mapping(mapping)
            self.log_message(f"💾 Đã thiết lập mapping cho {len(mapping)} chi nhánh")
        
        return mapping
    
    def save_config(self, config_file="drive_config.json"):
        """Lưu cấu hình upload"""
        config = {
            'auto_upload': self.auto_upload,
            'create_date_folders': self.create_date_folders,
            'create_branch_folders': self.create_branch_folders,
            'create_channel_folders': self.create_channel_folders,
            'root_folder_name': self.root_folder_name,
            'use_root_folder_id': self.use_root_folder_id,
            'use_custom_mapping': self.use_custom_mapping,
            'custom_folder_mapping': self.custom_folder_mapping,
            'upload_stats': self.upload_stats
        }
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, default=str)
            self.log_message(f"💾 Đã lưu cấu hình: {config_file}")
        except Exception as e:
            self.log_message(f"❌ Lỗi lưu cấu hình: {e}")
    
    def load_config(self, config_file="drive_config.json"):
        """Tải cấu hình upload"""
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                self.auto_upload = config.get('auto_upload', False)
                self.create_date_folders = config.get('create_date_folders', True)
                self.create_branch_folders = config.get('create_branch_folders', True)
                self.create_channel_folders = config.get('create_channel_folders', True)
                self.root_folder_name = config.get('root_folder_name', 'AutoScreen Photos')
                self.use_root_folder_id = config.get('use_root_folder_id', False)
                self.use_custom_mapping = config.get('use_custom_mapping', False)
                self.custom_folder_mapping = config.get('custom_folder_mapping', {})
                
                # Load stats nhưng reset current_session
                saved_stats = config.get('upload_stats', {})
                self.upload_stats.update(saved_stats)
                self.upload_stats['current_session'] = 0
                
                self.log_message(f"📂 Đã tải cấu hình: {config_file}")
                
                if self.use_root_folder_id:
                    self.log_message(f"📁 Sử dụng root folder ID: {self.root_folder_name}")
                
                if self.use_custom_mapping and self.custom_folder_mapping:
                    self.log_message(f"📁 Custom mapping: {len(self.custom_folder_mapping)} chi nhánh")
        except Exception as e:
            self.log_message(f"❌ Lỗi tải cấu hình: {e}")
    
    def debug_folder_structure(self):
        """Debug và hiển thị cấu trúc folder hiện tại"""
        if not self.service:
            self.log_message("❌ Chưa xác thực Google Drive")
            return
        
        self.log_message("🔍 DEBUG: Kiểm tra cấu trúc folder...")
        
        # Kiểm tra root folder
        if self.use_root_folder_id:
            root_id = self.root_folder_name
            self.log_message(f"📁 Root folder ID: {root_id}")
            
            if self._check_folder_exists(root_id):
                try:
                    folder_info = self.service.files().get(fileId=root_id, fields="name").execute()
                    folder_name = folder_info.get('name', 'Unknown')
                    self.log_message(f"✅ Root folder tồn tại: {folder_name} (ID: {root_id})")
                    
                    # Liệt kê các folder con
                    query = f"parents in '{root_id}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
                    results = self.service.files().list(q=query, fields="files(id, name)").execute()
                    items = results.get('files', [])
                    
                    self.log_message(f"📂 Tìm thấy {len(items)} folder con:")
                    for item in items:
                        self.log_message(f"  • {item['name']} (ID: {item['id']})")
                        
                except Exception as e:
                    self.log_message(f"❌ Lỗi lấy thông tin root folder: {e}")
            else:
                self.log_message(f"❌ Root folder ID không tồn tại: {root_id}")
                self.log_message("💡 Hãy kiểm tra lại ID hoặc quyền truy cập folder")
        
        # Kiểm tra custom mapping
        if self.use_custom_mapping:
            self.log_message("🗂️ Kiểm tra custom mapping:")
            for branch_code, folder_id in self.custom_folder_mapping.items():
                if self._check_folder_exists(folder_id):
                    try:
                        folder_info = self.service.files().get(fileId=folder_id, fields="name").execute()
                        folder_name = folder_info.get('name', 'Unknown')
                        self.log_message(f"  ✅ {branch_code}: {folder_name} (ID: {folder_id})")
                    except:
                        self.log_message(f"  ❌ {branch_code}: Lỗi lấy thông tin (ID: {folder_id})")
                else:
                    self.log_message(f"  ❌ {branch_code}: Folder không tồn tại (ID: {folder_id})")
                    
    def list_my_drive_folders(self, parent_folder_id=None):
        """Liệt kê tất cả folder trong Drive để tìm đúng ID"""
        if not self.service:
            self.log_message("❌ Chưa xác thực Google Drive")
            return
            
        try:
            self.log_message("🔍 SCAN: Tìm kiếm tất cả folder trong Drive...")
            
            if parent_folder_id:
                query = f"parents in '{parent_folder_id}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
                self.log_message(f"📂 Tìm trong folder ID: {parent_folder_id}")
            else:
                query = "mimeType='application/vnd.google-apps.folder' and trashed=false"
                self.log_message("📂 Tìm trong toàn bộ Drive")
            
            results = self.service.files().list(
                q=query,
                fields="files(id, name, parents)",
                pageSize=100
            ).execute()
            
            items = results.get('files', [])
            self.log_message(f"📋 Tìm thấy {len(items)} folder:")
            
            for item in items:
                parents = item.get('parents', ['root'])
                parent_info = f" (trong: {parents[0]})" if parents[0] != 'root' else " (root)"
                self.log_message(f"  📁 {item['name']} -> ID: {item['id']}{parent_info}")
                
        except Exception as e:
            self.log_message(f"❌ Lỗi scan folder: {e}")
