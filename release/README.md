# Daily Automation — 学术自动化助手

> 基于纯 Python 标准库的学术信息聚合、筛选与推送系统。零第三方依赖，支持 CLI / GUI 双模式运行，可 PyInstaller 一键打包为独立 exe。

---

## 架构概览

```
┌──────────────────────────────────────────────────────────┐
│  gui_app.py (Tkinter GUI / PyInstaller exe 入口)         │
│  ┌──────────────────────────────────────────────────────┐│
│  │ DailyAutomationApp                                   ││
│  │  首页 │ 新闻源 │ 关键词 │ 提醒 │ 邮箱 │ 课程表 │ 关于││
│  │                                                      ││
│  │  run_crawl() / run_remind() / run_once()             ││
│  │       │  subprocess（进程隔离，不阻塞 UI）            ││
│  └───────┼──────────────────────────────────────────────┘│
│          │                                               │
│  ┌───────┼──── CLI 模式 ──────────────────────────────┐ │
│  │       ▼                                            │ │
│  │  daily_assistant.py                                 │ │
│  │  InfoCrawler ──→ InfoProcessor ──→ EmailSender      │ │
│  │  (多源爬取)     (关键词筛选+排序)   (SMTP+MD→HTML)  │ │
│  │       │                                            │ │
│  │  Translator         ReminderSystem                  │ │
│  │  (术语词典离线翻译)  (时间匹配+提醒输出)            │ │
│  └────────────────────────────────────────────────────┘ │
│                                                         │
│  schedule_manager.py  — 课表管理 + 每日计划 HTML 生成    │
│  config_manager.py    — 配置 CRUD 统一层                │
│  app_paths.py         — 路径管理（打包/开发环境兼容）    │
└──────────────────────────────────────────────────────────┘
```

---

## 核心模块

### 1. InfoCrawler — 多源学术信息爬取

支持三种数据源类型的自动分发解析：

| 类型 | 解析方法 | 目标 |
|------|----------|------|
| `rss` | `parse_arxiv_rss()` / `parse_generic_rss()` | arXiv Atom XML、通用 RSS |
| `json` | 通用 JSON 解析 | PapersWithCode API（额外提取 `github_url`） |
| `web` | 按域名分发至专用解析器 | Semantic Scholar / AMiner / The Gradient / 通用网页 |

**爬取流程：**

```
crawl_all(sources)
  └─ for each enabled source (1.5s 礼貌延迟):
       └─ fetch_content(url)     → urllib.request, 依次尝试 UTF-8/GBK/Latin-1 解码
            └─ 根据 source_type 分发:
                 ├─ "rss"  → XML 解析 (xml.etree.ElementTree)
                 ├─ "json" → JSON 解析
                 └─ "web"  → 正则匹配论文链接 (3 种 pattern × 域名, 去重取前5)
```

### 2. InfoProcessor — 关键词筛选与报告生成

**相关性评分算法：**

```
score = Σ(标题命中关键词 × 3) + Σ(摘要命中关键词 × 1)
```

过滤 `score > 0` 的条目后按分数降序排列，生成 Markdown 学术简报（含数据概览、精选论文、来源分布统计）。

### 3. Translator — 离线术语翻译引擎

基于 50+ 条学术术语词典的规则翻译，**无 API 调用，离线可用**：

- **长词优先替换**：按术语长度降序遍历，避免子串误匹配
- **大小写保留**：翻译后保持原文首字母大小写
- **未命中标记**：无任何翻译命中时追加 `[待译]`
- **精华提取**：按 `[.!?。！？]` 分句，取前 2 句（>20 字符）拼接为摘要

### 4. EmailSender — SMTP 邮件推送

- 自动检测端口：465 → `SMTP_SSL`，其他 → `SMTP` + `STARTTLS`
- 双格式发送：`MIMEMultipart('alternative')` 同时附加纯文本和 HTML
- 内置简易 Markdown→HTML 转换器（标题/粗体/斜体/链接/分隔线）

