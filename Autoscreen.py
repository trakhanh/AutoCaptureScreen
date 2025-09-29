import subprocess, time, os, hashlib, re, argparse, sys, threading, json

def run(cmd, capture=False, check=True):
    if capture:
        return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check).stdout
    subprocess.run(cmd, check=check)

def adb_cmd(args, serial=None, capture=False, check=True):
    cmd = ["adb"]
    if serial:
        cmd += ["-s", serial]
    cmd += args
    if capture:
        return run(cmd, capture=True, check=check)
    run(cmd, capture=False, check=check)

def list_devices():
    out = adb_cmd(["devices"], capture=True).decode("utf-8", errors="ignore")
    devs = []
    for line in out.splitlines()[1:]:
        if line.strip() and "\tdevice" in line:
            devs.append(line.split("\t")[0])
    return devs

def ensure_device(serial=None):
    devs = list_devices()
    if serial:
        if serial not in devs:
            raise SystemExit(f"Không thấy thiết bị '{serial}'. Thiết bị khả dụng: {devs or '[]'}")
        return serial
    if not devs:
        raise SystemExit("Không thấy thiết bị/emulator. Mở AVD hoặc cắm máy rồi chạy: adb devices")
    if len(devs) > 1:
        raise SystemExit(f"Có hơn 1 thiết bị. Chỉ định --serial. Thiết bị: {devs}")
    return devs[0]

def get_screen_size(serial=None):
    out = adb_cmd(["shell","wm","size"], serial, capture=True).decode("utf-8", errors="ignore")
    m = re.search(r'Physical size:\s*(\d+)x(\d+)', out)
    if not m:
        out2 = adb_cmd(["shell","dumpsys","display"], serial, capture=True).decode("utf-8", errors="ignore")
        m = re.search(r'cur=\s*(\d+)x(\d+)', out2)
    if not m:
        raise SystemExit("Không lấy được độ phân giải màn hình.")
    return int(m.group(1)), int(m.group(2))

def screencap_to_file(path, serial=None):
    raw = adb_cmd(["exec-out","screencap","-p"], serial, capture=True)
    with open(path, "wb") as f:
        f.write(raw)

def swipe(x1,y1,x2,y2,duration_ms, serial=None):
    adb_cmd(["shell","input","swipe",str(x1),str(y1),str(x2),str(y2),str(duration_ms)], serial)

def sha256(path):
    h = hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()

def maybe_tune_device(serial=None):
    cmds = [
        ["shell","settings","put","global","window_animation_scale","0"],
        ["shell","settings","put","global","transition_animation_scale","0"],
        ["shell","settings","put","global","animator_duration_scale","0"],
        ["shell","settings","put","system","screen_off_timeout","1800000"]
    ]
    for c in cmds:
        try: adb_cmd(c, serial)
        except Exception: pass

