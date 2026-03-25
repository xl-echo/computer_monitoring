#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
services/archive.py
归档管理器 —— 将连接记录以可读文本格式写入每日归档文件
"""

import os
import glob
import json
from datetime import date
from typing import List

from services.description import (
    build_plain_description,
    build_params_description,
)

# 风险等级文字
RISK_LABELS = ["✅ 安全", "⚡ 低风险", "⚠️ 中风险", "🔴 高风险", "🆘 极高风险"]


class ArchiveManager:
    """
    按日期维护归档文本文件：
      logs/monitor_YYYY-MM-DD.txt

    每条记录包含：时间、应用、行为、通俗解读、请求/响应描述、原始参数。
    """

    def __init__(self, log_dir: str):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self._today_str: str = ""
        self._today_file: str = ""

    # ── 内部工具 ─────────────────────────────────────────────
    def _get_today_file(self) -> str:
        today = date.today().strftime("%Y-%m-%d")
        if today != self._today_str:
            self._today_str = today
            self._today_file = os.path.join(
                self.log_dir, "monitor_{}.txt".format(today)
            )
            if not os.path.exists(self._today_file):
                with open(self._today_file, "w", encoding="utf-8") as f:
                    f.write("=" * 70 + "\n")
                    f.write(
                        "  网络监控系统 v1.0.0  —  归档日期：{}\n".format(today)
                    )
                    f.write("=" * 70 + "\n\n")
        return self._today_file

    # ── 写入单条记录 ─────────────────────────────────────────
    def write_record(self, d: dict):
        """将一条连接记录追加写入当日归档文件"""
        try:
            fp = self._get_today_file()
            direction_cn = "向外发送" if d.get("direction") == "outbound" else "接收数据"
            risk_level = d.get("risk_level", 0)
            risk_text = RISK_LABELS[min(risk_level, 4)]

            plain = build_plain_description(d)
            req_desc, resp_desc = build_params_description(d)

            # 原始参数：尝试格式化 JSON，否则原样输出
            raw_params = d.get("full_params", "{}")
            try:
                raw_params = json.dumps(
                    json.loads(raw_params), ensure_ascii=False, indent=2
                )
            except Exception:
                pass

            record = (
                "─" * 60 + "\n"
                "  时间：{ts}\n"
                "  应用：{app}  |  行为：{action}  |  方向：{dir}\n"
                "  目标：{target}\n"
                "  分类：{cat}  |  风险：{risk}\n"
                "  说明：{desc}\n"
                "  通俗解读：{plain}\n"
                "  【请求内容】{req}\n"
                "  【响应内容】{resp}\n"
                "  【原始参数】{raw}\n"
                "  进程：{proc}（PID {pid}）  |  本地端口：{lport}\n"
                "  远端：{rip}:{rport}\n"
            ).format(
                ts=d.get("timestamp", ""),
                app=d.get("app_name", d.get("process_name", "")),
                action=d.get("action_type", ""),
                dir=direction_cn,
                target=d.get("target", ""),
                cat=d.get("category", ""),
                risk=risk_text,
                desc=d.get("description", ""),
                plain=plain,
                req=req_desc,
                resp=resp_desc,
                raw=raw_params,
                proc=d.get("process_name", ""),
                pid=d.get("process_id", ""),
                lport=d.get("local_port", ""),
                rip=d.get("remote_ip", ""),
                rport=d.get("remote_port", ""),
            )
            with open(fp, "a", encoding="utf-8") as f:
                f.write(record + "\n")
        except Exception as e:
            print("[ArchiveManager] 归档错误:", e)

    # ── 查询归档文件列表 ─────────────────────────────────────
    def list_archive_files(self) -> List[str]:
        """返回按日期倒序排列的归档文件路径列表"""
        files = glob.glob(os.path.join(self.log_dir, "monitor_*.txt"))
        files.sort(reverse=True)
        return files
