# 数据库、缓存与远程同步

> [返回 AI 项目地图总目录](../AI_PROJECT_MAP.md)
>
> **阅读范围：** 用于修改 SQLite schema、DatabaseManager、缓存、历史、flush、REST、鉴权、冲突和同步时序。
>
> **相关分卷：** 任务 UI 契约见 [02](02-desktop-task-flow.md)；定时任务/归档见 [04](04-scheduler-archive.md)；风险矩阵见 [08](08-change-guide-risks.md)。
## `database/` 文件职责

| 文件 | 职责 | 风险边界 |
|---|---|---|
| `database/database_manager.py` | 所有桌面持久化主路径；SQLite DDL；普通/定时任务缓存；历史缓存；5 秒 flush；180 秒可选同步；冲突检测与确认；分页 | 共享单例、共享连接、跨线程访问，是最高风险模块 |
| `database/sync_manual.py` | 下载/上传/覆盖服务器、查看状态、备份恢复的交互式 CLI | 使用 `from database_manager import ...`，从仓库根直接模块运行可能导入失败；“解决冲突”仍是占位实现 |
| `database/migrate_priority_to_urgency_importance.py` | 老库从 `priority` 迁移为 urgency/importance；先备份再 `ALTER TABLE`/`UPDATE` | 仅维护脚本；不应在当前已迁移库上盲跑 |
| `database/deduplicate_tasks.py` | 按 completed/deleted/text/notes 分组；保留历史最多且更新时间最新者；物理删除其余 | 会改 DB，必须先备份并人工确认 |
| `database/delete_test_tasks.py` | 物理删除标题包含 `test` 的任务，启用外键并备份 | 破坏性维护脚本，不属于应用正常删除流程 |
| `database/__init__.py` | 包标识 | 无业务逻辑 |

## SQLite 数据模型、缓存与 flush

### 数据库位置与连接

- 默认路径：`database/tasks.db`。
- `DatabaseManager` 把相对路径固定到仓库根下的 `database/`。
- 使用一个长期存活的 `sqlite3.Connection(check_same_thread=False)`，`row_factory=sqlite3.Row`。
- 代码未在主连接上执行 `PRAGMA foreign_keys = ON`，因此 DDL 中的级联外键通常不会生效。

### 表与字段

#### `config`

| 字段 | 类型/约束 | 用途 |
|---|---|---|
| `key` | TEXT PK | 配置键 |
| `value` | TEXT NOT NULL | 配置值 |
| `updated_at` | TIMESTAMP default current | 更新时间 |

当前桌面配置实际写 JSON 文件，此表在当前业务代码中没有读写路径，属于闲置/历史结构。

#### `tasks`

| 字段 | 说明 |
|---|---|
| `id` | TEXT 主键 |
| `color` | 标签色 |
| `position_x`, `position_y` | 标签左上角坐标 |
| `completed` | 完成标记 |
| `completed_date` | 完成日期文本 |
| `deleted` | 逻辑删除标记 |
| `created_at`, `updated_at` | ISO/SQLite 时间文本混用 |
| `text`, `notes`, `due_date` | 主内容 |
| `priority` | 旧字段，仍保留兼容/导出 |
| `urgency`, `importance` | 当前二维分类 |
| `directory` | 目录路径 |
| `create_date` | 用户字段形式的创建日期 |
| `sync_status` | `modified`/`synced` 等本地同步状态 |

#### `task_history`

| 字段 | 说明 |
|---|---|
| `task_id` | 外键指向 tasks |
| `field_name` | 字段名 |
| `field_value` | 新值字符串 |
| `action` | 当前主要是 `create`/`update` |
| `timestamp` | ISO 时间 |
| 主键 | `(task_id, field_name, timestamp)` |

#### `sync_status`

`id`、`last_sync_at`、`sync_type`、`status`、`message`；记录最近上传、下载和覆盖操作摘要。`get_sync_status()` 只取最近 5 条。

#### `scheduled_tasks`

`id`、`title`、旧 `priority`、`urgency`、`importance`、`notes`、`due_date`、`frequency`、`week_day`、`month_day`、`quarter_day`、`year_month`、`year_day`、`next_run_at`、`active`、`deleted`、`created_at`、`updated_at`。

注意：表中**没有 `sync_status` 字段**；该状态只存在于定时任务内存缓存，重启后从 DB 加载时默认视为 `synced`。

### 索引

| 索引 | 列 |
|---|---|
| `idx_tasks_completed` | `tasks(completed)` |
| `idx_tasks_deleted` | `tasks(deleted)` |
| `idx_tasks_sync_status` | `tasks(sync_status)` |
| `idx_task_history_task_id` | `task_history(task_id)` |
| `idx_task_history_timestamp` | `task_history(timestamp)` |
| `idx_tasks_completed_deleted_dates` | `completed, deleted, completed_date DESC, updated_at DESC, created_at DESC` |
| `idx_task_history_task_timestamp` | `task_id, timestamp DESC` |
| `idx_scheduled_active` | `scheduled_tasks(active)` |
| `idx_scheduled_next_run` | `scheduled_tasks(next_run_at)` |

