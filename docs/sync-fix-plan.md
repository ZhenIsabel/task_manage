# App 与 PC 端同步一致性修复文档

本文记录 app 端需要参照 PC 端同步实现修复的问题。范围仅包含已确认需要修复的 7 项：

- 仍然合理的问题 1、2、3
- 新增问题 1、3、4、5

PC 端参考项目：`D:\repositories\task_manage`  
App 端项目：`D:\repositories\task_manage_uniapp`

## 目标

App 端应与 PC 端共用同一服务器时保持相同的数据语义，尤其是：

- 本地优先保存，远程同步延后执行。
- 删除使用 tombstone，不直接丢失同步状态。
- 本地历史能随任务同步到服务器。
- 远程冲突在用户确认前不能被覆盖或清空。
- 时间戳比较兼容时区。
- 字段值在任务、历史、展示之间保持一致。

## 1. 本地删除没有 tombstone，导致远程删除无法延迟同步

### 问题

App 端 `deleteTask(taskId, false)` 直接从本地任务列表移除任务。由于任务记录被删除，后续 `syncToServer` 没有任何依据向服务器发送删除请求。

结果是：

- app 删除的任务仍保留在服务器。
- 下一次 `syncFromServer` 时，服务器任务会被重新拉回 app。
- 与 PC 端的删除语义不一致。

### PC 端参考

PC 端删除普通任务时不立即物理删除，而是：

- 设置 `deleted = True`
- 更新 `updated_at`
- 设置 `sync_status = 'modified'`
- 列表读取时隐藏 deleted 任务
- 后续同步再把删除状态或删除请求推给服务器

### 修复方案

App 端删除应改为软删除：

- 本地任务增加  `deleted` 字段。
- 删除时保留任务记录，设置 `deleted: true`、`_syncDirty: true`、`updatedAt: now`。
- `loadTasksFromStorage` 或页面过滤逻辑默认隐藏 deleted 任务。
- `syncToServer` 发现 deleted dirty task 时调用 `deleteTaskOnServer(task.id)`。
- 删除同步成功后，可以选择：
  - 保留 tombstone，避免远程旧数据复活。
  - 或记录已删除 id 后清理任务实体。

### 验收点

- 本地删除后任务不再显示。
- 删除前后不立即请求远程接口。
- 手动上传同步后调用 `DELETE /api/tasks/{id}`。
- 删除同步失败时 tombstone 仍保留，下一次可重试。
- 服务器仍存在该任务时，下一次拉取不会把本地刚删除的任务复活。

## 2. 延迟同步不会上传本地历史

### 问题

App 端保存任务时会写本地历史，但普通延迟同步只上传任务本体。只有 `syncRemote=true` 的即时路径才调用 `postTaskHistoryToServer`，而当前页面保存、完成、恢复都走 `saveTask(..., false)`。

结果是：

- app 本地详情页能看到历史。
- 服务器和 PC 端可能看不到 app 产生的历史。
- 两端历史记录长期不一致。

### PC 端参考

PC 端 `sync_to_server` 上传 dirty task 时，会把本地历史放入任务 payload 的 `history` 字段。

### 修复方案

优先采用与 PC 端一致的方式：

- `syncToServer` 上传每个 dirty task 时，附带该任务本地历史。
- `taskToServer` 支持把 `history` 原样带入 payload，格式与 PC 端保持一致：
  - `history: { [fieldName]: [{ value, timestamp, action }] }`
- 上传成功后标记任务为 clean。

如果服务器更适合单独历史接口，也可以：

- 为本地历史增加同步标记，例如 `_historySyncDirty` 或 `syncedAt`。
- `syncToServer` 在任务上传成功后 POST 未同步历史。
- 历史上传失败时不能把对应历史标记为已同步。

### 验收点

- app 修改任务后，本地历史产生记录。
- 执行 `syncToServer` 后，上传 payload 包含该任务历史，或调用历史上传接口。
- PC 端从服务器拉取后能看到 app 产生的历史。
- 重复同步不会重复插入同一条历史。

## 3. 待处理远程冲突可能被下一轮拉取覆盖或清空

### 问题

App 端每次 `syncFromServer` 都重新构造 `pendingChanges = []`，最后直接覆盖保存本地 pending remote changes。

结果是：

- 用户尚未处理的冲突可能在下一轮拉取时被清空。
- 本地任务可能继续参与上传，覆盖远端待确认变更。
- 冲突确认页显示的内容不稳定。

### PC 端参考

PC 端如果已有待确认远程变更，会先通知 UI，并跳过本轮继续拉取。上传时也会排除处于 pending conflict 的任务。

### 修复方案

- pending remote changes 改为以 `task:<id>` 为 key 的字典结构，或数组保存时按 id 合并。
- `syncFromServer` 开始时如果存在 pending：
  - 直接返回 pending 给 UI。
  - 不清空 pending。
  - 不覆盖对应本地任务。
- 新发现的 pending 与旧 pending 合并。
- 用户明确选择本地或远程后，才移除对应 pending。
- `syncToServer` 上传时跳过 pending 中的 task id，除非用户刚选择“保留本地”。

### 验收点

- 产生冲突后重复拉取，冲突仍存在。
- 未处理冲突的任务不会被上传覆盖服务器。
- 处理其中一个冲突不会清空其他冲突。
- app 重启后 pending 仍可恢复。

## 4. 没有 dirty task 时会上传全部任务

