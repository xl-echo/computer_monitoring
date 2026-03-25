#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ui/theme.py
全局样式常量 —— 所有颜色、QSS 字符串集中在此处定义
修改此文件即可统一调整整套 UI 风格
"""

# ── 颜色调色板 ───────────────────────────────────────────────
class Color:
    PRIMARY      = "#0d47a1"
    PRIMARY_DARK = "#0a3880"
    PRIMARY_MID  = "#1565c0"
    PRIMARY_LIGHT= "#1976d2"
    DANGER       = "#c62828"
    DANGER_DARK  = "#b71c1c"
    WARNING      = "#f57f17"
    SUCCESS      = "#2e7d32"
    TEAL         = "#00838f"
    BG           = "#f0f2f5"
    WHITE        = "#ffffff"
    TEXT_MAIN    = "#1a1a2e"
    TEXT_SUB     = "#555555"
    TEXT_HINT    = "#888888"
    BORDER       = "#dde0e5"


# ── 风险等级映射 ─────────────────────────────────────────────
RISK_LABELS = ["✅ 安全", "⚡ 低风险", "⚠️ 中风险", "🔴 高风险", "🆘 极高风险"]
RISK_COLORS = [Color.SUCCESS, Color.WARNING, Color.WARNING, Color.DANGER, Color.DANGER]


# ── 全局 QSS ─────────────────────────────────────────────────
MAIN_QSS = """
    QMainWindow, QWidget#central {{ background: {bg}; }}
    QTabWidget::pane {{
        border: none; background: white;
        border-radius: 0 8px 8px 8px;
    }}
    QTabBar::tab {{
        background: #dce3ee; color: #555;
        padding: 9px 24px; font-size: 9pt; font-weight: bold;
        border-top-left-radius: 6px; border-top-right-radius: 6px;
        margin-right: 3px;
    }}
    QTabBar::tab:selected {{ background: white; color: {primary}; }}
    QTabBar::tab:hover:!selected {{ background: #cdd5e5; }}
    QTableWidget {{
        background: white; border: none;
        gridline-color: #f0f0f0; font-size: 9pt;
    }}
    QTableWidget::item {{ padding: 5px; border-bottom: 1px solid #f5f5f5; }}
    QTableWidget::item:selected {{ background: #e3f0ff; color: {primary}; }}
    QHeaderView::section {{
        background: #f8f9fa; padding: 8px; border: none;
        border-bottom: 2px solid {primary};
        font-weight: bold; color: #444; font-size: 9pt;
    }}
    QScrollBar:vertical {{ background:#f5f5f5; width:8px; border-radius:4px; }}
    QScrollBar::handle:vertical {{ background:#c0c8d8; border-radius:4px; min-height:30px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0; }}
""".format(bg=Color.BG, primary=Color.PRIMARY)


NAV_QSS = (
    "QFrame{{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
    "stop:0 {c0},stop:0.6 {c1},stop:1 {c2});"
    "border-radius:10px;}}"
).format(c0=Color.PRIMARY, c1=Color.PRIMARY_MID, c2=Color.PRIMARY_LIGHT)


def btn_primary_qss(radius: int = 8) -> str:
    return (
        "QPushButton{{background:{c};color:white;border:none;"
        "border-radius:{r}px;font-size:10pt;font-weight:bold;}}"
        "QPushButton:hover{{background:{d};}}"
    ).format(c=Color.PRIMARY, d=Color.PRIMARY_DARK, r=radius)


def btn_danger_qss(radius: int = 8) -> str:
    return (
        "QPushButton{{background:{c};color:white;border:none;"
        "border-radius:{r}px;font-size:10pt;font-weight:bold;}}"
        "QPushButton:hover{{background:{d};}}"
    ).format(c=Color.DANGER, d=Color.DANGER_DARK, r=radius)


def btn_ghost_qss() -> str:
    """导航栏半透明幽灵按钮"""
    return (
        "QPushButton{background:rgba(255,255,255,0.25);color:white;"
        "border:2px solid rgba(255,255,255,0.6);"
        "border-radius:8px;font-size:10pt;font-weight:bold;}"
        "QPushButton:hover{background:rgba(255,255,255,0.4);}"
    )
