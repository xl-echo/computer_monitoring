#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
core/database.py
数据库管理器 —— 封装所有 SQLite 操作
依赖：Python 内置 sqlite3，无外部依赖
"""

import sqlite3
import hashlib
from datetime import date
from typing import Optional, List

from core.models import TodayStats, ConnectionRecord


def hash_password(password: str) -> str:
    """SHA-256 哈希密码"""
    return hashlib.sha256(password.encode()).hexdigest()


class DatabaseManager:
    """
    封装 network_monitor.db 的全部 CRUD 操作。
    线程安全注意：每次操作独立 connect/close，避免跨线程共享连接。
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_schema()

    # ── Schema 初始化 ────────────────────────────────────────
    def _init_schema(self):
        con = sqlite3.connect(self.db_path)
        c = con.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                totp_secret   TEXT,
                created_at    TEXT,
                is_admin      INTEGER DEFAULT 0
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS connections (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp    TEXT NOT NULL,
                local_ip     TEXT, local_port  INTEGER,
                remote_ip    TEXT, remote_port INTEGER,
                process_name TEXT, process_id  INTEGER,
                direction    TEXT, status      TEXT,
                bytes_sent   INTEGER DEFAULT 0,
                bytes_recv   INTEGER DEFAULT 0,
                app_name     TEXT, action_type TEXT,
                target       TEXT, description TEXT,
                category     TEXT,
                risk_level   INTEGER DEFAULT 0,
                icon         TEXT,
                full_params  TEXT
            )
        """)
        for idx, col in [
            ("idx_ts",   "timestamp"),
            ("idx_rip",  "remote_ip"),
            ("idx_proc", "process_name"),
            ("idx_cat",  "category"),
        ]:
            c.execute(
                "CREATE INDEX IF NOT EXISTS {} ON connections({})".format(idx, col)
            )
        con.commit()
        con.close()

    # ── 用户相关 ─────────────────────────────────────────────
    def get_user(self, username: str) -> Optional[tuple]:
        """按用户名查询用户行，不存在返回 None"""
        con = sqlite3.connect(self.db_path)
        try:
            c = con.cursor()
            c.execute("SELECT * FROM users WHERE username=?", (username,))
            row = c.fetchone()
            return row
        finally:
            con.close()

    def set_totp_secret(self, username: str, secret: str):
        """绑定 TOTP 密钥"""
        con = sqlite3.connect(self.db_path)
        try:
            con.execute(
                "UPDATE users SET totp_secret=? WHERE username=?", (secret, username)
            )
            con.commit()
        finally:
            con.close()

    # ── 连接记录相关 ─────────────────────────────────────────
    def add_connection(self, record: "ConnectionRecord | dict"):
        """插入一条连接记录，接受 ConnectionRecord 或字典"""
        d = record.to_dict() if isinstance(record, ConnectionRecord) else record
        con = sqlite3.connect(self.db_path)
        try:
            con.execute(
                """INSERT INTO connections
                   (timestamp, local_ip, local_port, remote_ip, remote_port,
                    process_name, process_id, direction, status,
                    bytes_sent, bytes_recv,
                    app_name, action_type, target, description,
                    category, risk_level, icon, full_params)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    d.get("timestamp", ""),
                    d.get("local_ip", ""),   d.get("local_port", 0),
                    d.get("remote_ip", ""),  d.get("remote_port", 0),
                    d.get("process_name", ""), d.get("process_id", 0),
                    d.get("direction", ""),  d.get("status", ""),
                    d.get("bytes_sent", 0),  d.get("bytes_recv", 0),
                    d.get("app_name", ""),   d.get("action_type", ""),
                    d.get("target", ""),     d.get("description", ""),
                    d.get("category", ""),
                    d.get("risk_level", 0),
                    d.get("icon", ""),       d.get("full_params", "{}"),
                ),
            )
            con.commit()
        except Exception as e:
            print("[DatabaseManager] 写入错误:", e)
        finally:
            con.close()

    def get_today_stats(self) -> TodayStats:
        """查询今日统计快照 - 单次查询优化"""
        today = date.today().strftime("%Y-%m-%d")
        con = sqlite3.connect(self.db_path)
        try:
            con.row_factory = sqlite3.Row
            c = con.cursor()
            # 使用单次查询 + 条件聚合代替 4 次查询
            c.execute(
                """SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN direction='outbound' THEN 1 ELSE 0 END) as outbound,
                    SUM(CASE WHEN direction='inbound' THEN 1 ELSE 0 END) as inbound,
                    SUM(CASE WHEN risk_level>=3 THEN 1 ELSE 0 END) as risk_high
                FROM connections
                WHERE DATE(timestamp) = ?""",
                (today,),
            )
            row = c.fetchone()
            return TodayStats(
                total=row["total"] or 0,
                outbound=row["outbound"] or 0,
                inbound=row["inbound"] or 0,
                risk_high=row["risk_high"] or 0
            )
        except Exception:
            return TodayStats()
        finally:
            con.close()

    def query_high_risk(self, limit: int = 500) -> List[dict]:
        """查询今日高风险连接（risk_level >= 3）"""
        return self._query_today(
            "risk_level >= 3", limit=limit
        )

    def _query_today(self, where_extra: str, limit: int = 500) -> List[dict]:
        today = date.today().strftime("%Y-%m-%d")
        con = sqlite3.connect(self.db_path)
        try:
            con.row_factory = sqlite3.Row
            c = con.cursor()
            c.execute(
                "SELECT * FROM connections "
                "WHERE DATE(timestamp) = ? AND {} "
                "ORDER BY timestamp DESC LIMIT {}".format(where_extra, limit),
                (today,),
            )
            rows = [dict(r) for r in c.fetchall()]
            return rows
        except Exception:
            return []
        finally:
            con.close()
