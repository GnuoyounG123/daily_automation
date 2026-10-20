# 开发交接（2026-10-20）

> 面向后续开发者或 GPT 的入口文档。先读本文件，再读
> [ARCHITECTURE.md](ARCHITECTURE.md) 和 [campus_notifications.md](campus_notifications.md)。
> 本文件只描述代码与当前状态，不包含任何账号、密钥、邮箱或个人通知内容。

## 1. 项目定位

Daily Automation 是一个**本地优先**的个人每日助手：

- 汇总学术/技术信息，生成每日简报并可按配置发送邮件。
- 汇总学在浙大作业、教务通知、钉钉应用中用户主动转发的单聊消息。
- 用 DeepSeek 生成摘要和待办建议，但日期与事项必须经本人确认后才进入计划。
- 生成每日计划、T-3/T-1 临期邮件，并提供本地网页端进行审核和操作。

它不是云服务，也不是多租户产品。当前默认单用户、单机运行。

## 2. 当前状态

| 项目 | 状态 |
| --- | --- |
| 单元/界面测试 | 101 项通过（`tests/`，无真实网络、SMTP、DeepSeek、钉钉连接） |
| 统一身份认证接入 | 已实现 CAS 登录、ZDBK 课表、LMS 待办、只读测试接口；可选用 Fernet 加密记住密码 |
| 校内通知主链路 | 已实现：接口/浏览器采集 → 去重入库 → 摘要 → 待办 → 人工确认 → 计划 → 邮件 |
| 采集策略 | 接口优先，失败回退专用浏览器；空/部分课表不覆盖旧数据 |
| 钉钉收件 | 已实现官方 Stream 应用机器人单聊收件；只在本机监听进程运行时在线 |
| 就绪自检 | 已实现 `python campus_monitor.py doctor`，本地检查配置和状态（含账号与学年学期） |
| Windows 计划任务 | 脚本已实现；本机仅做过 `-DryRun` 预演，尚未在真实环境注册验收 |
| 真实端到端验收 | **部分完成**：真实 `api-check` 与 `sync` 已通过；首轮 215 条已消化（116 条公开通知与 15 条 LMS 待办已摘要，84 条历史公开通知归档，待摘要 0），98 条因日期证据不足进入待核对；专用浏览器页面通知、机器人、SMTP、任务注册未验收 |
| 24/7 收件 | **本阶段不实现**：已评估 serverless/常开主机方案，凭证托管与离线补取待设计 |
| Git 状态 | 校内功能整体**尚未提交**；最后一次提交为 `c6ac1b0`（2026-05-25） |

因此：不要假设工作区代码已经在版本历史里；不要在没有用户明确授权时执行
`git commit`、`git tag` 或 `git push`。

## 3. 安全与合规边界（不可变）

以下限制来自产品需求与权限边界，不是可选优化：

1. **不做手机端静默通知抓取。** 不申请 `NotificationListenerService`，不后台读取
   微信、钉钉或其他应用的通知。手机端如继续开发，只能做用户主动分享/粘贴导入。
2. **不绕过微信、钉钉的防爬或访问控制。** 个人微信没有官方消息读取 API；
   企业微信/钉钉群机器人只负责发送。完整消息历史需要组织管理员授权的合规存档，
   不属于本项目的实现范围。
3. **只使用用户主动提供的渠道：**
   - 用户自己登录后的学在浙大/教务页面；
   - 教务公开通知接口；
   - 用户主动单聊转发给官方钉钉应用机器人的文字或链接。
4. **默认只处理单聊。** 钉钉监听只接受 `conversationType == "1"`，并支持
   `allowed_sender_ids` 白名单；白名单为空时自检会给出警告。
5. **AI 不编造截止日期。** 日期必须能在原文中找到依据；模糊、多候选、时间范围、
   原文截断或模型输入截断时进入待核对，不发送确定时间提醒。
6. **本人确认后才排入计划。** `action_items.review_state` 未达到 `ready` 的事项
   不进入每日计划，也不发送确定截止提醒。
