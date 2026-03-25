#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ui/widgets/stat_card.py
统计卡片组件 —— 带大数字和左色块，可选点击回调
"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt
from typing import Callable, Optional


class StatCard(QFrame):
    """
    可复用统计卡片。
    Args:
        icon:      Emoji 图标
        title:     标题文字
        value:     初始数值（字符串）
        accent:    左色块颜色（CSS 颜色字符串）
        clickable: 是否可点击
    """

    def __init__(
        self,
        icon: str,
        title: str,
        value: str,
        accent: str,
        clickable: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self._clickable = clickable
        self._click_callback: Optional[Callable] = None
        self._accent = accent

        self.setFixedHeight(90)
        self.setStyleSheet(
            "StatCard {{background:white;border-radius:10px;"
            "border-left:4px solid {accent};}}".format(accent=accent)
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        # 顶行：图标 + 标题
        top_row = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size:18pt;")
        top_row.addWidget(icon_lbl)
        top_row.addStretch()
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            "font-size:8pt;color:#888;font-weight:bold;letter-spacing:1px;"
        )
        top_row.addWidget(title_lbl)
        layout.addLayout(top_row)

        # 数值
        value_style = "font-size:22pt;font-weight:bold;color:{};".format(accent)
        if clickable:
            value_style += "text-decoration:underline;"
        self._value_lbl = QLabel(value)
        self._value_lbl.setStyleSheet(value_style)
        layout.addWidget(self._value_lbl)

        if clickable:
            hint = QLabel("点击查看详情")
            hint.setStyleSheet("font-size:7pt;color:#aaa;")
            layout.addWidget(hint)
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_click_callback(self, cb: Callable):
        self._click_callback = cb

    def mousePressEvent(self, event):
        if self._clickable and self._click_callback:
            self._click_callback()
        super().mousePressEvent(event)

    def set_value(self, v):
        self._value_lbl.setText(str(v))

    def get_value(self) -> int:
        try:
            return int(self._value_lbl.text())
        except ValueError:
            return 0
