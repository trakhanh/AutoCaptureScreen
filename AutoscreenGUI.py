import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog, simpledialog
import threading
import queue
import os
import sys
import re
from Autoscreen import (
    ChannelManager, ensure_device, get_screen_size, maybe_tune_device,
    screencap_to_file, swipe, sha256, get_next_image_number,
    auto_sort_files, get_folder_stats
)
import time
import json
from PIL import Image, ImageTk
import subprocess

# Import Google Drive uploader
try:
    from google_drive_uploader import GoogleDriveUploader
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False
    GoogleDriveUploader = None

# Modern styling
try:
    import ttkthemes  # pyright: ignore[reportMissingModuleSource]
    THEME_AVAILABLE = True
except ImportError:
    THEME_AVAILABLE = False

class AutoscreenGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🚀 AutoScreen Pro - Chụp ảnh tự động thông minh")
        
        # Detect screen size and set appropriate window size
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Calculate optimal window size (80% of screen, but not larger than 1200x800)
        window_width = min(int(screen_width * 0.8), 1200)
        window_height = min(int(screen_height * 0.8), 800)
        
        # Ensure minimum size for usability
        window_width = max(window_width, 720)
        window_height = max(window_height, 500)
        
        # Center the window
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.minsize(720, 500)  # Minimum size for small screens

        # Set window icon
        try:
            if os.path.exists("logo.ico"):
                self.root.iconbitmap("logo.ico")
        except Exception:
            pass  # Ignore if icon can't be loaded

        # Handle window resize with debounce
        self.root.bind('<Configure>', self.on_window_resize)

        # Modern styling - apply after window setup
        self.setup_modern_style()
        self.resize_after_id = None  # For debouncing resize events

        # Variables
        self.manager = ChannelManager()
        self.is_running = False
        self.stop_event = threading.Event()
        self.log_queue = queue.Queue()
        self.start_time = None
        self.last_image_path = None
        self.settings_file = "gui_settings.json"
        self.window_width = window_width
        self.window_height = window_height
        
        # Google Drive uploader
        self.drive_uploader = None
        if GOOGLE_DRIVE_AVAILABLE:
            self.drive_uploader = GoogleDriveUploader()
            self.drive_uploader.set_callbacks(
                log_callback=self.log_message,
                progress_callback=self.on_drive_upload_progress,
                completion_callback=self.on_drive_upload_complete
            )
            self.drive_uploader.load_config()
        
        # Setup GUI
        self.setup_gui()
        
        # Load settings
        self.load_settings()
        
        # Start log processor
        self.process_log_queue()
        
    def setup_gui(self):
        # Configure root window grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Create canvas and scrollbar for scrollable content
        canvas = tk.Canvas(self.root, highlightthickness=0, bg='#f8f9fa')
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        # Configure scrolling
        def configure_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        def configure_canvas_width(event):
            # Make the frame fill the canvas width
            canvas_width = event.width
            canvas.itemconfig(canvas_window, width=canvas_width)
        
        self.scrollable_frame.bind("<Configure>", configure_scroll_region)
        canvas.bind("<Configure>", configure_canvas_width)
        
        # Create window in canvas and store reference
        canvas_window = canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Bind mouse wheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Store canvas reference for later use
        self.main_canvas = canvas
        self.canvas_window = canvas_window
        
        # Configure scrollable frame to expand
        self.scrollable_frame.columnconfigure(0, weight=1)
        
        # Main frame inside scrollable area - fill entire width
        main_frame = ttk.Frame(self.scrollable_frame, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights for main frame
        main_frame.columnconfigure(1, weight=1)
        
        # Logo and Title frame
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        header_frame.columnconfigure(1, weight=1)
        
        # Logo
        try:
            if os.path.exists("logo.jpg"):
                logo_image = Image.open("logo.jpg")
                # Resize logo to fit header
                logo_image = logo_image.resize((60, 60), Image.Resampling.LANCZOS)
                self.logo_photo = ImageTk.PhotoImage(logo_image)
                logo_label = ttk.Label(header_frame, image=self.logo_photo)
                logo_label.grid(row=0, column=0, padx=(0, 15))
        except Exception:
            pass  # Ignore if logo can't be loaded
        
        # Title with modern styling
        title_label = ttk.Label(header_frame, text="🚀 AutoScreen Review",
                               font=("Segoe UI", 18, "bold"), foreground="#2c3e50")
        title_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))

        subtitle_label = ttk.Label(header_frame, text="Chụp ảnh tự động thông minh",
                                  font=("Segoe UI", 10), foreground="#7f8c8d")
        subtitle_label.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(0, 5))
        
        # Channel selection
        ttk.Label(main_frame, text="Kênh:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.channel_var = tk.StringVar()
        self.channel_combo = ttk.Combobox(main_frame, textvariable=self.channel_var, 
                                         state="readonly", width=30)
        self.channel_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        self.channel_combo.bind('<<ComboboxSelected>>', self.on_channel_change)
        
        # Branch selection
        ttk.Label(main_frame, text="Chi nhánh:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.branch_var = tk.StringVar()
        self.branch_combo = ttk.Combobox(main_frame, textvariable=self.branch_var, 
                                        state="readonly", width=30)
        self.branch_combo.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Output directory
        ttk.Label(main_frame, text="Thư mục lưu:").grid(row=3, column=0, sticky=tk.W, pady=5)
        output_frame = ttk.Frame(main_frame)
        output_frame.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5)
        output_frame.columnconfigure(0, weight=1)
        
        self.output_var = tk.StringVar(value="shots")
        self.output_entry = ttk.Entry(output_frame, textvariable=self.output_var)
        self.output_entry.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        browse_btn = tk.Button(output_frame, text="📁 Chọn", command=self.browse_output,
                               bg='#6c757d', fg='white', font=('Segoe UI', 8, 'bold'),
                               relief='raised', bd=1, padx=6, pady=2,
                               activebackground='#5a6268', activeforeground='white')
        browse_btn.grid(row=0, column=1, padx=(5, 0))
        
        # Settings frame with compact design for small screens
        settings_frame = ttk.LabelFrame(main_frame, text="⚙️ Cài đặt nâng cao", style="Card.TLabelframe", padding="10")
        settings_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        settings_frame.columnconfigure(0, weight=1)
        
        # Create a more compact settings layout
        settings_grid = ttk.Frame(settings_frame)
        settings_grid.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        settings_grid.columnconfigure(1, weight=1)
        settings_grid.columnconfigure(3, weight=1)
        settings_grid.columnconfigure(5, weight=1)
        
        # Row 1: Basic settings
        ttk.Label(settings_grid, text="Số ảnh:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5), pady=2)
        self.shots_var = tk.IntVar(value=100)
        shots_spin = ttk.Spinbox(settings_grid, from_=1, to=1000, textvariable=self.shots_var, width=8)
        shots_spin.grid(row=0, column=1, sticky=tk.W, padx=(0, 10), pady=2)
        
        ttk.Label(settings_grid, text="Delay(s):").grid(row=0, column=2, sticky=tk.W, padx=(0, 5), pady=2)
        self.delay_var = tk.DoubleVar(value=1.2)
        delay_spin = ttk.Spinbox(settings_grid, from_=0.1, to=10.0, increment=0.1, 
                                textvariable=self.delay_var, width=8)
        delay_spin.grid(row=0, column=3, sticky=tk.W, padx=(0, 10), pady=2)
        
        ttk.Label(settings_grid, text="Vuốt(ms):").grid(row=0, column=4, sticky=tk.W, padx=(0, 5), pady=2)
        self.swipe_var = tk.IntVar(value=550)
        swipe_spin = ttk.Spinbox(settings_grid, from_=100, to=2000, increment=50, 
                                textvariable=self.swipe_var, width=8)
        swipe_spin.grid(row=0, column=5, sticky=tk.W, pady=2)
        
        # Row 2: Advanced settings
        ttk.Label(settings_grid, text="Trên:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=2)
        self.padding_top_var = tk.DoubleVar(value=0.22)
        padding_top_spin = ttk.Spinbox(settings_grid, from_=0.0, to=1.0, increment=0.01, 
                                      textvariable=self.padding_top_var, width=8, format="%.2f")
        padding_top_spin.grid(row=1, column=1, sticky=tk.W, padx=(0, 10), pady=2)
        
        ttk.Label(settings_grid, text="Dưới:").grid(row=1, column=2, sticky=tk.W, padx=(0, 5), pady=2)
        self.padding_bottom_var = tk.DoubleVar(value=0.18)
        padding_bottom_spin = ttk.Spinbox(settings_grid, from_=0.0, to=1.0, increment=0.01, 
                                         textvariable=self.padding_bottom_var, width=8, format="%.2f")
        padding_bottom_spin.grid(row=1, column=3, sticky=tk.W, padx=(0, 10), pady=2)
        
        ttk.Label(settings_grid, text="Thử lại:").grid(row=1, column=4, sticky=tk.W, padx=(0, 5), pady=2)
        self.overswipe_var = tk.IntVar(value=2)
        overswipe_spin = ttk.Spinbox(settings_grid, from_=1, to=10, textvariable=self.overswipe_var, width=8)
        overswipe_spin.grid(row=1, column=5, sticky=tk.W, pady=2)
        
        # Row 3: Checkboxes
        checkbox_frame = ttk.Frame(settings_frame)
        checkbox_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        self.tune_var = tk.BooleanVar()
        tune_check = ttk.Checkbutton(checkbox_frame, text="Tối ưu thiết bị", 
                                    variable=self.tune_var)
        tune_check.pack(side=tk.LEFT, padx=(0, 20))
        
        self.continue_numbering_var = tk.BooleanVar(value=True)
        continue_check = ttk.Checkbutton(checkbox_frame, text="Tiếp số ảnh", 
                                       variable=self.continue_numbering_var)
        continue_check.pack(side=tk.LEFT)
        
        # Preset buttons with custom styling
        preset_frame = ttk.Frame(settings_frame)
        preset_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)

        tk.Button(preset_frame, text="💾 Lưu preset", command=self.save_preset,
                 bg='#28a745', fg='white', font=('Segoe UI', 8, 'bold'),
                 relief='raised', bd=1, padx=6, pady=3,
                 activebackground='#218838', activeforeground='white').pack(side=tk.LEFT, padx=2)

        tk.Button(preset_frame, text="📂 Tải preset", command=self.load_preset,
                 bg='#007bff', fg='white', font=('Segoe UI', 8, 'bold'),
                 relief='raised', bd=1, padx=6, pady=3,
                 activebackground='#0069d9', activeforeground='white').pack(side=tk.LEFT, padx=2)

        tk.Button(preset_frame, text="🔄 Reset", command=self.reset_settings,
                 bg='#6c757d', fg='white', font=('Segoe UI', 8, 'bold'),
                 relief='raised', bd=1, padx=6, pady=3,
                 activebackground='#5a6268', activeforeground='white').pack(side=tk.LEFT, padx=2)
        
        # Control buttons with modern spacing
        button_frame = ttk.Frame(main_frame, style="Card.TFrame")
        button_frame.grid(row=5, column=0, columnspan=2, pady=20, padx=10)
        
        # Primary action buttons with custom styling
        self.start_btn = tk.Button(button_frame, text="▶ Bắt đầu chụp", command=self.start_capture,
                                  bg='#28a745', fg='white', font=('Segoe UI', 9, 'bold'),
                                  relief='raised', bd=2, padx=12, pady=6,
                                  activebackground='#218838', activeforeground='white')
        self.start_btn.pack(side=tk.LEFT, padx=8, pady=5)

        self.stop_btn = tk.Button(button_frame, text="⏹ Dừng", command=self.stop_capture,
                                 state="disabled", bg='#dc3545', fg='white',
                                 font=('Segoe UI', 9, 'bold'), relief='raised', bd=2,
                                 padx=12, pady=6, activebackground='#c82333',
                                 activeforeground='white')
        self.stop_btn.pack(side=tk.LEFT, padx=8, pady=5)

        # Separator
        ttk.Separator(button_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=5)

        # Secondary action buttons with custom styling
        manage_btn = tk.Button(button_frame, text="⚙ Quản lý kênh", command=self.open_management,
                              bg='#495057', fg='white', font=('Segoe UI', 9, 'bold'),
                              relief='raised', bd=2, padx=10, pady=6,
                              activebackground='#6c757d', activeforeground='white')
        manage_btn.pack(side=tk.LEFT, padx=5, pady=5)

        sort_btn = tk.Button(button_frame, text="🔧 Sắp xếp file", command=self.sort_files,
                            bg='#495057', fg='white', font=('Segoe UI', 9, 'bold'),
                            relief='raised', bd=2, padx=10, pady=6,
                            activebackground='#6c757d', activeforeground='white')
        sort_btn.pack(side=tk.LEFT, padx=5, pady=5)

        refresh_btn = tk.Button(button_frame, text="🔄 Làm mới", command=self.refresh_data,
                               bg='#495057', fg='white', font=('Segoe UI', 9, 'bold'),
                               relief='raised', bd=2, padx=10, pady=6,
                               activebackground='#6c757d', activeforeground='white')
        refresh_btn.pack(side=tk.LEFT, padx=5, pady=5)

        self.open_folder_btn = tk.Button(button_frame, text="📁 Mở thư mục", command=self.open_result_folder,
                                        state="disabled", bg='#007bff', fg='white',
                                        font=('Segoe UI', 9, 'bold'), relief='raised', bd=2,
                                        padx=10, pady=6, activebackground='#0069d9',
                                        activeforeground='white')
        self.open_folder_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Progress and stats frame with modern design
        progress_frame = ttk.LabelFrame(main_frame, text="📊 Tiến trình", style="Card.TLabelframe", padding="10")
        progress_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        progress_frame.columnconfigure(0, weight=1)
        
        # Progress info
        self.progress_var = tk.StringVar(value="Sẵn sàng")
        progress_label = ttk.Label(progress_frame, textvariable=self.progress_var)
        progress_label.grid(row=0, column=0, sticky=tk.W)
        
        # Timer
        self.timer_var = tk.StringVar(value="")
        timer_label = ttk.Label(progress_frame, textvariable=self.timer_var)
        timer_label.grid(row=0, column=1, sticky=tk.E)
        
        # Progress bar with modern styling
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate',
                                          style='Modern.Horizontal.TProgressbar')
        self.progress_bar.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=8)
        
        # Main content area with tabs - responsive height
        main_notebook = ttk.Notebook(main_frame)
        main_notebook.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        main_frame.rowconfigure(7, weight=1)
        
        # Ensure the scrollable frame expands properly
        self.scrollable_frame.rowconfigure(0, weight=1)

        # Log tab
        log_tab = ttk.Frame(main_notebook)
        main_notebook.add(log_tab, text="📝 Log")
        log_tab.columnconfigure(0, weight=1)
        log_tab.rowconfigure(0, weight=1)

        log_frame = ttk.LabelFrame(log_tab, text="Hoạt động", style="Card.TLabelframe", padding="5")
        log_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=2, pady=2)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        # Responsive log height based on screen size
        log_height = max(8, min(15, self.window_height // 40))
        self.log_text = scrolledtext.ScrolledText(log_frame, height=log_height, width=60, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Preview tab
        preview_tab = ttk.Frame(main_notebook)
        main_notebook.add(preview_tab, text="🖼️ Xem")
        preview_tab.columnconfigure(0, weight=1)
        preview_tab.rowconfigure(0, weight=1)

        preview_frame = ttk.LabelFrame(preview_tab, text="Ảnh cuối", style="Card.TLabelframe", padding="5")
        preview_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=2, pady=2)
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)

        # Image preview
        self.preview_label = ttk.Label(preview_frame, text="Chưa có ảnh", anchor="center")
        self.preview_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Preview controls with custom styled buttons
        preview_controls = ttk.Frame(preview_frame)
        preview_controls.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)

        tk.Button(preview_controls, text="🔍 Phóng to", command=self.view_full_image,
                 bg='#6c757d', fg='white', font=('Segoe UI', 8, 'bold'),
                 relief='raised', bd=1, padx=8, pady=4,
                 activebackground='#5a6268', activeforeground='white').pack(side=tk.LEFT, padx=2)

        tk.Button(preview_controls, text="📂 Mở file", command=self.open_current_image,
                 bg='#007bff', fg='white', font=('Segoe UI', 8, 'bold'),
                 relief='raised', bd=1, padx=8, pady=4,
                 activebackground='#0069d9', activeforeground='white').pack(side=tk.LEFT, padx=2)

        tk.Button(preview_controls, text="📊 Làm mới thống kê", command=self.refresh_stats,
                 bg='#28a745', fg='white', font=('Segoe UI', 8, 'bold'),
                 relief='raised', bd=1, padx=8, pady=4,
                 activebackground='#218838', activeforeground='white').pack(side=tk.LEFT, padx=2)

        # Stats
        stats_frame = ttk.Frame(preview_frame)
        stats_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        stats_frame.columnconfigure(1, weight=1)

        ttk.Label(stats_frame, text="Tổng ảnh:").grid(row=0, column=0, sticky=tk.W, padx=2)
        self.total_images_var = tk.StringVar(value="0")
        ttk.Label(stats_frame, textvariable=self.total_images_var).grid(row=0, column=1, sticky=tk.W, padx=2)

        ttk.Label(stats_frame, text="Tốc độ:").grid(row=1, column=0, sticky=tk.W, padx=2)
        self.speed_var = tk.StringVar(value="0 ảnh/phút")
        ttk.Label(stats_frame, textvariable=self.speed_var).grid(row=1, column=1, sticky=tk.W, padx=2)

        ttk.Label(stats_frame, text="Kích thước:").grid(row=2, column=0, sticky=tk.W, padx=2)
        self.folder_size_var = tk.StringVar(value="0 MB")
        ttk.Label(stats_frame, textvariable=self.folder_size_var).grid(row=2, column=1, sticky=tk.W, padx=2)

        ttk.Label(stats_frame, text="File thiếu:").grid(row=3, column=0, sticky=tk.W, padx=2)
        self.missing_files_var = tk.StringVar(value="0")
        ttk.Label(stats_frame, textvariable=self.missing_files_var).grid(row=3, column=1, sticky=tk.W, padx=2)

        # Google Drive tab
        if GOOGLE_DRIVE_AVAILABLE:
            drive_tab = ttk.Frame(main_notebook)
            main_notebook.add(drive_tab, text="☁️ Drive")
            drive_tab.columnconfigure(0, weight=1)
            drive_tab.rowconfigure(0, weight=1)
            self.setup_drive_tab(drive_tab)

        # Image Management tab
        image_mgmt_tab = ttk.Frame(main_notebook)
        main_notebook.add(image_mgmt_tab, text="📁 Files")
        image_mgmt_tab.columnconfigure(0, weight=1)
        image_mgmt_tab.rowconfigure(0, weight=1)

        # File list area
        file_list_frame = ttk.LabelFrame(image_mgmt_tab, text="Danh sách ảnh", style="Card.TLabelframe", padding="5")
        file_list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=2, pady=2)
        file_list_frame.columnconfigure(0, weight=1)
        file_list_frame.rowconfigure(1, weight=1)

        # File list controls with custom styled buttons
        list_controls = ttk.Frame(file_list_frame)
        list_controls.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)

        tk.Button(list_controls, text="🔄 Làm mới", command=self.refresh_file_list,
                 bg='#28a745', fg='white', font=('Segoe UI', 8, 'bold'),
                 relief='raised', bd=1, padx=8, pady=4,
                 activebackground='#218838', activeforeground='white').pack(side=tk.LEFT, padx=2)

        tk.Button(list_controls, text="🗑️ Xóa file", command=self.delete_selected_file,
                 bg='#dc3545', fg='white', font=('Segoe UI', 8, 'bold'),
                 relief='raised', bd=1, padx=8, pady=4,
                 activebackground='#c82333', activeforeground='white').pack(side=tk.LEFT, padx=2)

        tk.Button(list_controls, text="🔧 Sắp xếp file", command=self.sort_files,
                 bg='#6c757d', fg='white', font=('Segoe UI', 8, 'bold'),
                 relief='raised', bd=1, padx=8, pady=4,
                 activebackground='#5a6268', activeforeground='white').pack(side=tk.LEFT, padx=2)

        # File listbox with scrollbar
        list_frame = ttk.Frame(file_list_frame)
        list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        # Responsive listbox height
        listbox_height = max(6, min(12, self.window_height // 50))
        self.file_listbox = tk.Listbox(list_frame, height=listbox_height, selectmode=tk.SINGLE,
                                      font=('Segoe UI', 9))
        self.file_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        file_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        file_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.file_listbox.config(yscrollcommand=file_scrollbar.set)

        self.file_listbox.bind('<<ListboxSelect>>', self.on_file_select)

        # File info and stats
        file_info_frame = ttk.Frame(file_list_frame)
        file_info_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        file_info_frame.columnconfigure(1, weight=1)

        ttk.Label(file_info_frame, text="File đã chọn:").grid(row=0, column=0, sticky=tk.W)
        self.selected_file_var = tk.StringVar(value="Chưa chọn")
        ttk.Label(file_info_frame, textvariable=self.selected_file_var).grid(row=0, column=1, sticky=tk.W, padx=5)

        ttk.Label(file_info_frame, text="Tổng số file:").grid(row=1, column=0, sticky=tk.W)
        self.total_files_var = tk.StringVar(value="0")
        ttk.Label(file_info_frame, textvariable=self.total_files_var).grid(row=1, column=1, sticky=tk.W, padx=5)
        
        # Load initial data
        self.refresh_data()

        # Start timer update
        self.update_timer()
    
    def setup_drive_tab(self, drive_tab):
        """Thiết lập tab Google Drive"""
        # Main frame
        main_frame = ttk.Frame(drive_tab, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(0, weight=1)
        
        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="📊 Trạng thái Google Drive", style="Card.TLabelframe", padding="10")
        status_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        status_frame.columnconfigure(1, weight=1)
        
        # Drive status
        ttk.Label(status_frame, text="Trạng thái:").grid(row=0, column=0, sticky=tk.W, padx=2)
        self.drive_status_var = tk.StringVar(value="Chưa xác thực")
        ttk.Label(status_frame, textvariable=self.drive_status_var, foreground="red").grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # Upload stats
        ttk.Label(status_frame, text="Đã upload:").grid(row=1, column=0, sticky=tk.W, padx=2)
        self.drive_uploaded_var = tk.StringVar(value="0 file")
        ttk.Label(status_frame, textvariable=self.drive_uploaded_var).grid(row=1, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(status_frame, text="Hàng đợi:").grid(row=2, column=0, sticky=tk.W, padx=2)
        self.drive_queue_var = tk.StringVar(value="0 file")
        ttk.Label(status_frame, textvariable=self.drive_queue_var).grid(row=2, column=1, sticky=tk.W, padx=5)
        
        # Configuration frame
        config_frame = ttk.LabelFrame(main_frame, text="⚙️ Cấu hình Upload", style="Card.TLabelframe", padding="10")
        config_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        config_frame.columnconfigure(1, weight=1)
        
        # Auto upload checkbox
        self.drive_auto_upload_var = tk.BooleanVar()
        ttk.Checkbutton(config_frame, text="Tự động upload sau khi chụp", 
                       variable=self.drive_auto_upload_var, 
                       command=self.on_drive_config_change).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        # Folder structure options
        self.drive_date_folders_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_frame, text="Tạo folder theo ngày", 
                       variable=self.drive_date_folders_var,
                       command=self.on_drive_config_change).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        self.drive_channel_folders_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_frame, text="Tạo folder riêng cho từng kênh", 
                       variable=self.drive_channel_folders_var,
                       command=self.on_drive_config_change).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        self.drive_branch_folders_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_frame, text="Tạo folder riêng cho từng chi nhánh", 
                       variable=self.drive_branch_folders_var,
                       command=self.on_drive_config_change).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        # Custom folder mapping option
        self.drive_use_custom_mapping_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(config_frame, text="Sử dụng folder tùy chỉnh cho chi nhánh", 
                       variable=self.drive_use_custom_mapping_var,
                       command=self.on_drive_config_change).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=2)
        
        # Root folder configuration
        ttk.Label(config_frame, text="Folder gốc:").grid(row=5, column=0, sticky=tk.W, padx=2)
        
        # Frame for root folder config
        root_folder_frame = ttk.Frame(config_frame)
        root_folder_frame.grid(row=5, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
        root_folder_frame.columnconfigure(0, weight=1)
        
        self.drive_root_folder_var = tk.StringVar(value="AutoScreen Photos")
        root_folder_entry = ttk.Entry(root_folder_frame, textvariable=self.drive_root_folder_var, width=25)
        root_folder_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        root_folder_entry.bind('<FocusOut>', self.on_drive_config_change)
        
        # Checkbox for using folder ID
        self.drive_use_root_folder_id_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(root_folder_frame, text="Dùng ID", 
                       variable=self.drive_use_root_folder_id_var,
                       command=self.on_drive_config_change).grid(row=0, column=1, sticky=tk.W)
        
        # Action buttons frame
        action_frame = ttk.Frame(config_frame)
        action_frame.grid(row=6, column=0, columnspan=2, pady=10)
        
        # Authentication button
        self.drive_auth_btn = tk.Button(action_frame, text="🔐 Xác thực Google Drive", 
                                       command=self.authenticate_drive,
                                       bg='#007bff', fg='white', font=('Segoe UI', 9, 'bold'),
                                       relief='raised', bd=2, padx=12, pady=6,
                                       activebackground='#0069d9', activeforeground='white')
        self.drive_auth_btn.pack(side=tk.LEFT, padx=5)
        
        # Upload current folder button
        self.drive_upload_folder_btn = tk.Button(action_frame, text="📤 Upload folder hiện tại", 
                                                command=self.upload_current_folder,
                                                bg='#28a745', fg='white', font=('Segoe UI', 9, 'bold'),
                                                relief='raised', bd=2, padx=12, pady=6,
                                                activebackground='#218838', activeforeground='white',
                                                state="disabled")
        self.drive_upload_folder_btn.pack(side=tk.LEFT, padx=5)
        
        # Stop upload button
        self.drive_stop_btn = tk.Button(action_frame, text="⏹ Dừng upload", 
                                       command=self.stop_drive_upload,
                                       bg='#dc3545', fg='white', font=('Segoe UI', 9, 'bold'),
                                       relief='raised', bd=2, padx=12, pady=6,
                                       activebackground='#c82333', activeforeground='white',
                                       state="disabled")
        self.drive_stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Custom mapping button
        self.drive_setup_mapping_btn = tk.Button(action_frame, text="🗂️ Cấu hình folder", 
                                                command=self.setup_custom_mapping,
                                                bg='#6c757d', fg='white', font=('Segoe UI', 9, 'bold'),
                                                relief='raised', bd=2, padx=12, pady=6,
                                                activebackground='#5a6268', activeforeground='white',
                                                state="disabled")
        self.drive_setup_mapping_btn.pack(side=tk.LEFT, padx=5)
        
        # Debug button
        self.drive_debug_btn = tk.Button(action_frame, text="🔍 Debug", 
                                        command=self.debug_drive_structure,
                                        bg='#ffc107', fg='black', font=('Segoe UI', 9, 'bold'),
                                        relief='raised', bd=2, padx=12, pady=6,
                                        activebackground='#e0a800', activeforeground='black',
                                        state="disabled")
        self.drive_debug_btn.pack(side=tk.LEFT, padx=5)
        
        # Scan folders button
        self.drive_scan_btn = tk.Button(action_frame, text="📋 Scan", 
                                       command=self.scan_drive_folders,
                                       bg='#17a2b8', fg='white', font=('Segoe UI', 9, 'bold'),
                                       relief='raised', bd=2, padx=12, pady=6,
                                       activebackground='#138496', activeforeground='white',
                                       state="disabled")
        self.drive_scan_btn.pack(side=tk.LEFT, padx=5)
        
        # Reset stats button
        self.drive_reset_btn = tk.Button(action_frame, text="🔄 Reset", 
                                        command=self.reset_drive_stats,
                                        bg='#fd7e14', fg='white', font=('Segoe UI', 9, 'bold'),
                                        relief='raised', bd=2, padx=12, pady=6,
                                        activebackground='#e8590c', activeforeground='white',
                                        state="disabled")
        self.drive_reset_btn.pack(side=tk.LEFT, padx=5)
        
        # Load initial config
        self.load_drive_config()
        self.update_drive_status()
    
    def load_drive_config(self):
        """Load cấu hình Google Drive"""
        if not self.drive_uploader:
            return
        
        self.drive_auto_upload_var.set(self.drive_uploader.auto_upload)
        self.drive_date_folders_var.set(self.drive_uploader.create_date_folders)
        self.drive_channel_folders_var.set(self.drive_uploader.create_channel_folders)
        self.drive_branch_folders_var.set(self.drive_uploader.create_branch_folders)
        self.drive_use_custom_mapping_var.set(self.drive_uploader.use_custom_mapping)
        self.drive_use_root_folder_id_var.set(self.drive_uploader.use_root_folder_id)
        self.drive_root_folder_var.set(self.drive_uploader.root_folder_name)
    
    def on_drive_config_change(self, event=None):
        """Xử lý khi thay đổi cấu hình Google Drive"""
        if not self.drive_uploader:
            return
        
        self.drive_uploader.configure_upload(
            auto_upload=self.drive_auto_upload_var.get(),
            create_date_folders=self.drive_date_folders_var.get(),
            create_channel_folders=self.drive_channel_folders_var.get(),
            create_branch_folders=self.drive_branch_folders_var.get(),
            use_custom_mapping=self.drive_use_custom_mapping_var.get(),
            use_root_folder_id=self.drive_use_root_folder_id_var.get(),
            root_folder_name=self.drive_root_folder_var.get()
        )
        self.drive_uploader.save_config()
    
    def authenticate_drive(self):
        """Xác thực Google Drive"""
        if not self.drive_uploader:
            messagebox.showerror("Lỗi", "Google Drive API không có sẵn!")
            return
        
        def auth_worker():
            try:
                self.log_message("🔐 Đang xác thực Google Drive...")
                success = self.drive_uploader.authenticate()
                if success:
                    self.root.after(0, lambda: [
                        self.update_drive_status(),
                        messagebox.showinfo("Thành công", "Đã xác thực Google Drive thành công!")
                    ])
                else:
                    self.root.after(0, lambda: messagebox.showerror("Lỗi", "Xác thực Google Drive thất bại!"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Lỗi", f"Lỗi xác thực: {e}"))
        
        threading.Thread(target=auth_worker, daemon=True).start()
    
    def upload_current_folder(self):
        """Upload folder hiện tại lên Google Drive"""
        channel_key, branch_code = self.get_selected_channel_branch()
        if not channel_key or not branch_code:
            messagebox.showerror("Lỗi", "Vui lòng chọn kênh và chi nhánh!")
            return
        
        if not self.drive_uploader or not self.drive_uploader.service:
            messagebox.showerror("Lỗi", "Vui lòng xác thực Google Drive trước!")
            return
        
        # Tạo đường dẫn thư mục
        channel_name = self.manager.get_channel_name(channel_key)
        branch_name = self.manager.get_branch_name(channel_key, branch_code)
        output_dir = os.path.join(self.output_var.get(), channel_name, branch_name)
        
        if not os.path.exists(output_dir):
            messagebox.showwarning("Cảnh báo", f"Thư mục {output_dir} không tồn tại!")
            return
        
        # Pattern để lọc file
        channel_short = channel_name.replace("Food", "")
        import re
        pattern = re.compile(rf"(\d+)_{re.escape(branch_code)}_{re.escape(channel_short)}\.png$", re.IGNORECASE)
        
        # Upload folder với branch_code thay vì branch_name
        files_added = self.drive_uploader.upload_folder_contents(output_dir, channel_name, branch_code, pattern)
        
        if files_added > 0:
            self.drive_uploader.start_upload_worker()
            self.drive_stop_btn.config(state="normal")
            self.drive_upload_folder_btn.config(state="disabled")
            messagebox.showinfo("Bắt đầu", f"Đã bắt đầu upload {files_added} file!")
        else:
            messagebox.showinfo("Thông báo", "Không có file nào để upload!")
    
    def stop_drive_upload(self):
        """Dừng upload Google Drive"""
        if self.drive_uploader:
            self.drive_uploader.stop_upload_worker()
            self.drive_stop_btn.config(state="disabled")
            self.drive_upload_folder_btn.config(state="normal")
            self.log_message("⏹ Đã dừng upload Google Drive")
    
    def on_drive_upload_progress(self, success, upload_item):
        """Callback khi có tiến trình upload"""
        filename = os.path.basename(upload_item['file_path'])
        if success:
            self.log_message(f"✅ Đã upload: {filename}")
        else:
            self.log_message(f"❌ Upload thất bại: {filename}")
        
        self.root.after(0, self.update_drive_status)
    
    def on_drive_upload_complete(self, stats):
        """Callback khi hoàn thành upload"""
        # Reset current session sau khi upload xong
        if self.drive_uploader:
            self.drive_uploader.upload_stats['current_session'] = 0
            self.drive_uploader.save_config()
        
        self.root.after(0, lambda: [
            self.update_drive_status(),
            self.drive_stop_btn.config(state="disabled"),
            self.drive_upload_folder_btn.config(state="normal"),
            messagebox.showinfo("Hoàn thành", 
                              f"Upload hoàn thành!\n"
                              f"Thành công: {stats['current_session']} file\n"
                              f"Tổng cộng: {stats['total_uploaded']} file")
        ])
    
    def setup_custom_mapping(self):
        """Mở dialog để cấu hình custom folder mapping"""
        if not self.drive_uploader or not self.drive_uploader.service:
            messagebox.showerror("Lỗi", "Vui lòng xác thực Google Drive trước!")
            return
        
        CustomMappingDialog(self.root, self.drive_uploader, self.manager, self.log_message)
    
    def debug_drive_structure(self):
        """Debug cấu trúc Google Drive"""
        if not self.drive_uploader or not self.drive_uploader.service:
            messagebox.showerror("Lỗi", "Vui lòng xác thực Google Drive trước!")
            return
        
        self.drive_uploader.debug_folder_structure()
    
    def update_drive_status(self):
        """Cập nhật trạng thái Google Drive"""
        if not self.drive_uploader:
            self.drive_status_var.set("Không có sẵn")
            return
        
        if self.drive_uploader.service:
            self.drive_status_var.set("✅ Đã xác thực")
            self.drive_upload_folder_btn.config(state="normal")
            self.drive_setup_mapping_btn.config(state="normal")
            self.drive_debug_btn.config(state="normal")
            self.drive_scan_btn.config(state="normal")
            self.drive_reset_btn.config(state="normal")
        else:
            self.drive_status_var.set("❌ Chưa xác thực")
            self.drive_upload_folder_btn.config(state="disabled")
            self.drive_setup_mapping_btn.config(state="disabled")
            self.drive_debug_btn.config(state="disabled")
            self.drive_scan_btn.config(state="disabled")
            self.drive_reset_btn.config(state="disabled")
        
        status = self.drive_uploader.get_upload_status()
        stats = status['stats']
        
        self.drive_uploaded_var.set(f"{stats['total_uploaded']} file")
        self.drive_queue_var.set(f"{status['queue_size']} file")
        
        if status['is_uploading']:
            self.drive_stop_btn.config(state="normal")
            self.drive_upload_folder_btn.config(state="disabled")
        else:
            self.drive_stop_btn.config(state="disabled")
            if self.drive_uploader.service:
                self.drive_upload_folder_btn.config(state="normal")

    def setup_modern_style(self):
        """Setup modern styling for the application"""
        try:
            # Try to use modern theme if available
            if THEME_AVAILABLE:
                self.style = ttkthemes.ThemedStyle(self.root)
                # Try different modern themes
                available_themes = self.style.theme_names()
                modern_themes = ['arc', 'yaru', 'breeze', 'adapta', 'plastik', 'clam']
                for theme in modern_themes:
                    if theme in available_themes:
                        self.style.set_theme(theme)
                        break
                else:
                    # Fallback to default
                    self.style = ttk.Style()
            else:
                self.style = ttk.Style()

            # Configure modern colors and fonts
            self.style.configure('TFrame', background='#f8f9fa')
            self.style.configure('TLabel', background='#f8f9fa', font=('Segoe UI', 10))
            self.style.configure('TButton', font=('Segoe UI', 9, 'bold'), padding=6)
            self.style.configure('TEntry', font=('Segoe UI', 10), padding=4)
            self.style.configure('TCombobox', font=('Segoe UI', 10), padding=4)
            self.style.configure('TSpinbox', font=('Segoe UI', 10), padding=4)
            self.style.configure('TCheckbutton', font=('Segoe UI', 10), background='#f8f9fa')
            self.style.configure('TNotebook', background='#f8f9fa')
            self.style.configure('TNotebook.Tab', font=('Segoe UI', 9, 'bold'), padding=[10, 5])

            # Custom button styles with high contrast and clear visibility
            # Force override any theme styles
            try:
                # Reset to default style first to ensure our styles take precedence
                default_style = ttk.Style()
                default_style.configure('TButton', font=('Segoe UI', 9, 'bold'), padding=6)
            except:
                pass

            # Primary button (Start) - Bright Green with high contrast
            self.style.configure('Primary.TButton',
                               font=('Segoe UI', 9, 'bold'),
                               background='#28a745',
                               foreground='#ffffff',  # Pure white text
                               borderwidth=2,
                               relief='raised',
                               bordercolor='#1e7e34',
                               lightcolor='#28a745',
                               darkcolor='#1e7e34')
            self.style.map('Primary.TButton',
                background=[('active', '#218838'), ('pressed', '#1e7e34'), ('hover', '#218838')],
                foreground=[('active', '#ffffff'), ('pressed', '#ffffff'), ('hover', '#ffffff')],
                bordercolor=[('active', '#1e7e34'), ('pressed', '#1e7e34'), ('hover', '#1e7e34')],
                relief=[('pressed', 'sunken'), ('!pressed', 'raised')])

            # Danger button (Stop) - Bright Red with high contrast
            self.style.configure('Danger.TButton',
                               font=('Segoe UI', 9, 'bold'),
                               background='#dc3545',
                               foreground='#ffffff',  # Pure white text
                               borderwidth=2,
                               relief='raised',
                               bordercolor='#bd2130',
                               lightcolor='#dc3545',
                               darkcolor='#bd2130')
            self.style.map('Danger.TButton',
                background=[('active', '#c82333'), ('pressed', '#bd2130'), ('hover', '#c82333')],
                foreground=[('active', '#ffffff'), ('pressed', '#ffffff'), ('hover', '#ffffff')],
                bordercolor=[('active', '#bd2130'), ('pressed', '#bd2130'), ('hover', '#bd2130')],
                relief=[('pressed', 'sunken'), ('!pressed', 'raised')])

            # Secondary button (Management, Sort, Refresh) - Dark Gray with white text
            self.style.configure('Secondary.TButton',
                               font=('Segoe UI', 9, 'bold'),
                               background='#495057',  # Darker gray for better contrast
                               foreground='#ffffff',  # Pure white text
                               borderwidth=2,
                               relief='raised',
                               bordercolor='#343a40',
                               lightcolor='#495057',
                               darkcolor='#343a40')
            self.style.map('Secondary.TButton',
                background=[('active', '#6c757d'), ('pressed', '#343a40'), ('hover', '#6c757d')],
                foreground=[('active', '#ffffff'), ('pressed', '#ffffff'), ('hover', '#ffffff')],
                bordercolor=[('active', '#343a40'), ('pressed', '#343a40'), ('hover', '#343a40')],
                relief=[('pressed', 'sunken'), ('!pressed', 'raised')])

            # Info button (Open folder) - Bright Blue with high contrast
            self.style.configure('Info.TButton',
                               font=('Segoe UI', 9, 'bold'),
                               background='#007bff',
                               foreground='#ffffff',  # Pure white text
                               borderwidth=2,
                               relief='raised',
                               bordercolor='#0056b3',
                               lightcolor='#007bff',
                               darkcolor='#0056b3')
            self.style.map('Info.TButton',
                background=[('active', '#0069d9'), ('pressed', '#0056b3'), ('hover', '#0069d9')],
                foreground=[('active', '#ffffff'), ('pressed', '#ffffff'), ('hover', '#ffffff')],
                bordercolor=[('active', '#0056b3'), ('pressed', '#0056b3'), ('hover', '#0056b3')],
                relief=[('pressed', 'sunken'), ('!pressed', 'raised')])

            # Configure LabelFrame with modern card look
            self.style.configure('Card.TLabelframe', background='#ffffff', borderwidth=2,
                               relief='raised', bordercolor='#e9ecef')
            self.style.configure('Card.TLabelframe.Label', background='#ffffff',
                               font=('Segoe UI', 12, 'bold'), foreground='#495057',
                               padding=[10, 5])

            # Card frame style
            self.style.configure('Card.TFrame', background='#ffffff', borderwidth=1,
                               relief='flat')

            # Progress bar styling with modern look
            self.style.configure('Modern.Horizontal.TProgressbar',
                               background='#28a745', troughcolor='#e9ecef',
                               borderwidth=0, lightcolor='#28a745', darkcolor='#28a745')

        except Exception as e:
            # Fallback to basic styling
            self.style = ttk.Style()
            print(f"Style setup error: {e}")

    def on_window_resize(self, event):
        """Handle window resize events with debouncing"""
        if event.widget == self.root:
            # Cancel previous scheduled resize if any
            if self.resize_after_id:
                self.root.after_cancel(self.resize_after_id)

            # Update stored dimensions
            self.window_width = event.width
            self.window_height = event.height

            # Schedule resize with debounce delay (200ms)
            self.resize_after_id = self.root.after(200, lambda: self._perform_resize(event.width, event.height))

    def _perform_resize(self, width, height):
        """Actually perform the resize after debounce delay"""
        try:
            self.adjust_layout_for_size(width, height)
        except AttributeError:
            # Method might not exist yet during initialization
            pass
        finally:
            self.resize_after_id = None

    def adjust_layout_for_size(self, width, height):
        """Adjust layout elements based on window size with smooth transitions"""
        try:
            # Update stored dimensions
            self.window_width = width
            self.window_height = height
            
            # Update canvas scroll region
            if hasattr(self, 'main_canvas'):
                self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
            
            # Adjust image preview size based on window size
            if hasattr(self, 'preview_label'):
                # Responsive preview size: smaller on smaller screens
                if width < 800:  # Small screen
                    max_width, max_height = 150, 120
                elif width < 1000:  # Medium screen
                    max_width, max_height = 200, 150
                else:  # Large screen
                    max_width, max_height = 250, 200

                # Update preview label size if image exists
                if hasattr(self.preview_label, 'image') and self.preview_label.image:
                    try:
                        # Resize preview image proportionally
                        original_image = Image.open(self.last_image_path)
                        original_image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                        photo = ImageTk.PhotoImage(original_image)
                        self.preview_label.config(image=photo)
                        self.preview_label.image = photo
                    except Exception:
                        pass

            # Adjust log text height based on window size with better scaling
            if hasattr(self, 'log_text'):
                log_height = max(6, min(15, height // 40))
                self.log_text.config(height=log_height)

            # Adjust listbox height with better responsive behavior
            if hasattr(self, 'file_listbox'):
                listbox_height = max(4, min(12, height // 50))
                self.file_listbox.config(height=listbox_height)

            # Adjust font sizes and padding for smaller screens
            if width < 800:
                # Extra compact for very small screens
                self.style.configure('TNotebook.Tab', font=('Segoe UI', 8, 'bold'), padding=[6, 3])
                self.style.configure('TLabel', font=('Segoe UI', 9))
                self.style.configure('TButton', font=('Segoe UI', 8, 'bold'), padding=4)
            elif width < 1000:
                # Compact for small screens
                self.style.configure('TNotebook.Tab', font=('Segoe UI', 8, 'bold'), padding=[8, 4])
                self.style.configure('TLabel', font=('Segoe UI', 10))
                self.style.configure('TButton', font=('Segoe UI', 9, 'bold'), padding=5)
            else:
                # Normal for larger screens
                self.style.configure('TNotebook.Tab', font=('Segoe UI', 9, 'bold'), padding=[10, 5])
                self.style.configure('TLabel', font=('Segoe UI', 10))
                self.style.configure('TButton', font=('Segoe UI', 9, 'bold'), padding=6)

        except Exception as e:
            # Silently handle layout adjustment errors
            pass

    def load_settings(self):
        """Load GUI settings from file"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self.shots_var.set(settings.get('shots', 100))
                    self.delay_var.set(settings.get('delay', 1.2))
                    self.swipe_var.set(settings.get('swipe_ms', 550))
                    self.padding_top_var.set(settings.get('padding_top', 0.22))
                    self.padding_bottom_var.set(settings.get('padding_bottom', 0.18))
                    self.overswipe_var.set(settings.get('overswipe', 2))
                    self.tune_var.set(settings.get('tune', False))
                    self.continue_numbering_var.set(settings.get('continue_numbering', True))
                    self.output_var.set(settings.get('output_dir', 'shots'))
        except Exception as e:
            self.log_message(f"Không thể tải settings: {e}")
    
    def save_settings(self):
        """Save current GUI settings to file"""
        try:
            settings = {
                'shots': self.shots_var.get(),
                'delay': self.delay_var.get(),
                'swipe_ms': self.swipe_var.get(),
                'padding_top': self.padding_top_var.get(),
                'padding_bottom': self.padding_bottom_var.get(),
                'overswipe': self.overswipe_var.get(),
                'tune': self.tune_var.get(),
                'continue_numbering': self.continue_numbering_var.get(),
                'output_dir': self.output_var.get()
            }
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            self.log_message(f"Không thể lưu settings: {e}")
    
    def save_preset(self):
        """Save current settings as preset"""
        preset_name = tk.simpledialog.askstring("Lưu preset", "Nhập tên preset:")
        if preset_name:
            try:
                preset_file = f"preset_{preset_name}.json"
                settings = {
                    'shots': self.shots_var.get(),
                    'delay': self.delay_var.get(),
                    'swipe_ms': self.swipe_var.get(),
                    'padding_top': self.padding_top_var.get(),
                    'padding_bottom': self.padding_bottom_var.get(),
                    'overswipe': self.overswipe_var.get(),
                    'tune': self.tune_var.get(),
                    'continue_numbering': self.continue_numbering_var.get()
                }
                with open(preset_file, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, indent=2)
                messagebox.showinfo("Thành công", f"Đã lưu preset '{preset_name}'")
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể lưu preset: {e}")
    
    def load_preset(self):
        """Load settings from preset file"""
        preset_file = filedialog.askopenfilename(
            title="Chọn preset",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if preset_file:
            try:
                with open(preset_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self.shots_var.set(settings.get('shots', 100))
                    self.delay_var.set(settings.get('delay', 1.2))
                    self.swipe_var.set(settings.get('swipe_ms', 550))
                    self.padding_top_var.set(settings.get('padding_top', 0.22))
                    self.padding_bottom_var.set(settings.get('padding_bottom', 0.18))
                    self.overswipe_var.set(settings.get('overswipe', 2))
                    self.tune_var.set(settings.get('tune', False))
                    self.continue_numbering_var.set(settings.get('continue_numbering', True))
                messagebox.showinfo("Thành công", "Đã tải preset")
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể tải preset: {e}")
    
    def reset_settings(self):
        """Reset settings to default values"""
        self.shots_var.set(100)
        self.delay_var.set(1.2)
        self.swipe_var.set(550)
        self.padding_top_var.set(0.22)
        self.padding_bottom_var.set(0.18)
        self.overswipe_var.set(2)
        self.tune_var.set(False)
        self.continue_numbering_var.set(True)
        messagebox.showinfo("Thành công", "Đã reset về cài đặt mặc định")
    
    def update_timer(self):
        """Update timer display"""
        if self.is_running and self.start_time:
            elapsed = time.time() - self.start_time
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            seconds = int(elapsed % 60)
            self.timer_var.set(f"⏱ {hours:02d}:{minutes:02d}:{seconds:02d}")
        elif not self.is_running:
            self.timer_var.set("")
        
        # Schedule next update
        self.root.after(1000, self.update_timer)
    
    def update_preview(self, image_path):
        """Update image preview with smooth transition"""
        try:
            self.last_image_path = image_path
            # Load and resize image
            image = Image.open(image_path)
            # Resize to fit preview area based on current window size
            max_width, max_height = self._get_preview_size()
            image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)

            # Smooth transition by temporarily hiding then showing
            self.preview_label.config(image="", text="Đang tải...")
            self.root.after(50, lambda: self._show_preview_image(photo))

        except Exception as e:
            self.preview_label.config(image="", text=f"Lỗi preview: {e}")

    def _show_preview_image(self, photo):
        """Show preview image with fade-in effect simulation"""
        self.preview_label.config(image=photo, text="")
        self.preview_label.image = photo  # Keep a reference

    def _get_preview_size(self):
        """Get appropriate preview size based on window dimensions"""
        width, height = self.window_width, self.window_height
        if width < 1000:  # Small screen
            return 200, 150
        elif width < 1400:  # Medium screen
            return 250, 200
        else:  # Large screen
            return 300, 250

    def _update_progress_smooth(self, value, percentage):
        """Update progress bar with smooth animation"""
        try:
            # Set progress bar value
            self.progress_bar.config(value=percentage)

            # Update progress text with percentage
            progress_text = f"Đang chụp... ({percentage:.1f}%)"
            self.progress_var.set(progress_text)

        except Exception:
            # Fallback to basic update
            self.progress_bar.config(value=value)

    def view_full_image(self):
        """Xem ảnh phóng to trong cửa sổ riêng"""
        if not self.last_image_path or not os.path.exists(self.last_image_path):
            messagebox.showwarning("Cảnh báo", "Không có ảnh để xem!")
            return

        try:
            # Tạo cửa sổ mới để xem ảnh
            view_window = tk.Toplevel(self.root)
            view_window.title(f"Xem ảnh: {os.path.basename(self.last_image_path)}")
            view_window.geometry("800x600")

            # Load và hiển thị ảnh
            image = Image.open(self.last_image_path)
            # Resize to fit window while maintaining aspect ratio
            image.thumbnail((780, 580), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)

            # Label để hiển thị ảnh
            image_label = ttk.Label(view_window, image=photo)
            image_label.image = photo  # Keep reference
            image_label.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

            # Đặt focus vào cửa sổ mới
            view_window.focus_set()

        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể mở ảnh: {e}")

    def open_current_image(self):
        """Mở file ảnh hiện tại bằng ứng dụng mặc định"""
        if not self.last_image_path or not os.path.exists(self.last_image_path):
            messagebox.showwarning("Cảnh báo", "Không có ảnh để mở!")
            return

        try:
            if os.name == 'nt':  # Windows
                subprocess.run(['start', self.last_image_path], shell=True)
            elif os.name == 'posix':  # macOS and Linux
                subprocess.run(['open' if sys.platform == 'darwin' else 'xdg-open', self.last_image_path])
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể mở file: {e}")

    def refresh_file_list(self):
        """Làm mới danh sách file ảnh"""
        channel_key, branch_code = self.get_selected_channel_branch()

        if not channel_key or not branch_code:
            self.file_listbox.delete(0, tk.END)
            return

        # Tạo đường dẫn thư mục
        channel_name = self.manager.get_channel_name(channel_key)
        branch_name = self.manager.get_branch_name(channel_key, branch_code)
        output_dir = os.path.join(self.output_var.get(), channel_name, branch_name)

        if not os.path.exists(output_dir):
            self.file_listbox.delete(0, tk.END)
            return

        # Lấy danh sách file
        channel_short = channel_name.replace("Food", "")
        pattern = re.compile(rf"(\d+)_{re.escape(branch_code)}_{re.escape(channel_short)}\.png$", re.IGNORECASE)

        files_info = []
        try:
            for filename in os.listdir(output_dir):
                match = pattern.match(filename)
                if match:
                    num = int(match.group(1))
                    files_info.append((num, filename))
        except Exception:
            pass

        # Sắp xếp và hiển thị
        files_info.sort(key=lambda x: x[0])

        self.file_listbox.delete(0, tk.END)
        for num, filename in files_info:
            file_path = os.path.join(output_dir, filename)
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            size_kb = file_size / 1024
            display_text = f"{num:02d}: {filename} ({size_kb:.1f}KB)"
            self.file_listbox.insert(tk.END, display_text)

        # Cập nhật tổng số file
        self.total_files_var.set(str(len(files_info)))

    def delete_selected_file(self):
        """Xóa file được chọn trong danh sách"""
        selection = self.file_listbox.curselection()
        if not selection:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn file để xóa!")
            return

        index = selection[0]
        file_text = self.file_listbox.get(index)

        # Extract filename from display text
        filename = file_text.split(': ')[1].split(' (')[0]

        channel_key, branch_code = self.get_selected_channel_branch()
        if not channel_key or not branch_code:
            return

        channel_name = self.manager.get_channel_name(channel_key)
        branch_name = self.manager.get_branch_name(channel_key, branch_code)
        output_dir = os.path.join(self.output_var.get(), channel_name, branch_name)
        file_path = os.path.join(output_dir, filename)

        if not os.path.exists(file_path):
            messagebox.showerror("Lỗi", "File không tồn tại!")
            return

        if messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn xóa file '{filename}'?"):
            try:
                os.remove(file_path)
                self.log_message(f"🗑️ Đã xóa file: {filename}")
                self.refresh_file_list()
                # Cập nhật thống kê
                self.refresh_stats()

                # Nếu file bị xóa là file đang preview, cập nhật preview
                if self.last_image_path == file_path:
                    self.preview_label.config(image="", text="Ảnh đã bị xóa")
                    self.last_image_path = None

            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể xóa file: {e}")

    def on_file_select(self, event):
        """Xử lý khi chọn file trong listbox"""
        selection = self.file_listbox.curselection()
        if not selection:
            self.selected_file_var.set("Chưa chọn")
            return

        index = selection[0]
        file_text = self.file_listbox.get(index)

        # Extract filename
        filename = file_text.split(': ')[1].split(' (')[0]
        self.selected_file_var.set(filename)

        # Update preview if possible
        channel_key, branch_code = self.get_selected_channel_branch()
        if channel_key and branch_code:
            channel_name = self.manager.get_channel_name(channel_key)
            branch_name = self.manager.get_branch_name(channel_key, branch_code)
            output_dir = os.path.join(self.output_var.get(), channel_name, branch_name)
            file_path = os.path.join(output_dir, filename)

            if os.path.exists(file_path):
                self.update_preview(file_path)

    def open_result_folder(self):
        """Open result folder in file explorer"""
        if self.last_image_path and os.path.exists(self.last_image_path):
            folder_path = os.path.dirname(self.last_image_path)
            try:
                if os.name == 'nt':  # Windows
                    subprocess.run(['explorer', folder_path])
                elif os.name == 'posix':  # macOS and Linux
                    subprocess.run(['open', folder_path] if sys.platform == 'darwin' else ['xdg-open', folder_path])
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể mở thư mục: {e}")
        else:
            messagebox.showwarning("Cảnh báo", "Chưa có thư mục kết quả để mở")
    
    def refresh_data(self):
        """Làm mới dữ liệu kênh và chi nhánh"""
        self.manager = ChannelManager()  # Reload config
        
        # Update channel combo
        channels = [(key, data['name']) for key, data in self.manager.channels.items()]
        self.channel_combo['values'] = [f"{name} ({key})" for key, name in channels]
        
        if channels:
            self.channel_combo.current(0)
            self.on_channel_change()

    def sort_files(self):
        """Sắp xếp lại tên file theo thứ tự số"""
        channel_key, branch_code = self.get_selected_channel_branch()

        if not channel_key or not branch_code:
            messagebox.showerror("Lỗi", "Vui lòng chọn kênh và chi nhánh!")
            return

        # Tạo đường dẫn thư mục
        channel_name = self.manager.get_channel_name(channel_key)
        branch_name = self.manager.get_branch_name(channel_key, branch_code)
        output_dir = os.path.join(self.output_var.get(), channel_name, branch_name)

        if not os.path.exists(output_dir):
            messagebox.showwarning("Cảnh báo", f"Thư mục {output_dir} không tồn tại!")
            return

        # Thực hiện sắp xếp
        self.log_message(f"🔧 Bắt đầu sắp xếp file trong: {output_dir}")

        channel_short = channel_name.replace("Food", "")
        sorted_count, total_files = auto_sort_files(output_dir, branch_code, channel_short,
                                                   log_callback=self.log_message)

        if sorted_count > 0:
            self.log_message(f"✅ Đã sắp xếp lại {sorted_count} file trong tổng số {total_files} file")
            messagebox.showinfo("Thành công", f"Đã sắp xếp lại {sorted_count} file thành công!")
        else:
            self.log_message(f"ℹ️ Không cần sắp xếp. Tổng số file: {total_files}")
            messagebox.showinfo("Thông báo", "File đã được sắp xếp đúng thứ tự!")

        # Cập nhật thống kê
        self.update_folder_stats(channel_key, branch_code)

    def update_folder_stats(self, channel_key, branch_code):
        """Cập nhật thống kê thư mục ảnh"""
        channel_name = self.manager.get_channel_name(channel_key)
        branch_name = self.manager.get_branch_name(channel_key, branch_code)
        output_dir = os.path.join(self.output_var.get(), channel_name, branch_name)

        channel_short = channel_name.replace("Food", "")
        file_count, size_mb, missing_count = get_folder_stats(output_dir, branch_code, channel_short)

        # Cập nhật các biến hiển thị
        self.folder_size_var.set(f"{size_mb:.1f} MB")
        self.missing_files_var.set(str(missing_count))

        # Cập nhật thông tin trong log
        if file_count > 0:
            status_msg = f"📊 Thống kê: {file_count} ảnh ({size_mb:.1f}MB)"
            if missing_count > 0:
                status_msg += f" | ⚠️ Thiếu {missing_count} file"
            else:
                status_msg += " | ✅ Đầy đủ"
            self.log_message(status_msg)

    def on_channel_change(self, event=None):
        """Cập nhật danh sách chi nhánh khi thay đổi kênh"""
        selection = self.channel_var.get()
        if not selection:
            return
            
        # Extract channel key from selection
        channel_key = selection.split('(')[-1].rstrip(')')
        
        if channel_key in self.manager.channels:
            branches = self.manager.channels[channel_key]['branches']
            branch_options = [f"{name} ({code})" for code, name in branches.items()]
            self.branch_combo['values'] = branch_options
            
            if branch_options:
                self.branch_combo.current(0)

        # Cập nhật thống kê khi thay đổi kênh
        self.refresh_stats()
        # Refresh Drive status khi thay đổi kênh
        if self.drive_uploader:
            self.update_drive_status()

    def refresh_stats(self):
        """Làm mới thống kê thư mục"""
        channel_key, branch_code = self.get_selected_channel_branch()
        if channel_key and branch_code:
            self.update_folder_stats(channel_key, branch_code)
            self.refresh_file_list()

    def browse_output(self):
        """Chọn thư mục lưu ảnh"""
        directory = filedialog.askdirectory(initialdir=self.output_var.get())
        if directory:
            self.output_var.set(directory)
    
    def log_message(self, message):
        """Thêm message vào log queue"""
        self.log_queue.put(message)
    
    def process_log_queue(self):
        """Xử lý log queue và cập nhật GUI"""
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_text.insert(tk.END, message + "\n")
                self.log_text.see(tk.END)
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self.process_log_queue)
    
    def get_selected_channel_branch(self):
        """Lấy kênh và chi nhánh được chọn"""
        channel_selection = self.channel_var.get()
        branch_selection = self.branch_var.get()
        
        if not channel_selection or not branch_selection:
            return None, None
            
        channel_key = channel_selection.split('(')[-1].rstrip(')')
        branch_code = branch_selection.split('(')[-1].rstrip(')')
        
        return channel_key, branch_code
    
    def start_capture(self):
        """Bắt đầu chụp ảnh"""
        channel_key, branch_code = self.get_selected_channel_branch()
        
        if not channel_key or not branch_code:
            messagebox.showerror("Lỗi", "Vui lòng chọn kênh và chi nhánh!")
            return
        
        # Validate selection
        valid, msg = self.manager.validate_selection(channel_key, branch_code)
        if not valid:
            messagebox.showerror("Lỗi", msg)
            return
        
        # Check device
        try:
            devices = []
            # This is a simplified check - in real implementation you'd call list_devices()
            # For now, we'll assume device is available
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể kết nối thiết bị: {e}")
            return
        
        # Save current settings
        self.save_settings()
        
        # Start capture in separate thread
        self.is_running = True
        self.stop_event.clear()
        self.start_time = time.time()
        
        # Update UI
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.open_folder_btn.config(state="disabled")
        self.progress_var.set("Đang chụp...")
        self.progress_bar.config(maximum=self.shots_var.get(), value=0)
        self.total_images_var.set("0")
        self.speed_var.set("0 ảnh/phút")
        
        # Start capture thread
        capture_thread = threading.Thread(target=self.capture_worker, 
                                         args=(channel_key, branch_code))
        capture_thread.daemon = True
        capture_thread.start()
    
    def stop_capture(self):
        """Dừng chụp ảnh"""
        self.stop_event.set()
        self.is_running = False
        
        # Update UI
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        if self.last_image_path:
            self.open_folder_btn.config(state="normal")
        self.progress_var.set("Đã dừng")
    
    def capture_worker(self, channel_key, branch_code):
        """Worker thread cho việc chụp ảnh"""
        try:
            # Get device
            serial = ensure_device(None)
            
            if self.tune_var.get():
                maybe_tune_device(serial)
                self.log_message("Đã tối ưu thiết bị")
            
            # Get screen size
            w, h = get_screen_size(serial)
            self.log_message(f"Kích thước màn hình: {w}x{h}")
            
            # Setup directories
            channel_name = self.manager.get_channel_name(channel_key)
            branch_name = self.manager.get_branch_name(channel_key, branch_code)
            output_dir = os.path.join(self.output_var.get(), channel_name, branch_name)
            os.makedirs(output_dir, exist_ok=True)
            
            self.log_message(f"Kênh: {channel_name} | Chi nhánh: {branch_name}")
            self.log_message(f"Lưu ảnh vào: {output_dir}")

            # Tự động sắp xếp file nếu cần
            channel_short = channel_name.replace("Food", "")
            sorted_count, total_files = auto_sort_files(output_dir, branch_code, channel_short,
                                                       log_callback=self.log_message)
            if sorted_count > 0:
                self.log_message(f"🔧 Tự động sắp xếp lại {sorted_count} file trước khi bắt đầu chụp")

            # Cập nhật thống kê thư mục
            self.root.after(0, lambda: self.update_folder_stats(channel_key, branch_code))

            # Setup swipe coordinates using user settings
            x = w // 2
            y_start = int(h * (1 - self.padding_bottom_var.get()))
            y_end = int(h * self.padding_top_var.get())
            
            last_hash, stuck, taken = None, 0, 0
            max_shots = self.shots_var.get()
            delay = self.delay_var.get()
            swipe_ms = self.swipe_var.get()
            overswipe_limit = self.overswipe_var.get()
            
            self.log_message(f"Tọa độ vuốt: ({x},{y_start}) -> ({x},{y_end})")
            
            # Xác định số bắt đầu cho ảnh
            if self.continue_numbering_var.get():
                start_num = get_next_image_number(output_dir, branch_code, channel_short)
                if start_num > 1:
                    self.log_message(f"📂 Tìm thấy {start_num-1} ảnh có sẵn, tiếp tục từ số {start_num}")
                else:
                    self.log_message("📂 Thư mục trống, bắt đầu từ số 1")
            else:
                start_num = 1
                self.log_message("📂 Bắt đầu từ số 1")
            
            for i in range(start_num, start_num + max_shots):
                if self.stop_event.is_set():
                    self.log_message("Dừng theo yêu cầu")
                    break

                # Update progress with smooth animation
                progress_val = i - start_num + 1
                progress_percent = (progress_val / max_shots) * 100
                self.root.after(0, lambda val=progress_val, pct=progress_percent: self._update_progress_smooth(val, pct))
                
                # Capture screenshot
                filename = f"{i:02d}_{branch_code}_{channel_short}.png"
                path = os.path.join(output_dir, filename)
                
                screencap_to_file(path, serial=serial)
                digest = sha256(path)
                
                if digest == last_hash:
                    stuck += 1
                    self.log_message(f"Ảnh {i:02d}: trùng với khung trước ({stuck}/{overswipe_limit})")
                    if stuck >= overswipe_limit:
                        self.log_message(f"Hết nội dung (trùng {stuck} lần). Dừng tại {i}.")
                        break
                else:
                    stuck = 0
                    taken += 1
                    self.log_message(f"Đã chụp: {filename}")
                    
                    # Update preview and stats
                    self.root.after(0, lambda p=path: self.update_preview(p))
                    self.root.after(0, lambda t=taken: self.total_images_var.set(str(t)))
                    self.root.after(0, self.refresh_file_list)
                    
                    # Auto upload to Google Drive if enabled
                    if (self.drive_uploader and 
                        self.drive_uploader.auto_upload and 
                        self.drive_uploader.service):
                        # Sử dụng branch_code thay vì branch_name cho custom mapping
                        self.drive_uploader.add_to_upload_queue(
                            path, channel_name, branch_code, filename
                        )
                        # Start upload worker if not already running
                        if not self.drive_uploader.is_uploading:
                            self.drive_uploader.start_upload_worker()
                            self.root.after(0, lambda: [
                                self.drive_stop_btn.config(state="normal"),
                                self.drive_upload_folder_btn.config(state="disabled")
                            ])
                    
                    # Calculate speed
                    if self.start_time:
                        elapsed_minutes = (time.time() - self.start_time) / 60
                        if elapsed_minutes > 0:
                            speed = taken / elapsed_minutes
                            self.root.after(0, lambda s=speed: self.speed_var.set(f"{s:.1f} ảnh/phút"))
                
                # Swipe
                swipe(x, y_start, x, y_end, swipe_ms, serial=serial)
                time.sleep(delay)
                last_hash = digest
                
        except Exception as e:
            self.log_message(f"Lỗi: {e}")
            messagebox.showerror("Lỗi", f"Có lỗi xảy ra: {e}")
        finally:
            # Reset UI
            self.is_running = False
            final_taken = taken if 'taken' in locals() else 0
            
            # Show completion message with upload info
            completion_msg = f"Hoàn tất: {final_taken} ảnh"
            if (self.drive_uploader and 
                self.drive_uploader.auto_upload and 
                self.drive_uploader.service and
                final_taken > 0):
                queue_size = self.drive_uploader.upload_queue.qsize()
                completion_msg += f" | {queue_size} file đang upload"
            
            self.root.after(0, lambda: [
                self.start_btn.config(state="normal"),
                self.stop_btn.config(state="disabled"),
                self.open_folder_btn.config(state="normal" if self.last_image_path else "disabled"),
                self.progress_var.set(completion_msg),
                self.update_drive_status() if self.drive_uploader else None
            ])
    
    def refresh_data(self):
        """Làm mới dữ liệu kênh và chi nhánh"""
        self.manager.load_config()
        
        # Update channel combo
        channels = self.manager.channels
        channel_options = [f"{channel['name']} ({key})" for key, channel in channels.items()]
        self.channel_combo['values'] = channel_options
        
        # Set first channel if available
        if channel_options and not self.channel_var.get():
            self.channel_combo.current(0)
            self.on_channel_change()
        
        self.refresh_file_list()
        self.refresh_stats()
        # Refresh Drive status khi thay đổi folder
        if self.drive_uploader:
            self.update_drive_status()
        self.log_message("🔄 Đã làm mới dữ liệu")
    
    def load_settings(self):
        """Load cài đặt ban đầu - simplified version"""
        # Just refresh data to populate combos
        self.refresh_data()
    
    def open_management(self):
        """Mở cửa sổ quản lý kênh và chi nhánh"""
        ManagementWindow(self.root, self.manager, self.refresh_data)
    
    def debug_drive_structure(self):
        """Debug cấu trúc folder Google Drive"""
        if self.drive_uploader and self.drive_uploader.service:
            self.drive_uploader.debug_folder_structure()
        else:
            self.log_message("❌ Chưa xác thực Google Drive")
            
    def scan_drive_folders(self):
        """Scan tất cả folder trong Google Drive"""
        if self.drive_uploader and self.drive_uploader.service:
            self.drive_uploader.list_my_drive_folders()
        else:
            self.log_message("❌ Chưa xác thực Google Drive")
    
    def reset_drive_stats(self):
        """Reset thống kê upload Google Drive"""
        if self.drive_uploader:
            from tkinter import messagebox
            if messagebox.askyesno("Xác nhận", "Bạn có chắc muốn reset thống kê upload?\nDữ liệu sẽ được xóa vĩnh viễn."):
                self.drive_uploader.reset_upload_stats()
                self.update_drive_status()
        else:
            self.log_message("❌ Chưa khởi tạo Google Drive uploader")

class CustomMappingDialog:
    def __init__(self, parent, drive_uploader, channel_manager, log_callback):
        self.drive_uploader = drive_uploader
        self.channel_manager = channel_manager
        self.log_callback = log_callback
        
        # Create dialog window
        self.window = tk.Toplevel(parent)
        self.window.title("🗂️ Cấu hình Folder Tùy chỉnh")
        self.window.geometry("800x600")
        self.window.transient(parent)
        self.window.grab_set()
        
        # Center window
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        x = parent_x + (parent_width - 800) // 2
        y = parent_y + (parent_height - 600) // 2
        self.window.geometry(f"800x600+{x}+{y}")
        
        self.setup_gui()
    
    def setup_gui(self):
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="🗂️ Cấu hình Folder Tùy chỉnh cho Chi nhánh", 
                               font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 20))
        
        # Instructions
        instruction_text = """Cấu hình này cho phép bạn upload trực tiếp vào các folder có sẵn trên Google Drive
thay vì tạo cấu trúc folder mới. Điều này hữu ích khi bạn đã có 4 folder đại diện cho 4 chi nhánh."""
        
        instruction_label = ttk.Label(main_frame, text=instruction_text, 
                                    font=("Arial", 10), wraplength=750)
        instruction_label.grid(row=1, column=0, pady=(0, 20))
        
        # Configuration frame
        config_frame = ttk.LabelFrame(main_frame, text="Mapping Chi nhánh -> Folder", padding="10")
        config_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        config_frame.columnconfigure(0, weight=1)
        config_frame.rowconfigure(0, weight=1)
        
        # Create treeview for mapping
        self.mapping_tree = ttk.Treeview(config_frame, columns=("folder_name", "folder_id", "status"), 
                                        show="tree headings", height=15)
        self.mapping_tree.heading("#0", text="Chi nhánh")
        self.mapping_tree.heading("folder_name", text="Tên Folder")
        self.mapping_tree.heading("folder_id", text="Folder ID")
        self.mapping_tree.heading("status", text="Trạng thái")
        
        self.mapping_tree.column("#0", width=150, minwidth=100)
        self.mapping_tree.column("folder_name", width=200, minwidth=150)
        self.mapping_tree.column("folder_id", width=250, minwidth=200)
        self.mapping_tree.column("status", width=100, minwidth=80)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(config_frame, orient="vertical", command=self.mapping_tree.yview)
        h_scrollbar = ttk.Scrollbar(config_frame, orient="horizontal", command=self.mapping_tree.xview)
        self.mapping_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.mapping_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, pady=20)
        
        # Quick setup button
        tk.Button(button_frame, text="🚀 Thiết lập nhanh", command=self.quick_setup,
                 bg='#28a745', fg='white', font=('Segoe UI', 9, 'bold'),
                 relief='raised', bd=2, padx=12, pady=6,
                 activebackground='#218838', activeforeground='white').pack(side=tk.LEFT, padx=5)
        
        # Edit mapping button
        tk.Button(button_frame, text="✏️ Chỉnh sửa", command=self.edit_mapping,
                 bg='#007bff', fg='white', font=('Segoe UI', 9, 'bold'),
                 relief='raised', bd=2, padx=12, pady=6,
                 activebackground='#0069d9', activeforeground='white').pack(side=tk.LEFT, padx=5)
        
        # Test mapping button
        tk.Button(button_frame, text="🧪 Test mapping", command=self.test_mapping,
                 bg='#6c757d', fg='white', font=('Segoe UI', 9, 'bold'),
                 relief='raised', bd=2, padx=12, pady=6,
                 activebackground='#5a6268', activeforeground='white').pack(side=tk.LEFT, padx=5)
        
        # Debug button
        tk.Button(button_frame, text="🔍 Debug", command=self.debug_folder_structure,
                 bg='#ffc107', fg='black', font=('Segoe UI', 9, 'bold'),
                 relief='raised', bd=2, padx=12, pady=6,
                 activebackground='#e0a800', activeforeground='black').pack(side=tk.LEFT, padx=5)
        
        # Save button
        tk.Button(button_frame, text="💾 Lưu", command=self.save_mapping,
                 bg='#28a745', fg='white', font=('Segoe UI', 9, 'bold'),
                 relief='raised', bd=2, padx=12, pady=6,
                 activebackground='#218838', activeforeground='white').pack(side=tk.LEFT, padx=5)
        
        # Close button
        tk.Button(button_frame, text="❌ Đóng", command=self.close_window,
                 bg='#dc3545', fg='white', font=('Segoe UI', 9, 'bold'),
                 relief='raised', bd=2, padx=12, pady=6,
                 activebackground='#c82333', activeforeground='white').pack(side=tk.LEFT, padx=5)
        
        # Load current mapping
        self.load_mapping()
    
    def load_mapping(self):
        """Load current mapping into treeview"""
        # Clear tree
        for item in self.mapping_tree.get_children():
            self.mapping_tree.delete(item)
        
        # Get all unique branches from channel manager
        all_branches = {}
        for channel_data in self.channel_manager.channels.values():
            for branch_code, branch_name in channel_data["branches"].items():
                if branch_code not in all_branches:
                    all_branches[branch_code] = branch_name
        
        # Add branches to tree
        for branch_code, branch_name in all_branches.items():
            folder_id = self.drive_uploader.custom_folder_mapping.get(branch_code, "")
            folder_name = ""
            status = "Chưa cấu hình"
            
            if folder_id:
                # Try to get folder name
                try:
                    folder_info = self.drive_uploader.service.files().get(fileId=folder_id, fields="name").execute()
                    folder_name = folder_info.get('name', 'Unknown')
                    status = "✅ OK"
                except:
                    folder_name = "Lỗi"
                    status = "❌ Không hợp lệ"
            
            self.mapping_tree.insert("", "end", 
                                   text=f"{branch_code} - {branch_name}",
                                   values=(folder_name, folder_id, status))
    
    def quick_setup(self):
        """Thiết lập nhanh bằng cách tìm folder theo tên chi nhánh"""
        if not self.drive_uploader.service:
            messagebox.showerror("Lỗi", "Chưa xác thực Google Drive!")
            return
        
        result = messagebox.askyesno("Thiết lập nhanh", 
                                   "Tìm và map tự động các folder có tên trùng với tên chi nhánh?\n\n"
                                   "Ví dụ: Chi nhánh 'Luỹ Bán Bích' sẽ tìm folder tên 'Luỹ Bán Bích'")
        
        if result:
            # Get all unique branches
            all_branches = {}
            for channel_data in self.channel_manager.channels.values():
                for branch_code, branch_name in channel_data["branches"].items():
                    if branch_code not in all_branches:
                        all_branches[branch_code] = branch_name
            
            # Setup mapping
            self.drive_uploader.setup_branch_folders_from_names(all_branches)
            self.load_mapping()
            messagebox.showinfo("Thành công", "Đã thiết lập mapping tự động!")
    
    def edit_mapping(self):
        """Chỉnh sửa mapping cho item được chọn"""
        selection = self.mapping_tree.selection()
        if not selection:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn chi nhánh để chỉnh sửa!")
            return
        
        item = selection[0]
        branch_text = self.mapping_tree.item(item, "text")
        branch_code = branch_text.split(" - ")[0]
        current_folder_id = self.mapping_tree.item(item, "values")[1]
        
        # Dialog to enter folder ID or name
        new_folder_input = simpledialog.askstring("Chỉnh sửa Mapping", 
                                                 f"Nhập Folder ID hoặc tên folder cho '{branch_text}':\n\n"
                                                 f"Hiện tại: {current_folder_id}",
                                                 initialvalue=current_folder_id)
        
        if new_folder_input:
            # Try to resolve folder ID if input is folder name
            if not new_folder_input.startswith('1'):  # Folder IDs usually start with '1'
                folder_id = self.drive_uploader.get_folder_id_by_name(new_folder_input)
                if not folder_id:
                    messagebox.showerror("Lỗi", f"Không tìm thấy folder có tên: {new_folder_input}")
                    return
            else:
                folder_id = new_folder_input
            
            # Update mapping
            self.drive_uploader.add_custom_folder_mapping(branch_code, folder_id)
            self.load_mapping()
    
    def test_mapping(self):
        """Test mapping hiện tại"""
        if not self.drive_uploader.custom_folder_mapping:
            messagebox.showwarning("Cảnh báo", "Chưa có mapping nào để test!")
            return
        
        results = []
        for branch_code, folder_id in self.drive_uploader.custom_folder_mapping.items():
            try:
                folder_info = self.drive_uploader.service.files().get(fileId=folder_id, fields="name").execute()
                folder_name = folder_info.get('name', 'Unknown')
                results.append(f"✅ {branch_code}: {folder_name} (ID: {folder_id})")
            except Exception as e:
                results.append(f"❌ {branch_code}: Lỗi - {str(e)}")
        
        result_text = "Kết quả test mapping:\n\n" + "\n".join(results)
        messagebox.showinfo("Kết quả Test", result_text)
    
    def save_mapping(self):
        """Lưu mapping và đóng dialog"""
        self.drive_uploader.save_config()
        messagebox.showinfo("Thành công", "Đã lưu cấu hình mapping!")
        if self.log_callback:
            mapping_count = len(self.drive_uploader.custom_folder_mapping)
            self.log_callback(f"💾 Đã lưu custom folder mapping cho {mapping_count} chi nhánh")
    
    def debug_folder_structure(self):
        """Debug cấu trúc folder"""
        if self.drive_uploader:
            self.drive_uploader.debug_folder_structure()
        else:
            messagebox.showerror("Lỗi", "Drive uploader không có sẵn!")
    
    def close_window(self):
        self.window.destroy()

class ManagementWindow:
    def __init__(self, parent, manager, refresh_callback):
        self.manager = manager
        self.refresh_callback = refresh_callback
        
        # Create window with responsive size
        self.window = tk.Toplevel(parent)
        self.window.title("Quản lý kênh và chi nhánh")
        
        # Get parent window size for responsive sizing
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        
        # Calculate management window size (90% of parent, but reasonable limits)
        mgmt_width = min(max(int(parent_width * 0.9), 600), 900)
        mgmt_height = min(max(int(parent_height * 0.9), 500), 700)
        
        # Center relative to parent
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        x = parent_x + (parent_width - mgmt_width) // 2
        y = parent_y + (parent_height - mgmt_height) // 2
        
        self.window.geometry(f"{mgmt_width}x{mgmt_height}+{x}+{y}")
        self.window.minsize(600, 400)
        self.window.transient(parent)
        self.window.grab_set()
        
        # Set window icon
        try:
            if os.path.exists("logo.ico"):
                self.window.iconbitmap("logo.ico")
        except Exception:
            pass  # Ignore if icon can't be loaded
        
        # Configure window for auto resize
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        
        self.setup_gui()
        
    def setup_gui(self):
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Quản lý kênh và chi nhánh", 
                               font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 20))
        
        # Control panel
        control_frame = ttk.LabelFrame(main_frame, text="Thao tác", padding="10")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        control_frame.columnconfigure(1, weight=1)
        control_frame.columnconfigure(3, weight=1)
        
        # Add channel section
        ttk.Label(control_frame, text="Thêm kênh:", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=4, sticky=tk.W, pady=(0, 5))
        
        ttk.Label(control_frame, text="Key:").grid(row=1, column=0, sticky=tk.W, padx=(10, 5))
        self.channel_key_var = tk.StringVar()
        ttk.Entry(control_frame, textvariable=self.channel_key_var, width=15).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        
        ttk.Label(control_frame, text="Tên:").grid(row=1, column=2, sticky=tk.W, padx=(10, 5))
        self.channel_name_var = tk.StringVar()
        ttk.Entry(control_frame, textvariable=self.channel_name_var, width=15).grid(row=1, column=3, sticky=(tk.W, tk.E), padx=5)
        
        # Copy from existing channel
        ttk.Label(control_frame, text="Copy chi nhánh từ:").grid(row=2, column=0, sticky=tk.W, padx=(10, 5))
        self.copy_from_var = tk.StringVar()
        self.copy_combo = ttk.Combobox(control_frame, textvariable=self.copy_from_var, state="readonly", width=15)
        self.copy_combo.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
        
        tk.Button(control_frame, text="➕ Thêm kênh", command=self.add_channel,
                  bg='#28a745', fg='white', font=('Segoe UI', 8, 'bold'),
                  relief='raised', bd=1, padx=8, pady=4,
                  activebackground='#218838', activeforeground='white').grid(row=2, column=3, sticky=tk.E, padx=5, pady=2)
        
        # Add branch section
        ttk.Separator(control_frame, orient='horizontal').grid(row=3, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=10)
        ttk.Label(control_frame, text="Thêm chi nhánh:", font=("Arial", 10, "bold")).grid(row=4, column=0, columnspan=4, sticky=tk.W, pady=(0, 5))
        
        # Channel selection with multiple choice
        ttk.Label(control_frame, text="Chọn kênh:").grid(row=5, column=0, sticky=tk.W, padx=(10, 5))
        
        # Frame for channel selection
        channel_frame = ttk.Frame(control_frame)
        channel_frame.grid(row=5, column=1, columnspan=3, sticky=(tk.W, tk.E), padx=5, pady=2)
        channel_frame.columnconfigure(0, weight=1)
        
        # Listbox for multiple channel selection
        self.channel_listbox = tk.Listbox(channel_frame, height=4, selectmode=tk.EXTENDED, font=('Segoe UI', 9))
        self.channel_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # Scrollbar for channel listbox
        channel_scrollbar = ttk.Scrollbar(channel_frame, orient=tk.VERTICAL, command=self.channel_listbox.yview)
        channel_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.channel_listbox.config(yscrollcommand=channel_scrollbar.set)
        
        # Selected channels display
        ttk.Label(control_frame, text="Đã chọn:").grid(row=6, column=0, sticky=tk.W, padx=(10, 5))
        self.selected_channels_var = tk.StringVar(value="Chưa chọn kênh nào")
        selected_label = ttk.Label(control_frame, textvariable=self.selected_channels_var, 
                                 font=('Segoe UI', 8), foreground='#007bff', wraplength=300)
        selected_label.grid(row=6, column=1, columnspan=3, sticky=(tk.W, tk.E), padx=5)
        
        # Bind selection event
        self.channel_listbox.bind('<<ListboxSelect>>', self.on_channel_listbox_select)
        
        ttk.Label(control_frame, text="Mã:").grid(row=7, column=0, sticky=tk.W, padx=(10, 5))
        self.branch_code_var = tk.StringVar()
        ttk.Entry(control_frame, textvariable=self.branch_code_var, width=15).grid(row=7, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
        
        ttk.Label(control_frame, text="Tên:").grid(row=7, column=2, sticky=tk.W, padx=(10, 5))
        self.branch_name_var = tk.StringVar()
        ttk.Entry(control_frame, textvariable=self.branch_name_var, width=15).grid(row=7, column=3, sticky=(tk.W, tk.E), padx=5, pady=2)
        
        # Buttons frame
        button_branch_frame = ttk.Frame(control_frame)
        button_branch_frame.grid(row=8, column=0, columnspan=4, pady=5)
        
        tk.Button(button_branch_frame, text="✅ Chọn tất cả", command=self.select_all_channels,
                  bg='#6c757d', fg='white', font=('Segoe UI', 8, 'bold'),
                  relief='raised', bd=1, padx=6, pady=3,
                  activebackground='#5a6268', activeforeground='white').pack(side=tk.LEFT, padx=2)
        
        tk.Button(button_branch_frame, text="❌ Bỏ chọn", command=self.clear_channel_selection,
                  bg='#6c757d', fg='white', font=('Segoe UI', 8, 'bold'),
                  relief='raised', bd=1, padx=6, pady=3,
                  activebackground='#5a6268', activeforeground='white').pack(side=tk.LEFT, padx=2)
        
        tk.Button(button_branch_frame, text="➕ Thêm chi nhánh", command=self.add_branch,
                  bg='#28a745', fg='white', font=('Segoe UI', 8, 'bold'),
                  relief='raised', bd=1, padx=8, pady=4,
                  activebackground='#218838', activeforeground='white').pack(side=tk.RIGHT, padx=5)
        
        # Tree view with context menu
        tree_frame = ttk.LabelFrame(main_frame, text="Danh sách kênh và chi nhánh", padding="10")
        tree_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        # Create treeview with scrollbars
        tree_container = ttk.Frame(tree_frame)
        tree_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_container.columnconfigure(0, weight=1)
        tree_container.rowconfigure(0, weight=1)
        
        self.channel_tree = ttk.Treeview(tree_container, columns=("info",), show="tree headings", height=15)
        self.channel_tree.heading("#0", text="Kênh / Chi nhánh")
        self.channel_tree.heading("info", text="Thông tin")
        self.channel_tree.column("#0", width=250, minwidth=200)
        self.channel_tree.column("info", width=200, minwidth=150)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.channel_tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_container, orient="horizontal", command=self.channel_tree.xview)
        self.channel_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.channel_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Context menu
        self.context_menu = tk.Menu(self.window, tearoff=0)
        self.context_menu.add_command(label="✏️ Chỉnh sửa", command=self.edit_selected)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🗑️ Xóa khỏi kênh này", command=self.delete_selected)
        self.context_menu.add_command(label="🗑️💥 Xóa khỏi TẤT CẢ kênh", command=self.delete_branch_from_all_channels)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="📋 Copy chi nhánh sang kênh khác", command=self.copy_branches)
        
        # Bind events
        self.channel_tree.bind("<Button-3>", self.show_context_menu)  # Right click
        self.channel_tree.bind("<Double-1>", self.on_double_click)  # Double click
        
        # Bottom buttons with custom styling
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, pady=10)

        tk.Button(button_frame, text="🔄 Làm mới", command=self.refresh_tree,
                 bg='#28a745', fg='white', font=('Segoe UI', 8, 'bold'),
                 relief='raised', bd=1, padx=8, pady=4,
                 activebackground='#218838', activeforeground='white').pack(side=tk.LEFT, padx=5)

        tk.Button(button_frame, text="🗑️ Xóa nhanh", command=self.quick_delete_dialog,
                 bg='#dc3545', fg='white', font=('Segoe UI', 8, 'bold'),
                 relief='raised', bd=1, padx=8, pady=4,
                 activebackground='#c82333', activeforeground='white').pack(side=tk.LEFT, padx=5)

        tk.Button(button_frame, text="📊 Thống kê", command=self.show_statistics,
                 bg='#6c757d', fg='white', font=('Segoe UI', 8, 'bold'),
                 relief='raised', bd=1, padx=8, pady=4,
                 activebackground='#5a6268', activeforeground='white').pack(side=tk.LEFT, padx=5)

        tk.Button(button_frame, text="❌ Đóng", command=self.close_window,
                 bg='#dc3545', fg='white', font=('Segoe UI', 8, 'bold'),
                 relief='raised', bd=1, padx=8, pady=4,
                 activebackground='#c82333', activeforeground='white').pack(side=tk.LEFT, padx=5)
        
        # Load data
        self.refresh_tree()
        self.update_combos()
    
    def update_combos(self):
        """Cập nhật các combobox và listbox"""
        channels = list(self.manager.channels.keys())
        self.copy_combo['values'] = [""] + channels
        
        # Update channel listbox for branch addition
        self.channel_listbox.delete(0, tk.END)
        for channel_key in channels:
            channel_name = self.manager.channels[channel_key]['name']
            display_text = f"{channel_name} ({channel_key})"
            self.channel_listbox.insert(tk.END, display_text)
        
        # Clear selection
        self.selected_channels_var.set("Chưa chọn kênh nào")
    
    def add_channel(self):
        key = self.channel_key_var.get().strip().lower()
        name = self.channel_name_var.get().strip()
        copy_from = self.copy_from_var.get()
        
        if not key or not name:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập đầy đủ thông tin!")
            return
        
        if self.manager.add_channel(key, name, copy_from if copy_from else None):
            self.channel_key_var.set("")
            self.channel_name_var.set("")
            self.copy_from_var.set("")
            self.refresh_tree()
            self.update_combos()
            messagebox.showinfo("Thành công", f"Đã thêm kênh '{name}' với chi nhánh tự động")
    
    def on_channel_listbox_select(self, event=None):
        """Xử lý khi chọn kênh trong listbox"""
        selected_indices = self.channel_listbox.curselection()
        if not selected_indices:
            self.selected_channels_var.set("Chưa chọn kênh nào")
            return
        
        selected_channels = []
        for index in selected_indices:
            channel_text = self.channel_listbox.get(index)
            channel_key = channel_text.split('(')[-1].rstrip(')')
            channel_name = self.manager.channels[channel_key]['name']
            selected_channels.append(channel_name)
        
        if len(selected_channels) == 1:
            display_text = f"1 kênh: {selected_channels[0]}"
        else:
            display_text = f"{len(selected_channels)} kênh: {', '.join(selected_channels[:2])}"
            if len(selected_channels) > 2:
                display_text += f" và {len(selected_channels) - 2} kênh khác"
        
        self.selected_channels_var.set(display_text)
    
    def select_all_channels(self):
        """Chọn tất cả kênh"""
        self.channel_listbox.select_set(0, tk.END)
        self.on_channel_listbox_select()
    
    def clear_channel_selection(self):
        """Bỏ chọn tất cả kênh"""
        self.channel_listbox.selection_clear(0, tk.END)
        self.on_channel_listbox_select()
    
    def get_selected_channels(self):
        """Lấy danh sách kênh được chọn"""
        selected_indices = self.channel_listbox.curselection()
        selected_channels = []
        
        for index in selected_indices:
            channel_text = self.channel_listbox.get(index)
            channel_key = channel_text.split('(')[-1].rstrip(')')
            selected_channels.append(channel_key)
        
        return selected_channels
    
    def add_branch(self):
        selected_channels = self.get_selected_channels()
        branch_code = self.branch_code_var.get().strip().upper()
        branch_name = self.branch_name_var.get().strip()
        
        if not selected_channels:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn ít nhất một kênh!")
            return
        
        if not branch_code or not branch_name:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập đầy đủ mã và tên chi nhánh!")
            return
        
        # Thêm chi nhánh vào tất cả kênh được chọn
        success_count = 0
        failed_channels = []
        
        for channel_key in selected_channels:
            if self.manager.add_branch(channel_key, branch_code, branch_name):
                success_count += 1
            else:
                failed_channels.append(self.manager.get_channel_name(channel_key))
        
        # Clear input fields
        self.branch_code_var.set("")
        self.branch_name_var.set("")
        self.clear_channel_selection()
        self.refresh_tree()
        
        # Show result message
        if success_count > 0:
            if failed_channels:
                messagebox.showinfo("Thành công một phần", 
                                  f"Đã thêm chi nhánh '{branch_name}' vào {success_count} kênh.\n"
                                  f"Thất bại: {', '.join(failed_channels)}")
            else:
                messagebox.showinfo("Thành công", 
                                  f"Đã thêm chi nhánh '{branch_name}' vào {success_count} kênh thành công!")
        else:
            messagebox.showerror("Lỗi", "Không thể thêm chi nhánh vào kênh nào!")
    
    def show_context_menu(self, event):
        """Hiển thị context menu khi click chuột phải"""
        item = self.channel_tree.selection()[0] if self.channel_tree.selection() else None
        if not item:
            return
        
        parent = self.channel_tree.parent(item)
        
        # Cấu hình menu dựa trên loại item được chọn
        if parent:  # This is a branch
            # Hiển thị tất cả tùy chọn cho chi nhánh
            self.context_menu.entryconfig("✏️ Chỉnh sửa", state="normal")
            self.context_menu.entryconfig("🗑️ Xóa khỏi kênh này", state="normal")
            self.context_menu.entryconfig("🗑️💥 Xóa khỏi TẤT CẢ kênh", state="normal")
            self.context_menu.entryconfig("📋 Copy chi nhánh sang kênh khác", state="disabled")
        else:  # This is a channel
            # Chỉ hiển thị tùy chọn phù hợp cho kênh
            self.context_menu.entryconfig("✏️ Chỉnh sửa", state="normal")
            self.context_menu.entryconfig("🗑️ Xóa khỏi kênh này", state="normal")
            self.context_menu.entryconfig("🗑️💥 Xóa khỏi TẤT CẢ kênh", state="disabled")
            self.context_menu.entryconfig("📋 Copy chi nhánh sang kênh khác", state="normal")
        
        self.context_menu.post(event.x_root, event.y_root)
    
    def on_double_click(self, event):
        """Xử lý double click - edit item"""
        item = self.channel_tree.selection()[0] if self.channel_tree.selection() else None
        if item:
            self.edit_selected()
    
    def delete_selected(self):
        """Xóa item được chọn khỏi kênh hiện tại"""
        selection = self.channel_tree.selection()
        if not selection:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn item để xóa!")
            return
        
        item = selection[0]
        parent = self.channel_tree.parent(item)
        item_text = self.channel_tree.item(item, "text")
        
        if parent:  # This is a branch
            # Extract channel and branch info
            parent_text = self.channel_tree.item(parent, "text")
            channel_key = parent_text.split('(')[-1].rstrip(')')
            branch_code = item_text.split(' - ')[0]
            channel_name = self.manager.get_channel_name(channel_key)
            
            if messagebox.askyesno("Xác nhận xóa chi nhánh", 
                                 f"Bạn có chắc muốn xóa chi nhánh '{item_text}' khỏi kênh '{channel_name}'?\n\n"
                                 f"Chi nhánh này vẫn sẽ tồn tại trong các kênh khác (nếu có)."):
                if self.manager.remove_branch(channel_key, branch_code):
                    self.refresh_tree()
                    self.update_combos()
                    messagebox.showinfo("Thành công", f"Đã xóa chi nhánh '{item_text}' khỏi kênh '{channel_name}'")
        else:  # This is a channel
            channel_key = item_text.split('(')[-1].rstrip(')')
            branch_count = len(self.manager.channels[channel_key]["branches"])
            
            if messagebox.askyesno("Xác nhận xóa kênh", 
                                 f"Bạn có chắc muốn xóa kênh '{item_text}' và tất cả {branch_count} chi nhánh của nó?"):
                if self.manager.remove_channel(channel_key):
                    self.refresh_tree()
                    self.update_combos()
                    messagebox.showinfo("Thành công", f"Đã xóa kênh '{item_text}' và {branch_count} chi nhánh")
    
    def delete_branch_from_all_channels(self):
        """Xóa chi nhánh khỏi tất cả kênh"""
        selection = self.channel_tree.selection()
        if not selection:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn chi nhánh để xóa!")
            return
        
        item = selection[0]
        parent = self.channel_tree.parent(item)
        
        if not parent:  # This is a channel, not a branch
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn chi nhánh, không phải kênh!")
            return
        
        item_text = self.channel_tree.item(item, "text")
        branch_code = item_text.split(' - ')[0]
        branch_name = item_text.split(' - ')[1] if ' - ' in item_text else branch_code
        
        # Tìm tất cả kênh có chi nhánh này
        channels_with_branch = []
        for channel_key, channel_data in self.manager.channels.items():
            if branch_code in channel_data["branches"]:
                channels_with_branch.append((channel_key, channel_data["name"]))
        
        if not channels_with_branch:
            messagebox.showinfo("Thông báo", f"Chi nhánh '{branch_code}' không tồn tại trong kênh nào!")
            return
        
        # Hiển thị dialog xác nhận với thông tin chi tiết
        channel_names = [f"• {name} ({key})" for key, name in channels_with_branch]
        confirm_message = f"""Bạn có chắc muốn xóa chi nhánh '{branch_name} ({branch_code})' khỏi TẤT CẢ {len(channels_with_branch)} kênh?

Các kênh sẽ bị ảnh hưởng:
{chr(10).join(channel_names)}

⚠️ CẢNH BÁO: Hành động này KHÔNG THỂ hoàn tác!"""
        
        if messagebox.askyesno("⚠️ Xác nhận xóa khỏi TẤT CẢ kênh", confirm_message):
            success_count = 0
            failed_channels = []
            
            for channel_key, channel_name in channels_with_branch:
                if self.manager.remove_branch(channel_key, branch_code):
                    success_count += 1
                else:
                    failed_channels.append(channel_name)
            
            self.refresh_tree()
            self.update_combos()
            
            # Hiển thị kết quả
            if success_count > 0:
                if failed_channels:
                    messagebox.showinfo("Thành công một phần", 
                                      f"Đã xóa chi nhánh '{branch_name}' khỏi {success_count} kênh.\n"
                                      f"Thất bại: {', '.join(failed_channels)}")
                else:
                    messagebox.showinfo("Thành công", 
                                      f"Đã xóa chi nhánh '{branch_name}' khỏi tất cả {success_count} kênh!")
            else:
                messagebox.showerror("Lỗi", "Không thể xóa chi nhánh khỏi kênh nào!")
    
    def edit_selected(self):
        """Chỉnh sửa item được chọn"""
        selection = self.channel_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        parent = self.channel_tree.parent(item)
        item_text = self.channel_tree.item(item, "text")
        
        if parent:  # Edit branch
            parent_text = self.channel_tree.item(parent, "text")
            channel_key = parent_text.split('(')[-1].rstrip(')')
            branch_parts = item_text.split(' - ')
            branch_code = branch_parts[0]
            branch_name = branch_parts[1] if len(branch_parts) > 1 else ""
            
            new_name = simpledialog.askstring("Chỉnh sửa chi nhánh", 
                                            f"Tên chi nhánh ({branch_code}):", 
                                            initialvalue=branch_name)
            if new_name and new_name != branch_name:
                self.manager.channels[channel_key]["branches"][branch_code] = new_name
                self.manager.save_config()
                self.refresh_tree()
                messagebox.showinfo("Thành công", f"Đã cập nhật chi nhánh '{branch_code}'")
        else:  # Edit channel
            channel_key = item_text.split('(')[-1].rstrip(')')
            channel_name = self.manager.channels[channel_key]["name"]
            
            new_name = simpledialog.askstring("Chỉnh sửa kênh", 
                                            f"Tên kênh ({channel_key}):", 
                                            initialvalue=channel_name)
            if new_name and new_name != channel_name:
                self.manager.channels[channel_key]["name"] = new_name
                self.manager.save_config()
                self.refresh_tree()
                self.update_combos()
                messagebox.showinfo("Thành công", f"Đã cập nhật kênh '{channel_key}'")
    
    def copy_branches(self):
        """Copy chi nhánh từ kênh này sang kênh khác"""
        selection = self.channel_tree.selection()
        if not selection:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn kênh để copy chi nhánh!")
            return
        
        item = selection[0]
        parent = self.channel_tree.parent(item)
        
        if parent:  # Selected a branch, get parent channel
            item = parent
        
        item_text = self.channel_tree.item(item, "text")
        source_channel = item_text.split('(')[-1].rstrip(')')
        
        # Show dialog to select target channel
        channels = [k for k in self.manager.channels.keys() if k != source_channel]
        if not channels:
            messagebox.showinfo("Thông báo", "Không có kênh nào khác để copy!")
            return
        
        target_channel = tk.simpledialog.askstring("Copy chi nhánh", 
                                                  f"Copy chi nhánh từ '{source_channel}' sang kênh nào?\n" +
                                                  f"Các kênh có sẵn: {', '.join(channels)}")
        
        if target_channel and target_channel in channels:
            # Copy branches
            source_branches = self.manager.channels[source_channel]["branches"].copy()
            self.manager.channels[target_channel]["branches"].update(source_branches)
            self.manager.save_config()
            self.refresh_tree()
            messagebox.showinfo("Thành công", f"Đã copy {len(source_branches)} chi nhánh sang '{target_channel}'")
    
    def quick_delete_dialog(self):
        """Dialog xóa nhanh chi nhánh"""
        # Tạo cửa sổ dialog
        dialog = tk.Toplevel(self.window)
        dialog.title("🗑️ Xóa nhanh chi nhánh")
        dialog.geometry("500x400")
        dialog.transient(self.window)
        dialog.grab_set()
        dialog.resizable(False, False)
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (dialog.winfo_screenheight() // 2) - (400 // 2)
        dialog.geometry(f"500x400+{x}+{y}")
        
        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="🗑️ Xóa nhanh chi nhánh", 
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Instructions
        instruction_label = ttk.Label(main_frame, 
                                    text="Chọn chi nhánh để xóa khỏi tất cả kênh:",
                                    font=("Arial", 10))
        instruction_label.pack(pady=(0, 10))
        
        # Get all unique branches
        all_branches = {}
        for channel_key, channel_data in self.manager.channels.items():
            for branch_code, branch_name in channel_data["branches"].items():
                if branch_code not in all_branches:
                    all_branches[branch_code] = branch_name
        
        if not all_branches:
            ttk.Label(main_frame, text="Không có chi nhánh nào để xóa!", 
                     font=("Arial", 10), foreground="red").pack(pady=20)
            ttk.Button(main_frame, text="Đóng", command=dialog.destroy).pack()
            return
        
        # Listbox for branch selection
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        branch_listbox = tk.Listbox(list_frame, height=12, font=('Segoe UI', 10))
        branch_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=branch_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        branch_listbox.config(yscrollcommand=scrollbar.set)
        
        # Populate listbox
        for branch_code, branch_name in sorted(all_branches.items()):
            # Count channels that have this branch
            channel_count = sum(1 for ch in self.manager.channels.values() 
                              if branch_code in ch["branches"])
            display_text = f"{branch_code} - {branch_name} ({channel_count} kênh)"
            branch_listbox.insert(tk.END, display_text)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        def delete_selected_branch():
            selection = branch_listbox.curselection()
            if not selection:
                messagebox.showwarning("Cảnh báo", "Vui lòng chọn chi nhánh để xóa!")
                return
            
            selected_text = branch_listbox.get(selection[0])
            branch_code = selected_text.split(' - ')[0]
            branch_name = selected_text.split(' - ')[1].split(' (')[0]
            
            # Find channels with this branch
            channels_with_branch = []
            for channel_key, channel_data in self.manager.channels.items():
                if branch_code in channel_data["branches"]:
                    channels_with_branch.append((channel_key, channel_data["name"]))
            
            if not channels_with_branch:
                messagebox.showinfo("Thông báo", f"Chi nhánh '{branch_code}' không tồn tại!")
                return
            
            # Confirmation dialog
            channel_names = [f"• {name}" for _, name in channels_with_branch]
            confirm_message = f"""Xóa chi nhánh '{branch_name} ({branch_code})' khỏi {len(channels_with_branch)} kênh?

Các kênh bị ảnh hưởng:
{chr(10).join(channel_names)}

⚠️ Hành động này KHÔNG THỂ hoàn tác!"""
            
            if messagebox.askyesno("⚠️ Xác nhận xóa", confirm_message):
                success_count = 0
                for channel_key, _ in channels_with_branch:
                    if self.manager.remove_branch(channel_key, branch_code):
                        success_count += 1
                
                self.refresh_tree()
                self.update_combos()
                dialog.destroy()
                
                if success_count > 0:
                    messagebox.showinfo("Thành công", 
                                      f"Đã xóa chi nhánh '{branch_name}' khỏi {success_count} kênh!")
                else:
                    messagebox.showerror("Lỗi", "Không thể xóa chi nhánh!")
        
        tk.Button(button_frame, text="🗑️ Xóa chi nhánh đã chọn", 
                 command=delete_selected_branch,
                 bg='#dc3545', fg='white', font=('Segoe UI', 9, 'bold'),
                 relief='raised', bd=2, padx=15, pady=8,
                 activebackground='#c82333', activeforeground='white').pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Button(button_frame, text="❌ Hủy", command=dialog.destroy,
                 bg='#6c757d', fg='white', font=('Segoe UI', 9, 'bold'),
                 relief='raised', bd=2, padx=15, pady=8,
                 activebackground='#5a6268', activeforeground='white').pack(side=tk.RIGHT)
    
    def show_statistics(self):
        """Hiển thị thống kê"""
        total_channels = len(self.manager.channels)
        total_branches = sum(len(ch["branches"]) for ch in self.manager.channels.values())
        
        # Count unique branches
        unique_branches = set()
        for channel in self.manager.channels.values():
            unique_branches.update(channel["branches"].keys())
        unique_branch_count = len(unique_branches)
        
        stats = f"""📊 THỐNG KÊ KÊNH VÀ CHI NHÁNH
        
🏪 Tổng số kênh: {total_channels}
🏢 Tổng số chi nhánh (tất cả): {total_branches}
🏢 Chi nhánh duy nhất: {unique_branch_count}
📈 Trung bình chi nhánh/kênh: {total_branches/total_channels:.1f}

Chi tiết theo kênh:"""
        
        for key, channel in self.manager.channels.items():
            branch_count = len(channel["branches"])
            stats += f"\n• {channel['name']}: {branch_count} chi nhánh"
        
        messagebox.showinfo("Thống kê", stats)
    
    def refresh_tree(self):
        # Clear tree
        for item in self.channel_tree.get_children():
            self.channel_tree.delete(item)
        
        # Add channels and branches
        for key, channel in self.manager.channels.items():
            branch_count = len(channel['branches'])
            parent_item = self.channel_tree.insert("", "end", 
                                                  text=f"{channel['name']} ({key})", 
                                                  values=(f"{branch_count} chi nhánh",),
                                                  tags=("channel",))
            
            # Add branches as children
            for code, name in channel['branches'].items():
                self.channel_tree.insert(parent_item, "end", 
                                       text=f"{code} - {name}", 
                                       values=("Chi nhánh",),
                                       tags=("branch",))
        
        # Configure tags for styling
        self.channel_tree.tag_configure("channel", background="#e8f4fd")
        self.channel_tree.tag_configure("branch", background="#f0f8ff")
    
    def close_window(self):
        self.refresh_callback()  # Refresh main window
        self.window.destroy()

def main():
    root = tk.Tk()
    app = AutoscreenGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
