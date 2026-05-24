# Daily Automation

一个本地运行的每日自动化助手。它会聚合学术与技术信息源，生成每日简报，按需发送邮件，并维护课程、提醒和日程输出。

当前项目以 **本地网页端** 作为主入口，命令行任务和桌面 GUI 作为辅助入口保留。

## 能做什么

| 能力 | 说明 |
| --- | --- |
| 每日学术简报 | 从 RSS、公开学术 API、技术博客等来源抓取内容，按关键词筛选并生成 Markdown 简报 |
| 邮件推送 | 将简报或每日计划发送到指定邮箱，授权码会加密保存在本地 |
| 天气建议 | 根据天气数据生成简短穿衣/出行建议 |
| 课程与提醒 | 管理课程表、每日任务和提醒，输出 HTML 日程 |
| 失败可见 | 网页端和桌面端都会显示任务进度、运行日志、警告和错误摘要 |

## 一分钟启动

```powershell
python -m pip install -r requirements.txt
python launcher.py web
```

浏览器打开：

```text
http://localhost:8501
```

Windows 用户也可以双击：

```text
scripts\windows\启动网页端.bat
```

## 使用路径

第一次使用建议按这个顺序：

1. 打开网页端。
2. 进入“配置”，填写邮箱、天气城市和需要的 API Key。
3. 回到“今日简报”，点击“生成并发送今日简报”。
4. 在页面中查看实时日志、运行耗时和结果提示。
5. 到 `runtime_local\data\` 查看生成的简报或日程文件。

## 入口说明

| 场景 | 命令 |
| --- | --- |
| 启动主界面 | `python launcher.py web` |
| 直接启动 Streamlit | `python -m streamlit run app.py` |
| 运行完整后端流程 | `python daily_assistant.py all` |
| 只生成学术简报 | `python daily_assistant.py crawl` |
| 只检查提醒/课程 | `python daily_assistant.py remind` |
| 启动备用桌面 GUI | `python gui_app.py` |

## 项目结构

```text
daily_automation
├─ app.py                         # 网页端入口，供 streamlit run 使用
├─ launcher.py                    # 启动网页端或后端任务
├─ daily_assistant.py             # 后端 CLI 兼容入口
├─ gui_app.py                     # 桌面 GUI 兼容入口
├─ src\daily_automation\          # 正式源码包
│  ├─ web_app.py                  # Streamlit 本地网页端
│  ├─ daily_assistant.py          # 抓取、筛选、报告、邮件、提醒主流程
│  ├─ gui_app.py                  # Tkinter 桌面备用界面
│  ├─ config_manager.py           # 配置读写和默认值
│  ├─ schedule_manager.py         # 课程、任务和每日计划
│  ├─ api_sources.py              # 学术 API 来源
│  ├─ web_fetcher.py              # HTTP/网页抓取降级
│  ├─ html_parser.py              # HTML/RSS 解析
│  ├─ password_crypto.py          # 本地授权码加密
│  └─ app_paths.py                # 开发/打包路径管理
├─ scripts\windows\               # Windows 启动和计划任务脚本
├─ packaging\pyinstaller\         # PyInstaller 打包脚本
├─ docs\                          # 架构、入口和仓库卫生说明
├─ tests\                         # 单元测试
├─ runtime_local\                 # 本机运行数据，不提交
└─ artifacts\                     # 构建和分发产物，不提交
```

## 本地数据在哪里

开发环境下，配置、密钥、日志和输出都放在：

```text
runtime_local\
```

常见文件：

```text
runtime_local\config.json
runtime_local\.secret_key
runtime_local\data\academic_briefing_YYYYMMDD.md
runtime_local\data\daily_plan_YYYYMMDD.html
runtime_local\logs\
```

这些文件可能包含邮箱、授权码、API Key、日志和个人日程，默认不进入 Git。

## 协作开发约定

请遵守这几条，避免仓库再次变乱：

| 类型 | 规则 |
| --- | --- |
| 新功能代码 | 写入 `src/daily_automation/` |
| 兼容入口 | 根目录 Python 文件只做转发，不放复杂逻辑 |
| 本地配置 | 不提交 `config.json`、`.secret_key`、`runtime_local/` |
| 构建产物 | 不提交 `build/`、`dist/`、`artifacts/`、`*.exe`、`*.zip` |
| 客户试跑 | `customer_test_copy/` 是本机测试副本，不提交 |
| 旧脚本 | 一次性修复脚本放入归档或删除，不进入主流程 |

## 开发检查

```powershell
python -m compileall -q app.py launcher.py src tests
python -m pytest
```

当前测试集应通过：

```text
23 passed
```

## 打包桌面版

桌面 GUI 是备用入口。如果需要生成 exe：

```powershell
python -m PyInstaller packaging\pyinstaller\build_exe.spec --clean --noconfirm
```

输出：

```text
dist\DailyAutomation.exe
```

也可以使用：

```text
packaging\pyinstaller\build.bat
```

## 相关文档

| 文档 | 用途 |
| --- | --- |
| `docs\ARCHITECTURE.md` | 当前架构和模块边界 |
| `docs\FRONTEND_ENTRYPOINTS.md` | 网页端、桌面端、CLI 的入口关系 |
| `docs\REPOSITORY_HYGIENE.md` | 哪些文件应该提交，哪些必须留在本地 |

## 注意

这个项目是本地自动化工具，不是云服务。运行任务时会访问外部信息源和邮件服务器；如果网络、API Key 或邮箱授权码未配置完整，前端会显示警告或错误摘要。
