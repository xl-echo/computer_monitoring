#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
launcher.py
程序主入口 —— 启动画面 + 安装检测路由
  已安装 → 启动主监控窗口
  未安装 → 启动安装向导

单例机制（Windows）：
  第一个实例持有命名互斥体，并监听命名管道。
  后续实例发现互斥体已存在，通过管道发送 "SHOW" 命令后退出。
"""

import sys
import os
import json
import traceback
import threading

from PyQt6.QtWidgets import (
    QApplication, QMessageBox, QSplashScreen
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QBrush, QColor, QPen, QFont

# ── 单例常量 ─────────────────────────────────────────────────
_MUTEX_NAME = "Global\\NetworkMonitor_v1_0_0_SingleInstance"
_PIPE_NAME  = r"\\.\pipe\NetworkMonitor_v1_0_0"

# 全局句柄，防止 GC
_g_mutex   = None
_g_pipe_server = None


def get_app_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


# ── 单例检测 ─────────────────────────────────────────────────

def _acquire_mutex() -> bool:
    """
    尝试创建命名互斥体。
    返回 True  → 本进程是第一个实例，已持有互斥体。
    返回 False → 已有其他实例在运行。
    """
    global _g_mutex
    try:
        import ctypes
        import ctypes.wintypes as wt
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.CreateMutexW(None, True, _MUTEX_NAME)
        err = kernel32.GetLastError()
        if handle and err != 183:   # 183 = ERROR_ALREADY_EXISTS
            _g_mutex = handle
            return True
        # 互斥体已存在
        if handle:
            kernel32.CloseHandle(handle)
        return False
    except Exception:
        return True     # 异常时允许启动，避免误拦


def _notify_existing_instance():
    """向已运行的实例发送 SHOW 命令（通过命名管道）。"""
    try:
        import ctypes
        import ctypes.wintypes as wt
        GENERIC_WRITE      = 0x40000000
        OPEN_EXISTING      = 3
        FILE_ATTRIBUTE_NORMAL = 0x80
        kernel32 = ctypes.windll.kernel32
        pipe = kernel32.CreateFileW(
            _PIPE_NAME, GENERIC_WRITE, 0, None,
            OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, None,
        )
        INVALID_HANDLE = ctypes.c_void_p(-1).value
        if pipe != INVALID_HANDLE:
            msg = b"SHOW"
            written = wt.DWORD(0)
            kernel32.WriteFile(pipe, msg, len(msg), ctypes.byref(written), None)
            kernel32.CloseHandle(pipe)
    except Exception:
        pass


def _start_pipe_server(app_ref: list):
    """
    在后台线程中监听命名管道，收到 "SHOW" 时唤起主窗口。
    app_ref 是一个列表，持有 [QApplication]，用于线程安全地调度到主线程。
    """
    def _serve():
        try:
            import ctypes
            import ctypes.wintypes as wt

            kernel32 = ctypes.windll.kernel32
            PIPE_ACCESS_INBOUND   = 0x00000001
            PIPE_TYPE_BYTE        = 0x00000000
            PIPE_READMODE_BYTE    = 0x00000000
            PIPE_WAIT             = 0x00000000
            INVALID_HANDLE        = ctypes.c_void_p(-1).value

            while True:
                pipe = kernel32.CreateNamedPipeW(
                    _PIPE_NAME,
                    PIPE_ACCESS_INBOUND,
                    PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT,
                    1,      # max instances
                    64, 64,
                    0, None,
                )
                if pipe == INVALID_HANDLE:
                    break

                connected = kernel32.ConnectNamedPipe(pipe, None)
                if connected or kernel32.GetLastError() == 535:  # ERROR_PIPE_CONNECTED
                    buf = ctypes.create_string_buffer(64)
                    read = wt.DWORD(0)
                    kernel32.ReadFile(pipe, buf, 64, ctypes.byref(read), None)
                    data = buf.raw[:read.value]
                    if data == b"SHOW":
                        # 调度到主线程
                        app = app_ref[0] if app_ref else None
                        if app:
                            QTimer.singleShot(0, _bring_to_front)
                kernel32.DisconnectNamedPipe(pipe)
                kernel32.CloseHandle(pipe)
        except Exception:
            pass

    t = threading.Thread(target=_serve, daemon=True)
    t.start()


def _bring_to_front():
    """把主窗口带到前台（在主线程中调用）。"""
    app = QApplication.instance()
    if not app:
        return
    mw = getattr(app, "_main_window", None)
    if mw:
        mw.show()
        mw.setWindowState(
            (mw.windowState() & ~Qt.WindowState.WindowMinimized)
            | Qt.WindowState.WindowActive
        )
        mw.raise_()
        mw.activateWindow()


# ── 安装状态检测 ─────────────────────────────────────────────

def _read_registry() -> dict | None:
    """从注册表读取安装配置"""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\NetworkMonitor\v1.0",
            0, winreg.KEY_READ,
        )
        installed = winreg.QueryValueEx(key, "Installed")[0]
        if not installed:
            winreg.CloseKey(key)
            return None
        data = {
            "install_dir": winreg.QueryValueEx(key, "InstallDir")[0],
            "data_dir":    winreg.QueryValueEx(key, "DataDir")[0],
            "db_path":     winreg.QueryValueEx(key, "DbPath")[0],
        }
        winreg.CloseKey(key)
        return data if os.path.exists(data["db_path"]) else None
    except Exception:
        return None


def _read_config_file() -> dict | None:
    """降级：从 config.json 读取安装配置"""
    app_dir = get_app_dir()
    pf = os.environ.get("ProgramFiles", "C:\\Program Files")
    candidates = [
        os.path.join(pf, "NetworkMonitor v1.0", "data", "config.json"),
        os.path.join(app_dir, "data", "config.json"),
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                if cfg.get("db_path") and os.path.exists(cfg["db_path"]):
                    return cfg
            except Exception:
                pass
    return None


def load_install_config() -> dict | None:
    return _read_registry() or _read_config_file()


# ── 启动画面 ─────────────────────────────────────────────────

def create_splash() -> QSplashScreen:
    pixmap = QPixmap(500, 300)
    pixmap.fill(QColor("#0d1b2a"))
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    p.setBrush(QBrush(QColor("#1a73e8")))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(30, 50, 440, 200, 12, 12)

    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor("white"), 3))
    for r in (20, 35, 50):
        p.drawEllipse(230 - r // 2, 80 - r // 2, r, r)

    font = QFont("Microsoft YaHei", 18, QFont.Weight.Bold)
    p.setFont(font)
    p.setPen(QPen(QColor("white")))
    p.drawText(0, 150, 500, 40, Qt.AlignmentFlag.AlignHCenter, "网络监控系统 v1.0.0")

    font2 = QFont("Microsoft YaHei", 9)
    p.setFont(font2)
    p.setPen(QPen(QColor("#b0c4de")))
    p.drawText(
        0, 192, 500, 28,
        Qt.AlignmentFlag.AlignHCenter,
        "Intelligent Network Activity Analysis Platform",
    )
    p.end()
    return QSplashScreen(pixmap, Qt.WindowType.WindowStaysOnTopHint)


# ── 主流程 ───────────────────────────────────────────────────

def main():
    # ── 单例检测 ──────────────────────────────────────────────
    if not _acquire_mutex():
        # 已有实例运行 → 尝试唤起它，然后退出
        _notify_existing_instance()
        # 用一个最小的 QApplication 弹提示（可选，不影响主实例）
        _app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.information(
            None,
            "网络监控系统",
            "程序已在运行中。\n\n主界面已为您弹出，请查看任务栏。",
        )
        sys.exit(0)

    # 将项目根目录加入 sys.path，保证分包 import 正常
    root = get_app_dir()
    if root not in sys.path:
        sys.path.insert(0, root)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 启动管道服务，监听其他实例发来的 SHOW 命令
    _start_pipe_server([app])

    splash = create_splash()
    app._splash = splash
    splash.show()
    splash.showMessage(
        "正在初始化...",
        Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom,
        QColor("white"),
    )
    app.processEvents()

    QTimer.singleShot(1000, lambda: _route(app, splash))
    sys.exit(app.exec())


def _route(app, splash):
    try:
        cfg = load_install_config()
        if cfg:
            splash.showMessage(
                "检测到已安装，正在启动...",
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom,
                QColor("white"),
            )
            app.processEvents()
            QTimer.singleShot(500, lambda: _start_main(app, splash, cfg))
        else:
            splash.showMessage(
                "首次运行，即将启动安装向导...",
                Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom,
                QColor("white"),
            )
            app.processEvents()
            QTimer.singleShot(600, lambda: _start_installer(app, splash))
    except Exception as e:
        splash.close()
        QMessageBox.critical(
            None, "启动错误",
            "程序初始化失败：\n\n{}\n\n{}".format(e, traceback.format_exc()),
        )
        sys.exit(1)


def _start_installer(app, splash):
    splash.close()
    try:
        from installer.wizard import InstallWizard
        wizard = InstallWizard()
        result = wizard.exec()

        if result != 1:
            QMessageBox.information(
                None, "提示", "您已取消安装。再次运行程序可重新启动安装向导。"
            )
            sys.exit(0)

        cfg = wizard.property("_install_config") or load_install_config()
        if not cfg:
            QMessageBox.critical(
                None, "错误", "安装已完成，但无法读取配置，请重新启动程序。"
            )
            sys.exit(1)

        launch_now = wizard.property("_launch_now")
        if launch_now is None:
            launch_now = True

        if launch_now:
            _start_main(app, splash, cfg)
        else:
            QMessageBox.information(
                None, "安装完成",
                "网络监控系统 v1.0.0 已安装完成。\n"
                "可通过桌面快捷方式或重新双击程序启动。",
            )
            sys.exit(0)
    except Exception as e:
        QMessageBox.critical(
            None, "安装向导错误",
            "安装向导启动失败：\n\n{}\n\n{}".format(e, traceback.format_exc()),
        )
        sys.exit(1)


def _start_main(app, splash, config=None):
    try:
        splash.close()
    except Exception:
        pass

    try:
        from ui.windows.main_window import MainWindow

        if config is None:
            config = load_install_config()
        if not config:
            QMessageBox.critical(
                None, "配置错误", "未检测到安装配置，请重新安装程序。"
            )
            sys.exit(1)

        db_path = config.get(
            "db_path", os.path.join(get_app_dir(), "data", "network_monitor.db")
        )
        log_dir = config.get("log_dir", os.path.join(get_app_dir(), "logs"))

        window = MainWindow(db_path, log_dir)
        if getattr(window, "_login_cancelled", False):
            sys.exit(0)

        app._main_window = window
        window.show()
        window.raise_()
        window.activateWindow()

    except Exception as e:
        QMessageBox.critical(
            None, "主程序错误",
            "程序启动失败：\n\n{}\n\n{}".format(e, traceback.format_exc()),
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
