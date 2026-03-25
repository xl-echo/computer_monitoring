#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ui/windows/login_window.py
登录窗口 —— 账密验证 + TOTP 两步认证 + 记住账密 + 自动登录
"""

import pyotp
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QStackedWidget, QCheckBox
)
from PyQt6.QtCore import Qt, QSettings, QTimer

from core.database import DatabaseManager, hash_password
from ui.dialogs.totp_bind import TotpBindDialog
from ui.theme import btn_primary_qss


class LoginWindow(QDialog):
    """
    两阶段登录窗口：
      页0 → 账密输入（含「记住账密」「自动登录」）
      页1 → TOTP 验证码输入

    登录成功后 self.username 持有已登录用户名。
    """

    def __init__(self, db_manager: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.username: str = ""
        self._pending_user_row = None
        self._pending_totp = None
        self._settings = QSettings("NetworkMonitor", "v1.0")

        self.setWindowTitle("网络监控系统 v1.0.0 — 登录")
        self.setMinimumSize(420, 430)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # 顶部 Banner
        banner = QFrame()
        banner.setFixedHeight(80)
        banner.setStyleSheet(
            "background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #0d47a1,stop:1 #1565c0);"
        )
        b_layout = QHBoxLayout(banner)
        b_lbl = QLabel("🌐  网络监控系统 v1.0.0")
        b_lbl.setStyleSheet("font-size:15pt;font-weight:bold;color:white;")
        b_layout.addWidget(b_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        root.addWidget(banner)

        # 主体区域
        body = QFrame()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(36, 24, 36, 24)
        body_layout.setSpacing(12)
        root.addWidget(body)

        self._stack = QStackedWidget()
        body_layout.addWidget(self._stack)

        # ── 页0：账密 ─────────────────────────────────────────
        page0 = self._build_page0()
        self._stack.addWidget(page0)

        # ── 页1：TOTP ─────────────────────────────────────────
        page1 = self._build_page1()
        self._stack.addWidget(page1)

        # 加载已保存凭据
        self._load_saved_credentials()

    # ── 页0 构建 ─────────────────────────────────────────────
    def _build_page0(self):
        from PyQt6.QtWidgets import QWidget
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        layout.addWidget(self._lbl("请输入账户信息", "font-size:10pt;color:#555;"))

        self.user_edit = QLineEdit()
        self.user_edit.setPlaceholderText("用户名")
        self.user_edit.setFixedHeight(38)
        self.user_edit.setStyleSheet(
            "font-size:10pt;padding:6px;border:1px solid #ccc;border-radius:6px;"
        )
        layout.addWidget(self.user_edit)

        self.pass_edit = QLineEdit()
        self.pass_edit.setPlaceholderText("密码")
        self.pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_edit.setFixedHeight(38)
        self.pass_edit.setStyleSheet(
            "font-size:10pt;padding:6px;border:1px solid #ccc;border-radius:6px;"
        )
        self.pass_edit.returnPressed.connect(self._on_login)
        layout.addWidget(self.pass_edit)

        # 记住账密 + 自动登录
        cb_row = QHBoxLayout()
        cb_row.setSpacing(16)
        self.remember_cb = QCheckBox("记住账密")
        self.remember_cb.setStyleSheet("font-size:9pt;color:#555;")
        self.autologin_cb = QCheckBox("自动登录")
        self.autologin_cb.setStyleSheet("font-size:9pt;color:#555;")
        self.autologin_cb.toggled.connect(
            lambda checked: self.remember_cb.setChecked(True) if checked else None
        )
        cb_row.addWidget(self.remember_cb)
        cb_row.addWidget(self.autologin_cb)
        cb_row.addStretch()
        layout.addLayout(cb_row)

        self.login_err = QLabel("")
        self.login_err.setStyleSheet("color:#dc3545;font-size:9pt;")
        layout.addWidget(self.login_err)

        login_btn = QPushButton("登  录")
        login_btn.setFixedHeight(40)
        login_btn.setStyleSheet(btn_primary_qss(radius=6))
        login_btn.clicked.connect(self._on_login)
        layout.addWidget(login_btn)

        layout.addStretch()
        return page

    # ── 页1 构建 ─────────────────────────────────────────────
    def _build_page1(self):
        from PyQt6.QtWidgets import QWidget
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(10)

        layout.addWidget(self._lbl("请输入两步验证码", "font-size:10pt;color:#555;"))

        self.totp_edit = QLineEdit()
        self.totp_edit.setPlaceholderText("Authenticator 中的 6 位验证码")
        self.totp_edit.setMaxLength(6)
        self.totp_edit.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.totp_edit.setFixedHeight(48)
        self.totp_edit.setStyleSheet(
            "font-size:16pt;letter-spacing:6px;padding:8px;"
            "border:1px solid #ccc;border-radius:6px;"
        )
        self.totp_edit.returnPressed.connect(self._on_totp)
        layout.addWidget(self.totp_edit)

        self.totp_err = QLabel("")
        self.totp_err.setStyleSheet("color:#dc3545;font-size:9pt;")
        layout.addWidget(self.totp_err)

        verify_btn = QPushButton("验  证")
        verify_btn.setFixedHeight(40)
        verify_btn.setStyleSheet(btn_primary_qss(radius=6))
        verify_btn.clicked.connect(self._on_totp)
        layout.addWidget(verify_btn)

        back_btn = QPushButton("← 返回")
        back_btn.setFixedHeight(32)
        back_btn.setStyleSheet("background:none;color:#0078d4;border:none;font-size:9pt;")
        back_btn.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        layout.addWidget(back_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        layout.addStretch()
        return page

    # ── 凭据持久化 ───────────────────────────────────────────
    def _load_saved_credentials(self):
        remember = self._settings.value("remember", False, type=bool)
        autologin = self._settings.value("autologin", False, type=bool)
        self.remember_cb.setChecked(remember)
        self.autologin_cb.setChecked(autologin)
        if remember:
            user = self._settings.value("saved_user", "")
            pwd = self._settings.value("saved_pass", "")
            if user:
                self.user_edit.setText(user)
            if pwd:
                self.pass_edit.setText(pwd)
        if autologin and remember:
            QTimer.singleShot(200, self._on_login)

    def _save_credentials(self, username: str, password: str):
        remember = self.remember_cb.isChecked()
        autologin = self.autologin_cb.isChecked()
        self._settings.setValue("remember", remember)
        self._settings.setValue("autologin", autologin)
        if remember:
            self._settings.setValue("saved_user", username)
            self._settings.setValue("saved_pass", password)
        else:
            self._settings.remove("saved_user")
            self._settings.remove("saved_pass")

    # ── 登录逻辑 ─────────────────────────────────────────────
    def _on_login(self):
        username = self.user_edit.text().strip()
        password = self.pass_edit.text()
        self.login_err.setText("")

        if not username or not password:
            self.login_err.setText("请填写用户名和密码")
            return

        row = self.db_manager.get_user(username)
        if not row or row[2] != hash_password(password):
            self.login_err.setText("用户名或密码错误")
            # 登录失败时清除自动登录，防止死循环
            self._settings.setValue("autologin", False)
            self.autologin_cb.setChecked(False)
            return

        self._save_credentials(username, password)
        self._pending_user_row = row
        totp_secret = row[3]

        if not totp_secret:
            # 首次登录：绑定 TOTP
            new_secret = pyotp.random_base32()
            dlg = TotpBindDialog(username, new_secret, self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self.db_manager.set_totp_secret(username, new_secret)
                self.username = username
                self.accept()
            else:
                self.login_err.setText("TOTP 绑定未完成，请重试")
        else:
            self._pending_totp = pyotp.TOTP(totp_secret)
            self.totp_edit.clear()
            self.totp_err.setText("")
            self._stack.setCurrentIndex(1)
            self.totp_edit.setFocus()

    def _on_totp(self):
        code = self.totp_edit.text().strip()
        if not code:
            self.totp_err.setText("请输入验证码")
            return
        if self._pending_totp.verify(code, valid_window=1):
            self.username = self._pending_user_row[1]
            self.accept()
        else:
            self.totp_err.setText("验证码错误，请重新输入")
            self.totp_edit.clear()
            self.totp_edit.setFocus()

    # ── 工具 ─────────────────────────────────────────────────
    @staticmethod
    def _lbl(text: str, style: str = "") -> QLabel:
        lbl = QLabel(text)
        if style:
            lbl.setStyleSheet(style)
        return lbl
