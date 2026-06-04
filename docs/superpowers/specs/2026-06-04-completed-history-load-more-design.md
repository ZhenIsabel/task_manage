# 已完成任务与历史记录加载更多设计

## 背景

当前已完成任务和历史记录在数据量较大时打开较慢。之前已完成的表格高度限制只解决了弹窗被内容撑高的问题，没有减少初始查询、数据搬运和表格渲染的工作量。

已完成任务弹窗当前会先通过 `load_tasks(all_tasks=True)` 读取全部任务，再在 UI 层筛选已完成任务。历史记录弹窗当前会读取某个任务的全部历史，合并所有字段后一次性渲染到表格。两者在数据量增大后都会让打开弹窗变慢。

本次设计目标是把两个入口都改成“初始只加载一页，用户需要时再加载更多”，并统一按以下顺序排序：

```text
completed_date DESC, updated_at DESC, created_at DESC
```

对于历史记录，`completed_date` 不属于 `task_history` 表本身，因此历史记录列表的主排序仍以 `task_history.timestamp DESC` 为准；如果需要跨任务查看历史列表，才适用任务级 `completed_date DESC, updated_at DESC, created_at DESC` 排序。本次历史弹窗仍是单任务历史弹窗，因此不把任务排序字段强行套到每条历史记录上。

## 可行性判断

方案可行。

### 已完成任务

已完成任务列表适合在数据库或数据库管理层新增分页查询接口，按 `completed_date DESC, updated_at DESC, created_at DESC` 返回一页数据。UI 层不再加载全部任务后筛选，而是持有当前页数据和分页状态。

需要注意的是，当前 `DatabaseManager` 启动时会把任务载入 `_task_cache`。第一版可以先基于缓存做分页筛选，改动较小；但为了长期性能更稳，推荐新增 SQLite 查询接口，利用复合索引直接按条件分页读取。

推荐走 SQLite 查询接口。

### 历史记录

历史记录当前已经走本地 SQLite 的 `task_history` 表读取，适合新增分页查询接口：

```text
get_task_history_page(task_id, limit, offset, order="DESC")
count_task_history(task_id)
```

历史弹窗初始只加载最近一页历史，点击“加载更多”后追加下一页。导出功能保持全量导出，不受 UI 分页影响。

### 排序规则

已完成任务排序可完整实现：

```sql
ORDER BY completed_date DESC, updated_at DESC, created_at DESC
```

历史弹窗是“单个任务的历史记录”，历史记录表只有 `timestamp`，没有 `completed_date`、`updated_at`、`created_at` 三个任务排序字段。因此历史弹窗推荐排序为：

```sql
ORDER BY timestamp DESC
```

如果后续新增“所有历史记录总览”，该总览可以 join `tasks` 后使用任务排序字段。

## 范围

本次设计覆盖：

1. 已完成任务弹窗加载更多。
2. 历史记录弹窗加载更多。
3. 已完成任务排序改为 `completed_date DESC, updated_at DESC, created_at DESC`。
4. 历史记录弹窗按最近历史优先展示。
5. 数据库查询接口和必要索引。
6. 测试覆盖分页、排序、加载更多和导出全量不变。

本次不覆盖：

1. 不重写为 `QAbstractTableModel` 虚拟表格。
2. 不改变任务完成、还原、同步的业务语义。
3. 不改变历史记录导出格式。
4. 不新增跨任务历史总览页。

## 设计

### 1. 数据库接口

在 `database/database_manager.py` 中新增已完成任务分页接口：

```python
def load_completed_tasks_page(
    self,
    limit: int = 100,
    offset: int = 0,
    search_query: str = "",
) -> list[dict]:
    ...
```

查询条件：

```sql
WHERE completed = 1
  AND deleted = 0
```

当存在搜索关键词时，对任务标题 `text` 做关键词过滤。多个关键词继续沿用当前 UI 的语义：空格分隔，全部命中才算匹配。

