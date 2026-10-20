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
| 失败可见 | 网页端会显示配置检查、任务进度、运行记录、警告和错误摘要 |
| 校内事项 | 用统一身份认证接口读取教务课表与学在浙大待办，辅以浏览器登录回退；汇总通知和钉钉转发，生成待办、每日计划及临期邮件 |

## 一分钟启动

```powershell
python -m pip install -r requirements.txt
python launcher.py web
```

## 校内通知与个人计划

1. 安装 `requirements.txt`，在网页端「配置」填写 DeepSeek API Key、钉钉应用 Client ID/Secret，并启用校内检查。新密钥使用本机 `runtime_local/.secret_key` 加密；不要把密钥填入仓库文件。
2. 在同一页面填写浙大学号、密码、学年和学期，先点「测试统一身份认证（不保存）」确认 CAS、教务课表与学在浙大待办均可读取，再保存。只有勾选「记住密码」才会用本机 Fernet 密钥加密保存，计划任务才能自动接口同步；不勾选则接口自动同步不可用，可改用专用浏览器会话；临时的 `api-check` 可直接输入密码做只读测试。密码框留空表示保留原密码。
3. 接口不可用时可回退到浏览器：在「校内事项」打开专用浏览器，分别登录学在浙大和本科教学管理平台；学在浙大登录后需点击「进入平台」。浏览器配置保存在 `runtime_local/campus_browser_profile/`。运行 `python campus_monitor.py sync` 检查每个来源的状态。`python campus_monitor.py doctor` 会在本地检查凭证、登录目录、课表周次、来源状态和计划任务安装记录，不访问网络。
4. 在钉钉开放平台创建可接收单聊消息的**应用机器人**，接收模式设为 Stream。启动 `python campus_monitor.py listen` 后，向机器人单聊转发单条文字或链接；只有收到「已记录」回复才算收件成功。合并转发、图片和文件需要在网页端补录或核对。
5. 配置完成后执行 `powershell -File scripts/windows/setup_campus_tasks.ps1 -PythonPath "C:\path\to\python.exe"`。任务在当前用户登录时启动机器人监听，并在每天 09:00 运行 `python campus_monitor.py daily`。电脑离线时钉钉消息不保证补取；未收到确认请在「校内事项」粘贴补录。

校内监测只在开关启用后运行。配置了可用的加密凭证时，同步先用统一身份认证接口读取教务课表和学在浙大待办，通常无需启动浏览器；接口失败会自动回退到专用浏览器，空结果或明显偏少的课表不会覆盖已有课表。公开通知、个人页面、课表、DeepSeek 各自显示检查状态；登录失效会显示错误，不会显示为「无新通知」。公开发布超过 180 天的历史通知只归档、不调用模型，避免旧截止日期污染计划。每日计划邮件和截止前 3 天、1 天的提醒按项目已有邮箱配置发送，每个日期和提醒阶段只发送一次。原通知、变更记录、计划和邮件去重记录存于 `runtime_local/campus_notices.sqlite3`。

校内平台的登录后页面可能调整。首次登录和平台改版后，应运行同步并核对来源状态及几条真实通知；如果提示「需要校准页面」，请提供该页面的地址或截图以更新采集规则。DeepSeek 只接收必要的通知文本和用于筛选的年级、学院、专业；摘要和日期仍以原通知为准。

完整配置、验收步骤及运行边界见 [校内通知操作说明](docs/campus_notifications.md)。本机已创建 `.venv` 时，可使用 `.venv\Scripts\python.exe` 运行上述命令。网页端也提供启动监听、安装计划任务和预览今日计划按钮。

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
2. 进入“配置检查”，确认后端入口、运行目录、输出目录和信息源状态。
3. 进入“配置”，填写邮箱、天气城市、关键词和需要的 API Key。
4. 回到“今日简报”，点击“生成并发送今日简报”。
5. 在页面中查看实时日志、运行记录、警告和错误摘要。
6. 到 `runtime_local\data\` 查看生成的简报或日程文件。

学术源说明：Semantic Scholar 使用公开 API，未配置 API Key 时可能返回 HTTP 429，
日志会直接提示限流原因；配置 API Key 或停用该来源即可。AMiner 当前没有免密钥 API，
默认停用。天气城市会自动去除多余空白并进行 URL 编码，留空时使用 Beijing。

## 入口说明

| 场景 | 命令 |
| --- | --- |
| 启动主界面 | `python launcher.py web` |
| 直接启动 Streamlit | `python -m streamlit run app.py` |
| 运行完整后端流程 | `python daily_assistant.py all` |
| 只生成学术简报 | `python daily_assistant.py crawl` |
| 只检查提醒/课程 | `python daily_assistant.py remind` |
| 发送测试邮件 | `python daily_assistant.py test-email` |
| 校内接入自检 | `python campus_monitor.py doctor` |
| 测试账号登录与数据读取 | `python campus_monitor.py api-check` |
| 查看校内来源状态 | `python campus_monitor.py status` |
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
│  ├─ config_diagnostics.py       # 配置检查与前端诊断
│  ├─ run_records.py              # 任务运行记录读写
│  ├─ gui_app.py                  # Tkinter 桌面备用界面
│  ├─ config_manager.py           # 配置读写和默认值
│  ├─ schedule_manager.py         # 课程、任务和每日计划
│  ├─ api_sources.py              # 学术 API 来源
│  ├─ web_fetcher.py              # HTTP/网页抓取降级
│  ├─ html_parser.py              # HTML/RSS 解析
│  ├─ campus_cli.py               # 校内通知 CLI（doctor 自检、api-check）
│  ├─ campus_service.py           # 校内收件箱、摘要、计划与提醒编排
│  ├─ campus_cas.py               # 统一身份认证客户端、教务课表与学在浙大待办
│  ├─ campus_sources.py           # 校园页面采集与课表解析
│  ├─ campus_diagnostics.py       # 校内接入本地自检
│  ├─ dingtalk_listener.py        # 钉钉 Stream 单聊监听
│  ├─ notice_store.py             # 通知、待办与邮件去重 SQLite
│  ├─ notice_processing.py        # DeepSeek 摘要与日期证据校验
│  ├─ password_crypto.py          # 本地授权码加密
│  └─ app_paths.py                # 开发/打包路径管理
├─ scripts\windows\               # Windows 启动和计划任务脚本
├─ scripts\security_check.py      # 提交前安全检查
├─ .github\workflows\ci.yml       # GitHub Actions 检查
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
runtime_local\campus_notices.sqlite3
runtime_local\tasks_installed.json
runtime_local\logs\
runtime_local\runs\YYYYMMDD-HHMMSS-xxxxxxxx.json
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
python scripts\security_check.py
python -m compileall -q app.py launcher.py src tests
python -m pytest
```

当前测试集应通过：

```text
101 passed
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
| `docs\DEVELOPMENT_HANDOFF.md` | 当前进度、架构、验证方式、风险与下一步交接 |
| `docs\ARCHITECTURE.md` | 当前架构和模块边界 |
| `docs\FRONTEND_ENTRYPOINTS.md` | 网页端、桌面端、CLI 的入口关系 |
| `docs\REPOSITORY_HYGIENE.md` | 哪些文件应该提交，哪些必须留在本地 |

## 注意

这个项目是本地自动化工具，不是云服务。运行任务时会访问外部信息源和邮件服务器；如果网络、API Key 或邮箱授权码未配置完整，前端会显示警告或错误摘要。真实邮件只会在用户启用邮件并手动运行完整流程或测试邮件时发送。
