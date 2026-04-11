# 📚 每日学术自动化系统 - 使用指南

> 「主人，您不在的时候，喵去打探了一下外面的世界喵。」

---

## ✨ 功能特性

- 🤖 **自动爬取** arXiv、PapersWithCode、OECD、SSRN 四大学术数据库
- 🌏 **智能翻译** - 自动将英文标题/摘要翻译为中文
- 📝 **精华提取** - 提取核心要点，过滤冗余信息
- 🔍 **关键词匹配** - 基于您的研究领域筛选相关文献
- ⏰ **定时提醒** - 每天9:00学术早报，18:00晚间复盘
- 📊 **可视化报告** - 生成Markdown格式的精美简报

---

## 📁 文件结构

```
daily_automation/
├── daily_assistant.py          # 主程序（Python）- 爬取+翻译+提醒
├── run_daily.bat               # 手动运行入口
├── setup_task_scheduler.bat    # 一键配置定时任务
├── config.json                 # 个性化配置文件
├── README.md                   # 本文件
├── data/                       # 生成的学术简报存放目录
│   └── academic_briefing_YYYYMMDD.md
└── logs/                       # 日志文件目录
    └── YYYYMMDD.log
```

---

## 🚀 快速开始

### 第一步：安装Python

确保系统已安装 **Python 3.7+**

```bash
python --version
```

> 如未安装，前往 https://www.python.org/downloads/ 下载安装

### 第二步：测试运行

双击运行 `run_daily.bat`，检查是否正常执行。

### 第三步：设置自动运行

**右键** `setup_task_scheduler.bat` → **以管理员身份运行**

这会自动创建两个定时任务：
- `DailyAutomation_Morning` - 每天 **9:00** 运行学术早报
- `DailyAutomation_Evening` - 每天 **18:00** 运行晚间复盘

---

## ⚙️ 个性化配置

编辑 `config.json` 文件：

```json
{
  "news_sources": [
    {
      "name": "arXiv AI",
      "url": "http://export.arxiv.org/api/query?search_query=cat:cs.AI...",
      "type": "rss",
      "enabled": true
    }
  ],
  "reminders": [
    {
      "time": "09:00",
      "title": "学术早报",
      "description": "主人，您不在的时候，喵去打探了一下外面的世界喵。今日最新学术资讯已整理完毕，请查阅。"
    }
  ],
  "keywords": [
    "artificial intelligence",
    "big data",
    "public governance",
    "digital governance"
  ],
  "keywords_cn": [
    "人工智能",
    "大数据",
    "公共治理",
    "数字治理"
  ],
  "max_items_per_source": 5
}
```

### 配置说明

| 配置项 | 说明 |
|--------|------|
| `news_sources` | 学术信息源列表，支持RSS和JSON API |
| `reminders` | 提醒时间和内容 |
| `keywords` | 英文关键词（用于匹配文献）|
| `keywords_cn` | 中文关键词（用于显示）|
| `max_items_per_source` | 每来源最多显示几条精选 |

---

## 🎮 运行模式

### 手动运行

```batch
run_daily.bat        # 完整模式（爬取+提醒）
run_daily.bat crawl  # 仅爬取学术信息
run_daily.bat remind # 仅检查提醒
run_daily.bat all    # 完整模式
```

### Python直接运行

```bash
python daily_assistant.py        # 完整模式
python daily_assistant.py crawl  # 仅爬取
python daily_assistant.py remind # 仅提醒
```

---

## 📊 输出示例

系统会生成精美的Markdown报告：