### 5. ReminderSystem — 定时提醒

- **精确匹配**：当前 `HH:MM` 与配置时间比对（允许 1 分钟误差）
- **预告收集**：未来 2 小时内的提醒
- **GBK 宽度换行**：按 GBK 编码计算字符宽度，自动在框线内换行

### 6. ConfigManager — 配置管理层

统一 CRUD 接口，管理三类 JSON 配置文件：

| 文件 | 内容 |
|------|------|
| `config.json` | 新闻源 / 关键词 / 提醒 / 邮箱 / 翻译 / 输出设置 |
| `schedule.json` | 周课表 + 上课时间表 |
| `weekly_tasks.json` | 每周任务 / 学期目标 |

支持配置备份（带时间戳）、导入导出、重置默认。

---

## 运行模式

### CLI 模式

```bash
python daily_assistant.py crawl   # 爬取 → 筛选 → 生成简报 → 邮件推送
python daily_assistant.py remind  # 检查提醒 → 输出 → 记录日志
python daily_assistant.py all     # 先 crawl 再 remind
```

**crawl 流程：**

```
load_config → InfoCrawler.crawl_all → InfoProcessor.generate_academic_report
  → save_report (data/academic_briefing_YYYYMMDD.md)
  → EmailSender.send_report (if enabled)
  → 控制台预览前3条
```

### GUI 模式

```bash
python gui_app.py          # 启动 Tkinter 桌面应用
python gui_app.py --task   # 任务模式（不启动 GUI，直接执行 daily_assistant）
python gui_app.py --task crawl   # 任务模式：仅学术简报
python gui_app.py --task remind  # 任务模式：仅日程提醒
```

**GUI → CLI 进程隔离设计：**

```
GUI 主进程 (Tkinter mainloop)
  └─ run_crawl() / run_remind()
       └─ threading.Thread(daemon=True)   ← 避免阻塞 UI
            └─ subprocess.run(
                 [sys.executable, "daily_assistant.py", "crawl"],
                 capture_output=True, encoding="utf-8", errors="replace",
                 timeout=600
               )
            └─ root.after(0, callback)    ← 子线程 → 主线程 UI 更新
```

打包环境下额外使用 `CREATE_NO_WINDOW` + `STARTF_USESHOWWINDOW(SW_HIDE)` 隐藏控制台窗口。

---

## 文件结构

```
daily_automation/
├── gui_app.py               # GUI 入口 + DailyAutomationApp 类
├── daily_assistant.py       # CLI 核心：InfoCrawler / InfoProcessor / Translator / EmailSender / ReminderSystem
├── config_manager.py        # 配置 CRUD 统一层
├── schedule_manager.py      # 课表管理 + 每日计划 HTML 生成
├── app_paths.py             # 路径管理（PyInstaller 兼容）
├── build_exe.spec           # PyInstaller 打包配置
├── config.json              # 主配置
├── schedule.json            # 课程表
├── weekly_tasks.json        # 每周任务
├── run_daily.bat            # CLI 快捷入口
├── setup_task_scheduler.bat # Windows 定时任务配置
├── data/                    # 输出：学术简报 .md / 每日计划 .html
├── logs/                    # 运行日志
└── release/                 # 可分发的完整安装包
    ├── DailyAutomation.exe  # 打包后的独立可执行文件
    ├── install.bat          # 安装工具（桌面快捷方式/定时任务）
    └── ...                  # 全部运行所需文件
```

---

## 配置说明

### config.json 结构