7. **密钥只加密保存。** 邮箱授权码、DeepSeek Key、钉钉 Client Secret、
   可选记住的浙大密码使用 `runtime_local/.secret_key` 的 Fernet 密钥加密。
   DeepSeek、钉钉与校园接口只会使用 `fernet:` 格式的凭证；旧 `enc:` 或明文会被
   拒绝或提示重新保存。未勾选「记住密码」时，保存配置会清除已存密码。
8. **不提交本地数据。** `runtime_local/`、`config.json`、`.secret_key`、
   `schedule.json`、`weekly_tasks.json` 都不进入 Git。文档和测试不得写入真实密钥、
   邮箱、学号、通知正文。
9. **邮件去重不等于绝对单次投递。** `mail_ledger` 在发送成功后保留记录；发送失败
   会释放以便重试，但 SMTP 断网或进程被强制终止时仍需人工核对收件。
10. **校园接口只做本人账号的只读访问。** 不保存 SSO 票据或服务 Cookie，不绕过
    验证码、限流或访问控制；遇到验证码、HTTP 921 限流或认证失败时停止该轮接口
    同步并提示，不自动重试或伪造请求。测试与文档不得包含真实账号、密码或 Cookie。

## 4. 数据流

```text
学号/密码（可选 Fernet 记住）
        │  CampusCasClient：CAS → ZDBK 课表 / LMS 待办
        ▼（失败回退）
学在浙大 / 教务公开接口 / 教务登录页
        │  CampusBrowser + parser / collect_public_zdbk
        ▼
   CampusService.sync()
        │  upsert_notice（source + external_id 去重，正文变化保留 revision）
        ▼
 runtime_local/campus_notices.sqlite3
        │  process_pending()，每次最多 30 条
        ▼
 DeepSeekSummarizer → validate_analysis
        │  日期证据校验、相关性、多个 action、建议开始日期
        ▼
 action_items（review_state = pending / review / ready）
        │  网页端逐条核对、修改、加入个人计划
        ▼
 schedule_manager + weekly_tasks
        │
        ├─ build_daily_plan() → runtime_local/data/daily_plan_YYYYMMDD.html
        ├─ send_daily_plan()  → 每日一封（mail_ledger 去重）
        └─ send_due_reminders() → T-3 / T-1（按事项、截止时间、阶段去重）

钉钉官方应用机器人（Stream 单聊）
        │  dingtalk_listener.listen()
        ▼
 record_message() → CampusService.ingest() → 同一收件箱与摘要链路
```

Windows 计划任务：

| 任务 | 触发 | 行为 |
| --- | --- | --- |
| `DailyAutomation_CampusDaily` | 每天 09:00，漏执行可补 | `campus_monitor.py daily` |
| `DailyAutomation_DingTalkListener` | 当前用户登录 | `campus_monitor.py listen`，隐藏运行 |

## 5. 模块地图

