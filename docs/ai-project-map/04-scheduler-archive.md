# 定时任务、归档与历史

> [返回 AI 项目地图总目录](../AI_PROJECT_MAP.md)
>
> **阅读范围：** 用于修改定时任务计算和生成、完成/删除列表、逻辑删除、恢复、分页、搜索、全选和历史查看。
>
> **相关分卷：** 底层 DB 与同步见 [03](03-database-sync.md)；共享表格/UI 规范见 [05](05-ui-configuration.md)。
## 定时任务

### 创建与存储

- 默认配置字段：`title`、`frequency`、`urgency`、`importance`、`notes`、`due_offset_days`、`start_time`；旧配置中的固定 `due_date` 字段仍被表单和保存路径兼容。
- `due_offset_days`（触发后 N 天到期）：非负整数，`None`/空串表示“未配置”，此时生成任务回退使用固定 `due_date`（见下文“触发”）。规范化入口有三处且语义一致：`TaskScheduler.add_scheduled_task()`、`ScheduledTaskDialog._normalize_offset_days()`、`DatabaseManager._coerce_due_offset_days()`。
- 表单中 `due_offset_days` 用 `qfluentwidgets.SpinBox` 渲染，以 `最小值-1` 作为“未设置”哨兵值显示 `empty_text`，与“偏移 0 天（触发当天到期）”明确区分；`get_data()` 在哨兵值时返回空串。
- 支持频率：`daily`、`weekly`、`monthly`、`quarterly`、`yearly`。
- ID 形如 `sched_<时间戳>`，冲突时最多尝试 100 个后缀。
- 创建/修改/删除只先写缓存并标记 `modified`，不立即远程上传。

### 编辑已有定时任务

`ScheduledTaskDialog.edit_task()`（“编辑”按钮，要求恰好选中一条）：

- 复用 `AddScheduleDialog`，通过 `dialog_title`/`submit_label` 参数切换为“编辑定时任务/保存”。
- `_extract_field_default()` 把已有记录回填为表单默认值：`start_time` 取 `created_at` 的日期部分；未配置的 `due_offset_days` 回填为空（显示“未设置”），不会被静默改写为 0。
- 仅当频率或开始日期实际变化时才重算 `next_run_at`（`_resolve_edit_base_time()` 判断），并把结果滚动推进到当前时间之后，避免仅改备注就把 `next_run_at` 重置到过去导致立即重复触发。
- 日期控件默认值为空时保持“未选择”状态，不再预填当天，避免编辑无固定到期日的旧任务时日期被静默改成当天。

### 时区处理

`core/scheduler.py` 顶层的 `to_naive_local()` 把带时区的 datetime 转为无时区本地时间。`calculate_next_run_time()` 入口和 `created_at` 解析处统一调用，修复外部导入的带时区时间与 `datetime.now()` 比较抛 `TypeError` 的问题。

### 下次运行计算

| 频率 | 当前实现 |
|---|---|
| daily | 基准时间 +1 天，并强制时间为 00:02:00 |
| weekly | 基准时间 +7 天 |
| monthly | 月份 +1，日溢出截到月末 |
| quarterly | 月份 +3，日溢出截到月末 |
| yearly | 年份 +1，2 月 29 日等截到合法月末 |
| 其他 | 默认 +1 天 |

`week_day/month_day/quarter_day/year_month/year_day` 字段虽然在表、API 和函数签名中存在，但当前计算明确忽略这些参数，仅保留兼容。

### 触发

- `main.py` 每 60 秒检查一次配置的每日刷新时刻。
- 配置中的时、分、秒共同组成当天目标 `datetime`；实际触发可能因 60 秒检查周期稍晚。
- 使用 `last_refresh_target` 记录最近一次已满足的目标时间点，而不是只记录日期。
- 运行中把刷新时间改到当天更晚时间时，新目标大于旧目标，仍会在新时间正常触发；
  同一目标不会重复触发。
- 启动时若已经超过当天目标，会把该目标记为已满足，避免程序启动后立即补执行。
- 应用保持运行时，即使定时器漂移错过目标分钟，后续检查仍会在当天补触发。
- 到点后 `TaskScheduler.check_and_spawn_scheduled_tasks()`：
  1. 取 `active=True`、`deleted=False`、`next_run_at <= now` 的定时任务。
  2. 每个到期计划生成一个普通任务，ID 为 `scheduled_<schedule_id>_<当前时间>`。
  3. 生成任务的 `due_date` 由 `_resolve_spawned_due_date()` 决定：配置了 `due_offset_days` 时为 `触发时间 + N 天`；未配置（NULL/空）或值无效时回退到计划上保存的固定 `due_date`。
  4. 普通任务初始位置固定 `{x:100,y:100}`，颜色固定默认青色。
  5. 下次运行从本次检查的 `now` 计算，而不是从原计划时间连续追赶。
  6. 批量生成后立即 flush。

因此，运行中的短暂定时器延迟不会再漏掉当天触发；但应用若在目标时间之后才启动，
当天仍不会补执行。长期停机后恢复时也只为每个到期计划生成一条，不补齐所有漏期。

## 归档、完成、删除与历史分页

### “归档”定义

数据库没有 `archived` 字段或归档表。`ArchiveTableDialog` 是共享 UI 抽象：

- 完成集合：`completed=1 AND deleted=0`。
- 删除集合：`deleted=1`，不区分完成状态。

### 分页与搜索

- 页面大小：50。
- 搜索：输入按空格拆关键字；每个关键字对 `LOWER(COALESCE(text,''))` 做 AND 模糊匹配。
- `%`、`_`、反斜杠会转义，按字面匹配。
- 搜索防抖：500ms。
- 已完成排序：`completed_date DESC, updated_at DESC, created_at DESC`。
- 已删除排序：`updated_at DESC, created_at DESC`。
- “全选”调用独立 ID 查询，覆盖所有匹配项，不限已加载页。
- 若计数过期而下一页为空，UI 会收缩 total 并禁用“加载更多”。

### 历史分页

- 每页 50 条。
- DB 按 `timestamp DESC LIMIT/OFFSET`。
- 返回结构仍按字段分组，UI 再摊平成行并倒序。
- 导出走全量本地历史。
