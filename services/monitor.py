#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
services/monitor.py
网络监控线程 —— 持续捕获系统网络连接，通过 Qt 信号推送给 UI
"""

from datetime import datetime

import psutil
from PyQt6.QtCore import QThread, pyqtSignal

from core.analyzer import RequestAnalyzer
from core.database import DatabaseManager
from services.archive import ArchiveManager


class NetworkMonitorThread(QThread):
    """
    后台线程，每 5 秒轮询 psutil.net_connections()，
    对新出现的连接进行分析并持久化，通过 new_connection 信号通知 UI。
    """

    new_connection = pyqtSignal(dict)   # 信号：携带连接记录字典

    # 最多缓存 5000 个已见连接 key，防止内存无限增长
    _SEEN_MAX = 5000
    _SEEN_TRIM = 2000

    def __init__(
        self,
        db_manager: DatabaseManager,
        archive_manager: ArchiveManager,
    ):
        super().__init__()
        self._db = db_manager
        self._archive = archive_manager
        self._running = False
        self._analyzer = RequestAnalyzer()
        self._proc_cache: dict = {}
        self._seen_keys: set = set()

    # ── 线程入口 ─────────────────────────────────────────────
    def run(self):
        self._running = True
        while self._running:
            self._scan_once()
            # 以 100ms 为最小单位等待 5 秒，同时响应停止信号
            for _ in range(50):
                if not self._running:
                    break
                self.msleep(100)

    def stop_request(self):
        """请求停止监控（线程安全）"""
        self._running = False

    # ── 单次扫描 ─────────────────────────────────────────────
    def _scan_once(self):
        try:
            for conn in psutil.net_connections(kind="inet"):
                if not self._running:
                    break
                self._process_conn(conn)
        except Exception as e:
            print("[MonitorThread] 扫描错误:", e)

        # 裁剪 seen_keys 防止无限增长
        if len(self._seen_keys) > self._SEEN_MAX:
            self._seen_keys = set(list(self._seen_keys)[-self._SEEN_TRIM:])

    def _process_conn(self, conn):
        try:
            laddr = (conn.laddr.ip, conn.laddr.port) if conn.laddr else ("", 0)
            raddr = (conn.raddr.ip, conn.raddr.port) if conn.raddr else ("", 0)
            key = (laddr, raddr, conn.pid or 0)
            if key in self._seen_keys:
                return
            self._seen_keys.add(key)

            # 进程名（带缓存）
            pid = conn.pid
            if pid and pid not in self._proc_cache:
                try:
                    self._proc_cache[pid] = psutil.Process(pid).name()
                except Exception:
                    self._proc_cache[pid] = "进程{}".format(pid)
            proc = self._proc_cache.get(pid, "") if pid else ""

            direction = "outbound" if raddr[0] else "inbound"
            analysis = self._analyzer.analyze(
                proc or "未知", raddr[0], raddr[1], direction
            )

            record = {
                "timestamp":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "local_ip":     laddr[0],
                "local_port":   laddr[1],
                "remote_ip":    raddr[0],
                "remote_port":  raddr[1],
                "process_name": proc,
                "process_id":   pid,
                "direction":    direction,
                "status":       conn.status,
                "bytes_sent":   0,
                "bytes_recv":   0,
                "app_name":     analysis.app_name,
                "action_type":  analysis.action_type,
                "target":       analysis.target,
                "description":  analysis.description,
                "category":     analysis.category,
                "risk_level":   analysis.risk_level,
                "icon":         analysis.icon,
                "full_params":  "{}",
            }

            self._db.add_connection(record)
            self._archive.write_record(record)
            self.new_connection.emit(record)

        except Exception:
            pass