| 文件 | 职责 |
| --- | --- |
| `app.py` | Streamlit 兼容入口 |
| `launcher.py` | 启动网页端或后端任务 |
| `campus_monitor.py` | 校内 CLI 兼容入口 → `campus_cli.main` |
| `src/daily_automation/web_app.py` | 本地网页端；简报、校内事项、自检、配置、运行记录 |
| `src/daily_automation/campus_cli.py` | `login/sync/daily/listen/status/doctor/api-check` |
| `src/daily_automation/campus_service.py` | 接口优先同步编排、浏览器回退、摘要处理、计划、邮件、去重发送 |
| `src/daily_automation/campus_cas.py` | CAS 登录、原始 RSA 加密、ZDBK 课表、LMS 待办、只读 `probe_account` |
| `src/daily_automation/campus_sources.py` | 专用 Chrome、登录检测、公开通知、页面采集、课表解析（浏览器回退） |
| `src/daily_automation/campus_diagnostics.py` | 本地就绪检查（含账号凭证与学年学期） |
| `src/daily_automation/dingtalk_listener.py` | 官方 Stream 客户端、单聊限制、确认回复、心跳 |
| `src/daily_automation/notice_store.py` | SQLite 收件箱、revision、action_items、source_state、mail_ledger |
| `src/daily_automation/notice_processing.py` | DeepSeek JSON 摘要、日期证据校验、建议开始日期 |
| `src/daily_automation/course_calendar.py` | 周次/单双周解析 |
| `src/daily_automation/notice_links.py` | 只读取公开 HTTPS 链接正文 |
| `src/daily_automation/config_manager.py` | 配置、课表、每周任务读写 |
| `src/daily_automation/password_crypto.py` | 本地 Fernet 加解密 |
| `src/daily_automation/config_diagnostics.py` | 通用配置检查（新闻源、邮件、API Key） |
| `tests/test_campus_cas.py` | CAS/RSA/跳转链/新旧课表字段/待办解析/错误分类/只读探测单测（新增 14 项） |
| `tests/test_campus_notices.py` | 日期、去重、改期、多动作、监听、邮件、接口优先与课表保护 |
| `tests/test_campus_web.py` | 真实 Streamlit 控件测试（隔离临时目录） |
| `tests/test_campus_diagnostics.py` | 就绪检查单测（含账号与学期检查） |

根目录其他 Python 文件是旧命令/导入的薄包装，不承载业务逻辑。

## 6. 本地数据

| 路径 | 内容 | Git |
| --- | --- | --- |
| `runtime_local/config.json` | 用户配置（含加密后的凭证） | 忽略 |
| `runtime_local/.secret_key` | Fernet 密钥，丢失后旧密文无法解密 | 忽略 |
| `runtime_local/schedule.json` | 课表、学期开始日期 | 忽略 |
| `runtime_local/weekly_tasks.json` | 每周个人任务 | 忽略 |
| `runtime_local/campus_notices.sqlite3` | 通知、版本、待办、来源状态、邮件账本 | 忽略 |
| `runtime_local/campus_browser_profile/` | 专用 Chrome 登录会话 | 忽略 |
| `runtime_local/tasks_installed.json` | 计划任务安装标记（本次新增） | 忽略 |
| `runtime_local/data/` | 简报、每日计划 HTML | 忽略 |
| `runtime_local/logs/` | 运行日志 | 忽略 |
| `runtime_local/runs/` | 网页端任务运行记录 | 忽略 |

备份时必须同时保留 `config.json` 和 `.secret_key`；只恢复其中一个会导致凭证无法解密。

## 7. 本次交付（2026-10-20）：统一身份认证接入

1. 新增 `campus_cas.py`：
   - CAS 登录页执行令牌解析、`getPubKey` 原始 RSA 加密（无 PKCS#1 填充）、
     错误密码与验证码识别；
   - 教务（ZDBK）服务登录，读取 `kbList` 课表并映射为日程结构；兼容旧版
     `kcmc/cdmc/xm/jc/zcd` 与新版 `kcb` HTML 块、`djj/skcd` 节次、`xxq/dsz` 周次提示；
   - 学在浙大（LMS）服务登录，读取 `/api/todos` 待办并映射为通知；
   - 处理 meta-refresh 与自动提交表单跳转，但只允许校内 HTTPS 域名；
   - HTTP 921 限流、验证码、会话失效、协议异常分别归类；
   - `probe_account()` 只读测试 CAS、课表与待办，不落库、不打印凭证。
2. 配置新增 `username`、`password`、`remember_password`、`academic_year`、`term`。
   密码仅在用户勾选「记住密码」时用 Fernet 加密保存；关闭记住或更换学号会清除
   旧密码。`ensure_default_config` 现在会把缺失的 campus 键合并进旧配置，并使用
   `copy.deepcopy` 避免默认值被修改。
3. 同步改为接口优先：CAS → ZDBK 课表 → LMS 待办；接口成功且缺少浏览器会话时
   跳过 Chrome，并把未覆盖的页面来源标为警告。接口失败自动回退浏览器。
