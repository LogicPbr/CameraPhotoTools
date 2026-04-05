# PyInstaller spec — build: pyinstaller CameraPhotoTools.spec
# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

spec_dir = Path(SPEC).parent.resolve()
datas = list(collect_data_files("ttkbootstrap"))
icon_path = spec_dir / "assets" / "CameraPhotoTools.ico"
icon_arg = str(icon_path) if icon_path.is_file() else None
if icon_path.is_file():
    datas.append((str(icon_path), "assets"))

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=["send2trash", "send2trash.win"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

_exe_opts = dict(
    name="CameraPhotoTools",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
if icon_arg:
    _exe_opts["icon"] = icon_arg

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    **_exe_opts,
)
