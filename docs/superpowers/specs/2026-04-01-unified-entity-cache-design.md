# Unified Entity Cache and Deferred Sync Design

Date: 2026-04-01

## Background

The project currently uses two different local write models:

- Regular tasks already follow an in-memory cache model: write to memory first, flush to SQLite later, and sync to the server on an explicit or periodic path.
- Scheduled tasks still write directly to SQLite and may also push to the remote API immediately during create, update, and delete operations.
- Regular tasks use soft delete semantics through a `deleted` field, while scheduled tasks are still physically deleted.

The user requirements for this change are:

1. Do not sync CRUD operations immediately to the local database.
2. Do not sync CRUD operations immediately to the server.
3. Apply the same rule to both regular tasks and scheduled tasks.
4. Make scheduled task reads use the cache view so unflushed changes are immediately visible.
5. Keep deleted scheduled tasks as long-lived tombstones, matching regular tasks.
6. Prefer a unified cache mechanism instead of maintaining two unrelated implementations.

## Goals

Implement a unified local cache framework for regular tasks and scheduled tasks while keeping the public `DatabaseManager` API largely stable.

The new behavior must ensure that:

- writes go to memory first,
- reads reflect the current cache view,
- flush to SQLite happens only on explicit or periodic paths,
- remote sync happens only on explicit or periodic paths,
- delete semantics are soft-delete tombstones for both entity types.

## Non-Goals

This change does not aim to:

- redesign the entire persistence stack into a new repository/service architecture,
- merge the regular-task and scheduled-task remote API protocols into a single transport layer,
- introduce a queueing system or event sourcing,
- redesign the UI, scheduler workflow, or remote conflict UX,
- add scheduled-task history tracking.

## Options Considered

### Option A: Stop Immediate Remote Sync for Scheduled Tasks Only

Keep scheduled tasks writing directly to SQLite, but remove the immediate server calls.

Pros:
- Smallest change.
- Lowest short-term implementation cost.

Cons:
- Still violates the requirement to avoid immediate local database writes.
- Keeps regular tasks and scheduled tasks on different local write models.
- Does not address scheduled-task delete semantics.

### Option B: Add a Separate Scheduled-Task Cache Layer

Leave the regular-task cache as-is and add a parallel cache implementation for scheduled tasks.

Pros:
- Meets the functional requirements.
- Lower risk than a broader abstraction.

Cons:
- Creates two similar but separate caching implementations.
- Increases long-term maintenance cost and divergence risk.

### Option C: Introduce a Unified Entity Cache Framework

Abstract the existing regular-task cache into an entity-agnostic cache skeleton and let regular tasks and scheduled tasks plug into it with type-specific adapters.

Pros:
- Meets the current requirements.
- Removes the local write-model split between the two entity types.
- Reuses the existing `DatabaseManager` shape and keeps external call sites mostly stable.

Cons:
- Larger change surface than Option A or B.
- Requires careful migration of the existing regular-task cache behavior.

## Chosen Approach

Use Option C.

The system will introduce a shared entity-cache framework inside `DatabaseManager` while keeping entity-specific normalization, SQLite mapping, and remote serialization logic separate for regular tasks and scheduled tasks.

## Architecture

### Unified Cache Skeleton

`DatabaseManager` remains the coordinator, but its internal state moves from task-specific structures toward per-entity cache buckets.

A representative internal shape is:

```python
self._entity_cache = {
    'task': {
        'records': {},
        'deleted_ids': set(),
        'dirty': False,
        'loaded': False,
    },
    'scheduled_task': {
        'records': {},
        'deleted_ids': set(),
        'dirty': False,
        'loaded': False,
    },
}
```

Each bucket is responsible for:

- the in-memory record view,
- tombstone tracking,
- dirty-state tracking,
- providing a consistent source of truth for flush and sync.

### Entity-Specific Responsibilities

The unified cache layer does not replace entity-specific logic.

Regular-task code still owns:

- task field normalization,
- task history caching,
- `tasks` table mapping,
- `/api/tasks` request payload mapping.

Scheduled-task code still owns:

- scheduled-task field normalization,
- `scheduled_tasks` table mapping,
- `/api/scheduled_tasks` request payload mapping.

## Data Model Changes

### `tasks`

The existing `deleted` tombstone field stays in place and keeps its current meaning.

### `scheduled_tasks`

