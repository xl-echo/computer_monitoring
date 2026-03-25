#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ui/dialogs/connection_detail.py
连接详情弹窗 —— 展示单条连接记录的完整信息
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QWidget
)
from PyQt6.QtCore import Qt

from ui.theme import RISK_LABELS, btn_primary_qss
from services.description import build_plain_description, build_friendly_action, build_params_description


class ConnectionDetailDialog(QDialog):
    """展示一条连接记录所有字段，供用户阅读"""

    def __init__(self, row_data: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("连接详情")
        self.setMinimumSize(580, 480)
        self.resize(640, 520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(10)

        # 顶部标题栏
        hdr = QFrame()
        hdr.setStyleSheet("background:#0d47a1;border-radius:6px;")
        hdr_l = QHBoxLayout(hdr)
        hdr_l.setContentsMargins(14, 10, 14, 10)
        risk = row_data.get("risk_level", 0)
        risk_text = RISK_LABELS[min(risk, 4)]
        title_lbl = QLabel(
            "🔍  {}  {}".format(row_data.get("app_name", ""), risk_text)
        )
        title_lbl.setStyleSheet("color:white;font-size:11pt;font-weight:bold;")
        hdr_l.addWidget(title_lbl)
        layout.addWidget(hdr)

        # 字段行工厂
        def make_row(label, val):
            row_w = QWidget()
            row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(0, 0, 0, 0)
            row_l.setSpacing(10)
            lbl = QLabel(label)
            lbl.setFixedWidth(110)
            lbl.setStyleSheet("font-size:9pt;color:#555;font-weight:bold;")
            val_lbl = QLabel(str(val) if val else "—")
            val_lbl.setStyleSheet("font-size:9pt;color:#222;")
            val_lbl.setWordWrap(True)
            row_l.addWidget(lbl)
            row_l.addWidget(val_lbl, 1)
            return row_w

        direction_cn = "向外发送" if row_data.get("direction") == "outbound" else "接收数据"
        plain = build_plain_description(row_data)
        req_desc, resp_desc = build_params_description(row_data)

        for label, val in [
            ("🕐 时间",      row_data.get("timestamp", "")),
            ("📱 应用程序",  row_data.get("app_name", "")),
            ("🎯 行为说明",  build_friendly_action(row_data)),
            ("🌐 目标地址",  row_data.get("target", row_data.get("remote_ip", ""))),
            ("📡 连接方向",  direction_cn),
            ("📂 分类",      row_data.get("category", "")),
            ("⚠️ 风险评级", risk_text),
            ("📝 通俗解读",  plain),
            ("📤 请求内容",  req_desc),
            ("📥 响应内容",  resp_desc),
            ("🔌 本机端口",  str(row_data.get("local_port", ""))),
            ("🖥️ 远端地址", "{}:{}".format(
                row_data.get("remote_ip", ""), row_data.get("remote_port", ""))),
            ("⚙️ 进程名称",  "{} (PID {})".format(
                row_data.get("process_name", ""), row_data.get("process_id", ""))),
        ]:
            layout.addWidget(make_row(label, val))

        layout.addStretch()

        # 关闭按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("关  闭")
        close_btn.setFixedSize(90, 34)
        close_btn.setStyleSheet(btn_primary_qss(radius=5))
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)
