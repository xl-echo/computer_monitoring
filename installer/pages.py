#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
installer/pages.py
安装向导各步骤页面（QWizardPage 子类）
"""

import os
import json
import sqlite3
import hashlib
import traceback
from datetime import datetime

from PyQt6.QtWidgets import (
    QWizardPage, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QProgressBar,
    QGroupBox, QFileDialog, QCheckBox, QMessageBox, QApplication
)
from PyQt6.QtCore import QTimer


def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def get_app_dir() -> str:
    import sys
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


# ── 欢迎页 ───────────────────────────────────────────────────
class WelcomePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("欢迎使用网络监控系统 v1.0.0")
        self.setSubTitle("专业级智能网络活动分析平台")
        layout = QVBoxLayout()
        html = (
            "<h2>欢迎使用网络监控系统 v1.0.0</h2>"
            "<p>本系统是一款专业的网络活动智能分析工具，主要功能包括：</p>"
            "<ul>"
            "<li><b>智能行为识别</b>：自动分析网络活动，如 QQ 发消息、Chrome 访问网址等</li>"
            "<li><b>专业可视化界面</b>：现代化 UI，清晰直观</li>"
            "<li><b>多层安全保障</b>：账密登录 + 双因素认证（2FA / TOTP）</li>"
            "<li><b>实时监控能力</b>：实时捕获全部网络连接，自动风险标注</li>"
            "<li><b>静默运行模式</b>：最小化到系统托盘，后台持续监控</li>"
            "</ul>"
            "<p><b>隐私声明：</b>完全本地运行，所有数据仅存本机，不上传任何云端。</p>"
        )
        lbl = QLabel(html)
        lbl.setWordWrap(True)
        layout.addWidget(lbl)
        layout.addStretch()
        self.setLayout(layout)


# ── 许可协议页 ───────────────────────────────────────────────
LICENSE_TEXT = """\
网络监控系统 v1.0.0  最终用户许可协议（EULA）

第一章  使用授权
1.1  本软件授权用户在个人计算机上安装和使用，用于网络活动监控与数据分析。
1.2  本授权为非独占性、不可转让的个人许可。
1.3  用户可制作备份副本，但不得对软件进行反向工程、反编译或反汇编。

第二章  数据安全与隐私保护
2.1  本系统采用纯本地化运行架构，所有数据仅存储于用户本机。
2.2  系统不会将任何监控数据上传至云端服务器或第三方平台。
2.3  本系统仅记录网络连接基本信息（IP、端口、进程名等），不记录通信内容。
2.4  用户须在符合法律法规的前提下使用本系统。

第三章  免责声明
3.1  本软件按"原样"提供，不附带任何明示或暗示的保证。
3.2  开发者不对因使用本软件导致的任何直接或间接损失承担责任。

第四章  合规使用条款
4.1  未经授权监控他人计算机或网络设备违反相关法律法规，严禁此类行为。
4.2  严禁使用本软件侵犯他人隐私权或其他合法权益。

第五章  知识产权
5.1  本软件著作权及相关知识产权归开发者所有。

