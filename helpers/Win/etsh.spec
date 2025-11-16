# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:/vhost/Repositorios/ETailTabbed/helpers/Win/etsh.py'],
    pathex=[],
    binaries=[],
    datas=[('C:/vhost/Repositorios/ETailTabbed/helpers/Win/EtMaps.ico', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='etsh',
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
    icon=['C:\\vhost\\Repositorios\\ETailTabbed\\helpers\\Win\\EtMaps.ico'],
)