# --- Quản lý kênh và chi nhánh ---
class ChannelManager:
    def __init__(self, config_file="channels_config.json"):
        self.config_file = config_file
        self.channels = self.load_config()
    
    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        # Cấu hình mặc định
        return {
            "shopeefood": {
                "name": "ShopeeFood",
                "branches": {
                    "LBB": "Luỹ Bán Bích",
                    "LVT": "Lê Văn Thọ", 
                    "BC": "Bàu Cát",
                    "PVC": "Phạm Viết Chánh"
                }
            },
            "grabfood": {
                "name": "GrabFood",
                "branches": {
                    "LBB": "Luỹ Bán Bích",
                    "LVT": "Lê Văn Thọ",
                    "BC": "Bàu Cát", 
                    "PVC": "Phạm Viết Chánh"
                }
            }
        }
    
    def save_config(self):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.channels, f, ensure_ascii=False, indent=2)
    
    def list_channels(self):
        print("\n=== DANH SÁCH KÊNH ===")
        for key, channel in self.channels.items():
            print(f"- {key}: {channel['name']}")
            print(f"  Chi nhánh: {list(channel['branches'].keys())}")
    
    def add_channel(self, key, name, copy_branches_from=None):
        if key in self.channels:
            print(f"Kênh '{key}' đã tồn tại!")
            return False
        
        # Tự động copy chi nhánh từ kênh khác hoặc tạo mặc định
        branches = {}
        if copy_branches_from and copy_branches_from in self.channels:
            branches = self.channels[copy_branches_from]["branches"].copy()
        elif self.channels:  # Copy từ kênh đầu tiên nếu có
            first_channel = list(self.channels.values())[0]
            branches = first_channel["branches"].copy()
        else:  # Tạo chi nhánh mặc định nếu chưa có kênh nào
            branches = {
                "LBB": "Luỹ Bán Bích",
                "LVT": "Lê Văn Thọ",
                "BC": "Bàu Cát",
                "PVC": "Phạm Viết Chánh"
            }
        
        self.channels[key] = {
            "name": name,
            "branches": branches
        }
        self.save_config()
        print(f"Đã thêm kênh '{key}': {name} với {len(branches)} chi nhánh")
        return True
    
    def remove_channel(self, key):
        if key not in self.channels:
            print(f"Kênh '{key}' không tồn tại!")
            return False
        
        channel_name = self.channels[key]["name"]
        del self.channels[key]
        self.save_config()
        print(f"Đã xóa kênh '{channel_name}'")
        return True
    
    def remove_branch(self, channel_key, branch_code):
        if channel_key not in self.channels:
            print(f"Kênh '{channel_key}' không tồn tại!")
            return False
        
        if branch_code not in self.channels[channel_key]["branches"]:
            print(f"Chi nhánh '{branch_code}' không tồn tại trong kênh '{channel_key}'!")
            return False
        
        branch_name = self.channels[channel_key]["branches"][branch_code]
        del self.channels[channel_key]["branches"][branch_code]
        self.save_config()
        print(f"Đã xóa chi nhánh '{branch_name}' khỏi kênh '{channel_key}'")
        return True
    
    def add_branch(self, channel_key, branch_code, branch_name):
        if channel_key not in self.channels:
            print(f"Kênh '{channel_key}' không tồn tại!")
            return False
        
        # Kiểm tra chi nhánh đã tồn tại
        if branch_code in self.channels[channel_key]["branches"]:
            existing_name = self.channels[channel_key]["branches"][branch_code]
            if existing_name == branch_name:
                print(f"Chi nhánh '{branch_code}': {branch_name} đã tồn tại trong kênh {channel_key}")
                return True  # Trả về True vì chi nhánh đã có đúng thông tin
            else:
                # Cập nhật tên nếu khác
                self.channels[channel_key]["branches"][branch_code] = branch_name
                self.save_config()
                print(f"Đã cập nhật chi nhánh '{branch_code}': {existing_name} -> {branch_name} trong kênh {channel_key}")
                return True
        
        self.channels[channel_key]["branches"][branch_code] = branch_name
        self.save_config()
        print(f"Đã thêm chi nhánh '{branch_code}': {branch_name} vào kênh {channel_key}")
        return True
    
    def get_channel_name(self, key):
        return self.channels.get(key, {}).get("name", key)
    
    def get_branch_name(self, channel_key, branch_code):
        return self.channels.get(channel_key, {}).get("branches", {}).get(branch_code, branch_code)
    
    def validate_selection(self, channel_key, branch_code):
        if channel_key not in self.channels:
            return False, f"Kênh '{channel_key}' không tồn tại"
        if branch_code not in self.channels[channel_key]["branches"]:
            return False, f"Chi nhánh '{branch_code}' không có trong kênh '{channel_key}'"
        return True, "OK"