4. 课表保护：空结果或课程数不足上次一半时保留旧课表；学期变更时才允许替换为
   更小的课表。手工课程继续与同步课程合并。
5. 网页端「配置」新增学号、密码、记住密码、学年、学期和「测试统一身份认证
   （不保存）」；保存前校验学年为 `20xx`、学期合法、第一周周一日期有效。
6. `doctor` 新增 `campus_login` 与 `campus_term` 检查；完整配置下共 18 项。
7. 新增 CLI `python campus_monitor.py api-check`：复用已存加密密码或提示输入，
   输出 CAS/课表/待办状态与条数；两项服务成功才返回 0。
8. 测试从 74 增至 91：新增 14 项 CAS/解析/错误分类测试（含新版 `kcb` 课表），
   以及接口优先、部分课表保护、接口失败回退、诊断计数等用例。
9. 24/7 收件本阶段明确不实现；不新增云端服务、队列、数据库迁移或计划任务。

真实 `api-check` 已验证：CAS 登录成功，ZDBK 读取 18 门课程，LMS 读取 15 条待办，
无错误消息。真实 `sync` 随后通过 API 入库，`changed=215`；215 条为公开通知
（最多 200 条）与 LMS 待办的首次导入。

10. 修复摘要批次中断：DeepSeek 默认思考模式会消耗 2000–4000 token 预算并截断 JSON；
    请求改为 `thinking: {"type": "disabled"}`，仅在截断时按 2000→4000 token 重试。
    单条摘要失败不再中断整批，来源状态会记录失败通知编号和简短错误。
11. 公开通知增加历史归档：发布超过 180 天的通知只标记为已归档、不相关，不调用模型；
    首轮导入中的 84 条历史通知因此未产生模型调用。
12. 测试从 91 增至 94：新增“推理截断后重试”“单条失败继续处理”“历史公开通知归档”
    三项回归测试。
13. 修复简报生成中的天气与学术源失败：
    - `WeatherAPI` 先折叠城市名空白并做 URL 编码，空值回退 `Beijing`；
      `ConfigManager` 的读取、保存和旧配置迁移也统一规范化城市名。
    - 配置增加 `config_version`（当前为 1）。旧配置一次性迁移：
      Semantic Scholar 首页 `web` 源改为公开 API（`type: api`）；
      AMiner 因当前没有免密钥 API 而停用并写入说明。
    - `daily_assistant.load_config()` 开始调用 `ensure_default_config()`，
      命令行生成简报也会应用迁移。
    - Semantic Scholar 在 HTTP 429 且响应体为文本时不再误报“JSON 无效”，
      而是记录“HTTP 429 限流，请配置 API Key 或稍后重试”；
      API 类型来源不再回退 Selenium。
14. 测试从 94 增至 101：新增天气空白/URL 编码、配置迁移与幂等、
    API 429 文案等回归测试。真实天气请求已验证成功；真实 Semantic Scholar
    无 Key 时被正确识别为 429 限流。

真实摘要链路已验证：最终 `status` 为待摘要 0；116 条公开通知与 15 条 LMS 待办已有摘要，
84 条历史公开通知归档；98 条通知因日期范围、原文不明确或缺少可靠日期依据进入待核对，
对应 116 条活动行动项。未建立专用浏览器，因此课程公告/作业页面和个人通知页面尚未检查。

上一阶段的 `doctor`、安装标记 `tasks_installed.json` 与网页端自检面板保持不变。

## 8. 验证命令

在项目目录执行（本机已创建 `.venv`）：

```powershell
.venv\Scripts\python.exe scripts\security_check.py
.venv\Scripts\python.exe -m compileall -q app.py launcher.py campus_monitor.py src tests
.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q --basetemp=runtime_local/pytest-tmp-verify
```

