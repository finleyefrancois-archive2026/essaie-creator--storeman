# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build specification for Smart File Organizer."""

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

a = Analysis(
    ['main_entry.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('frontend.html', '.'),
        ('assets/tailwind-offline.css', 'assets'),
    ],
    hiddenimports=collect_submodules('http'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SmartOrganizer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window for cleaner UI
    disable_windowed_console_on_fatal_exception=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Optional: add icon file here if you have one
)