def interactive_channel_selection(manager):
    """Menu tương tác để chọn kênh và chi nhánh"""
    print("\n=== CHỌN KÊNH VÀ CHI NHÁNH ===")
    
    # Hiển thị danh sách kênh
    channels = list(manager.channels.keys())
    print("\nCác kênh có sẵn:")
    for i, key in enumerate(channels, 1):
        print(f"{i}. {key} ({manager.channels[key]['name']})")
    
    while True:
        try:
            choice = input(f"\nChọn kênh (1-{len(channels)}) hoặc 'q' để thoát: ").strip()
            if choice.lower() == 'q':
                return None, None
            
            channel_idx = int(choice) - 1
            if 0 <= channel_idx < len(channels):
                selected_channel = channels[channel_idx]
                break
            else:
                print("Lựa chọn không hợp lệ!")
        except ValueError:
            print("Vui lòng nhập số!")
    
    # Hiển thị danh sách chi nhánh
    branches = list(manager.channels[selected_channel]["branches"].items())
    print(f"\nChi nhánh của {manager.channels[selected_channel]['name']}:")
    for i, (code, name) in enumerate(branches, 1):
        print(f"{i}. {code} - {name}")
    
    while True:
        try:
            choice = input(f"\nChọn chi nhánh (1-{len(branches)}): ").strip()
            branch_idx = int(choice) - 1
            if 0 <= branch_idx < len(branches):
                selected_branch = branches[branch_idx][0]
                break
            else:
                print("Lựa chọn không hợp lệ!")
        except ValueError:
            print("Vui lòng nhập số!")
    
    return selected_channel, selected_branch

def management_menu(manager):
    """Menu quản lý kênh và chi nhánh"""
    while True:
        print("\n=== QUẢN LÝ KÊNH VÀ CHI NHÁNH ===")
        print("1. Xem danh sách kênh")
        print("2. Thêm kênh mới")
        print("3. Thêm chi nhánh")
        print("4. Quay lại")
        
        choice = input("\nChọn (1-4): ").strip()
        
        if choice == '1':
            manager.list_channels()
        elif choice == '2':
            key = input("Nhập key kênh (vd: shopeefood): ").strip().lower()
            name = input("Nhập tên kênh (vd: ShopeeFood): ").strip()
            if key and name:
                manager.add_channel(key, name)
        elif choice == '3':
            manager.list_channels()
            channel_key = input("\nNhập key kênh: ").strip().lower()
            if channel_key in manager.channels:
                branch_code = input("Nhập mã chi nhánh (vd: BC): ").strip().upper()
                branch_name = input("Nhập tên chi nhánh (vd: Bàu Cát): ").strip()
                if branch_code and branch_name:
                    manager.add_branch(channel_key, branch_code, branch_name)
            else:
                print(f"Kênh '{channel_key}' không tồn tại!")
        elif choice == '4':
            break

# --- Nút dừng bằng ENTER (chạy ở thread riêng) ---
class Stopper:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self._evt = threading.Event()
        if enabled:
            t = threading.Thread(target=self._wait_enter, daemon=True)
            t.start()
    def _wait_enter(self):
        try:
            # Một số terminal (VD: VSCode task) có thể không cho input -> bắt lỗi và bỏ qua
            input(">> Nhấn ENTER để dừng sớm...\n")
            self._evt.set()
        except Exception:
            pass
    def should_stop(self):
        return self._evt.is_set()

def get_next_image_number(output_dir, branch_code, channel_short):
    """Tìm số ảnh tiếp theo dựa trên file có sẵn trong thư mục"""
    if not os.path.exists(output_dir):
        return 1
    
    max_num = 0
    pattern = re.compile(rf"(\d+)_{re.escape(branch_code)}_{re.escape(channel_short)}\.png$", re.IGNORECASE)
    
    try:
        for filename in os.listdir(output_dir):
            match = pattern.match(filename)
            if match:
                num = int(match.group(1))
                max_num = max(max_num, num)
    except Exception as e:
        print(f"Lỗi khi đọc thư mục {output_dir}: {e}")
    
    return max_num + 1

