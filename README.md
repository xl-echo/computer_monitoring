# 网络监控系统 v1.0.0

> 专业级智能网络活动分析平台 — 架构重构版

---

## 项目概述

本系统是一款面向 Windows 桌面的网络活动实时监控与智能分析工具。采用 PyQt6 构建现代化 UI，SQLite 存储连接数据，支持账密登录 + TOTP 双因素认证，完全本地化运行。

---

## 目录结构

```
v1.0.0/
├── core/                    # 核心层（数据模型 / 数据库 / 分析引擎）
│   ├── __init__.py
│   ├── models.py            # 数据类定义（RequestInfo）
│   ├── database.py          # 数据库管理器（DatabaseManager）
│   └── analyzer.py          # 智能请求分析引擎（RequestAnalyzer）
│
├── services/                # 服务层（监控线程 / 归档管理 / 描述生成）
│   ├── __init__.py
│   ├── monitor.py           # 网络监控线程（NetworkMonitorThread）
│   ├── archive.py           # 归档管理器（ArchiveManager）
│   └── description.py       # 行为描述生成器（通俗化文本）
│
├── ui/                      # 表现层
│   ├── __init__.py
│   ├── theme.py             # 全局样式常量（QSS / 颜色）
│   ├── dialogs/             # 独立对话框
│   │   ├── __init__.py
│   │   ├── connection_detail.py  # 连接详情弹窗
│   │   ├── risk_list.py          # 高风险列表弹窗（含分页）
│   │   ├── archive_view.py       # 归档文件查看弹窗
│   │   └── totp_bind.py          # TOTP 绑定弹窗
│   ├── widgets/             # 可复用自定义控件
│   │   ├── __init__.py
│   │   └── stat_card.py          # 统计卡片组件（StatCard）
│   └── windows/             # 主窗口 / 登录窗口
│       ├── __init__.py
│       ├── login_window.py       # 登录窗口（含记住账密/自动登录）
│       └── main_window.py        # 主监控窗口
│
├── assets/                  # 静态资源
│   └── app_icon.ico         # 应用图标
│
├── installer/               # 安装向导（独立模块）
│   ├── __init__.py
│   ├── wizard.py            # 安装向导主类（InstallWizard）
│   └── pages.py             # 向导各步骤页面
│
├── scripts/                 # 工具脚本
│   └── build.py             # PyInstaller 打包脚本
│
├── launcher.py              # 程序入口：启动画面 + 路由（安装/主程序）
├── requirements.txt         # 依赖清单
└── README.md                # 本文件
```

---

## 分层架构说明

| 层次 | 目录 | 职责 | 可替换性 |
|------|------|------|----------|
| 核心层 | `core/` | 数据模型、数据库 CRUD、连接分析算法 | 高（可单独测试） |
| 服务层 | `services/` | 监控线程、文件归档、描述文本生成 | 高（可独立运行） |
| 表现层 | `ui/` | PyQt6 界面、弹窗、控件 | 高（可整体替换为其他 UI） |
| 安装层 | `installer/` | 安装向导、注册表写入、快捷方式 | 中 |
| 入口 | `launcher.py` | 路由判断、启动画面 | 低（粘合剂） |

---

## 快速开始（开发调试）

```bash
# 安装依赖
pip install -r requirements.txt

# 直接运行（跳过安装向导）
python launcher.py
```

---

## 打包发布

```bash
python scripts/build.py
# 输出：dist/NetworkMonitor-Setup.exe
```

---

## 技术栈

- **UI 框架**：PyQt6
- **数据库**：SQLite 3（内置）
- **网络监控**：psutil
- **双因素认证**：pyotp + qrcode
- **图标处理**：Pillow
- **打包工具**：PyInstaller + NSIS（安装包）

---

## 二次开发指引

- 扩展应用识别规则 → 修改 `core/analyzer.py` 中 `app_signatures` 字典
- 修改界面样式 → 修改 `ui/theme.py` 中颜色/QSS 常量
- 新增统计卡片 → 在 `ui/widgets/stat_card.py` 扩展，在 `ui/windows/main_window.py` 引用
- 新增归档字段 → 修改 `services/archive.py` 的 `write_record()` 方法
