#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/build.py
PyInstaller 打包脚本
用法：  python scripts/build.py
输出：  dist/NetworkMonitor-v1.0.0.exe  (单文件可执行)
"""

import io
import os
import sys
import shutil
import subprocess

# 强制 stdout/stderr 使用 UTF-8，避免 GBK 编码错误
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── 路径配置 ────────────────────────────────────────────────
PYTHON   = r"C:\Users\ZTSK\.workbuddy\binaries\python\versions\3.13.12\python.exe"
ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # v1.0.0/
DIST     = os.path.join(ROOT, "dist")
BUILD    = os.path.join(ROOT, "build")
ICON     = os.path.join(ROOT, "assets", "app_icon.ico")
ASSETS   = os.path.join(ROOT, "assets")
ENTRY    = os.path.join(ROOT, "launcher.py")
EXE_NAME = "NetworkMonitor-v1.0.0"


def main():
    print("=" * 60)
    print("  Network Monitor v1.0.0 -- Build Script")
    print("=" * 60)

    # 检查图标
    if not os.path.exists(ICON):
        print("[WARN] icon not found: {}".format(ICON))
        icon_args = []
    else:
        print("[OK]   icon: {}".format(ICON))
        icon_args = ["--icon", ICON]

    # 清理上次构建
    for d in (DIST, BUILD):
        if os.path.exists(d):
            shutil.rmtree(d)
            print("[CLN]  cleaned: {}".format(d))

    # assets 数据嵌入（Windows 用 ; 分隔，源:目标）
    add_data = []
    if os.path.exists(ASSETS):
        add_data = ["--add-data", "{};assets".format(ASSETS)]

    cmd = [
        PYTHON, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name",     EXE_NAME,
        "--distpath", DIST,
        "--workpath", BUILD,
        "--clean",
    ] + icon_args + add_data + [
        # 隐式导入（frozen 模式常丢失）
        "--hidden-import=PyQt6",
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtWidgets",
        "--hidden-import=PyQt6.QtGui",
        "--hidden-import=PyQt6.sip",
        "--hidden-import=psutil",
        "--hidden-import=pyotp",
        "--hidden-import=qrcode",
        "--hidden-import=qrcode.image.pil",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--hidden-import=PIL.ImageDraw",
        "--hidden-import=PIL.ImageFont",
        "--hidden-import=winreg",
        "--hidden-import=sqlite3",
        "--hidden-import=hashlib",
        "--hidden-import=hmac",
        # 收集完整包，保证 Qt 插件和 PIL 完整
        "--collect-all", "PyQt6",
        "--collect-all", "PIL",
        # 项目分包
        "--hidden-import=core",
        "--hidden-import=core.models",
        "--hidden-import=core.database",
        "--hidden-import=core.analyzer",
        "--hidden-import=services",
        "--hidden-import=services.monitor",
        "--hidden-import=services.archive",
        "--hidden-import=services.description",
        "--hidden-import=ui",
        "--hidden-import=ui.theme",
        "--hidden-import=ui.widgets",
        "--hidden-import=ui.widgets.stat_card",
        "--hidden-import=ui.dialogs",
        "--hidden-import=ui.dialogs.totp_bind",
        "--hidden-import=ui.dialogs.connection_detail",
        "--hidden-import=ui.dialogs.risk_list",
        "--hidden-import=ui.dialogs.archive_view",
        "--hidden-import=ui.windows",
        "--hidden-import=ui.windows.login_window",
        "--hidden-import=ui.windows.main_window",
        "--hidden-import=installer",
        "--hidden-import=installer.pages",
        "--hidden-import=installer.wizard",
        ENTRY,
    ]

    print("\n[RUN]  Starting PyInstaller...\n")
    result = subprocess.run(cmd, cwd=ROOT)

    if result.returncode != 0:
        print("\n[FAIL] Build failed. Check errors above.")
        return False

    exe_path = os.path.join(DIST, EXE_NAME + ".exe")
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / 1024 / 1024
        print("\n[OK]   Build complete!")
        print("       EXE : {}".format(exe_path))
        print("       Size: {:.1f} MB".format(size_mb))
        return True
    else:
        print("\n[FAIL] EXE not found after build.")
        return False


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