Add:

```sql
deleted BOOLEAN DEFAULT FALSE
```

This aligns scheduled-task delete semantics with regular tasks.

The database initialization path must ensure the column exists for both fresh databases and older local databases. If query performance becomes an issue, an index such as `idx_scheduled_deleted` may be added.

## Read Model

All public read operations should use the cache view instead of querying SQLite directly.

This includes:

- regular-task reads,
- `get_scheduled_task()`,
- `list_scheduled_tasks()`.

Default behavior:

- records marked `deleted=True` are hidden from public reads,
- internal flows can opt in to tombstone visibility with an explicit `include_deleted=True` parameter.

This ensures:

- newly created scheduled tasks are visible before flush,
- updated scheduled tasks are visible before flush,
- deleted scheduled tasks disappear from normal reads immediately,
- scheduler-driven updates to `next_run_at` are visible immediately,
- ID generation for new scheduled tasks can detect unflushed cached records.

## Write Model

### Regular Tasks

Public methods such as `save_task()` and `delete_task()` remain in place, but internally they use the unified cache layer.

Rules:

- create and update write to memory only,
- delete marks the record as `deleted=True` and keeps a tombstone,
- `sync_status` becomes `modified`,
- CRUD does not immediately flush to SQLite,
- CRUD does not immediately call the remote API.

### Scheduled Tasks

Public methods such as `create_scheduled_task()`, `update_scheduled_task()`, and `delete_scheduled_task()` keep their signatures, but their behavior changes to match the regular-task model.

Rules:

- create and update write to memory only,
- delete becomes a tombstone write with `deleted=True`,
- `sync_status` becomes `modified`,
- CRUD does not immediately flush to SQLite,
- CRUD does not immediately call the remote API.

## Delete Semantics

Both entity types use long-lived tombstones.

Required behavior:

- deleting a record never triggers physical local deletion in the normal CRUD path,
- flush writes tombstone state into SQLite,
- remote delete success does not remove the local tombstone,
- normal read APIs filter tombstones out,
- remote pulls must not resurrect a locally tombstoned record by treating it as missing local data.

## Flush Model

`flush_cache_to_db()` becomes the unified batch persistence entry point.

Expected flow:

1. Lock the cache.
2. Return immediately if all buckets are clean and task-history cache is empty.
3. Batch upsert regular-task cache into `tasks`.
4. Batch upsert scheduled-task cache into `scheduled_tasks`.
5. Batch write regular-task history entries.
6. Commit.
7. Clear per-bucket dirty markers and transient pending-delete bookkeeping.

Important constraint:

- `deleted_ids` exist to ensure tombstone writes are preserved during flush and sync.
- They do not imply physical deletion.

## Remote Sync Model

### Core Rule

Manual CRUD no longer pushes remotely.

Only explicit or periodic sync paths may send remote writes.

### Regular Tasks

`sync_to_server()` and `sync_from_server()` remain the public entry points, but local outgoing data should be derived from the cache view instead of assuming SQLite is the freshest source.

### Scheduled Tasks

`sync_scheduled_tasks_to_server()` and `sync_scheduled_tasks_from_server()` remain the public entry points, but outgoing behavior changes:

- non-deleted cached records with `sync_status != 'synced'` are sent with `POST /api/scheduled_tasks`,
- deleted cached records are sent with `DELETE /api/scheduled_tasks/<id>`,
- success marks the cached record as `synced`,
- successful remote deletion still keeps the local tombstone.

## Remote Pull and Conflict Handling

Remote-downloaded records must be applied to the cache view, not written directly to SQLite.

Rules:

- remote regular-task data updates the regular-task cache,
- remote scheduled-task data updates the scheduled-task cache,
- existing local conflict handling remains in place for both entity types,
- conflict resolution outcomes are written back to cache first and only later persisted by flush.

## Scheduler Behavior

`TaskScheduler.check_and_spawn_scheduled_tasks()` currently does two kinds of writes:

1. it creates regular tasks from due schedules,
2. it updates the scheduled task's `next_run_at`.

Under the new model, both writes go to cache only.

That means:

- spawned regular tasks become visible immediately through the cache view,
- updated `next_run_at` values become visible immediately through the cache view,
- no immediate flush happens inside the scheduler path.

## Compatibility Constraints

To minimize impact, the following public methods remain stable in name and general calling style:

