# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec: onedir bundle under dist/Cryptoriale/."""

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

block_cipher = None

_hidden = (
    collect_submodules("gui")
    + collect_submodules("game")
    + collect_submodules("llm")
)

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=collect_dynamic_libs("pygame"),
    datas=collect_data_files("pygame"),
    hiddenimports=_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Cryptoriale",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Cryptoriale",
)
