# Daily Automation Project

## 当前状态

- 仓库来源: `https://github.com/GnuoyounG123/daily_automation`
- 当前分支: `main`
- 上游分支: `origin/main`
- 项目类型: 本地运行的每日自动化助手
- 主入口: Streamlit 本地网页端

## 项目定位

Daily Automation 用于聚合学术与技术信息源，生成每日简报，按需发送邮件，并维护课程、提醒和日程输出。当前代码以本地网页端为主入口，CLI 和桌面 GUI 作为兼容入口保留。

## 常用命令

```bash
python -m pip install -r requirements.txt
python launcher.py web
```

```bash
python -m compileall -q app.py launcher.py src tests
python -m pytest
```

## 关键目录

| 路径 | 用途 |
| --- | --- |
| `src/daily_automation/` | 正式源码包 |
| `app.py` | Streamlit 兼容入口 |
| `launcher.py` | 网页端和后端任务启动入口 |
| `docs/` | 架构、入口和仓库维护说明 |
| `tests/` | 单元测试 |
| `scripts/windows/` | Windows 启动和计划任务脚本 |
| `runtime_local/` | 本机配置、密钥、日志和生成文件，不提交 |

## 初始化待办

- [ ] 安装依赖并确认本地 Python 版本为 3.10 或更高。
- [ ] 运行测试命令确认当前环境可用。
- [ ] 启动 `python launcher.py web`，在浏览器打开 `http://localhost:8501`。
- [ ] 在网页端配置邮箱、天气城市和需要的 API Key。
- [ ] 生成一次今日简报，确认 `runtime_local/data/` 有输出文件。

## 协作约定

- 新功能优先写入 `src/daily_automation/`。
- 根目录 Python 文件只保留兼容转发逻辑。
- 不提交本地配置、密钥、日志、运行数据或构建产物。
- 代码质量与维护流水线见 `docs/CODE_QUALITY_AND_MAINTENANCE.md`。
- 修改入口、路径、打包或运行方式时，同步更新 `README.md` 和 `docs/`。
