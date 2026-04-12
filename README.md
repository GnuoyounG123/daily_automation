# Daily Automation — 学术自动化助手

> 学术信息聚合、筛选与推送系统。支持多架构爬取自动降级、CLI / GUI 双模式运行，可 PyInstaller 一键打包为独立 exe。

---

## 架构概览

```
┌──────────────────────────────────────────────────────────────────────┐
│  gui_app.py (Tkinter GUI / PyInstaller exe 入口)                     │
│  ┌──────────────────────────────────────────────────────────────────┐│
│  │ DailyAutomationApp                                               ││
│  │  首页 │ 新闻源 │ 关键词 │ 提醒 │ 邮箱 │ API密钥 │ 课程表 │ 关于 ││
│  │                                                                  ││
│  │  run_crawl() / run_remind() / run_once()                         ││
│  │       │  subprocess（进程隔离，不阻塞 UI）                        ││
│  └───────┼──────────────────────────────────────────────────────────┘│
│          │                                                           │
│  ┌───────┼──── CLI 模式 ──────────────────────────────────────────┐ │
│  │       ▼                                                        │ │
│  │  daily_assistant.py                                             │ │
│  │  InfoCrawler ──→ InfoProcessor ──→ EmailSender                  │ │
│  │  (多架构爬取)    (关键词筛选+排序)   (SMTP+MD→HTML)              │ │
│  │       │                                                        │ │
│  │  Translator         ReminderSystem                              │ │
│  │  (术语词典离线翻译)  (时间匹配+提醒输出)                        │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌── 多架构爬取引擎 ──────────────────────────────────────────────┐ │
│  │ web_fetcher.py   — 4后端HTTP获取 (requests→httpx→urllib→selenium)│ │
│  │ html_parser.py   — 4策略HTML解析 (BS4→lxml→regex + feedparser) │ │
│  │ api_sources.py   — 5公开学术API (Semantic Scholar/CrossRef/     │ │
│  │                     DBLP/OpenAlex/CORE)                         │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  schedule_manager.py  — 课表管理 + 每日计划 HTML 生成                │
│  config_manager.py    — 配置 CRUD 统一层                            │
│  app_paths.py         — 路径管理（打包/开发环境兼容）                │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 核心模块

### 1. InfoCrawler — 多架构学术信息爬取

**四级降级策略链：**

```
crawl_source(source)
  ├─ 策略1: API优先    → api_sources.py (5个公开学术API)
  ├─ 策略2: 静态爬取   → web_fetcher.py (4后端自动降级) + html_parser.py (4策略自动降级)
  ├─ 策略3: JS渲染     → Selenium 无头浏览器渲染后解析
  └─ 策略4: 标记失败   → 记录失败源，生成报告提示用户手动输入
```

**HTTP 获取自动降级（web_fetcher.py）：**

| 优先级 | 后端 | 特点 |
|--------|------|------|
| 1 | `requests` | 连接池管理，自动编码检测 |
| 2 | `httpx` | HTTP/2 支持，异步就绪 |
| 3 | `urllib` | 标准库，零依赖兜底 |
| 4 | `selenium` | JS 渲染，Chrome/Edge 自动选择 |

**HTML 解析自动降级（html_parser.py）：**

| 优先级 | 解析器 | 特点 |
|--------|--------|------|
| 1 | `BeautifulSoup` | 容错性强，智能提取文章容器 |
| 2 | `lxml` | 速度最快，XPath 精准定位 |
| 3 | `regex` | 零依赖兜底，按域名分发专用正则 |
| + | `feedparser` | RSS/Atom 专用，arXiv XML 命名空间解析 |

**API 驱动学术源（api_sources.py）：**

| API | 是否需要 Key | 获取链接 |
|-----|-------------|----------|
| Semantic Scholar | 可选（无 Key 限流 100次/5分钟） | [申请链接](https://www.semanticscholar.org/product/api#api-key) |
| CrossRef | 不需要 | — |
| DBLP | 不需要 | — |
| OpenAlex | 可选（无 Key 限速，有 Key 更快） | [申请链接](https://docs.openalex.org/how-to-use-the-api/get-an-api-key) |
| CORE | **需要** | [申请链接](https://core.ac.uk/services/api) |

### 2. InfoProcessor — 关键词筛选与报告生成

**相关性评分算法：**

```
score = Σ(标题命中关键词 × 3) + Σ(摘要命中关键词 × 1)
```

过滤 `score > 0` 的条目后按分数降序排列，生成 Markdown 学术简报（含数据概览、精选论文、来源分布统计、失败源报告）。

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
| `config.json` | 新闻源 / 关键词 / 提醒 / 邮箱 / API密钥 / 翻译 / 输出设置 |
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
load_config → InfoCrawler.crawl_all (多架构自动降级) → InfoProcessor.generate_academic_report
  → save_report (data/academic_briefing_YYYYMMDD.md)
  → EmailSender.send_report (if enabled)
  → 控制台预览前3条 + 失败源报告
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
├── web_fetcher.py           # 多后端HTTP获取器 (requests/httpx/urllib/selenium)
├── html_parser.py           # 多策略HTML解析器 (BS4/lxml/regex/feedparser)
├── api_sources.py           # API驱动学术源 (5个公开API)
├── config_manager.py        # 配置 CRUD 统一层
├── schedule_manager.py      # 课表管理 + 每日计划 HTML 生成
├── app_paths.py             # 路径管理（PyInstaller 兼容）
├── build_exe.spec           # PyInstaller 打包配置
├── requirements.txt         # Python 依赖
├── config.json              # 主配置（含 API 密钥）
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
      "type": "rss",
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
  "api_keys": {
    "semantic_scholar": "",
    "openalex": "",
    "core": ""
  },
  "translation": {"enabled": false, "target_lang": "zh"},
  "max_items_per_source": 5
}
```

