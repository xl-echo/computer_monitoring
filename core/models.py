#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/models.py
数据类定义 —— 系统内流转的核心数据结构
"""

from dataclasses import dataclass, field
from typing import Optional


# ────────────────────────────────────────────────────────────
#  网络连接分析结果
# ────────────────────────────────────────────────────────────
@dataclass
class RequestInfo:
    """RequestAnalyzer.analyze() 的返回值，描述一条网络连接的语义信息"""

    app_name: str        # 应用名称，如 "QQ"、"Chrome浏览器"
    action_type: str     # 行为类型，如 "发送消息"、"访问网站"
    target: str          # 目标描述，如 "119.29.29.29:8001"
    description: str     # 中文描述，普通用户可理解
    category: str        # 分类：通讯 / 浏览器 / 邮件 / 下载 / 远程 / 游戏 / 系统 / 其他
    risk_level: int      # 风险等级 0~4（0安全、1低、2中、3高、4极高）
    icon: str            # 图标标识，供 UI 层使用


# ────────────────────────────────────────────────────────────
#  连接记录（对应数据库 connections 表一行）
# ────────────────────────────────────────────────────────────
@dataclass
class ConnectionRecord:
    """一条完整的网络连接记录，用于数据库写入 / 归档 / UI 展示"""

    timestamp: str
    local_ip: str = ""
    local_port: int = 0
    remote_ip: str = ""
    remote_port: int = 0
    process_name: str = ""
    process_id: int = 0
    direction: str = "outbound"   # outbound | inbound
    status: str = ""
    bytes_sent: int = 0
    bytes_recv: int = 0

    # 由 RequestAnalyzer 填充
    app_name: str = ""
    action_type: str = ""
    target: str = ""
    description: str = ""
    category: str = ""
    risk_level: int = 0
    icon: str = ""
    full_params: str = "{}"

    def to_dict(self) -> dict:
        """转换为普通字典，方便数据库 / 归档层使用"""
        return {
            "timestamp":    self.timestamp,
            "local_ip":     self.local_ip,
            "local_port":   self.local_port,
            "remote_ip":    self.remote_ip,
            "remote_port":  self.remote_port,
            "process_name": self.process_name,
            "process_id":   self.process_id,
            "direction":    self.direction,
            "status":       self.status,
            "bytes_sent":   self.bytes_sent,
            "bytes_recv":   self.bytes_recv,
            "app_name":     self.app_name,
            "action_type":  self.action_type,
            "target":       self.target,
            "description":  self.description,
            "category":     self.category,
            "risk_level":   self.risk_level,
            "icon":         self.icon,
            "full_params":  self.full_params,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ConnectionRecord":
        return cls(
            timestamp=d.get("timestamp", ""),
            local_ip=d.get("local_ip", ""),
            local_port=d.get("local_port", 0),
            remote_ip=d.get("remote_ip", ""),
            remote_port=d.get("remote_port", 0),
            process_name=d.get("process_name", ""),
            process_id=d.get("process_id", 0),
            direction=d.get("direction", "outbound"),
            status=d.get("status", ""),
            bytes_sent=d.get("bytes_sent", 0),
            bytes_recv=d.get("bytes_recv", 0),
            app_name=d.get("app_name", ""),
            action_type=d.get("action_type", ""),
            target=d.get("target", ""),
            description=d.get("description", ""),
            category=d.get("category", ""),
            risk_level=d.get("risk_level", 0),
            icon=d.get("icon", ""),
            full_params=d.get("full_params", "{}"),
        )


# ────────────────────────────────────────────────────────────
#  今日统计快照
# ────────────────────────────────────────────────────────────
@dataclass
class TodayStats:
    total: int = 0
    outbound: int = 0
    inbound: int = 0
    risk_high: int = 0