def auto_sort_files(output_dir, branch_code, channel_short, log_callback=None):
    """
    Tự động sắp xếp lại tên file theo thứ tự số liên tục
    Trả về: (số file đã sắp xếp, số file cuối cùng)
    """
    if not os.path.exists(output_dir):
        return 0, 0

    # Pattern để tìm file: số_branch_channel.png
    pattern = re.compile(rf"(\d+)_{re.escape(branch_code)}_{re.escape(channel_short)}\.png$", re.IGNORECASE)

    # Tìm tất cả file phù hợp
    files_info = []
    try:
        for filename in os.listdir(output_dir):
            match = pattern.match(filename)
            if match:
                num = int(match.group(1))
                files_info.append((num, filename))
    except Exception as e:
        if log_callback:
            log_callback(f"Lỗi khi đọc thư mục {output_dir}: {e}")
        return 0, 0

    if not files_info:
        return 0, 0

    # Sắp xếp theo số thứ tự hiện tại
    files_info.sort(key=lambda x: x[0])

    # Kiểm tra xem có cần sắp xếp lại không
    needs_sorting = False
    for i, (current_num, _) in enumerate(files_info):
        expected_num = i + 1
        if current_num != expected_num:
            needs_sorting = True
            break

    if not needs_sorting:
        return 0, len(files_info)

    # Sắp xếp lại tên file
    sorted_count = 0
    for i, (old_num, old_filename) in enumerate(files_info):
        new_num = i + 1
        if old_num != new_num:
            new_filename = f"{new_num:02d}_{branch_code}_{channel_short}.png"
            old_path = os.path.join(output_dir, old_filename)
            new_path = os.path.join(output_dir, new_filename)

            try:
                os.rename(old_path, new_path)
                sorted_count += 1
                if log_callback:
                    log_callback(f"Đổi tên: {old_filename} → {new_filename}")
            except Exception as e:
                if log_callback:
                    log_callback(f"Lỗi khi đổi tên {old_filename}: {e}")

    return sorted_count, len(files_info)

def get_folder_stats(output_dir, branch_code, channel_short):
    """
    Lấy thống kê về thư mục ảnh
    Trả về: (tổng ảnh, kích thước thư mục MB, file bị thiếu)
    """
    if not os.path.exists(output_dir):
        return 0, 0, 0

    pattern = re.compile(rf"(\d+)_{re.escape(branch_code)}_{re.escape(channel_short)}\.png$", re.IGNORECASE)

    numbers_found = set()
    total_size = 0
    file_count = 0

    try:
        for filename in os.listdir(output_dir):
            match = pattern.match(filename)
            if match:
                num = int(match.group(1))
                numbers_found.add(num)
                file_count += 1

                # Tính kích thước file
                filepath = os.path.join(output_dir, filename)
                if os.path.isfile(filepath):
                    total_size += os.path.getsize(filepath)
    except Exception:
        pass

    # Tìm số file bị thiếu
    if numbers_found:
        max_num = max(numbers_found)
        expected_numbers = set(range(1, max_num + 1))
        missing_count = len(expected_numbers - numbers_found)
    else:
        missing_count = 0

    # Chuyển kích thước sang MB
    size_mb = total_size / (1024 * 1024)

    return file_count, size_mb, missing_count