```json
{
  "news_sources": [
    {
      "name": "arXiv AI",
      "url": "http://export.arxiv.org/api/query?search_query=cat:cs.AI",
      "source_type": "rss",
      "enabled": true
    }
  ],
  "keywords": ["artificial intelligence", "digital governance"],
  "keywords_cn": ["人工智能", "数字治理"],
  "reminders": [
    {"time": "09:00", "title": "学术早报", "description": "今日学术资讯已整理完毕"}
  ],
  "email": {
    "enabled": false,
    "smtp_server": "smtp.qq.com",
    "smtp_port": 587,
    "sender_email": "",
    "sender_password": "",
    "receiver_email": "",
    "subject_prefix": "[学术简报]"
  },
  "translation": {"enabled": false, "target_lang": "zh"},
  "max_items_per_source": 5
}
```

### 数据源类型

| source_type | 解析逻辑 | 适用场景 |
|-------------|----------|----------|
| `rss` | arXiv 用 Atom XML 命名空间解析；其他用标准 RSS 解析 | arXiv、OECD、SSRN 等 |
| `json` | 直接 `json.loads()`，自动提取 paper/title/abstract/url 字段 | PapersWithCode API |
| `web` | 按域名分发专用正则解析器；未知域名走通用链接提取 | Semantic Scholar、AMiner 等 |

---

## 打包与分发

```bash
# 使用 PyInstaller 打包为单文件 exe
python -m PyInstaller build_exe.spec --clean --noconfirm
```

**打包配置要点（build_exe.spec）：**

- 单文件模式（`EXE` 内含所有依赖）
- `console=False`：无控制台窗口
- `hiddenimports`：显式声明 `config_manager`、`daily_assistant`、`schedule_manager`、`app_paths`
- `datas`：嵌入 `config.json`、`schedule.json`、`weekly_tasks.json`、`data/`、`logs/`
- 路径兼容：运行时通过 `sys.frozen` / `sys._MEIPASS` 区分打包/开发环境

---

## 关键设计决策

| 决策 | 理由 |
|------|------|
| 零第三方依赖 | 全部使用标准库（`urllib`、`smtplib`、`tkinter`、`xml.etree`），降低部署门槛 |
| subprocess 进程隔离 | GUI 与爬取/网络操作完全解耦，避免 UI 卡顿 |
| 术语词典离线翻译 | 无 API 调用，离线可用，响应即时 |
| 长词优先替换 | 防止子串误匹配（如 "learning" 先于 "deep learning" 被替换） |
| 配置双路径兼容 | `app_paths.py` 统一处理 `sys.executable`（打包）与 `__file__`（开发）的路径差异 |
| GBK 宽度换行 | Windows 控制台默认 GBK 编码，CJK 字符占 2 宽度，需按宽度计算换行位置 |
| UTF-8 强制编码 | `subprocess.run(encoding="utf-8", errors="replace")` 确保表情符号等 Unicode 字符不触发编码异常 |

---

## 故障排除

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 爬取返回空 | 网络限制 / 源站变更 | 检查 `logs/` 日志；确认 URL 可访问；尝试代理 |
| exe 点击按钮无响应 | 旧版 exe 未更新 | 重新打包：`python -m PyInstaller build_exe.spec --clean` |
| UnicodeEncodeError | Windows 控制台 GBK 编码 | 已通过 `encoding="utf-8", errors="replace"` 处理 |
| 定时任务不执行 | 任务计划程序配置问题 | `Win+R` → `taskschd.msc` 检查任务状态和触发器 |
| 翻译质量不佳 | 术语词典覆盖有限 | 扩展 `Translator.TERM_DICT` 或启用 `translation.enabled` |

---

## 技术栈

| 层 | 技术 |
|----|------|
| GUI | Tkinter + ttk（原生，无需安装） |
| Web 界面 | Streamlit（`app.py`，可选） |
| HTTP 爬取 | `urllib.request`（标准库） |
| XML 解析 | `xml.etree.ElementTree`（标准库） |
| 邮件发送 | `smtplib` + `email.mime`（标准库） |
| 配置管理 | JSON 文件读写 |
| 打包 | PyInstaller 6.x |
| Python | 3.8+ |
