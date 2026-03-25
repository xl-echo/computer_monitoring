#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ui/dialogs/archive_view.py
归档文件查看弹窗 —— 以等宽字体展示归档文本内容
"""

import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTextEdit
)

from ui.theme import btn_primary_qss


class ArchiveViewDialog(QDialog):
    """只读展示单个归档文本文件"""

    def __init__(self, filepath: str, parent=None):
        super().__init__(parent)
        fname = os.path.basename(filepath)
        self.setWindowTitle("归档记录 — {}".format(fname))
        self.setMinimumSize(820, 620)
        self.resize(920, 700)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 10)
        layout.setSpacing(8)

        # 标题栏
        hdr = QFrame()
        hdr.setStyleSheet("background:#0d47a1;border-radius:6px;")
        hdr_l = QHBoxLayout(hdr)
        hdr_l.setContentsMargins(14, 10, 14, 10)
        title_lbl = QLabel("📄 {}".format(fname))
        title_lbl.setStyleSheet("color:white;font-size:11pt;font-weight:bold;")
        hdr_l.addWidget(title_lbl)
        layout.addWidget(hdr)

        # 文本区
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setStyleSheet(
            "QTextEdit{background:#1e1e2e;color:#cdd6f4;"
            "font-family:Consolas,'Microsoft YaHei',monospace;"
            "font-size:9pt;border-radius:6px;padding:10px;}"
        )
        layout.addWidget(text_edit)

        # 关闭
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("关  闭")
        close_btn.setFixedSize(90, 34)
        close_btn.setStyleSheet(btn_primary_qss(radius=5))
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        # 加载文件
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                text_edit.setPlainText(f.read())
        except Exception as e:
            text_edit.setPlainText("读取失败：{}".format(e))