**Windows 临时目录特例：** 本机 `C:\Users\<user>\AppData\Local\Temp\pytest-of-<user>`
存在 ACL 问题，直接运行 `pytest` 可能在收集阶段报
`PermissionError: [WinError 5]`。这不是测试失败；使用上面的
`--basetemp=runtime_local/pytest-tmp-verify` 即可。该目录已被忽略，不要提交。

其他验证：

```powershell
# 本地诊断，不访问网络
python campus_monitor.py doctor

# 只读测试统一身份认证、课表与待办（会访问校园网）
python campus_monitor.py api-check

# 查看来源状态和待处理数量
python campus_monitor.py status

# 只验证计划任务配置，不注册
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/windows/setup_campus_tasks.ps1 -DryRun

# 本地网页端
python launcher.py web
```

## 9. 已知缺口与风险

按优先级：

1. **真实摘要已跑通，人工抽查与页面覆盖仍待验收。** 本人 `api-check` 与 `sync` 已证明
   CAS、ZDBK 课表（18 门）、LMS 待办（15 条）和公开通知可读取、入库并摘要；首轮
   215 条已消化，待摘要 0。98 条进入待核对，日期证据校验偏保守（日期范围、原文
   不明确或没有可信截止时间时会进入该状态），需要人工抽查摘要与相关性。专用浏览器
   页面通知、机器人、SMTP、任务注册未验收。
2. **校园内部接口可能变化。** ZDBK 课表与 LMS 待办不是公开承诺的稳定 API；字段、
   学期代码、跳转链或风控策略调整会导致失败。失败会标记来源并回退浏览器，但需要
   真实样本补回归测试。验证码、HTTP 921 和异常登录只提示，不自动绕过。
3. **监听是本机进程，电脑关机/未登录/进程退出时钉钉消息没有历史补取通道。**
   未收到「已记录」回复只能网页端粘贴补录。24/7 serverless 方案本阶段评估后暂缓，
   这是当前最大的可用性缺口。
4. **校内页面解析仍然脆弱。** 公开通知和个人通知页依赖渲染后的链接与文本；平台
   改版会导致采集失败。接口已覆盖课表与待办，但通知正文仍需浏览器或公开接口。
5. **接入摩擦高。** 用户需要创建钉钉应用机器人、配置校园账号与学期、DeepSeek、
   邮箱和 Windows 任务。`doctor` 与测试登录降低了定位成本，但没有消除配置步骤。
6. **安装标记不是实时状态。** `tasks_installed.json` 只能证明脚本成功运行过。
7. **单用户/单机假设。** 数据库、锁、浏览器 profile、邮件账本都在本地，没有多租户
   隔离、鉴权、配额和云端队列。
8. **未提交工作区。** 校内功能和本次文档全部未提交；提交前需要用户明确授权，并先
   检查 `git status`、`security_check.py`，确认不包含 `runtime_local/` 和密钥。

## 10. 推荐开发顺序

### P0：把当前工作安全落库

- 用户确认后，按源码/测试/文档分组提交；不要提交 `runtime_local/`、`config.json`、
  `.secret_key`、`schedule.json`、`weekly_tasks.json`。
- 提交前运行 `security_check.py` 和完整 pytest。

验收：`git status` 只剩未跟踪的本地运行目录；CI 的 compile/test/security 全绿。

### P1：完成真实端到端验收

- 真实 `sync` 已完成首轮摘要与历史归档（待摘要 0）；下一步人工抽查摘要与日期证据，
  处理 98 条待核对通知，避免旧事项进入计划。
- 建立专用浏览器会话，补验课程公告、作业页面和个人通知页面，再验收机器人、SMTP
  与计划任务注册。
- 按 `docs/campus_notifications.md` 的「上线验收清单」逐项执行。
- 记录每项的真实结果，不要用 mock 结果代替。
- 对失败项保留原页面地址/截图，更新解析器并补 fixture 测试；不要把真实 Cookie、
  学号、密码或通知正文写入测试。

验收：`api-check` 两个服务成功，清单全部通过，且 `doctor` 无错误项。

### P2：让收件 24/7 可用