排序固定为：

```sql
ORDER BY completed_date DESC, updated_at DESC, created_at DESC
```

同时新增计数接口：

```python
def count_completed_tasks(self, search_query: str = "") -> int:
    ...
```

在 `database/database_manager.py` 中新增历史记录分页接口：

```python
def get_task_history_page(
    self,
    task_id: str,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, list[dict]]:
    ...
```

查询排序：

```sql
ORDER BY timestamp DESC
```

同时新增计数接口：

```python
def count_task_history(self, task_id: str) -> int:
    ...
```

现有 `get_task_history()` 保留，用于导出全量历史和兼容已有调用。

### 2. 索引

新增复合索引：

```sql
CREATE INDEX IF NOT EXISTS idx_tasks_completed_deleted_dates
ON tasks(completed, deleted, completed_date DESC, updated_at DESC, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_task_history_task_timestamp
ON task_history(task_id, timestamp DESC);
```

如果搜索性能后续仍不足，再考虑 SQLite FTS5。本次不直接引入全文索引，避免扩大迁移复杂度。

### 3. 已完成任务弹窗

`core/complete_table.py` 的加载逻辑改为分页状态驱动：

- `self.page_size = 100`
- `self.loaded_count = 0`
- `self.total_count = 0`
- `self.completed_tasks = []`
- `self.current_search_query = ""`

打开弹窗时：

1. 查询总数。
2. 加载第一页。
3. 渲染第一页。
4. 如果还有更多，显示“加载更多”按钮。

点击“加载更多”时：

1. 使用当前 `loaded_count` 作为 offset。
2. 查询下一页。
3. 追加到 `self.completed_tasks`。
4. 调用表格渲染。
5. 更新按钮文案，例如 `加载更多 (100/560)`。

搜索时：

1. 继续保留 500ms 防抖。
2. 搜索关键词变化后重置分页状态。
3. 查询匹配总数。
4. 加载匹配结果第一页。

还原选中任务后：

1. 执行还原。
2. 重置分页状态。
3. 按当前搜索条件重新加载第一页。
4. 通知父窗口刷新任务列表。

### 4. 历史记录弹窗

`core/history_viewer.py` 改为保存表格实例和分页状态：

- `self.page_size = 100`
- `self.history_offset = 0`
- `self.history_total_count = 0`
- `self.merged_history_rows = []`

打开弹窗时：

1. 查询历史总数。
2. 加载最近一页历史。
3. 渲染表格。
4. 如果还有更多，显示“加载更多”按钮。

点击“加载更多”时：

1. 查询下一页历史。
2. 合并成 UI 行数据。
3. 追加到表格已有行。
4. 更新按钮文案，例如 `加载更多 (100/1240)`。

历史记录按 `timestamp DESC` 展示，因此最新变更会显示在上方。

导出按钮继续调用 `get_task_history()`，导出全量历史。导出排序可以继续使用原来的时间升序，也可以与弹窗保持一致改为时间倒序。为减少行为变化，第一版建议导出保持原有排序。

### 5. 表格行为

现有 `AdaptiveTextTableWidget` 可以继续使用，但每次只渲染已加载的数据。由于页大小默认 100，当前的多行高度计算和复选框创建成本可接受。

第一版不做虚拟表格。如果后续几千条都点“加载更多”后仍然卡，再考虑升级为 `QAbstractTableModel`。

### 6. 空状态和按钮文案

已完成任务空状态：

```text
暂无已完成任务
```

搜索无结果：

```text
未找到匹配的已完成任务
```

历史记录空状态：

```text
未找到该任务的历史记录
```

加载更多按钮：

```text
加载更多 (已加载/总数)
```

全部加载完成后：

```text
已全部加载
```

按钮禁用或隐藏均可。建议禁用并显示“已全部加载”，让用户明确知道不是按钮丢了。

## Todo