### 内存缓存

```text
_task_cache: id -> 普通任务记录
_scheduled_task_cache: id -> 定时任务记录
_task_history_cache: 待插入历史 tuple 列表
_deleted_task_ids / _deleted_scheduled_task_ids: tombstone ID 集合
_entity_cache: 为 task / scheduled_task 包装 records、deleted_ids、dirty、loaded
_pending_remote_task_changes: change_key -> 待用户确认的远程变化
```

所有主要缓存读写应在 `_cache_lock` 下进行；listener 列表另用 `_listener_lock`。

### flush 行为

- 默认后台周期：5 秒。
- `flush_cache_to_db()` 在锁内：
  1. 对 `_task_cache` **所有记录**执行 `INSERT OR REPLACE`。
  2. 对 `_scheduled_task_cache` **所有记录**执行 `INSERT OR REPLACE`。
  3. 对历史缓存执行 `INSERT OR IGNORE`。
  4. 单事务 commit，随后清 dirty。
- 分页读取、历史读取、导出、同步、关闭前都会主动 flush。
- flush 线程为 daemon；进程被外部强杀时不能保证最后一批数据落盘。
- `INSERT OR REPLACE` 在 SQLite 语义上是删除后插入；当前主连接未启用外键，历史未被级联删除，但未来若启用外键必须重新评估。

## 远程同步配置与协议

### 配置键

`remote_config.json` 只描述以下键，不在本文记录任何值：

| 键 | 用途 |
|---|---|
| `enabled` | 是否启用远程模式 |
| `api_base_url` | 远程服务基地址 |
| `api_token` | Bearer 令牌，同时用于自动注册 |
| `username` | 自动注册用户标识 |

应用配置中的 `LLM_CONFIG` 键：

| 键 | 用途 |
|---|---|
| `api_key` | LLM SDK 凭据 |
| `model` | 模型/推理端点标识 |
| `base_url` | LLM API 基地址 |

**安全警告：当前工作树的 `config/config.json` 和 `config/remote_config.json` 可能含明文敏感值。任何 AI、日志、测试快照、issue、PR 或文档都不得复制真实值。**

### 客户端 REST 契约

| 方法与端点 | 鉴权 | 客户端期望 |
|---|---|---|
| `GET /api/health` | 公共 | 返回可解析 JSON，truthy 表示健康 |
| `POST /api/users` | 公共 | `{username, api_token}`；200/201/409 均视为注册可继续 |
| `GET /api/tasks` | Bearer | `{"tasks": [...]}` |
| `POST /api/tasks` | Bearer | 单任务；包含 `position: {x,y}` 和 `history` |
| `DELETE /api/tasks/{id}` | Bearer | 200/201/204 视为成功 |
| `GET /api/tasks/{id}/history` | Bearer | `{"history": {field_name: [...]}}` |
| `GET /api/scheduled_tasks` | Bearer | `{"scheduled_tasks": [...]}` |
| `POST /api/scheduled_tasks` | Bearer | 单定时任务；`active` 强制序列化为布尔 |
| `DELETE /api/scheduled_tasks/{id}` | Bearer | 删除远端定时任务 |

请求统一 JSON、30 秒超时。受保护端点收到 401 后，客户端最多尝试一次自动注册并重试；注册失败会暂停后续受保护请求，避免周期日志风暴。

### 启动同步和周期同步

1. `DatabaseManager.__init__()` 不主动访问网络。
2. `QuadrantWidget` 注册 listener 后，`QTimer.singleShot(0, ...)` 启动后台 bootstrap。
3. 缺少 username 或 token 时打开设置页，不发业务请求。
4. bootstrap 顺序：health -> 下载普通任务 -> 下载定时任务。
5. 全部成功且同步间隔非零时启动周期线程，默认 180 秒。
6. 周期顺序：普通任务下载 -> 普通任务上传 -> 定时任务下载 -> 定时任务上传。

### 冲突规则

- 时间统一转换为 UTC 基准的 naive datetime 比较，兼容时区感知字符串。
- 远端仅 `updated_at` 改变而内容未变时，不提示冲突。
- 本地最近 5 分钟内有修改时，本地优先：更新时间刷新、标记 `modified`，跳过确认。
- 其他新建/修改/远端删除进入 `_pending_remote_task_changes`。
- 有 UI listener 时弹出逐条“接受本地/接受远程”选择；每条必须且只能选一侧。
- 接受远程或拒绝远程时都会合并远端历史到本地，去重键为字段、时间、action、value。
- 普通任务处理后会把最终结果重新上传；定时任务拒绝远端时直接 POST 本地版本或 DELETE。
- 没有 listener 时普通任务远端变化会自动应用；这与 GUI 模式的人工确认不同。
