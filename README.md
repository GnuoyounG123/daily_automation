# Daily Automation

本项目是一个本地运行的每日自动化助手，用于聚合学术/技术信息源、生成简报、发送邮件，并管理课程/提醒任务。

当前主入口是本地浏览器网页端，桌面 GUI 和命令行任务作为辅助入口保留。

## 快速开始

安装依赖：

```powershell
python -m pip install -r requirements.txt
```

启动网页端：

```powershell
python launcher.py web
```

或直接运行：

```powershell
python -m streamlit run app.py
```

打开浏览器访问：

```text
http://localhost:8501
```

Windows 用户也可以双击：

```text
scripts\windows\启动网页端.bat
```

## 当前入口

| 入口 | 命令/文件 | 用途 |
| --- | --- | --- |
| 网页端 | `python launcher.py web` | 主界面，简报优先，含配置和控制台 |
| Streamlit | `python -m streamlit run app.py` | 等价网页端入口 |
| 桌面 GUI | `python gui_app.py` | 备用 Tkinter 桌面界面 |
| 后端完整任务 | `python daily_assistant.py all` | 生成简报并检查提醒 |
| 学术简报 | `python daily_assistant.py crawl` | 只生成/发送学术简报 |
| 提醒检查 | `python daily_assistant.py remind` | 只检查课程/提醒 |

## 项目结构

```text
.
├─ app.py                         # Streamlit 网页端兼容入口
├─ launcher.py                    # 启动网页端/运行后端任务
├─ daily_assistant.py             # 后端 CLI 兼容入口
├─ gui_app.py                     # 桌面 GUI 兼容入口
├─ src\daily_automation\          # 正式源码包
│  ├─ web_app.py                  # Streamlit 网页端
│  ├─ daily_assistant.py          # 信息抓取、筛选、报告、邮件、提醒
│  ├─ gui_app.py                  # Tkinter 备用界面
│  ├─ config_manager.py           # 配置读写和默认值
│  ├─ schedule_manager.py         # 课程/任务计划
│  ├─ api_sources.py              # 学术 API 来源
│  ├─ web_fetcher.py              # HTTP/网页抓取降级
│  ├─ html_parser.py              # HTML/RSS 解析
│  ├─ password_crypto.py          # 本地密码加密
│  └─ app_paths.py                # 路径管理
├─ scripts\windows\               # Windows 启动和计划任务脚本
├─ packaging\pyinstaller\         # PyInstaller 打包配置
├─ docs\                          # 架构和维护说明
├─ tests\                         # 单元测试
├─ runtime_local\                 # 本地配置、密钥、日志、输出；不提交
└─ artifacts\                     # 构建/分发产物；不提交
```

## 配置和输出

开发环境运行时，配置和输出都写入：

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

这些文件包含本机状态、邮箱授权码或 API 密钥，已经被 `.gitignore` 排除。

## 客户/同事试跑

本地客户测试副本位于：

```text
customer_test_copy\
```

这是本机测试目录，不提交到 GitHub。需要重新生成时，应从当前源码复制干净文件，并避免带入 `config.json`、`.secret_key`、`runtime_local\`、日志或 exe 构建产物。

## 开发检查

运行测试：

```powershell
python -m pytest
```

语法检查：

```powershell
python -m compileall -q app.py launcher.py src tests
```

当前约定：

- 新代码优先写入 `src/daily_automation/`
- 根目录 Python 文件只保留兼容入口
- 不提交真实配置、密钥、日志、日报、exe、zip、build/dist/release 产物
- 网页端是主体验；桌面 GUI 是备用体验

## 打包

桌面版可执行文件使用 PyInstaller：

```powershell
python -m PyInstaller packaging\pyinstaller\build_exe.spec --clean --noconfirm
```

输出在：

```text
dist\DailyAutomation.exe
```

`dist\`、`build\`、`artifacts\`、`customer_test_copy\` 都不进入源码仓库。