### 问题

App 端 `syncToServer` 当前逻辑是：

- 有 dirty task 时上传 dirty task。
- 没有 dirty task 时上传全部任务。

这与 PC 端不一致。PC 端没有待同步任务时直接 no-op。

结果是：

- 普通同步可能无意义地覆盖服务器任务。
- 如果服务器有 app 未识别的字段，虽然当前尝试用 `_serverRaw` 保留，但全量重传仍增加风险。
- 与“清空服务器并覆盖上传”的显式操作边界混淆。

### 修复方案

- `syncToServer` 默认只上传 `_syncDirty === true` 的任务。
- 没有 dirty task 时返回 `{ success: true, uploaded: 0 }`。
- 如需全量覆盖，保留在 `clearServerAndUpload` 或单独的“强制覆盖上传”入口。

### 验收点

- 全部任务 clean 时执行上传，不产生 `POST /api/tasks`。
- dirty task 存在时只上传 dirty task。
- 强制覆盖上传仍能上传全部本地任务。

## 5. App 不处理 PC 端的远程删除语义

### 问题

App 端 `taskFromServer` 没有映射服务器 `deleted` 字段，任务比较快照也没有包含 deleted。服务器或 PC 端删除任务后，app 可能无法正确识别远程删除。

结果是：

- PC 端删除的任务可能继续在 app 端显示。
- app 端可能把远程 deleted task 当作普通任务拉回。
- 远程删除与本地修改冲突无法进入确认流程。

### PC 端参考

PC 端同步比较包含 `deleted` 字段；如果服务器任务缺失，也会把已同步本地任务视为远程删除候选，并生成待确认变更。

### 修复方案

- `taskFromServer` 映射 `deleted` 到本地字段。
- `taskToServer` 上传时带上 deleted 状态。
- 任务内容比较快照加入 deleted。
- 本地列表默认隐藏 deleted task。
- `syncFromServer` 处理两类远程删除：
  - 服务器返回 `deleted: true` 的任务。
  - 服务器任务列表缺少某个本地已同步、未删除任务。
- 如果本地最近修改或本地 dirty，则进入冲突确认；否则应用远程删除。

### 验收点

- PC 删除任务后 app 拉取能隐藏或提示删除冲突。
- app 本地 dirty task 遇到远程删除时，不会被静默删除。
- app 接受远程删除后本地标记 deleted。
- app 保留本地后会重新上传本地任务覆盖远程删除。

## 6. 时间戳比较不兼容时区

### 问题

App 端直接用字符串比较 `updatedAt`。当 PC 端或服务器返回 `Z`、`+08:00`、无时区格式混用时，字符串顺序可能不等于真实时间顺序。

结果是：

- 远程新版本可能被误判为旧版本。
- 本地旧版本可能覆盖远程新版本。
- 冲突判断不稳定。

### PC 端参考

PC 端会解析时间戳，并统一转换到 UTC 基准后比较。

### 修复方案

新增 app 端同步时间工具：

- `parseSyncTime(value)`：支持 `Z`、`+08:00`、普通 ISO 字符串。
- 无时区值按本地时区或统一约定时区解释。
- `isRemoteTimeNewer(remoteUpdatedAt, localUpdatedAt)` 使用毫秒时间比较。
- 只有解析失败时才降级字符串比较。

### 验收点

- `2026-04-14T15:00:00Z` 能正确判断晚于 `2026-04-14T20:00:00+08:00`。
- 无时区时间不会导致异常。
- `syncFromServer` 冲突判断使用新的时间比较函数。

## 7. 重要/紧急历史值格式不一致，详情页显示可能错误

### 问题

App 端任务上传时会把重要/紧急转成服务器值 `高/低`，但本地历史记录保存的是 `high/low`。详情页历史展示只按 `高` 判断。

结果是：

- 本地历史里的 `high` 会被详情页显示成“一般”或“不急”。
- 从服务器拉取的历史和 app 本地历史格式不一致。
- 同一字段在任务、历史、展示之间语义不统一。

### 修复方案

优先统一历史保存格式为服务器格式：

- `fieldToServerValue` 对 `urgency`、`importance` 返回 `高/低`。
- 详情页显示函数同时兼容旧历史值：
  - `高`、`high` -> 重要/紧急
  - `低`、`low` -> 一般/不急
- 如已有本地历史，不做强制迁移也可以；展示层兼容即可。

### 验收点

- 新增或修改高重要任务后，历史值保存为 `高`。
- 旧历史值 `high` 仍显示为“重要/紧急”。
- 从 PC 端或服务器来的 `高/低` 历史显示正确。

## 建议实施顺序

1. 修复时间戳比较和历史值格式，降低后续同步判断误差。
2. 修复 dirty 上传策略，确保普通上传只处理待同步任务。
3. 引入 tombstone 删除，并补齐远程 deleted 映射。
4. 修复 pending conflict 持久化与上传阻塞。
5. 补齐历史随任务同步。

## 建议测试覆盖

- `deleteTask` 本地软删除与列表隐藏。
- `syncToServer` 无 dirty 时不上传。
- `syncToServer` 上传 dirty task 时附带 history。
- `syncFromServer` 重复拉取不会清空 pending。
- `syncFromServer` 识别远程 deleted task。
- `syncFromServer` 正确比较带时区时间戳。
- 详情页历史兼容 `high/low` 与 `高/低`。
