# AI 项目地图总目录

> 面向后续 AI 代理的按需阅读入口。先读本页，再根据任务选择 1–3 个分卷；不要默认加载全部分卷。

## 项目快照

- Windows 优先的 PyQt6 四象限桌面任务管理器。
- `main.py` 是桌面应用入口，`windows/tray_launcher.py` 是独立托盘包装进程。
- `core/quadrant_widget.py` 是主 UI 与工作流协调中心。
- `database/database_manager.py` 是 SQLite、缓存、历史、flush 和远程同步中心。
- 任务空间契约：右侧为高紧急，上方为高重要。
- 当前地图基线：2026-06-10，提交 `59e5548`。

## 阅读协议

1. 先判断任务类型，只打开路由表列出的分卷。
2. 一般任务读取总目录加 1 个主分卷；跨层修改最多先读 2–3 个相关分卷。
3. 不要为了“完整了解”一次性加载全部八卷。
4. 分卷事实冲突时，以当前可执行源码和测试为准，并更新对应分卷。
5. 修改目录、入口、依赖、schema、配置、同步、关键流程或测试所有权时，更新相应分卷和本目录。

## 任务路由

| 准备理解或修改 | 必读 | 需要时追加 |
|---|---|---|
| 项目结构、入口、模块边界 | [01 架构](ai-project-map/01-architecture.md) | [08 风险](ai-project-map/08-change-guide-risks.md) |
| 启动、托盘、主窗口、任务标签 | [02 桌面任务流](ai-project-map/02-desktop-task-flow.md) | [05 UI 配置](ai-project-map/05-ui-configuration.md) |
| 拖动、象限、urgency/importance | [02 桌面任务流](ai-project-map/02-desktop-task-flow.md) | [03 数据同步](ai-project-map/03-database-sync.md)、[07 测试](ai-project-map/07-dependencies-tests.md) |
| SQLite、字段、缓存、flush、历史 | [03 数据同步](ai-project-map/03-database-sync.md) | [07 测试](ai-project-map/07-dependencies-tests.md)、[08 风险](ai-project-map/08-change-guide-risks.md) |
| REST、认证、远程同步、冲突 | [03 数据同步](ai-project-map/03-database-sync.md) | [02 桌面任务流](ai-project-map/02-desktop-task-flow.md)、[07 测试](ai-project-map/07-dependencies-tests.md) |
| 定时任务、完成/删除列表、恢复 | [04 定时归档](ai-project-map/04-scheduler-archive.md) | [03 数据同步](ai-project-map/03-database-sync.md)、[07 测试](ai-project-map/07-dependencies-tests.md) |
| 样式、通知、日期控件、表格、设置 | [05 UI 配置](ai-project-map/05-ui-configuration.md) | [02 桌面任务流](ai-project-map/02-desktop-task-flow.md)、[07 测试](ai-project-map/07-dependencies-tests.md) |
| 导出、Excel、LLM 摘要、甘特图 | [06 导出与扩展](ai-project-map/06-export-llm-gantt.md) | [03 数据同步](ai-project-map/03-database-sync.md)、[07 测试](ai-project-map/07-dependencies-tests.md) |
| 依赖升级、选测试、判断基线失败 | [07 依赖测试](ai-project-map/07-dependencies-tests.md) | [08 风险](ai-project-map/08-change-guide-risks.md) |
| 评估影响面、技术债、README 偏差 | [08 改动风险](ai-project-map/08-change-guide-risks.md) | 对应业务分卷 |

## 分卷目录

| 分卷 | 内容 |
|---|---|
| [01-architecture.md](ai-project-map/01-architecture.md) | 元数据、项目概览、真实目录树、入口职责、总体架构、依赖方向和耦合热点 |
| [02-desktop-task-flow.md](ai-project-map/02-desktop-task-flow.md) | Core/Windows 职责、直接/托盘启动、关闭、任务生命周期和坐标契约 |
| [03-database-sync.md](ai-project-map/03-database-sync.md) | Database 文件、SQLite schema、索引、缓存、flush、REST、鉴权和冲突 |
| [04-scheduler-archive.md](ai-project-map/04-scheduler-archive.md) | 定时任务、生成规则、完成/删除归档、恢复、搜索、全选和历史分页 |
| [05-ui-configuration.md](ai-project-map/05-ui-configuration.md) | Config/UI 文件、样式、Fluent、通知、滚动条、表格、徽标和配置键 |
| [06-export-llm-gantt.md](ai-project-map/06-export-llm-gantt.md) | 文本/Excel/历史导出、LLM 摘要、Flask 和 Frappe Gantt |
| [07-dependencies-tests.md](ai-project-map/07-dependencies-tests.md) | 第三方依赖映射、测试文件所有权、当前基线和测试缺口 |
| [08-change-guide-risks.md](ai-project-map/08-change-guide-risks.md) | 修改影响矩阵、已知风险、README 偏差、AI 工作协议和维护规则 |

## 全局不可破坏契约

- 不输出、提交或复制 `api_key`、`api_token`、用户名或私有服务地址。
- 不把数据库、备份、日志、缓存、venv、`.tmp-tests` 或 `.worktrees` 当源码修改。
- 桌面业务复用 `get_db_manager()`；Gantt 的独立只读连接是现有例外。
- 保留逻辑删除、任务历史、缓存锁、dirty、周期 flush 和关闭 flush。
- 保留“右高紧急、上高重要”，除非同时设计数据迁移和回归测试。
- UI 优先复用 `ui.notifications`、`ui.styles`、`ui.fluent`、`ui.scrollbar` 和 `ui.adaptive_table`。

## 当前测试状态

- 首选完整命令：`& '.\venv\Scripts\python.exe' -m unittest discover -s tests -v`
- 2026-06-10 基线不是全绿：`tests.test_database_manager_remote` 有 8 个既有 error。
- 详细原因、测试所有权和缺口见 [07-dependencies-tests.md](ai-project-map/07-dependencies-tests.md)。

## 维护入口

- 更新具体事实：修改对应领域分卷。
- 新增或移动分卷：同步更新本页任务路由和分卷目录。
- 改变全局安全或工作协议：更新本页、`AGENTS.md` 和 [08-change-guide-risks.md](ai-project-map/08-change-guide-risks.md)。
- 每次维护都要重新检查 UTF-8、Markdown 链接、Mermaid 和敏感值零泄露。