- `save_task`
- `delete_task`
- `create_scheduled_task`
- `update_scheduled_task`
- `delete_scheduled_task`
- `list_scheduled_tasks`
- `get_scheduled_task`
- `flush_cache_to_db`
- `sync_to_server`
- `sync_scheduled_tasks_to_server`
- `sync_from_server`
- `sync_scheduled_tasks_from_server`

This keeps UI and scheduler call sites focused on behavior changes instead of API rewrites.

## File Responsibilities

### `database/database_manager.py`

Responsible for:

- the unified entity-cache framework,
- cache loading,
- cache reads and writes,
- soft-delete handling,
- batch flush,
- remote sync coordination,
- conflict application.

### `core/scheduler.py`

Responsible for:

- continuing to use `DatabaseManager` as the only read/write interface,
- removing assumptions that scheduler-driven updates are flushed immediately,
- relying on the cache view for immediate visibility.

### `core/quadrant_widget.py`

Responsible for:

- reading through `DatabaseManager`,
- remaining compatible with cache-first reads,
- avoiding assumptions that scheduled-task CRUD is already persisted in SQLite.

### `tests/test_database_manager_remote.py`

Responsible for:

- covering cache-first scheduled-task behavior,
- covering deferred SQLite persistence,
- covering deferred remote sync,
- covering tombstone behavior,
- covering conflict resolution behavior under the cache-first model.

## Error Handling

- Cache-write failure returns failure immediately and does not flush or sync.
- Flush failure rolls back the transaction and keeps cache state dirty.
- Remote sync failure never rolls back successful local edits.
- Remote pull failure keeps current local cache state intact.
- Malformed scheduled-task records are skipped with logging instead of breaking the entire read path.

## Testing Strategy

### Unit Tests

At minimum, cover:

1. scheduled-task create, update, and delete are visible through cache reads before flush,
2. scheduled-task create, update, and delete do not immediately write SQLite,
3. scheduled-task create, update, and delete do not immediately call the remote API,
4. `flush_cache_to_db()` writes scheduled-task cache state and tombstones into SQLite,
5. `sync_scheduled_tasks_to_server()` only sends changes during explicit or periodic sync,
6. deleted scheduled tasks are hidden from default reads but visible when `include_deleted=True`,
7. scheduler-generated regular tasks and `next_run_at` updates are visible immediately without immediate flush,
8. remote scheduled-task conflict resolution writes results into cache before flush.

### Manual Verification

1. Create a scheduled task and confirm it appears immediately in the UI.
2. Before flush, verify SQLite still does not contain the new record.
3. Delete a scheduled task and confirm the UI hides it while SQLite later stores `deleted=1`.
4. Trigger a due schedule and confirm the spawned regular task and updated `next_run_at` are visible immediately without restart.
5. Disconnect the remote service and confirm local edits continue to work.

## Risks and Mitigations

### Risk 1: Regressing Stable Regular-Task Behavior

Mitigation:

- keep public APIs stable,
- migrate existing behavior into the shared cache skeleton rather than redesigning it,
- add regression coverage for regular-task expectations touched by the change.

### Risk 2: Soft-Delete Query Ambiguity for Scheduled Tasks

Mitigation:

- default reads always filter tombstones,
- internal flows use explicit `include_deleted=True`,
- centralize the filtering logic instead of duplicating ad hoc conditions.

### Risk 3: Cache and SQLite Views Diverge Temporarily

Mitigation:

- treat this as expected behavior, not a defect,
- require business reads to go through `DatabaseManager`,
- avoid introducing new code that assumes CRUD implies immediate SQLite persistence.

### Risk 4: Tombstones Grow Indefinitely

Mitigation:

- this is an explicit requirement for now,
- if storage growth becomes a real problem, address archival or compaction in a later scoped design.

## Acceptance Criteria

This work is complete when:

1. regular-task CRUD no longer writes SQLite immediately,
2. scheduled-task CRUD no longer writes SQLite immediately,
3. regular-task CRUD no longer syncs remotely immediately,
4. scheduled-task CRUD no longer syncs remotely immediately,
5. scheduled-task reads are cache-first,
6. scheduled-task deletes become long-lived tombstones,
7. scheduler writes are cache-only until flush,
8. existing UI and scheduler integration remain compatible,
9. remote sync and conflict handling still function under the cache-first model.
