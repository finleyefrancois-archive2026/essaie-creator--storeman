# PyInstaller spec for Smart File Organizer. Build with: pyinstaller build.spec
from pathlib import Path

block_cipher = None
root = Path.cwd()

a = Analysis(
    ['main_entry.py'],
    pathex=[str(root)],
    binaries=[],
    datas=[('frontend.html', '.'), ('assets/tailwind-offline.css', 'assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'pydoc', 'email', 'xmlrpc', 'distutils'],
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
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/app.ico' if Path('assets/app.ico').exists() else None,
)
