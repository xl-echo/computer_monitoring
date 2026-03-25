#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/analyzer.py
智能请求分析引擎 —— 将 TCP 连接转换为人类可读的行为描述
"""

import socket
import re
from typing import Tuple, Dict

from core.models import RequestInfo


class RequestAnalyzer:
    """
    根据进程名、远端 IP/Port、方向等信息，推断该网络连接的语义。
    规则库（app_signatures / known_ports）可通过修改字典扩展。
    """

    # 常见端口 → 协议名称
    KNOWN_PORTS: Dict[int, str] = {
        80:   "HTTP",
        443:  "HTTPS",
        25:   "SMTP",
        110:  "POP3",
        143:  "IMAP",
        465:  "SMTPS",
        993:  "IMAPS",
        995:  "POP3S",
        21:   "FTP",
        22:   "SSH",
        3306: "MySQL",
        5432: "PostgreSQL",
        3389: "RDP",
        6379: "Redis",
        8080: "HTTP-Proxy",
        8000: "HTTP-Dev",
        8888: "HTTP-Custom",
    }

    # 进程名（小写）→ 应用信息
    APP_SIGNATURES: Dict[str, dict] = {
        "qq.exe":              {"name": "QQ",           "category": "通讯",  "icon": "qq"},
        "qqmusic.exe":         {"name": "QQ音乐",        "category": "娱乐",  "icon": "music"},
        "weixin.exe":          {"name": "微信",           "category": "通讯",  "icon": "wechat"},
        "dingtalk.exe":        {"name": "钉钉",           "category": "通讯",  "icon": "dingtalk"},
        "feishu.exe":          {"name": "飞书",           "category": "通讯",  "icon": "feishu"},
        "chrome.exe":          {"name": "Chrome浏览器",  "category": "浏览器","icon": "chrome"},
        "msedge.exe":          {"name": "Edge浏览器",    "category": "浏览器","icon": "edge"},
        "firefox.exe":         {"name": "Firefox浏览器", "category": "浏览器","icon": "firefox"},
        "safari.exe":          {"name": "Safari浏览器",  "category": "浏览器","icon": "safari"},
        "thunder.exe":         {"name": "迅雷",           "category": "下载",  "icon": "download"},
        "bittorrent.exe":      {"name": "BitTorrent",   "category": "下载",  "icon": "download"},
        "outlook.exe":         {"name": "Outlook",      "category": "邮件",  "icon": "email"},
        "foxmail.exe":         {"name": "Foxmail",      "category": "邮件",  "icon": "email"},
        "thunderbird.exe":     {"name": "Thunderbird",  "category": "邮件",  "icon": "email"},
        "teamviewer.exe":      {"name": "TeamViewer",   "category": "远程",  "icon": "remote"},
        "anydesk.exe":         {"name": "AnyDesk",      "category": "远程",  "icon": "remote"},
        "steam.exe":           {"name": "Steam",        "category": "游戏",  "icon": "game"},
        "epicgameslauncher.exe":{"name": "Epic游戏",    "category": "游戏",  "icon": "game"},
        "explorer.exe":        {"name": "系统",          "category": "系统",  "icon": "system"},
        "svchost.exe":         {"name": "系统服务",       "category": "系统",  "icon": "system"},
    }

    # 域名正则 → 服务名称
    DOMAIN_PATTERNS: Dict[str, str] = {
        r"google\.com":       "Google搜索",
        r"bing\.com":         "Bing搜索",
        r"baidu\.com":        "百度搜索",
        r"youtube\.com":      "YouTube视频",
        r"bilibili\.com":     "B站视频",
        r"taobao\.com":       "淘宝购物",
        r"jd\.com":           "京东购物",
        r"amazon\.com":       "亚马逊购物",
        r"zhihu\.com":        "知乎浏览",
        r"weibo\.com":        "微博浏览",
        r"twitter\.com":      "Twitter浏览",
        r"facebook\.com":     "Facebook浏览",
        r"github\.com":       "GitHub代码",
        r"stackoverflow\.com":"StackOverflow技术",
    }

    # ── 公开接口 ─────────────────────────────────────────────
    def analyze(
        self,
        process_name: str,
        remote_ip: str,
        remote_port: int,
        direction: str,
        bytes_sent: int = 0,
        bytes_recv: int = 0,
    ) -> RequestInfo:
        """
        分析一条网络连接，返回 RequestInfo。

        Args:
            process_name: 进程名称（如 chrome.exe）
            remote_ip:    远端 IP
            remote_port:  远端端口
            direction:    "outbound" 或 "inbound"
            bytes_sent:   本次发送字节数
            bytes_recv:   本次接收字节数
        """
        app = self._identify_app(process_name)
        category = app["category"]

        dispatch = {
            "通讯":  self._analyze_communication,
            "浏览器": self._analyze_browser,
            "邮件":  self._analyze_email,
            "下载":  self._analyze_download,
            "远程":  self._analyze_remote,
            "游戏":  self._analyze_game,
        }
        fn = dispatch.get(category, self._analyze_generic)
        action_type, target, description, risk = fn(
            app["name"], remote_ip, remote_port, direction, bytes_sent, bytes_recv
        )

        return RequestInfo(
            app_name=app["name"],
            action_type=action_type,
            target=target,
            description=description,
            category=category,
            risk_level=risk,
            icon=app["icon"],
        )

    # ── 应用识别 ─────────────────────────────────────────────
    def _identify_app(self, process_name: str) -> dict:
        lower = process_name.lower()
        if lower in self.APP_SIGNATURES:
            return self.APP_SIGNATURES[lower]
        for key, info in self.APP_SIGNATURES.items():
            if key in lower:
                return info
        return {"name": process_name, "category": "其他", "icon": "unknown"}

    # ── 各类型分析 ───────────────────────────────────────────
    def _analyze_communication(
        self, app_name, remote_ip, remote_port, direction, bytes_sent, bytes_recv
    ) -> Tuple:
        addr = "{}:{}".format(remote_ip, remote_port)
        if direction == "outbound":
            if bytes_sent > 0 and bytes_recv > 0:
                return "双向通讯", addr, "{}正在通讯（发送+接收）".format(app_name), 0
            if bytes_sent > 0:
                return "发送消息", addr, "{}发送了一条消息".format(app_name), 0
            return "连接服务器", addr, "{}连接到服务器".format(app_name), 0
        return "接收消息", addr, "{}接收了一条消息".format(app_name), 0

    def _analyze_browser(
        self, app_name, remote_ip, remote_port, direction, bytes_sent, bytes_recv
    ) -> Tuple:
        try:
            hostname = socket.gethostbyaddr(remote_ip)[0]
        except Exception:
            hostname = remote_ip

        action_type, description = "访问网站", "{} 访问了 {}".format(app_name, hostname)
        for pattern, svc in self.DOMAIN_PATTERNS.items():
            if re.search(pattern, hostname, re.IGNORECASE):
                action_type = svc
                description = "{} {}（{}）".format(app_name, svc, hostname)
                break

        if direction == "inbound":
            action_type = "网站响应"
            description = "{} 向 {} 返回数据".format(hostname, app_name)

        return action_type, hostname, description, 1

    def _analyze_email(
        self, app_name, remote_ip, remote_port, direction, bytes_sent, bytes_recv
    ) -> Tuple:
        addr = "{}:{}".format(remote_ip, remote_port)
        if remote_port in (25, 465, 587):
            return "发送邮件", addr, "{} 发送了一封邮件".format(app_name), 0
        if remote_port in (110, 143, 993, 995):
            return "接收邮件", addr, "{} 接收新邮件".format(app_name), 0
        return "邮件通讯", addr, "{} 邮件通讯".format(app_name), 0

    def _analyze_download(
        self, app_name, remote_ip, remote_port, direction, bytes_sent, bytes_recv
    ) -> Tuple:
        addr = "{}:{}".format(remote_ip, remote_port)
        if direction == "inbound" and bytes_recv > 1024:
            return "下载文件", addr, "{} 正在下载文件（{}）".format(
                app_name, self._fmt_bytes(bytes_recv)), 1
        if direction == "outbound" and bytes_sent > 1024:
            return "上传文件", addr, "{} 正在上传文件（{}）".format(
                app_name, self._fmt_bytes(bytes_sent)), 1
        return "P2P连接", addr, "{} P2P 网络连接".format(app_name), 2

    def _analyze_remote(
        self, app_name, remote_ip, remote_port, direction, bytes_sent, bytes_recv
    ) -> Tuple:
        addr = "{}:{}".format(remote_ip, remote_port)
        if direction == "outbound":
            return "远程连接", addr, "{} 连接到远程主机 {}".format(app_name, remote_ip), 3
        return "远程访问", addr, "远程主机 {} 通过 {} 访问本机".format(remote_ip, app_name), 4

    def _analyze_game(
        self, app_name, remote_ip, remote_port, direction, bytes_sent, bytes_recv
    ) -> Tuple:
        addr = "{}:{}".format(remote_ip, remote_port)
        desc = "{} 游戏数据传输".format(app_name) if (bytes_sent and bytes_recv) \
            else "{} 连接到游戏服务器".format(app_name)
        return "游戏连接", addr, desc, 1

    def _analyze_generic(
        self, process_name, remote_ip, remote_port, direction, bytes_sent, bytes_recv
    ) -> Tuple:
        svc = self.KNOWN_PORTS.get(remote_port, "端口{}".format(remote_port))
        addr = "{}:{}".format(remote_ip, remote_port)
        if direction == "outbound":
            if bytes_sent > 0 and bytes_recv == 0:
                return "发送数据", addr, "{} 向 {} 发送数据".format(process_name, addr), 1
            return "连接", addr, "{} 连接到 {}（{}）".format(process_name, addr, svc), 1
        return "接收数据", addr, "{} 从 {} 接收数据（{}）".format(process_name, addr, svc), 1

    # ── 辅助 ─────────────────────────────────────────────────
    @staticmethod
    def _fmt_bytes(n: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if n < 1024:
                return "{:.1f}{}".format(n, unit)
            n /= 1024
        return "{:.1f}TB".format(n)
