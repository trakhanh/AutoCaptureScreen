# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_data_files

# Collect all data files
datas = [
    ('logo.ico', '.'),
    ('logo.jpg', '.'),
    ('channels_config.json', '.'),
    ('gui_settings.json', '.'),
    ('drive_config.json', '.'),
    ('token.json', '.'),
    ('credentials_template.json', '.'),  # Template cho người dùng
    ('CUSTOM_FOLDER_GUIDE.md', '.'),
    ('GOOGLE_DRIVE_SETUP.md', '.'),
    ('GOOGLE_DRIVE_CREDENTIALS_SETUP.md', '.'),  # Hướng dẫn thiết lập
    ('README.md', '.'),
]

# Add shots directory if it exists
if os.path.exists('shots'):
    datas.append(('shots', 'shots'))

# Collect data files from google_drive_uploader if it exists
try:
    google_drive_datas = collect_data_files('google_drive_uploader')
    datas.extend(google_drive_datas)
except:
    pass

a = Analysis(
    ['AutoscreenGUI.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'PIL._tkinter_finder',
        'googleapiclient.discovery',
        'googleapiclient.http',
        'google.auth.transport.requests',
        'google.oauth2.credentials',
        'google_auth_oauthlib.flow',
        'google_auth_httplib2',
        'ttkthemes',
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.scrolledtext',
        'tkinter.filedialog',
        'tkinter.simpledialog',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AutoScreen',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to False for GUI application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='logo.ico',  # Use the logo as icon
)
