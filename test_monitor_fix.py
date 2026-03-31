#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试监控线程修复
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import DatabaseManager
from services.archive import ArchiveManager
from services.monitor import NetworkMonitorThread
from PyQt6.QtCore import QCoreApplication
import time

def test_monitor_thread():
    """测试监控线程能否正常启动和运行"""
    print("=== 测试监控线程修复 ===")
    
    # 创建 QCoreApplication 实例（Qt 信号系统需要）
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    
    # 初始化数据库和归档管理器
    db_path = "test_network_monitor.db"
    log_dir = "test_logs"
    
    # 清理旧测试文件
    if os.path.exists(db_path):
        os.remove(db_path)
    if os.path.exists(log_dir):
        import shutil
        shutil.rmtree(log_dir)
    
    db_manager = DatabaseManager(db_path)
    archive_manager = ArchiveManager(log_dir)
    
    print("1. 创建监控线程...")
    monitor_thread = NetworkMonitorThread(db_manager, archive_manager)
    
    # 连接信号
    def on_new_connection(record):
        print(f"  收到新连接: {record.get('app_name')} -> {record.get('target')}")
    
    monitor_thread.new_connection.connect(on_new_connection)
    
    print("2. 启动监控线程...")
    monitor_thread.start()
    
    print("3. 等待 5 秒收集数据...")
    for i in range(5):
        print(f"  等待 {i+1}/5 秒...")
        time.sleep(1)
        app.processEvents()  # 处理 Qt 事件
    
    print("4. 停止监控线程...")
    monitor_thread.stop_request()
    monitor_thread.wait(2000)  # 等待线程结束
    
    if monitor_thread.isRunning():
        print("  警告: 线程仍在运行，强制终止")
        monitor_thread.terminate()
        monitor_thread.wait(1000)
    else:
        print("  线程已正常停止")
    
    # 检查是否有数据写入
    import sqlite3
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM connections")
    count = c.fetchone()[0]
    conn.close()
    
    print(f"5. 结果: 数据库中有 {count} 条连接记录")
    
    # 检查日志文件
    log_files = []
    if os.path.exists(log_dir):
        log_files = [f for f in os.listdir(log_dir) if f.endswith('.txt')]
    
    print(f"   日志目录中有 {len(log_files)} 个日志文件")
    
    # 清理测试文件
    if os.path.exists(db_path):
        os.remove(db_path)
    if os.path.exists(log_dir):
        import shutil
        shutil.rmtree(log_dir)
    
    if count > 0 or len(log_files) > 0:
        print("测试通过: 监控线程正常工作")
        return True
    else:
        print("测试失败: 没有收集到数据")
        return False

if __name__ == "__main__":
    success = test_monitor_thread()
    sys.exit(0 if success else 1)