#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
installer/wizard.py
安装向导主类 —— 组装各步骤页面，完成后弹出结果对话框
"""

import os
import sys
import subprocess

from PyQt6.QtWidgets import (
    QWizard, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QCheckBox, QApplication
)
from PyQt6.QtCore import Qt

from installer.pages import (
    WelcomePage, LicensePage, AccountSetupPage,
    DirectorySetupPage, InstallationPage, FinalPage,
)


class FinishDialog(QDialog):
    """
    安装完成对话框：选择是否创建桌面快捷方式，以及立即/稍后运行。
    exec() == Accepted  → 立即运行
    exec() == Rejected  → 稍后运行
    """

    def __init__(self, install_dir: str, data_dir: str, username: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("安装完成")
        self.setMinimumWidth(480)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(28, 24, 28, 20)

        title = QLabel("✅  安装成功")
        title.setStyleSheet("font-size:16pt;font-weight:bold;color:#0078d4;")
        layout.addWidget(title)

        # 摘要信息
        info_frame = QFrame()
        info_frame.setStyleSheet(
            "QFrame{background:#f0f7ff;border:1px solid #c0d8f0;"
            "border-radius:8px;padding:4px;}"
        )
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(12, 10, 12, 10)
        info_layout.setSpacing(4)
        for label, value in [
            ("管理员账户：", username),
            ("安装目录：",   install_dir),
            ("数据目录：",   data_dir),
        ]:
            lbl = QLabel("<b>{}</b>　{}".format(label, value))
            lbl.setStyleSheet("font-size:9pt;color:#333;")
            lbl.setWordWrap(True)
            info_layout.addWidget(lbl)
        layout.addWidget(info_frame)

        # 桌面快捷方式
        self._shortcut_chk = QCheckBox("在桌面创建快捷方式")
        self._shortcut_chk.setChecked(True)
        self._shortcut_chk.setStyleSheet("font-size:10pt;")
        layout.addWidget(self._shortcut_chk)
        layout.addSpacing(4)

        # 启动选择
        prompt = QLabel("安装完成后，您希望：")
        prompt.setStyleSheet("font-size:10pt;font-weight:bold;color:#333;")
        layout.addWidget(prompt)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        self._btn_now = QPushButton("🚀  立即运行")
        self._btn_now.setFixedHeight(42)
        self._btn_now.setStyleSheet(self._btn_style(True))
        self._btn_now.clicked.connect(self._launch_now)
        self._btn_later = QPushButton("⏰  稍后运行")
        self._btn_later.setFixedHeight(42)
        self._btn_later.setStyleSheet(self._btn_style(False))
        self._btn_later.clicked.connect(self._launch_later)
        btn_row.addWidget(self._btn_now)
        btn_row.addWidget(self._btn_later)
        layout.addLayout(btn_row)

    @staticmethod
    def _btn_style(primary: bool) -> str:
        if primary:
            return ("QPushButton{background:#0078d4;color:white;border:none;"
                    "border-radius:6px;font-size:10pt;font-weight:bold;}"
                    "QPushButton:hover{background:#0063b1;}")
        return ("QPushButton{background:white;color:#333;"
                "border:1.5px solid #b0b0b0;border-radius:6px;font-size:10pt;}"
                "QPushButton:hover{border-color:#0078d4;color:#0078d4;}")

    def _do_shortcut(self):
        if self._shortcut_chk.isChecked():
            exe = sys.executable if getattr(sys, "frozen", False) else ""
            if exe:
                _create_desktop_shortcut(exe)

    def _launch_now(self):
        self._do_shortcut()
        self.accept()

    def _launch_later(self):
        self._do_shortcut()
        self.reject()


class InstallWizard(QWizard):
    """
    安装向导，exec() 返回 1 表示完成。
    完成后：
      property("_install_config") → 安装路径信息
      property("_launch_now")     → True/False
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("网络监控系统 v1.0.0 安装向导")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setMinimumSize(720, 560)
        self.setOption(QWizard.WizardOption.HaveHelpButton, False)

        self.addPage(WelcomePage())
        self.addPage(LicensePage())
        self.addPage(AccountSetupPage())
        self.addPage(DirectorySetupPage())
        self.addPage(InstallationPage())
        self.addPage(FinalPage())

        self.setStyleSheet("""
            QWizard     { background: #f0f2f5; }
            QWizardPage { background: white; }
            QLabel      { color: #1a1a2e; font-size: 11pt; }
            QPushButton {
                background: #1a73e8; color: white;
                border: none; border-radius: 5px;
                padding: 8px 22px; font-size: 10pt; font-weight: bold;
            }
            QPushButton:hover    { background: #1558b0; }
            QPushButton:disabled { background: #b0b0b0; }
            QGroupBox {
                border: 1px solid #c5cae9; border-radius: 6px;
                margin-top: 12px; padding-top: 8px; font-weight: bold;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
            QLineEdit {
                border: 1px solid #c5cae9; border-radius: 4px;
                padding: 6px 8px; font-size: 10pt; background: #fafafa;
            }
            QLineEdit:focus { border: 1.5px solid #1a73e8; }
            QProgressBar {
                border: 1px solid #c5cae9; border-radius: 4px;
                text-align: center; height: 22px; background: #f0f2f5;
            }
            QProgressBar::chunk { background: #1a73e8; border-radius: 4px; }
            QTextEdit  { border: 1px solid #c5cae9; border-radius: 4px; background: #fafafa; }
            QCheckBox  { spacing: 6px; font-size: 10pt; }
            QCheckBox::indicator { width: 18px; height: 18px; }
        """)

        self.finished.connect(self._on_finished)

    def _on_finished(self, result):
        if result != 1:
            return
        cfg = self.property("_install_config") or {}
        dlg = FinishDialog(
            cfg.get("install_dir", "—"),
            cfg.get("data_dir", "—"),
            cfg.get("username", "—"),
        )
        launch_now = dlg.exec() == QDialog.DialogCode.Accepted
        self.setProperty("_launch_now", launch_now)


# ── 快捷方式工具 ─────────────────────────────────────────────
def _create_desktop_shortcut(exe_path: str) -> bool:
    try:
        import winreg
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        try:
            k = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
            )
            desktop = winreg.QueryValueEx(k, "Desktop")[0]
            winreg.CloseKey(k)
        except Exception:
            pass

        lnk = os.path.join(desktop, "网络监控系统 v1.0.0.lnk")
        ps = (
            '$ws = New-Object -ComObject WScript.Shell; '
            '$s  = $ws.CreateShortcut("{lnk}"); '
            '$s.TargetPath       = "{exe}"; '
            '$s.WorkingDirectory = "{wd}"; '
            '$s.Description      = "网络监控系统 v1.0.0"; '
            '$s.Save()'
        ).format(
            lnk=lnk.replace("\\", "\\\\"),
            exe=exe_path.replace("\\", "\\\\"),
            wd=os.path.dirname(exe_path).replace("\\", "\\\\"),
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive",
             "-ExecutionPolicy", "Bypass", "-Command", ps],
            capture_output=True, text=True, timeout=15,
            creationflags=0x08000000,
        )
        return result.returncode == 0
    except Exception:
        return False