勾选下方复选框并点击【下一步】即视为您已阅读、理解并接受本协议全部条款。
"""


class LicensePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("最终用户许可协议（EULA）")
        self.setSubTitle("请仔细阅读以下条款，勾选同意后方可继续安装")
        layout = QVBoxLayout()
        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setPlainText(LICENSE_TEXT)
        layout.addWidget(txt)
        self._cb = QCheckBox("我已阅读、理解并同意以上全部许可条款")
        self._cb.toggled.connect(self.completeChanged)
        layout.addWidget(self._cb)
        self.setLayout(layout)

    def isComplete(self):
        return self._cb.isChecked()


# ── 账户配置页 ───────────────────────────────────────────────
class AccountSetupPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("管理员账户配置")
        self.setSubTitle("设置用于登录系统的管理员凭据")
        layout = QFormLayout()
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("管理员用户名（至少 3 个字符）")
        layout.addRow("用户名：", self.username_edit)
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("登录密码（至少 6 位）")
        self.password_edit.textChanged.connect(self._update_strength)
        layout.addRow("密码：", self.password_edit)
        self.confirm_edit = QLineEdit()
        self.confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_edit.setPlaceholderText("再次输入密码")
        layout.addRow("确认密码：", self.confirm_edit)
        self.strength_lbl = QLabel("")
        layout.addRow("密码强度：", self.strength_lbl)
        self.setLayout(layout)

    def _update_strength(self, pwd):
        if not pwd:
            self.strength_lbl.setText("")
            return
        score = sum([
            len(pwd) >= 8,
            any(c.isupper() for c in pwd),
            any(c.islower() for c in pwd),
            any(c.isdigit() for c in pwd),
            any(not c.isalnum() for c in pwd),
        ])
        labels = ["极弱", "弱", "中等", "强", "很强", "极强"]
        colors = ["#d32f2f", "#f57c00", "#fbc02d", "#388e3c", "#1976d2", "#00796b"]
        self.strength_lbl.setText(
            "<b style='color:{}'>{}</b>".format(colors[score], labels[score])
        )

    def validatePage(self):
        u = self.username_edit.text().strip()
        p = self.password_edit.text()
        c = self.confirm_edit.text()
        if len(u) < 3:
            QMessageBox.warning(self, "验证", "用户名长度不能少于 3 个字符。")
            return False
        if len(p) < 6:
            QMessageBox.warning(self, "验证", "密码长度不能少于 6 位。")
            return False
        if p != c:
            QMessageBox.warning(self, "验证", "两次密码不一致。")
            return False
        self.wizard().setProperty("_username", u)
        self.wizard().setProperty("_password", hash_password(p))
        return True


# ── 路径配置页 ───────────────────────────────────────────────
class DirectorySetupPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("系统路径配置")
        self.setSubTitle("指定程序安装目录及数据存储路径")
        layout = QVBoxLayout()
        pf = os.environ.get("ProgramFiles", "C:\\Program Files")
        base = os.path.join(pf, "NetworkMonitor v1.0")
        self.install_edit = self._row(layout, "程序安装目录", base)
        self.data_edit    = self._row(layout, "数据库文件存储目录", os.path.join(base, "data"))
        self.log_edit     = self._row(layout, "运行日志归档目录",   os.path.join(base, "logs"))
        layout.addStretch()
        self.setLayout(layout)

    def _row(self, parent, title, default):
        grp = QGroupBox(title)
        row = QHBoxLayout()
        edit = QLineEdit(default)
        btn = QPushButton("浏览...")
        btn.clicked.connect(lambda _, e=edit, t=title: self._browse(e, t))
        row.addWidget(edit)
        row.addWidget(btn)
        grp.setLayout(row)
        parent.addWidget(grp)
        return edit

    def _browse(self, edit, title):
        path = QFileDialog.getExistingDirectory(self, "选择" + title, edit.text())
        if path:
            edit.setText(path)

    def validatePage(self):
        for edit, name in [
            (self.install_edit, "安装目录"),
            (self.data_edit,   "数据目录"),
            (self.log_edit,    "日志目录"),
        ]:
            p = edit.text().strip()
            if not p:
                QMessageBox.warning(self, "路径验证", name + "不能为空。")
                return False
            try:
                os.makedirs(p, exist_ok=True)
                test = os.path.join(p, ".write_test")
                with open(test, "w") as f:
                    f.write("ok")
                os.remove(test)
            except Exception as e:
                QMessageBox.warning(
                    self, "路径验证失败", "目录【{}】不可写：{}".format(name, e)
                )
                return False
        self.wizard().setProperty("_install_dir", self.install_edit.text().strip())
        self.wizard().setProperty("_data_dir",    self.data_edit.text().strip())
        self.wizard().setProperty("_log_dir",     self.log_edit.text().strip())
        return True


# ── 安装进度页 ───────────────────────────────────────────────
class InstallationPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("系统安装")
        self.setSubTitle("正在配置系统环境并初始化数据库，请稍候...")
        self._install_done = False
        layout = QVBoxLayout()
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)
        self.status_lbl = QLabel("正在初始化...")
        layout.addWidget(self.status_lbl)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMinimumHeight(200)
        layout.addWidget(self.log_box)
        self.setLayout(layout)

    def initializePage(self):
        self._install_done = False
        self.progress.setValue(0)
        self.log_box.clear()
        self.status_lbl.setText("正在初始化安装程序...")
        QTimer.singleShot(300, self._run_install)

    def isComplete(self):
        return self._install_done

    def _log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.append("[{}]  {}".format(ts, msg))
        QApplication.processEvents()

    def _step(self, pct, text):
        self.progress.setValue(pct)
        self.status_lbl.setText(text)
        QApplication.processEvents()

    def _run_install(self):
        try:
            wiz = self.wizard()
            username    = wiz.property("_username")    or "admin"
            pwd_hash    = wiz.property("_password")    or hash_password("admin123")
            install_dir = wiz.property("_install_dir") or get_app_dir()
            data_dir    = wiz.property("_data_dir")    or os.path.join(get_app_dir(), "data")
            log_dir     = wiz.property("_log_dir")     or os.path.join(get_app_dir(), "logs")

            self._step(5, "正在创建系统目录...")
            for d in [install_dir, data_dir, log_dir]:
                os.makedirs(d, exist_ok=True)
                self._log("目录已就绪：" + d)

            self._step(20, "正在初始化数据库...")
            db_path = os.path.join(data_dir, "network_monitor.db")
            conn = sqlite3.connect(db_path)
            cur  = conn.cursor()
            cur.execute("""CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                totp_secret TEXT,
                created_at TEXT,
                is_admin INTEGER DEFAULT 0)""")
            self._log("数据表 [users] 就绪")

            cur.execute("""CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY, value TEXT)""")
            self._log("数据表 [settings] 就绪")

            self._step(40, "正在创建连接记录表...")
            cur.execute("""CREATE TABLE IF NOT EXISTS connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                local_ip TEXT, local_port INTEGER,
                remote_ip TEXT, remote_port INTEGER,
                process_name TEXT, process_id INTEGER,
                direction TEXT, status TEXT,
                bytes_sent INTEGER DEFAULT 0, bytes_recv INTEGER DEFAULT 0,
                app_name TEXT, action_type TEXT, target TEXT,
                description TEXT, category TEXT,
                risk_level INTEGER DEFAULT 0, icon TEXT, full_params TEXT)""")
            self._log("数据表 [connections] 就绪")

            self._step(55, "正在创建数据库索引...")
            for idx, col in [("idx_ts","timestamp"), ("idx_rip","remote_ip"),
                              ("idx_proc","process_name"), ("idx_cat","category")]:
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS {} ON connections({})".format(idx, col)
                )
            self._log("数据库索引创建完成")

            self._step(68, "正在写入管理员账户...")
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute(
                "INSERT OR IGNORE INTO users "
                "(username, password_hash, created_at, is_admin) VALUES(?,?,?,1)",
                (username, pwd_hash, now_str),
            )
            self._log("管理员账户写入完成：" + username)

            self._step(78, "正在保存系统配置...")
            config = {
                "version":      "1.0.0",
                "install_date": now_str,
                "install_dir":  install_dir,
                "data_dir":     data_dir,
                "log_dir":      log_dir,
                "db_path":      db_path,
            }
            cur.execute(
                "INSERT OR REPLACE INTO settings (key,value) VALUES(?,?)",
                ("config", json.dumps(config, ensure_ascii=False)),
            )
            conn.commit()
            conn.close()

            self._step(88, "正在写入配置文件...")
            config_file = os.path.join(data_dir, "config.json")
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self._log("配置文件已保存：" + config_file)

            self._step(95, "正在写入注册表...")
            if self._write_registry(install_dir, data_dir, db_path):
                self._log("注册表写入成功")
            else:
                self._log("注册表写入失败（将使用配置文件方式）")

            self._step(100, "安装完成")
            self._log("=" * 44)
            self._log("系统安装完成！请点击【下一步】继续。")

            wiz.setProperty("_install_config", {
                "username":    username,
                "install_dir": install_dir,
                "data_dir":    data_dir,
                "log_dir":     log_dir,
                "db_path":     db_path,
            })
            self._install_done = True
            self.completeChanged.emit()

        except Exception as e:
            self._log("[错误] " + str(e))
            self._log(traceback.format_exc())
            QMessageBox.critical(
                self, "安装失败",
                "安装过程中发生错误：\n\n{}\n\n请检查权限后重试。".format(e),
            )

    @staticmethod
    def _write_registry(install_dir: str, data_dir: str, db_path: str) -> bool:
        try:
            import winreg
            key = winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER,
                r"SOFTWARE\NetworkMonitor\v1.0",
                0, winreg.KEY_SET_VALUE,
            )
            winreg.SetValueEx(key, "InstallDir", 0, winreg.REG_SZ, install_dir)
            winreg.SetValueEx(key, "DataDir",    0, winreg.REG_SZ, data_dir)
            winreg.SetValueEx(key, "DbPath",     0, winreg.REG_SZ, db_path)
            winreg.SetValueEx(key, "Installed",  0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            return True
        except Exception:
            return False


# ── 完成页（壳） ──────────────────────────────────────────────
class FinalPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("准备完成")
        self.setSubTitle("安装已完成，点击【完成】查看选项")
        self.setFinalPage(True)
        layout = QVBoxLayout()
        lbl = QLabel(
            "✅  所有组件已安装完毕。\n\n"
            "点击下方【完成】按钮，选择是否创建桌面快捷方式及立即运行。"
        )
        lbl.setWordWrap(True)
        lbl.setStyleSheet("font-size:11pt;color:#333;")
        layout.addWidget(lbl)
        layout.addStretch()
        self.setLayout(layout)