- [ ] 在 `database/database_manager.py` 新增已完成任务分页查询接口。
- [ ] 在 `database/database_manager.py` 新增已完成任务计数接口。
- [ ] 在 `database/database_manager.py` 新增单任务历史分页查询接口。
- [ ] 在 `database/database_manager.py` 新增单任务历史计数接口。
- [ ] 在数据库初始化中增加 `idx_tasks_completed_deleted_dates` 复合索引。
- [ ] 在数据库初始化中增加 `idx_task_history_task_timestamp` 复合索引。
- [ ] 修改 `core/complete_table.py`，用分页查询替代 `load_tasks(all_tasks=True)` 后 UI 层筛选。
- [ ] 为已完成任务弹窗增加分页状态和“加载更多”按钮。
- [ ] 保留已完成任务搜索防抖，并让搜索触发分页重置。
- [ ] 修改还原任务后的刷新逻辑，按当前搜索条件重新加载第一页。
- [ ] 修改 `core/history_viewer.py`，初始只加载最近一页历史。
- [ ] 为历史记录弹窗增加分页状态和“加载更多”按钮。
- [ ] 确保历史记录导出仍然导出全量历史。
- [ ] 增加数据库层测试，验证已完成任务按 `completed_date DESC, updated_at DESC, created_at DESC` 排序。
- [ ] 增加数据库层测试，验证已完成任务分页 `limit/offset` 正确。
- [ ] 增加数据库层测试，验证历史记录按 `timestamp DESC` 分页。
- [ ] 增加 UI 测试，验证已完成任务初始渲染不超过 page size。
- [ ] 增加 UI 测试，验证点击“加载更多”会追加下一页。
- [ ] 增加 UI 测试，验证搜索后分页状态重置。
- [ ] 增加 UI 测试，验证历史记录导出仍调用全量历史读取。

## 验收标准

1. 已完成任务弹窗初次打开只加载第一页，不再调用 `load_tasks(all_tasks=True)` 获取全部任务。
2. 已完成任务按 `completed_date DESC, updated_at DESC, created_at DESC` 排序。
3. 已完成任务点击“加载更多”后追加下一页，不清空已有选择以外的已加载数据。
4. 已完成任务搜索后只显示匹配结果第一页，并可继续加载更多匹配结果。
5. 还原任务后列表刷新，已还原任务不再出现在已完成任务列表中。
6. 历史记录弹窗初次打开只加载最近一页历史。
7. 历史记录点击“加载更多”后追加更早的历史记录。
8. 历史记录导出仍包含该任务全部历史。
9. 当没有更多数据时，“加载更多”按钮不可继续触发重复查询。
10. 现有历史记录、已完成任务表格高度限制行为不回退。

## 风险与处理

### 搜索性能

普通 `LIKE` 搜索在任务标题很多时可能仍会慢。第一版先通过分页降低渲染成本；如果搜索仍慢，再引入 FTS5。

### 缓存一致性

当前任务数据有内存缓存和延迟落库。已完成任务分页若直接读 SQLite，需要在查询前确保缓存已 flush，或者在缓存层实现分页。推荐第一版在分页查询前调用 `flush_cache_to_db()`，保证 UI 展示和数据库状态一致。

### 历史记录排序语义

用户要求的 `completed_date DESC, updated_at DESC, created_at DESC` 对已完成任务完全适用；历史弹窗是单任务历史，不存在这些任务级排序字段。历史记录按 `timestamp DESC` 更符合数据结构和用户意图。若后续做跨任务历史总览，再使用任务级排序字段。

### 一次加载过多

如果用户连续点击“加载更多”直到加载数千行，当前表格仍可能变慢。第一版通过 page size 降低初始卡顿；长期方案是虚拟表格模型。

## 推荐实施顺序

1. 先做数据库接口和排序测试。
2. 再改已完成任务弹窗，因为收益最大且排序要求明确。
3. 再改历史记录弹窗，保留导出全量。
4. 最后补 UI 测试和手工验证。
