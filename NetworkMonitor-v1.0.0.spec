# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('D:\\AI\\product\\networkMonitor\\v1.0.0\\assets', 'assets')]
binaries = []
hiddenimports = ['PyQt6', 'PyQt6.QtCore', 'PyQt6.QtWidgets', 'PyQt6.QtGui', 'PyQt6.sip', 'psutil', 'pyotp', 'qrcode', 'qrcode.image.pil', 'PIL', 'PIL.Image', 'PIL.ImageDraw', 'PIL.ImageFont', 'winreg', 'sqlite3', 'hashlib', 'hmac', 'core', 'core.models', 'core.database', 'core.analyzer', 'services', 'services.monitor', 'services.archive', 'services.description', 'ui', 'ui.theme', 'ui.widgets', 'ui.widgets.stat_card', 'ui.dialogs', 'ui.dialogs.totp_bind', 'ui.dialogs.connection_detail', 'ui.dialogs.risk_list', 'ui.dialogs.archive_view', 'ui.windows', 'ui.windows.login_window', 'ui.windows.main_window', 'installer', 'installer.pages', 'installer.wizard']
tmp_ret = collect_all('PyQt6')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('PIL')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['D:\\AI\\product\\networkMonitor\\v1.0.0\\launcher.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='NetworkMonitor-v1.0.0',
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
    icon=['D:\\AI\\product\\networkMonitor\\v1.0.0\\assets\\app_icon.ico'],
)
