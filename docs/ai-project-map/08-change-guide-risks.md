# 改动指南、风险与维护规则

> [返回 AI 项目地图总目录](../AI_PROJECT_MAP.md)
>
> **阅读范围：** 用于代码修改前评估影响范围，了解已知风险、README 偏差、AI 工作协议和地图维护规则。
>
> **相关分卷：** 具体实现事实按总目录路由到 [01-07](../AI_PROJECT_MAP.md#分卷目录)。
## 修改影响矩阵

| 修改区域 | 直接影响 | 必查调用者/契约 | 最小测试 |
|---|---|---|---|
| `database_manager.py` DDL/任务字段 | 缓存、flush、分页、同步、导出、甘特 | config 保存、TaskLabel 数据、远程 payload、维护脚本 | 两个 database 测试文件 + 全套 |
| 普通任务保存/坐标 | 象限语义、历史、颜色一致性 | `config_manager.save_tasks`、`TaskLabel.pos`、窗口缩放 | 新增坐标测试 + UI/DB 全套 |
| 完成/删除语义 | 主面板可见性、归档、远程 tombstone | `load_tasks`、restore 方法、归档基类 | history_sync + archive panels |
| 历史结构 | 历史页、同步 payload、LLM 概要、导出 | `task_history` PK、merge key、SummaryWorker | history_sync + history_viewer |
| 定时任务字段/算法 | 生成时间、远程同步、计划表 UI | scheduler、scheduled cache/API | remote 测试 + 新调度测试 |
| 远程配置/认证 | bootstrap、周期线程、设置提交 | `RemoteConfigManager`、DB 单例、冲突 UI | remote 测试全文件 |
| `QuadrantWidget` 设置 | 实时预览、回滚、配置持久化 | SettingsDialog result contract | remote 设置段 + settings |
| 共享样式/Fluent | 所有对话框和表格 | objectName、私有 monkey patch | panel styles + fluent + transparency |
| 自适应表格 | 历史/完成/删除/定时表格 | 排序与 cellWidget 对齐 | history_viewer + archive |
| LLM/概要 | SQL、提示词、SDK、线程 | `LLM_CONFIG`、JSON Schema、Excel 列 | 新增 SummaryWorker 单测 |
| 甘特图 | DB 读取、端口、浏览器/CDN | DB_PATH、flush、QWebEngine fallback | 新增 Flask 路由测试 |
| 托盘/批处理 | Windows 启动、退出、编码 | venv 路径、cwd、正常关闭 | Windows 手工冒烟 |
| 配置字段定义 | 表单、历史字段、DB 映射 | task/schedule dialogs、默认字段 | urgency UI + settings + DB |

共享 UI、配置、数据库或同步改动完成后应跑全套；纯局部文案/QSS 也要跑对应静态集成测试。

## 已知风险与 README 偏差

### 高优先级风险

1. **敏感配置明文**：两个 JSON 可能含真实 LLM/远程凭据和服务地址，且配置 CLI 会显示令牌前缀。
2. **共享 SQLite 连接跨线程**：`check_same_thread=False` 允许跨线程，但除缓存锁外没有独立 DB 锁；概要线程、flush、同步和 GUI 查询可能并发使用同一连接。
3. **flush 全量 REPLACE**：每次 dirty 都重写所有缓存记录，数据量增大后性能下降；启用外键后还可能改变历史语义。
4. **托盘强杀绕过关闭流程**：`terminate/kill` 可能跳过最后 flush/同步。
5. **定时任务 `sync_status` 不持久化**：未 flush/未上传的修改在重启后可能被当成已同步。

### 中优先级风险

1. 坐标颜色象限与持久化 urgency/importance 可能在中心附近不一致。
2. 每日刷新只在精确分钟触发，错过不补；seconds 配置无效。
3. 周期字段中的 week/day 等参数实际不参与计算，UI/远端可能误以为支持。
4. LLM 概要历史键名不匹配，提示词实际历史信息缺失。
5. LLM 异步客户端跨线程/跨事件循环共享，兼容性未知。
6. Gantt 直接读磁盘且依赖 CDN，离线和缓存新鲜度有限。
7. 主 DB 连接未启用外键，维护脚本宣称的级联与应用运行时行为不一致。
8. `sync_manual.py` 的顶层导入路径不符合包结构。
9. `windows/*.bat` 中文呈现疑似乱码，可能是历史编码已损坏。
10. `load_config()` 只浅合并默认配置，嵌套缺失不自动修复。

### 低优先级/技术债

- `save_undo_state()`、`undo_action()`、`SyncManager.resolve_conflicts()` 是占位或注释实现。
- 甘特按钮被注释但相关代码、依赖和入口仍保留。
- `config` SQLite 表未使用。
- `priority` 已迁移但仍散落在 schema、导出和 LLM。
- `UIManager` 的 30 秒自动保存只记录日志。
- 多处宽泛 `except:` 隐藏具体错误。
- 主窗口和 DB 管理器体积大，改动影响面广。

### README 与当前源码偏差

| README 说法 | 当前事实 |
|---|---|
| 根目录有 `ui.py`、`quadrant_widget.py` 等平铺文件 | 已迁入 `ui/`、`core/`、`database/`、`config/` |
| `python tray_launcher.py` | 实际文件为 `windows/tray_launcher.py`；推荐 `windows/start.bat` 或直接 `python main.py` |
| 存在 `sync_manager.py` | 当前是 `database/sync_manual.py`，且导入路径可疑 |
| 存在 `server_example.py`、`server_requirements.txt` | 当前仓库不存在服务器实现 |
| 应用配置存储在数据库 | 当前主配置存储在 `config/config.json`；SQLite `config` 表未使用 |
| 完整客户端-服务器架构含服务器数据库 | 仓库只有客户端 REST 契约，无法验证服务端数据库 |
| 同步冲突为纯时间戳自动解决 | 当前 GUI 有 5 分钟本地优先 + 逐条人工选择 |
| 本地模式可运行托盘入口 | 可行，但 README 路径错误 |
| API 示例 payload 以 `priority` 为主 | 当前核心分类是 urgency/importance，priority 仅兼容保留 |

## AI 工作协议

后续 AI 代理修改此仓库时：

1. 先读本地图，再读目标文件和对应测试；不要只读 README。
2. 先执行 `git status --short`，保留其他代理和用户的未提交改动。
3. 不读取、输出、提交或复制配置中的真实 `api_key`、`api_token`、用户名、服务地址。
4. 桌面业务必须复用 `get_db_manager()`；不要新增平行 SQLite 连接。Gantt 是现有例外。
5. 保留逻辑删除、历史、缓存锁、dirty、周期 flush、关闭 flush 和远程同步语义。
6. 任何位置/尺寸改动必须明确验证“右高紧急、上高重要”。
7. UI 优先复用 `ui.notifications`、`ui.styles`、`ui.fluent`、`ui.scrollbar`、`ui.adaptive_table` 和 `ui.degree_badges`。
8. 修改 DB/schema/API 时同步检查：缓存规范化、flush SQL、分页 SQL、远程 payload、Gantt、维护脚本和测试。
9. 修改动态字段时同步检查普通表单、定时表单、TaskLabel、历史字段和导出列。
10. Windows 文件写入只用 PowerShell 7 或直接编辑工具，并显式 UTF-8；保留中文和原换行风格。
11. 不把数据库、备份、日志、缓存、venv、`.tmp-tests`、`.worktrees` 当源码修改。
12. 高风险修改先加聚焦测试，再跑全套；视觉修改还需 UI 冒烟验证。

## 地图维护规则

出现以下变化时必须同步更新本文件：

- 新增/移动/删除源码文件或入口。
- import 方向、模块职责或关键调用链改变。
- 配置键、敏感信息位置、默认值契约改变。
- SQLite 表、字段、索引、缓存、flush、锁或单例行为改变。
- 远程端点、鉴权、payload、冲突或同步时序改变。
- 坐标与 urgency/importance 映射改变。
- 定时任务周期或触发策略改变。
- 完成、删除、还原、历史、搜索、分页规则改变。
- 导出列、LLM SDK/Schema/提示词或甘特数据映射改变。
- 第三方依赖、Windows 启动方式或测试所有权改变。

维护时应：

1. 更新“分析日期、基线提交、工作树状态”。
2. 重新扫描实际目录，继续排除生成物和二进制。
3. 用当前源码验证 README 偏差，不机械复制旧描述。
4. 在“已知风险”中删除已修复项并记录新风险。
5. 更新影响矩阵和测试覆盖地图。
6. 对文档执行敏感键值扫描，只允许出现键名和占位说明。
7. 保证 Mermaid 可渲染、文件为 UTF-8、中文为主。