优先做**单用户常在线监听**，而不是立刻做多租户：

- 方案 A：一台常开 Windows 迷你主机/NAS 运行现有监听和每日任务；只建立出站
  WebSocket，不开放入站端口。最小改动，但仍依赖本机在线。
- 方案 B：在受控 VPS/容器运行监听，消息写入加密队列或对象存储，再由本地同步；
  需要解决凭证托管、鉴权、去重和离线补取。不能直接复制本地 SQLite 到公网。
- 方案 C：发布多用户机器人。需要组织授权、应用审核、租户隔离、隐私政策和合规
  存档，当前不推荐作为下一步。

验收：断网/退出登录/进程重启后，用户能明确知道是否漏收；已收到的消息不重复、
不丢失，并且不扩大消息读取权限。

### P3：降低接入与运维成本

- 把 `doctor` 的修复建议做成可点击的配置引导（当前已展示明细）。
- 安装脚本增加实时任务状态查询（`Get-ScheduledTask`），而不是只依赖标记文件。
- 增加来源状态时间线、日志导出和「一键重试摘要」。
- 在网页端明确区分「监听未启动」「心跳过期」「凭证错误」「来源登录失效」。

验收：新用户在不看源码的情况下能完成配置，并能从界面判断下一步该做什么。

### P4：解析可靠性

- 用脱敏 HTML fixture 覆盖公开通知接口、LMS 作业/公告、课表、登录失效页面。
- 为每个来源定义显式的 schema/selector 失败信号；解析不到时标记错误，不返回空列表。
- 增加「最近一次成功采集时间」和「本次采集条数」的对比告警。

验收：平台改版时测试能指出具体来源和缺失字段，而不是静默变成 0 条。

### P5：职业规划方向的扩展

如果回到更大的个人生涯规划产品：

- 先做用户主动触发的导出（Markdown/JSON），让用户自己决定是否交给云端 agent。
- 云端分析只接收用户确认过的内容；需要明确的删除、保留期和撤回机制。
- 手机端只做「分享/粘贴导入 + 逐条批准 + 仅导出批准项」，不做通知监听。
- 不要把「绕过平台防爬」作为产品能力描述或技术路线。

## 11. 给后续 GPT 的工作约定

1. 先读本文件、`docs/ARCHITECTURE.md`、`docs/campus_notifications.md`，再改代码。
2. 业务代码放 `src/daily_automation/`；根目录入口只做转发。
3. 修改数据表结构时写迁移或兼容逻辑；不要要求用户删除现有 SQLite。
4. 测试不得访问真实校园网、DeepSeek、SMTP 或钉钉；使用 mock/临时目录。
5. 运行测试必须带 `--basetemp=runtime_local/pytest-tmp-verify`（本机 Temp ACL 问题）。
6. 不把任何真实密钥、邮箱、学号、通知正文写进代码、测试、文档或提交信息。
7. 不新增静默通知读取、微信/钉钉历史抓取、验证码/密码采集、反检测或绕过限流能力。
8. 任何提交、打 tag、推送、注册计划任务、发送真实邮件，都要先获得用户明确同意。
9. 如果发现文档与代码不一致，以当前代码和测试为准，并更新文档。
10. 交接时说明：改了什么、如何验证、哪些是模拟结果、哪些尚未真实验收。
11. 修改 `campus_cas.py` 时保持只读、按服务建立会话、不持久化 Cookie/票据；
    测试只用合成响应和假 RSA 密钥，真实 `api-check` 必须由用户主动执行。

## 12. 相关文档

- [ARCHITECTURE.md](ARCHITECTURE.md)：模块边界与仓库分区
- [campus_notifications.md](campus_notifications.md)：校内功能说明、配置步骤、验收清单
- [FRONTEND_ENTRYPOINTS.md](FRONTEND_ENTRYPOINTS.md)：网页端/桌面端/CLI 入口
- [REPOSITORY_HYGIENE.md](REPOSITORY_HYGIENE.md)：哪些文件必须留在本地
