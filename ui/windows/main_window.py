#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ui/windows/main_window.py
主监控窗口 —— 顶部导航栏、统计卡片、实时监控表格、归档记录
"""

import os
import sys
import subprocess
from datetime import date

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QStatusBar, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QListWidget, QListWidgetItem, QSystemTrayIcon, QMenu, QMessageBox,
    QDialog
)
from PyQt6.QtGui import (
    QAction, QIcon, QPixmap, QPainter, QBrush, QColor, QPen
)
from PyQt6.QtCore import Qt, QTimer, QSize

from core.database import DatabaseManager
from services.archive import ArchiveManager
from services.monitor import NetworkMonitorThread
from services.description import build_friendly_action
from ui.theme import (
    MAIN_QSS, NAV_QSS, RISK_LABELS, Color,
    btn_primary_qss, btn_danger_qss, btn_ghost_qss
)
from ui.widgets.stat_card import StatCard
from ui.dialogs.risk_list import RiskListDialog
from ui.dialogs.archive_view import ArchiveViewDialog
from ui.windows.login_window import LoginWindow


class MainWindow(QMainWindow):
    """
    主窗口。构造时触发登录流程，登录取消则设置 _login_cancelled=True。
    """

    # 实时监控表最多保留的行数
    TABLE_MAX_ROWS = 300
    # 统计刷新间隔（毫秒）
    STATS_INTERVAL = 5000
    # 归档列表刷新间隔（毫秒）
    ARCHIVE_INTERVAL = 30000

    def __init__(self, db_path: str, log_dir: str):
        super().__init__()
        self.db_path = db_path
        self.log_dir = log_dir
        self.db_manager = DatabaseManager(db_path)
        self.archive_manager = ArchiveManager(log_dir)
        self.monitor_thread: "NetworkMonitorThread | None" = None
        self._monitoring = False
        self._logged_user = ""
        self._login_cancelled = False

        if not self._do_login():
            self._login_cancelled = True
            return

        self._setup_ui()
        self._setup_tray()

        self._stats_timer = QTimer(self)
        self._stats_timer.timeout.connect(self._refresh_stats)
        self._stats_timer.start(self.STATS_INTERVAL)
        self._refresh_stats()

        self._archive_timer = QTimer(self)
        self._archive_timer.timeout.connect(self._refresh_archive_list)
        self._archive_timer.start(self.ARCHIVE_INTERVAL)

    # ── 登录 ─────────────────────────────────────────────────
    def _do_login(self) -> bool:
        login = LoginWindow(self.db_manager)
        if login.exec() == QDialog.DialogCode.Accepted:
            self._logged_user = login.username
            return True
        return False

    # ── UI 搭建 ──────────────────────────────────────────────
    def _setup_ui(self):
        self.setWindowTitle("网络监控系统 v1.0.0  —  {}".format(self._logged_user))
        self.setMinimumSize(1200, 780)
        self.setStyleSheet(MAIN_QSS)

        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(12)
        root.setContentsMargins(16, 14, 16, 10)

        root.addWidget(self._build_nav())
        root.addLayout(self._build_today_row())
        root.addLayout(self._build_cards())
        root.addWidget(self._build_tabs())
        self._build_statusbar()
        self._refresh_archive_list()

    # ── 导航栏 ───────────────────────────────────────────────
    def _build_nav(self) -> QFrame:
        nav = QFrame()
        nav.setFixedHeight(56)
        nav.setStyleSheet(NAV_QSS)
        layout = QHBoxLayout(nav)
        layout.setContentsMargins(20, 0, 16, 0)
        layout.setSpacing(12)

        logo = QLabel("🌐  网络监控系统 v1.0.0")
        logo.setStyleSheet(
            "font-size:14pt;font-weight:bold;color:white;letter-spacing:1px;"
        )
        layout.addWidget(logo)
        layout.addStretch()

        # 用户下拉按钮
        self._user_btn = QPushButton("👤  {}  ▾".format(self._logged_user))
        self._user_btn.setStyleSheet(
            "QPushButton{font-size:9pt;color:rgba(255,255,255,0.9);font-weight:bold;"
            "background:rgba(255,255,255,0.15);border-radius:12px;padding:4px 14px;border:none;}"
            "QPushButton:hover{background:rgba(255,255,255,0.28);}"
        )
        self._user_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._user_btn.clicked.connect(self._show_user_menu)
        layout.addWidget(self._user_btn)

        # 开始/停止监控
        self.toggle_btn = QPushButton("▶  开始监控")
        self.toggle_btn.setFixedSize(130, 34)
        self._apply_toggle_style(False)
        self.toggle_btn.clicked.connect(self._toggle_monitoring)
        layout.addWidget(self.toggle_btn)

        # 静默运行
        self.silent_btn = QPushButton("🔕  静默运行")
        self.silent_btn.setFixedSize(115, 34)
        self.silent_btn.setCheckable(True)
        self.silent_btn.setStyleSheet(
            "QPushButton{background:rgba(255,255,255,0.18);color:rgba(255,255,255,0.85);"
            "border:2px solid rgba(255,255,255,0.45);border-radius:8px;"
            "font-size:9pt;font-weight:bold;}"
            "QPushButton:hover{background:rgba(255,255,255,0.3);}"
            "QPushButton:checked{background:rgba(255,200,0,0.35);"
            "color:#fff;border-color:rgba(255,200,0,0.8);}"
        )
        self.silent_btn.clicked.connect(self._toggle_silent)
        layout.addWidget(self.silent_btn)

        return nav

    def _build_today_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        lbl = QLabel(
            "📅  今日统计  —  {}".format(date.today().strftime("%Y年%m月%d日"))
        )
        lbl.setStyleSheet("font-size:9pt;color:#666;font-weight:bold;padding:2px 0;")
        row.addWidget(lbl)
        row.addStretch()
        return row

    def _build_cards(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(12)
        self._card_total    = StatCard("📡", "总连接数", "0", Color.PRIMARY)
        self._card_outbound = StatCard("📤", "向外发送", "0", Color.SUCCESS)
        self._card_inbound  = StatCard("📥", "接收数据", "0", Color.TEAL)
        self._card_risk     = StatCard("🔴", "高风险",   "0", Color.DANGER, clickable=True)
        self._card_risk.set_click_callback(self._show_high_risk_list)
        for card in [self._card_total, self._card_outbound,
                     self._card_inbound, self._card_risk]:
            layout.addWidget(card)
        return layout

    def _build_tabs(self) -> QTabWidget:
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)

        # Tab 1：实时监控
        monitor_page = QWidget()
        monitor_page.setStyleSheet("background:white;")
        m_layout = QVBoxLayout(monitor_page)
        m_layout.setContentsMargins(0, 0, 0, 0)
        m_layout.setSpacing(0)

        self.monitor_table = QTableWidget()
        self.monitor_table.setColumnCount(7)
        self.monitor_table.setHorizontalHeaderLabels(
            ["时间", "应用", "行为", "目标", "分类", "方向", "风险"]
        )
        self.monitor_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.monitor_table.verticalHeader().setVisible(False)
        self.monitor_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.monitor_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.monitor_table.setAlternatingRowColors(True)
        self.monitor_table.setStyleSheet(
            "QTableWidget{alternate-background-color:#f7f9ff;}"
        )
        m_layout.addWidget(self.monitor_table)
        self.tab_widget.addTab(monitor_page, "📊  实时监控")

        # Tab 2：归档记录
        archive_page = QWidget()
        archive_page.setStyleSheet("background:white;")
        a_layout = QVBoxLayout(archive_page)
        a_layout.setContentsMargins(12, 10, 12, 10)
        a_layout.setSpacing(8)

        tip = QLabel("📁  双击文件名打开完整归档内容")
        tip.setStyleSheet("font-size:9pt;color:#888;padding:2px 0;")
        a_layout.addWidget(tip)

        self.archive_list = QListWidget()
        self.archive_list.setStyleSheet("""
            QListWidget{border:1px solid #e8ecf0;border-radius:6px;
                        background:#fafbfc;font-size:9pt;}
            QListWidget::item{padding:10px 14px;border-bottom:1px solid #f0f2f5;}
            QListWidget::item:hover{background:#e8f0fe;color:#1565c0;}
            QListWidget::item:selected{background:#1565c0;color:white;border-radius:4px;}
        """)
        self.archive_list.itemDoubleClicked.connect(self._on_archive_dblclick)
        a_layout.addWidget(self.archive_list)

        open_btn = QPushButton("📂  打开归档目录")
        open_btn.setFixedHeight(34)
        open_btn.setStyleSheet(
            "QPushButton{background:#e8f0fe;color:#1565c0;border:none;"
            "border-radius:6px;font-size:9pt;font-weight:bold;padding:0 16px;}"
            "QPushButton:hover{background:#d0e4fd;}"
        )
        open_btn.clicked.connect(self._open_log_dir)
        a_layout.addWidget(open_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        self.tab_widget.addTab(archive_page, "📁  归档记录")

        return self.tab_widget

    def _build_statusbar(self):
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet(
            "QStatusBar{background:#f0f2f5;color:#666;font-size:8pt;"
            "border-top:1px solid #dde0e5;}"
        )
        self.status_bar.showMessage(
            "就绪  —  用户：{}  |  今日 {}".format(
                self._logged_user, date.today().strftime("%Y-%m-%d")
            )
        )
        self.setStatusBar(self.status_bar)

    # ── 系统托盘 ─────────────────────────────────────────────
    def _setup_tray(self):
        icon = self._load_app_icon()
        self.setWindowIcon(icon)
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(icon)
        menu = QMenu()
        menu.addAction(QAction("显示窗口", self, triggered=self.show))
        menu.addAction(QAction("隐藏窗口", self, triggered=self.hide))
        menu.addSeparator()
        menu.addAction(QAction("退出", self, triggered=self._quit))
        self.tray.setContextMenu(menu)
        self.tray.show()
        self.tray.activated.connect(self._on_tray_activated)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show()
            self.raise_()
            self.activateWindow()
            if self.silent_btn.isChecked():
                self.silent_btn.setChecked(False)
                self.silent_btn.setText("🔕  静默运行")

    def _load_app_icon(self) -> QIcon:
        # frozen 模式：PyInstaller 将 assets 解压到 sys._MEIPASS/assets/
        # 源码模式：相对 ui/windows/ 向上两级找 assets/
        candidates = []
        if getattr(sys, "frozen", False):
            meipass = getattr(sys, "_MEIPASS", "")
            if meipass:
                candidates += [
                    os.path.join(meipass, "assets", "app_icon.ico"),
                    os.path.join(meipass, "assets", "app_icon.png"),
                ]
        # 源码模式 & 兜底：从 exe / 脚本所在目录向上找
        app_dir = _get_app_dir()
        root_dir = os.path.dirname(os.path.dirname(app_dir))  # v1.0.0/
        candidates += [
            os.path.join(root_dir, "assets", "app_icon.ico"),
            os.path.join(root_dir, "assets", "app_icon.png"),
            os.path.join(app_dir, "app_icon.ico"),
            os.path.join(app_dir, "app_icon.png"),
        ]
        for fp in candidates:
            if os.path.exists(fp):
                pix = QPixmap(fp)
                if not pix.isNull():
                    return QIcon(pix)
        # 默认绘制图标
        pix = QPixmap(64, 64)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(QColor(Color.PRIMARY)))
        p.setPen(QPen(Qt.PenStyle.NoPen))
        p.drawEllipse(0, 0, 64, 64)
        p.setPen(QPen(QColor("white"), 3))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(20, 20, 24, 24)
        p.drawEllipse(28, 28, 8, 8)
        p.end()
        return QIcon(pix)

    # ── 统计刷新 ─────────────────────────────────────────────
    def _refresh_stats(self):
        s = self.db_manager.get_today_stats()
        self._card_total.set_value(s.total)
        self._card_outbound.set_value(s.outbound)
        self._card_inbound.set_value(s.inbound)
        self._card_risk.set_value(s.risk_high)

    # ── 高风险列表弹窗 ───────────────────────────────────────
    def _show_high_risk_list(self):
        if self._card_risk.get_value() == 0:
            QMessageBox.information(self, "高风险", "今日暂无高风险连接记录")
            return
        RiskListDialog(self.db_path, self).exec()

    # ── 归档列表 ─────────────────────────────────────────────
    def _refresh_archive_list(self):
        files = self.archive_manager.list_archive_files()
        self.archive_list.clear()
        today_str = date.today().strftime("%Y-%m-%d")
        for fp in files:
            fname = os.path.basename(fp)
            date_part = fname.replace("monitor_", "").replace(".txt", "")
            try:
                kb = os.path.getsize(fp) / 1024
                size_str = "{:.0f} KB".format(kb) if kb < 1024 \
                    else "{:.1f} MB".format(kb / 1024)
            except Exception:
                size_str = ""
            is_today = date_part == today_str
            tag = "  🔴 今日" if is_today else ""
            display = "📄  {}{}    {}".format(date_part, tag, size_str)
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, fp)
            if is_today:
                item.setForeground(QColor(Color.PRIMARY))
                f = item.font()
                f.setBold(True)
                item.setFont(f)
            self.archive_list.addItem(item)

        if not files:
            placeholder = QListWidgetItem("  暂无归档记录，开始监控后将自动生成")
            placeholder.setForeground(QColor("#aaa"))
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self.archive_list.addItem(placeholder)

    def _on_archive_dblclick(self, item: QListWidgetItem):
        fp = item.data(Qt.ItemDataRole.UserRole)
        if fp and os.path.exists(fp):
            ArchiveViewDialog(fp, self).exec()

    def _open_log_dir(self):
        try:
            subprocess.Popen(
                ["explorer", self.log_dir],
                creationflags=0x08000000
            )
        except Exception:
            pass

    # ── 监控控制 ─────────────────────────────────────────────
    def _toggle_monitoring(self):
        if self._monitoring:
            self._stop_monitoring()
        else:
            self._start_monitoring()

    def _start_monitoring(self):
        if self.monitor_thread and self.monitor_thread.isRunning():
            return
        self._monitoring = True
        self._apply_toggle_style(True)
        self.toggle_btn.setEnabled(False)
        self.monitor_thread = NetworkMonitorThread(
            self.db_manager, self.archive_manager
        )
        self.monitor_thread.new_connection.connect(self._on_new_conn)
        self.monitor_thread.started.connect(
            lambda: self.toggle_btn.setEnabled(True)
        )
        self.monitor_thread.start()
        self.status_bar.showMessage(
            "监控中...  —  用户：{}".format(self._logged_user)
        )
        self.tab_widget.setCurrentIndex(0)

    def _stop_monitoring(self):
        if not self.monitor_thread:
            return
        self.toggle_btn.setEnabled(False)
        self.status_bar.showMessage("正在停止监控...")
        self.monitor_thread.finished.connect(self._on_thread_stopped)
        self.monitor_thread.stop_request()

    def _on_thread_stopped(self):
        self.monitor_thread = None
        self._monitoring = False
        self._apply_toggle_style(False)
        self.toggle_btn.setEnabled(True)
        self.status_bar.showMessage(
            "监控已停止  —  用户：{}".format(self._logged_user)
        )
        self._refresh_archive_list()
        self._refresh_stats()

    def _apply_toggle_style(self, monitoring: bool):
        if monitoring:
            self.toggle_btn.setText("⏹  停止监控")
            self.toggle_btn.setStyleSheet(btn_danger_qss())
        else:
            self.toggle_btn.setText("▶  开始监控")
            self.toggle_btn.setStyleSheet(btn_ghost_qss())

    # ── 实时数据更新 ─────────────────────────────────────────
    def _on_new_conn(self, d: dict):
        row = self.monitor_table.rowCount()
        self.monitor_table.insertRow(row)
        direction_cn = "向外发送" if d.get("direction") == "outbound" else "接收数据"
        items = [
            d.get("timestamp", ""),
            d.get("app_name", d.get("process_name", "")),
            build_friendly_action(d),
            d.get("target", d.get("remote_ip", "")),
            d.get("category", ""),
            direction_cn,
        ]
        for col, text in enumerate(items):
            self.monitor_table.setItem(row, col, QTableWidgetItem(text))

        risk = d.get("risk_level", 0)
        risk_item = QTableWidgetItem(RISK_LABELS[min(risk, 4)])
        if risk >= 3:
            risk_item.setForeground(QColor(Color.DANGER))
        elif risk >= 2:
            risk_item.setForeground(QColor(Color.WARNING))
        self.monitor_table.setItem(row, 6, risk_item)

        if self.monitor_table.rowCount() > self.TABLE_MAX_ROWS:
            self.monitor_table.removeRow(0)
        self.monitor_table.scrollToBottom()

        if row % 10 == 0:
            self._refresh_stats()

    # ── 用户菜单 ─────────────────────────────────────────────
    def _show_user_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu{background:white;border:1px solid #dde0e5;
                  border-radius:8px;padding:4px 0;font-size:9pt;}
            QMenu::item{padding:9px 20px;color:#333;}
            QMenu::item:selected{background:#e8f0fe;color:#1565c0;}
            QMenu::separator{height:1px;background:#eee;margin:4px 10px;}
        """)
        user_act = menu.addAction("👤  当前用户：{}".format(self._logged_user))
        user_act.setEnabled(False)
        menu.addSeparator()
        logout_act = menu.addAction("🔄  退出登录（切换账户）")
        menu.addSeparator()
        quit_act = menu.addAction("🚪  退出程序")

        pos = self._user_btn.mapToGlobal(self._user_btn.rect().bottomLeft())
        action = menu.exec(pos)
        if action == logout_act:
            self._logout()
        elif action == quit_act:
            self._quit()

    def _logout(self):
        if self.monitor_thread and self.monitor_thread.isRunning():
            self.monitor_thread.stop_request()
            self.monitor_thread.wait(2000)
            self.monitor_thread = None
        self._monitoring = False
        self.hide()

        login = LoginWindow(self.db_manager)
        if login.exec() == QDialog.DialogCode.Accepted:
            self._logged_user = login.username
            self._user_btn.setText("👤  {}  ▾".format(self._logged_user))
            self.setWindowTitle(
                "网络监控系统 v1.0.0  —  {}".format(self._logged_user)
            )
            self.status_bar.showMessage(
                "就绪  —  用户：{}  |  今日 {}".format(
                    self._logged_user, date.today().strftime("%Y-%m-%d")
                )
            )
            self._refresh_stats()
            self._refresh_archive_list()
            self.show()
            self.raise_()
            self.activateWindow()
        else:
            self._quit()

    # ── 静默运行 ─────────────────────────────────────────────
    def _toggle_silent(self):
        if self.silent_btn.isChecked():
            self.silent_btn.setText("🔔  退出静默")
            self.hide()
            self.tray.showMessage(
                "网络监控系统 v1.0.0",
                "程序已切换到静默运行模式，在系统托盘中继续工作。\n单击托盘图标可恢复窗口。",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )
        else:
            self.silent_btn.setText("🔕  静默运行")
            self.show()
            self.raise_()
            self.activateWindow()

    # ── 退出 ─────────────────────────────────────────────────
    def _quit(self):
        if self.monitor_thread:
            self.monitor_thread.stop_request()
        if hasattr(self, "tray") and self.tray:
            self.tray.hide()
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self, "确认退出", "确定要退出网络监控系统吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._quit()
            event.accept()
        else:
            event.ignore()


# ── 工具函数 ─────────────────────────────────────────────────
def _get_app_dir() -> str:
    """
    frozen 模式：返回 exe 所在目录（安装目录）
    源码模式：返回 ui/windows/ 目录
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))