### 数据源类型

| source_type | 解析逻辑 | 适用场景 |
|-------------|----------|----------|
| `rss` | feedparser + arXiv XML 命名空间解析 | arXiv、OECD、SSRN 等 |
| `json` | 直接 `json.loads()`，自动提取字段 | PapersWithCode API |
| `web` | 多后端获取 → 多策略解析自动降级 | Semantic Scholar、AMiner、The Gradient 等 |
| `api` | 直接调用公开学术 API | Semantic Scholar API、CrossRef、DBLP、OpenAlex、CORE |

### API 密钥配置

部分学术 API 提供免费密钥，配置后可提升访问速率和配额：

| API | 是否必须 | 配置字段 | 获取方式 |
|-----|---------|---------|---------|
| Semantic Scholar | 可选 | `api_keys.semantic_scholar` | [申请 API Key](https://www.semanticscholar.org/product/api#api-key) |
| OpenAlex | 可选 | `api_keys.openalex` | [申请 API Key](https://docs.openalex.org/how-to-use-the-api/get-an-api-key) |
| CORE | **必须** | `api_keys.core` | [申请 API Key](https://core.ac.uk/services/api) |

> 💡 未配置密钥时，系统仍可使用无需密钥的 API（CrossRef、DBLP），部分 API 会以限速模式运行。当爬取因缺少 API Key 失败时，系统会自动提醒并提供获取链接。

---

## 安装

### 从源码运行

```bash
# 克隆仓库
git clone https://github.com/GnuoyounG123/daily_automation.git
cd daily_automation

# 安装依赖
pip install -r requirements.txt

# 启动 GUI
python gui_app.py

# 或使用 CLI
python daily_assistant.py all
```

### 依赖说明

| 依赖 | 用途 | 是否必须 |
|------|------|---------|
| `requests` | HTTP 获取（首选后端） | 推荐 |
| `beautifulsoup4` | HTML 解析（首选策略） | 推荐 |
| `lxml` | HTML 解析（高速策略） | 可选 |
| `feedparser` | RSS/Atom 解析 | 推荐 |
| `httpx` | HTTP 获取（备选后端） | 可选 |
| `selenium` | JS 渲染爬取 | 可选 |

> 最小依赖仅需 Python 标准库（`urllib` + `regex` 解析器自动兜底），安装 `requests` + `beautifulsoup4` 即可获得完整体验。

---

## 打包与分发

```bash
# 使用 PyInstaller 打包为单文件 exe
python -m PyInstaller build_exe.spec --clean --noconfirm
```

**打包配置要点（build_exe.spec）：**

- 单文件模式（`EXE` 内含所有依赖）
- `console=False`：无控制台窗口
- `hiddenimports`：显式声明所有模块
- `datas`：嵌入配置文件和输出目录
- 路径兼容：运行时通过 `sys.frozen` / `sys._MEIPASS` 区分打包/开发环境

---

## 关键设计决策

| 决策 | 理由 |
|------|------|
| 多架构自动降级 | 单一爬取方式脆弱，4级降级链确保最大覆盖率 |
| API 优先策略 | 公开 API 最稳定，优先使用；失败再降级到爬取 |
| 后端/解析器可插拔 | 按可用性自动初始化，缺包不报错，优雅降级 |
| subprocess 进程隔离 | GUI 与爬取/网络操作完全解耦，避免 UI 卡顿 |
| 术语词典离线翻译 | 无 API 调用，离线可用，响应即时 |
| 长词优先替换 | 防止子串误匹配（如 "learning" 先于 "deep learning" 被替换） |
| 配置双路径兼容 | `app_paths.py` 统一处理打包/开发环境的路径差异 |
| GBK 宽度换行 | Windows 控制台默认 GBK 编码，CJK 字符占 2 宽度 |
| 失败源报告 | 无法自动爬取的源不静默丢弃，生成报告提示用户 |

---

## 故障排除

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 爬取返回空 | 网络限制 / 源站变更 | 检查 `logs/` 日志；确认 URL 可访问；尝试代理 |
| Semantic Scholar 429 | API 限流 | 在 `config.json` 中配置 `api_keys.semantic_scholar` |
| CORE API 无结果 | 缺少 API Key | 在 `config.json` 中配置 `api_keys.core`（[获取链接](https://core.ac.uk/services/api)） |
| AMiner 爬取失败 | SPA 站点需 JS 渲染 | 建议切换为 API 模式或手动输入信息 |
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
| HTTP 爬取 | `requests` / `httpx` / `urllib` / `selenium`（四级自动降级） |
| HTML 解析 | `BeautifulSoup` / `lxml` / `regex` / `feedparser`（四级自动降级） |
| 学术 API | Semantic Scholar / CrossRef / DBLP / OpenAlex / CORE |
| 邮件发送 | `smtplib` + `email.mime`（标准库） |
| 配置管理 | JSON 文件读写 |
| 打包 | PyInstaller 6.x |
| Python | 3.8+ |

---

## License

MIT
