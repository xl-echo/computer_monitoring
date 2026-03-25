#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ui/dialogs/risk_list.py
高风险连接列表弹窗 —— 分页展示今日高风险连接，支持点击查看详情
"""

import sqlite3
from datetime import date

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt

from ui.theme import RISK_LABELS, btn_primary_qss
from services.description import build_friendly_action
from ui.dialogs.connection_detail import ConnectionDetailDialog


class RiskListDialog(QDialog):
    """
    分页列出今日高风险（risk_level >= 3）连接记录。
    每页 20 条，双击或点击"详情"按钮查看单条详情。
    """

    PAGE_SIZE = 20

    def __init__(self, db_path: str, parent=None):
        super().__init__(parent)
        self._db_path = db_path
        self._page = 0
        self._all_rows: list = []

        self.setWindowTitle("🔴 高风险连接列表（今日）")
        self.setMinimumSize(900, 600)
        self.resize(1000, 660)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 10)
        layout.setSpacing(8)

        # 标题栏
        hdr = QFrame()
        hdr.setStyleSheet("background:#b71c1c;border-radius:6px;")
        hdr_l = QHBoxLayout(hdr)
        hdr_l.setContentsMargins(14, 10, 14, 10)
        hdr_l.addWidget(
            self._make_label("🔴 高风险连接列表（今日）",
                             "color:white;font-size:11pt;font-weight:bold;")
        )
        hdr_l.addStretch()
        self._count_lbl = self._make_label("共 0 条",
                                           "color:rgba(255,255,255,0.8);font-size:9pt;")
        hdr_l.addWidget(self._count_lbl)
        layout.addWidget(hdr)

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["时间", "应用程序", "行为说明", "目标", "方向", "风险", "操作"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 80)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            "QTableWidget{alternate-background-color:#fff5f5;border:none;font-size:9pt;}"
        )
        self.table.doubleClicked.connect(self._on_dblclick)
        layout.addWidget(self.table)

        # 分页
        page_row = QHBoxLayout()
        self._prev_btn = self._make_page_btn("◀ 上一页")
        self._prev_btn.clicked.connect(self._prev_page)
        self._page_lbl = self._make_label("第 1 页", "font-size:9pt;color:#666;")
        self._next_btn = self._make_page_btn("下一页 ▶")
        self._next_btn.clicked.connect(self._next_page)
        page_row.addStretch()
        page_row.addWidget(self._prev_btn)
        page_row.addWidget(self._page_lbl)
        page_row.addWidget(self._next_btn)
        page_row.addStretch()
        layout.addLayout(page_row)

        # 关闭
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("关  闭")
        close_btn.setFixedSize(90, 34)
        close_btn.setStyleSheet(btn_primary_qss(radius=5))
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        self._load_data()

    # ── 数据加载 ─────────────────────────────────────────────
    def _load_data(self):
        today = date.today().strftime("%Y-%m-%d")
        try:
            con = sqlite3.connect(self._db_path)
            con.row_factory = sqlite3.Row
            c = con.cursor()
            c.execute(
                "SELECT * FROM connections "
                "WHERE timestamp LIKE ? AND risk_level>=3 "
                "ORDER BY timestamp DESC LIMIT 500",
                (today + "%",),
            )
            self._all_rows = [dict(r) for r in c.fetchall()]
            con.close()
        except Exception:
            self._all_rows = []
        self._count_lbl.setText("共 {} 条（今日）".format(len(self._all_rows)))
        self._page = 0
        self._render_page()

    # ── 渲染当前页 ───────────────────────────────────────────
    def _render_page(self):
        start = self._page * self.PAGE_SIZE
        end = start + self.PAGE_SIZE
        page_rows = self._all_rows[start:end]
        total = max(1, (len(self._all_rows) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self._page_lbl.setText("第 {}/{} 页".format(self._page + 1, total))
        self._prev_btn.setEnabled(self._page > 0)
        self._next_btn.setEnabled(end < len(self._all_rows))

        self.table.setRowCount(0)
        for i, row in enumerate(page_rows):
            self.table.insertRow(i)
            risk_lv = row.get("risk_level", 0)
            risk_text = RISK_LABELS[min(risk_lv, 4)]
            direction_cn = "向外发送" if row.get("direction") == "outbound" else "接收数据"
            cells = [
                row.get("timestamp", ""),
                row.get("app_name", row.get("process_name", "")),
                build_friendly_action(row),
                row.get("target", row.get("remote_ip", "")),
                direction_cn,
                risk_text,
            ]
            for col, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if risk_lv >= 3:
                    item.setForeground(QColor("#c62828"))
                elif risk_lv >= 2:
                    item.setForeground(QColor("#f57f17"))
                self.table.setItem(i, col, item)

            detail_btn = QPushButton("详情")
            detail_btn.setFixedSize(68, 26)
            detail_btn.setStyleSheet(
                "QPushButton{background:#1565c0;color:white;border:none;"
                "border-radius:4px;font-size:8pt;}"
                "QPushButton:hover{background:#0d47a1;}"
            )
            detail_btn.clicked.connect(lambda _, r=row: self._show_detail(r))
            self.table.setCellWidget(i, 6, detail_btn)

    # ── 分页控制 ─────────────────────────────────────────────
    def _prev_page(self):
        if self._page > 0:
            self._page -= 1
            self._render_page()

    def _next_page(self):
        if (self._page + 1) * self.PAGE_SIZE < len(self._all_rows):
            self._page += 1
            self._render_page()

    def _on_dblclick(self, index):
        idx = self._page * self.PAGE_SIZE + index.row()
        if 0 <= idx < len(self._all_rows):
            self._show_detail(self._all_rows[idx])

    def _show_detail(self, row_data: dict):
        ConnectionDetailDialog(row_data, self).exec()

    # ── 工厂 ─────────────────────────────────────────────────
    @staticmethod
    def _make_label(text: str, style: str = "") -> "QLabel":
        from PyQt6.QtWidgets import QLabel
        lbl = QLabel(text)
        if style:
            lbl.setStyleSheet(style)
        return lbl

    @staticmethod
    def _make_page_btn(text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(90, 30)
        btn.setStyleSheet(
            "QPushButton{background:#e0e0e0;color:#333;border:none;border-radius:5px;font-size:9pt;}"
            "QPushButton:hover{background:#bdbdbd;}"
            "QPushButton:disabled{color:#aaa;}"
        )
        return btn
