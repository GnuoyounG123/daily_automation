# Daily Automation — 学术自动化助手

> 学术信息聚合、筛选与推送系统。支持多架构爬取自动降级、CLI / GUI 双模式运行。

---

## 快速开始

### 1. 安装

双击 `install.bat`，自动完成：
- 检测并安装 Python 依赖
- 创建桌面快捷方式
- 配置 Windows 定时任务（可选）

### 2. 运行

- **GUI 模式**：双击 `DailyAutomation.exe` 或桌面快捷方式
- **CLI 模式**：`python daily_assistant.py all`

### 3. 配置

首次运行后在 GUI 中配置：
1. **新闻源** — 添加/编辑学术信息来源（支持 RSS / Web / JSON / API 四种类型）
2. **关键词** — 设置筛选关键词（中英文分别配置）
3. **邮箱** — 配置 SMTP 邮件推送（支持 QQ/163/Gmail 等）
4. **API 密钥** — 配置学术 API 密钥以提升访问配额
5. **课程表** — 管理周课表和每日计划

---

## 功能特性

- ✅ **多架构爬取自动降级** — API → 静态爬取 → JS渲染 → 失败报告
- ✅ **5个公开学术API** — Semantic Scholar / CrossRef / DBLP / OpenAlex / CORE
- ✅ **4后端HTTP获取** — requests / httpx / urllib / selenium 自动降级
- ✅ **4策略HTML解析** — BeautifulSoup / lxml / regex / feedparser 自动降级
- ✅ **智能关键词筛选** — 标题权重×3 + 摘要权重×1
- ✅ **每日学术简报** — Markdown 格式，含精选论文和来源统计
- ✅ **邮件自动推送** — SMTP 发送，纯文本+HTML 双格式
- ✅ **离线术语翻译** — 50+ 学术术语词典，无需 API
- ✅ **日程提醒** — 精确时间匹配 + 未来2小时预告
- ✅ **课程表管理** — 周课表 + 每日计划 HTML 生成
- ✅ **失败源报告** — 无法爬取的源自动提醒，提供解决建议

---

## API 密钥配置

部分学术 API 需要密钥才能正常使用或提升配额，在 GUI 的「API密钥」标签页中配置：

| API | 是否必须 | 获取方式 |
|-----|---------|---------|
| Semantic Scholar | 可选（无 Key 限流） | [申请链接](https://www.semanticscholar.org/product/api#api-key) |
| OpenAlex | 可选（有 Key 更快） | [申请链接](https://docs.openalex.org/how-to-use-the-api/get-an-api-key) |
| CORE | **必须** | [申请链接](https://core.ac.uk/services/api) |

> 💡 未配置密钥时，CrossRef 和 DBLP 仍可正常使用。当爬取因缺少 API Key 失败时，系统会自动提醒并提供获取链接。

---

## 常见问题

| 问题 | 解决方案 |
|------|----------|
| 爬取返回空 | 检查网络连接；查看 `logs/` 日志 |
| Semantic Scholar 429 | 配置 API Key 或等待限流恢复 |
| CORE API 无结果 | 需配置 `api_keys.core`（[获取链接](https://core.ac.uk/services/api)） |
| AMiner 爬取失败 | SPA 站点，建议切换为 API 模式 |
| 定时任务不执行 | `Win+R` → `taskschd.msc` 检查任务状态 |
| 邮件发送失败 | 检查 SMTP 配置和授权码 |

---

## 技术栈

Python 3.8+ / Tkinter / requests / BeautifulSoup / feedparser / selenium / PyInstaller

---

## License

MIT
