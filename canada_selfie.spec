# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

block_cipher = None

# Collect data files
datas = [
    ('backgrounds', 'backgrounds'),
    ('emoji_icons', 'emoji_icons'),
    ('README.md', '.'),
]

# Add only the u2netp model that the app uses
home = Path.home()
u2netp_model = home / '.u2net' / 'u2netp.onnx'
if u2netp_model.exists():
    datas.append((str(u2netp_model), '.u2net'))

# Hidden imports for PyInstaller
hiddenimports = [
    'PyQt5.QtCore',
    'PyQt5.QtGui', 
    'PyQt5.QtWidgets',
    'PyQt5.QtMultimedia',
    'cv2',
    'numpy',
    'rembg',
    'rembg.sessions',
    'rembg.sessions.u2netp',
    'onnxruntime',
    'onnxruntime.capi',
    'onnxruntime.capi.onnxruntime_pybind11_state',
    'PIL',
    'PIL._imaging',
    # Additional scipy imports for rembg
    'scipy._lib.messagestream',
    'scipy._cyutility',
    'scipy.spatial.transform._rotation_groups',
    'scipy.special._cdflib',
    'scipy.special._ufuncs_cxx',
]

a = Analysis(
    ['canada_selfie_app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=['.'],  # Include current directory for custom hooks
    hooksconfig={},
    runtime_hooks=['rthook_onnxruntime.py'],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

import sys

# Use onefile for both platforms
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='CanadaSelfieApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='emoji_icons/maple_leaf.png' if __import__('os').path.exists('emoji_icons/maple_leaf.png') else None,
    onefile=True,  # Create single executable file
)

# Create .app bundle on macOS
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='Canada Selfie.app',
        icon='emoji_icons/maple_leaf.png' if __import__('os').path.exists('emoji_icons/maple_leaf.png') else None,
        bundle_identifier='com.canadaselfie.app',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'NSCameraUsageDescription': 'Canada Selfie needs camera access to take awesome Canadian-themed selfies!',
            'LSApplicationCategoryType': 'public.app-category.photography',
            'CFBundleShortVersionString': '1.0',
            'CFBundleVersion': '1.0',
            'NSRequiresAquaSystemAppearance': 'False',
            'NSSupportsAutomaticGraphicsSwitching': 'True',
        },
    )