def main():
    ap = argparse.ArgumentParser(description="Auto screenshot + swipe via ADB với quản lý kênh và chi nhánh")
    ap.add_argument("--out", default="shots", help="Thư mục gốc lưu ảnh")
    ap.add_argument("--shots", type=int, default=100, help="Số lần chụp tối đa")
    ap.add_argument("--delay", type=float, default=1.2, help="Chờ giữa mỗi lần (giây)")
    ap.add_argument("--swipe-ms", type=int, default=550, help="Thời gian vuốt (ms)")
    ap.add_argument("--padding-top", type=float, default=0.22, help="Tỉ lệ padding trên (0-1)")
    ap.add_argument("--padding-bottom", type=float, default=0.18, help="Tỉ lệ padding dưới (0-1)")
    ap.add_argument("--overswipe", type=int, default=2, help="Số lần thử thêm khi trùng ảnh (chạm đáy)")
    ap.add_argument("--serial", default=None, help="ADB serial (ví dụ emulator-5554)")
    ap.add_argument("--tune", action="store_true", help="Tối ưu emulator (tắt animation, kéo dài timeout)")
    ap.add_argument("--continue-numbering", action="store_true", default=True, help="Tự động tiếp số ảnh từ file có sẵn (mặc định: bật)")
    ap.add_argument("--reset-numbering", action="store_true", help="Bắt đầu lại từ số 1 (ghi đè --continue-numbering)")
    
    # Tham số mới cho kênh và chi nhánh
    ap.add_argument("--channel", help="Kênh (vd: shopeefood, grabfood)")
    ap.add_argument("--branch", help="Mã chi nhánh (vd: BC, LBB, LVT, PVC)")
    ap.add_argument("--manage", action="store_true", help="Vào menu quản lý kênh và chi nhánh")
    ap.add_argument("--list-channels", action="store_true", help="Hiển thị danh sách kênh")
    
    # bật ENTER-stop mặc định; muốn tắt thì thêm --no-interactive-stop
    ap.add_argument("--no-interactive-stop", dest="interactive_stop", action="store_false",
                    help="Tắt chức năng bấm ENTER để dừng")
    ap.set_defaults(interactive_stop=True)
    args = ap.parse_args()
    
    # Khởi tạo manager
    manager = ChannelManager()
    
    # Xử lý các chế độ đặc biệt
    if args.manage:
        management_menu(manager)
        return
    
    if args.list_channels:
        manager.list_channels()
        return

    # Xử lý chọn kênh và chi nhánh
    channel_key = args.channel
    branch_code = args.branch
    
    # Nếu không có tham số, hiển thị menu chọn
    if not channel_key or not branch_code:
        print("Chưa chỉ định kênh và chi nhánh. Chọn từ menu:")
        channel_key, branch_code = interactive_channel_selection(manager)
        if not channel_key or not branch_code:
            print("Hủy bỏ.")
            return
    
    # Validate selection
    valid, msg = manager.validate_selection(channel_key, branch_code)
    if not valid:
        print(f"Lỗi: {msg}")
        return
    
    serial = ensure_device(args.serial)
    if args.tune:
        maybe_tune_device(serial)

    w,h = get_screen_size(serial)
    
    # Tạo folder theo cấu trúc: shots/kênh/chi_nhánh
    channel_name = manager.get_channel_name(channel_key)
    branch_name = manager.get_branch_name(channel_key, branch_code)
    output_dir = os.path.join(args.out, channel_name, branch_name)
    os.makedirs(output_dir, exist_ok=True)

    x = w // 2
    y_start = int(h * (1 - args.padding_bottom))
    y_end   = int(h * args.padding_top)

    print(f"Thiết bị: {serial} | Screen {w}x{h}")
    print(f"Kênh: {channel_name} | Chi nhánh: {branch_name}")
    print(f"Swipe: ({x},{y_start}) -> ({x},{y_end}) in {args.swipe_ms}ms")
    print(f"Lưu ảnh vào: {output_dir}")

    # Xác định số bắt đầu cho ảnh
    channel_short = channel_name.replace("Food", "")
    if args.reset_numbering:
        start_num = 1
        print("🔄 Bắt đầu lại từ số 1")
    elif args.continue_numbering:
        start_num = get_next_image_number(output_dir, branch_code, channel_short)
        if start_num > 1:
            print(f"📂 Tìm thấy {start_num-1} ảnh có sẵn, tiếp tục từ số {start_num}")
        else:
            print("📂 Thư mục trống, bắt đầu từ số 1")
    else:
        start_num = 1
        print("📂 Bắt đầu từ số 1")

    stopper = Stopper(enabled=args.interactive_stop)

    last_hash, stuck, taken = None, 0, 0

    try:
        for i in range(start_num, start_num + args.shots):
            if stopper.should_stop():
                print(">> Dừng theo yêu cầu (ENTER).")
                break

            # Đặt tên file theo quy ước: SốThứTự_MãChiNhánh_Kênh.png
            # Chuyển đổi tên kênh: ShopeeFood -> Shopee, GrabFood -> Grab
            filename = f"{i:02d}_{branch_code}_{channel_short}.png"
            path = os.path.join(output_dir, filename)
            screencap_to_file(path, serial=serial)
            digest = sha256(path)

            if digest == last_hash:
                stuck += 1
                print(f"- Ảnh {i:02d}: trùng với khung trước ({stuck}/{args.overswipe}).")
                if stuck >= args.overswipe:
                    print(f"Hết nội dung (trùng {stuck} lần). Dừng tại {i}.")
                    break
            else:
                stuck = 0
                taken += 1
                print(f"+ Đã chụp: {filename}")

            swipe(x, y_start, x, y_end, args.swipe_ms, serial=serial)
            time.sleep(args.delay)
            last_hash = digest
    except KeyboardInterrupt:
        print("\n>> Dừng do Ctrl+C")
    finally:
        print(f"Hoàn tất: {taken} ảnh trong '{output_dir}'.")

if __name__ == "__main__":
    main()
