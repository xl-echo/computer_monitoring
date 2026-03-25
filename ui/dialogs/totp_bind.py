#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ui/dialogs/totp_bind.py
TOTP 绑定弹窗 —— 首次登录时引导用户绑定验证器 App
"""

import io
import pyotp
import qrcode

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

from ui.theme import btn_primary_qss


class TotpBindDialog(QDialog):
    """
    展示二维码和手动密钥，要求用户输入 6 位验证码完成绑定。
    exec() 返回 Accepted 表示绑定成功。
    """

    def __init__(self, username: str, secret: str, parent=None):
        super().__init__(parent)
        self._totp = pyotp.TOTP(secret)
        self.setWindowTitle("绑定两步验证")
        self.setMinimumWidth(400)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.WindowTitleHint
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 20, 24, 20)

        title = QLabel("首次登录：请绑定两步验证")
        title.setStyleSheet("font-size:13pt;font-weight:bold;color:#0078d4;")
        layout.addWidget(title)

        tips = QLabel(
            "1. 打开 <b>Google Authenticator</b> 或 <b>Microsoft Authenticator</b><br>"
            "2. 扫描下方二维码完成绑定<br>"
            "3. 输入 App 中显示的 6 位验证码"
        )
        tips.setWordWrap(True)
        tips.setStyleSheet("font-size:9pt;color:#555;")
        layout.addWidget(tips)

        # 二维码
        uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=username, issuer_name="NetworkMonitor v1.0"
        )
        qr = qrcode.make(uri)
        buf = io.BytesIO()
        qr.save(buf, format="PNG")
        buf.seek(0)
        qr_pix = QPixmap()
        qr_pix.loadFromData(buf.read())
        qr_pix = qr_pix.scaled(
            200, 200,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        qr_lbl = QLabel()
        qr_lbl.setPixmap(qr_pix)
        qr_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(qr_lbl)

        secret_lbl = QLabel("手动密钥：<b>{}</b>".format(secret))
        secret_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        secret_lbl.setStyleSheet("font-size:9pt;color:#666;")
        layout.addWidget(secret_lbl)

        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("输入 6 位验证码")
        self.code_edit.setMaxLength(6)
        self.code_edit.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.code_edit.setStyleSheet(
            "font-size:14pt;letter-spacing:4px;padding:8px;"
        )
        self.code_edit.returnPressed.connect(self._verify)
        layout.addWidget(self.code_edit)

        self.err_lbl = QLabel("")
        self.err_lbl.setStyleSheet("color:#dc3545;font-size:9pt;")
        self.err_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.err_lbl)

        btn = QPushButton("确认绑定")
        btn.setFixedHeight(38)
        btn.setStyleSheet(btn_primary_qss(radius=6))
        btn.clicked.connect(self._verify)
        layout.addWidget(btn)

    def _verify(self):
        code = self.code_edit.text().strip()
        if self._totp.verify(code, valid_window=1):
            self.accept()
        else:
            self.err_lbl.setText("验证码错误，请重新输入")
            self.code_edit.clear()
            self.code_edit.setFocus()