```markdown
# 📚 每日学术简报 - 2026年04月06日

> ⏰ 生成时间：09:00:00
> 🤖 您的专属学术助手已为您筛选今日最新研究动态

---

## 📊 数据概览

| 指标 | 数值 |
|------|------|
| 爬取来源 | 4个学术数据库 |
| 总文献数 | 40 篇 |
| 相关文献 | 12 篇 |
| 精选推荐 | 5 篇 |

---

## 🔥 重点推荐

### 1. 基于深度学习的公共政策分析框架

**来源**：arXiv | **日期**：2026-04-05

**核心要点**：
本研究提出了一种新的深度学习框架，用于分析政府公开数据...

**相关领域**：人工智能、公共治理、深度学习

**原文链接**：[点击查看](https://arxiv.org/abs/...)
```

---

## 🔧 故障排除

### 问题1：爬取失败或返回空结果

**解决**：
- 检查网络连接
- 学术网站可能有访问限制，尝试使用代理
- 查看 `logs/` 目录下的日志文件排查原因

### 问题2：翻译质量不佳

**解决**：
- 系统使用术语词典+规则翻译，专业术语会优先翻译
- 可在 `Translator.TERM_DICT` 中添加更多术语

### 问题3：定时任务不执行

**解决**：
1. 按 `Win+R`，输入 `taskschd.msc` 打开任务计划程序
2. 检查任务状态是否为"准备就绪"
3. 右键任务 → 属性 → 触发器，确认设置正确
4. 尝试手动运行任务测试

### 问题4：提示"未找到Python"

**解决**：
编辑 `run_daily.bat`，修改：
```batch
set PYTHON_CMD=python
```
为Python的完整路径，如：
```batch
set PYTHON_CMD=C:\Python311\python.exe
```

---

## 📜 任务计划程序命令

```batch
# 查看所有任务
schtasks /query

# 查看特定任务
schtasks /query /tn "DailyAutomation_Morning" /v

# 立即运行任务
schtasks /run /tn "DailyAutomation_Morning"

# 暂停任务
schtasks /change /tn "DailyAutomation_Morning" /disable

# 恢复任务
schtasks /change /tn "DailyAutomation_Morning" /enable

# 删除任务
schtasks /delete /tn "DailyAutomation_Morning" /f
```

---

## 🔬 数据源说明

| 数据源 | 类型 | 内容 |
|--------|------|------|
| arXiv | RSS | 计算机科学、人工智能最新预印本 |
| PapersWithCode | API | 带代码实现的最新论文 |
| OECD Library | RSS | 公共政策、治理研究 |
| SSRN | RSS | 社会科学研究网络 |

---

## 💡 进阶建议

1. **扩展关键词**：在 `config.json` 中添加更多领域词汇
2. **添加新源**：可以添加其他学术数据库的RSS或API
3. **邮件推送**：已内置邮件发送功能，将简报发送到指定邮箱
4. **历史归档**：定期将 `data/` 目录的报告归档到其他位置

---

## 📧 邮件配置说明

系统已内置邮件发送功能，简报会自动发送到您的QQ邮箱。

### 配置步骤：

1. **获取QQ邮箱授权码**（不是QQ密码）：
   - 登录QQ邮箱网页版
   - 设置 → 账户 → 开启SMTP服务
   - 获取16位授权码

2. **编辑 config.json**：
```json
"email": {
    "enabled": true,
    "smtp_server": "smtp.qq.com",
    "smtp_port": 587,
    "sender_email": "your_qq@qq.com",
    "sender_password": "your_auth_code",
    "receiver_email": "yg1114702713@qq.com",
    "subject_prefix": "[学术简报]"
}
```

3. **替换配置**：
   - `sender_email`：您的QQ邮箱地址
   - `sender_password`：授权码（不是QQ密码）
   - `receiver_email`：收件人邮箱（已设置为您的邮箱）

### 其他邮箱设置：

| 邮箱类型 | SMTP服务器 | 端口 |
|---------|-----------|------|
| QQ邮箱 | smtp.qq.com | 587 |
| 163邮箱 | smtp.163.com | 25 |
| Gmail | smtp.gmail.com | 587 |
| Outlook | smtp.office365.com | 587 |

---

> 主人若有任何需求，随时唤我调整配置喵～ 🐾
