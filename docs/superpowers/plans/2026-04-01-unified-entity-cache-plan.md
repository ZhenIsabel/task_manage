# Unified Entity Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify regular-task and scheduled-task local persistence behind a cache-first, soft-delete, deferred-flush, deferred-sync model.

**Architecture:** Keep `DatabaseManager` as the coordination point, but introduce per-entity cache buckets shared by regular tasks and scheduled tasks. Preserve entity-specific normalization and remote serialization, while moving reads, writes, flush, and delete semantics onto the same cache-first framework.

**Tech Stack:** Python, sqlite3, threading, unittest, PyQt6

---

### Task 1: Add Failing Tests for Scheduled-Task Cache-First CRUD

**Files:**
- Modify: `tests/test_database_manager_remote.py`
- Modify: `database/database_manager.py`
- Test: `tests/test_database_manager_remote.py`

- [ ] **Step 1: Write the failing test for create-before-flush visibility**

```python
def test_create_scheduled_task_is_visible_from_cache_before_flush(self):
    manager = self._build_manager(remote_config={})

    result = manager.create_scheduled_task({
        'id': 'sched-1',
        'title': 'Daily review',
        'frequency': 'daily',
    })

    self.assertTrue(result)
    self.assertIsNotNone(manager.get_scheduled_task('sched-1'))
    self.assertEqual(len(manager.list_scheduled_tasks()), 1)

    conn = manager.get_connection()
    row = conn.execute(
        'SELECT id FROM scheduled_tasks WHERE id = ?',
        ('sched-1',),
    ).fetchone()
    self.assertIsNone(row)
```

- [ ] **Step 2: Run the single test and verify it fails**

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_create_scheduled_task_is_visible_from_cache_before_flush -v`
Expected: FAIL because `create_scheduled_task()` currently writes directly to SQLite.

- [ ] **Step 3: Write the failing test for update-before-flush visibility**

```python
def test_update_scheduled_task_uses_cache_before_flush(self):
    manager = self._build_manager(remote_config={})
    manager.create_scheduled_task({
        'id': 'sched-1',
        'title': 'Original',
        'frequency': 'daily',
    })
    manager.flush_cache_to_db()

    result = manager.update_scheduled_task('sched-1', {'title': 'Updated'})

    self.assertTrue(result)
    self.assertEqual(manager.get_scheduled_task('sched-1')['title'], 'Updated')

    conn = manager.get_connection()
    row = conn.execute(
        'SELECT title FROM scheduled_tasks WHERE id = ?',
        ('sched-1',),
    ).fetchone()
    self.assertEqual(row['title'], 'Original')
```

- [ ] **Step 4: Run the single test and verify it fails**

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_update_scheduled_task_uses_cache_before_flush -v`
Expected: FAIL because `update_scheduled_task()` currently updates SQLite immediately.

- [ ] **Step 5: Write the failing test for soft delete tombstones**

```python
def test_delete_scheduled_task_marks_tombstone_and_hides_default_reads(self):
    manager = self._build_manager(remote_config={})
    manager.create_scheduled_task({
        'id': 'sched-1',
        'title': 'Delete me',
        'frequency': 'daily',
    })
    manager.flush_cache_to_db()

    result = manager.delete_scheduled_task('sched-1')

    self.assertTrue(result)
    self.assertIsNone(manager.get_scheduled_task('sched-1'))
    self.assertEqual(manager.list_scheduled_tasks(), [])
    deleted_record = manager.get_scheduled_task('sched-1', include_deleted=True)
    self.assertIsNotNone(deleted_record)
    self.assertTrue(deleted_record['deleted'])
```

- [ ] **Step 6: Run the single test and verify it fails**

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_delete_scheduled_task_marks_tombstone_and_hides_default_reads -v`
Expected: FAIL because scheduled tasks are still physically deleted and `include_deleted` does not exist yet.

- [ ] **Step 7: Commit the red tests**

```bash
git add tests/test_database_manager_remote.py
git commit -m "test: define scheduled-task cache-first behavior"
```

### Task 2: Introduce Unified Entity Cache Buckets in `DatabaseManager`

**Files:**
- Modify: `database/database_manager.py`
- Test: `tests/test_database_manager_remote.py`

- [ ] **Step 1: Add a failing test for cache initialization**

```python
def test_database_manager_loads_scheduled_tasks_into_entity_cache(self):
    manager = self._build_manager(remote_config={})
    conn = manager.get_connection()
    conn.execute(
        '''
        INSERT INTO scheduled_tasks
        (id, title, frequency, active, deleted, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''',
        ('sched-1', 'Loaded', 'daily', True, False, '2026-04-01T00:00:00', '2026-04-01T00:00:00'),
    )
    conn.commit()

    manager._load_all_entities_to_cache()

    self.assertIn('sched-1', manager._entity_cache['scheduled_task']['records'])
```

- [ ] **Step 2: Run the single test and verify it fails**

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_database_manager_loads_scheduled_tasks_into_entity_cache -v`
Expected: FAIL because `_entity_cache` and `_load_all_entities_to_cache()` do not exist yet.

- [ ] **Step 3: Implement the minimal cache-bucket skeleton**

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

Add helper methods with focused responsibilities:

```python
def _get_entity_bucket(self, entity_type: str) -> Dict[str, Any]:
    return self._entity_cache[entity_type]


def _mark_entity_dirty(self, entity_type: str) -> None:
    self._get_entity_bucket(entity_type)['dirty'] = True
```

- [ ] **Step 4: Load both entity types into cache on startup**

```python
def _load_all_entities_to_cache(self):
    self._load_all_tasks_to_cache()
    self._load_all_scheduled_tasks_to_cache()
```

```python
def _load_all_scheduled_tasks_to_cache(self):
    bucket = self._get_entity_bucket('scheduled_task')
    bucket['records'].clear()
    bucket['deleted_ids'].clear()
    cursor = self.get_connection().cursor()
    cursor.execute('SELECT * FROM scheduled_tasks')
    for row in cursor.fetchall():
        record = dict(row)
        bucket['records'][record['id']] = record
        if record.get('deleted'):
            bucket['deleted_ids'].add(record['id'])
    bucket['dirty'] = False
    bucket['loaded'] = True
```

- [ ] **Step 5: Run the targeted tests and verify they pass**

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_database_manager_loads_scheduled_tasks_into_entity_cache -v`
Expected: PASS

- [ ] **Step 6: Commit the cache skeleton**

```bash
git add database/database_manager.py tests/test_database_manager_remote.py
git commit -m "refactor: add unified entity cache buckets"
```

### Task 3: Move Scheduled-Task Reads and Writes to the Cache View

**Files:**
- Modify: `database/database_manager.py`
- Test: `tests/test_database_manager_remote.py`

- [ ] **Step 1: Add a failing test for `include_deleted=True` read support**

```python
def test_get_scheduled_task_can_return_deleted_tombstone_when_requested(self):
    manager = self._build_manager(remote_config={})
    manager.create_scheduled_task({
        'id': 'sched-1',
        'title': 'Keep tombstone',
        'frequency': 'daily',
    })
    manager.flush_cache_to_db()
    manager.delete_scheduled_task('sched-1')

    self.assertIsNone(manager.get_scheduled_task('sched-1'))
    self.assertTrue(manager.get_scheduled_task('sched-1', include_deleted=True)['deleted'])
```

- [ ] **Step 2: Run the single test and verify it fails**

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_get_scheduled_task_can_return_deleted_tombstone_when_requested -v`
Expected: FAIL because the current read path goes straight to SQLite and has no tombstone-aware API.

- [ ] **Step 3: Add the `deleted` column to scheduled tasks during initialization**

```python
cursor.execute(
    '''
    CREATE TABLE IF NOT EXISTS scheduled_tasks (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        priority TEXT,
        urgency TEXT DEFAULT 'low',
        importance TEXT DEFAULT 'low',
        notes TEXT,
        due_date TEXT,
        frequency TEXT NOT NULL,
        week_day INTEGER,
        month_day INTEGER,
        quarter_day INTEGER,
        year_month INTEGER,
        year_day INTEGER,
        next_run_at TIMESTAMP,
        active BOOLEAN DEFAULT TRUE,
        deleted BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    '''
)
```

Also add an upgrade check:

```python
scheduled_columns = [col[1] for col in cursor.execute('PRAGMA table_info(scheduled_tasks)').fetchall()]
if 'deleted' not in scheduled_columns:
    cursor.execute('ALTER TABLE scheduled_tasks ADD COLUMN deleted BOOLEAN DEFAULT FALSE')
```

- [ ] **Step 4: Rework scheduled-task CRUD to use the cache bucket**

```python
def create_scheduled_task(self, schedule_data: Dict[str, Any]) -> bool:
    record = self._normalize_scheduled_task_data(schedule_data)
    record['deleted'] = False
    record['sync_status'] = 'modified'
    bucket = self._get_entity_bucket('scheduled_task')
    bucket['records'][record['id']] = record
    bucket['deleted_ids'].discard(record['id'])
    bucket['dirty'] = True
    return True
```

```python
def get_scheduled_task(self, task_id: str, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
    record = copy.deepcopy(self._get_entity_bucket('scheduled_task')['records'].get(task_id))
    if not record:
        return None
    if record.get('deleted') and not include_deleted:
        return None
    return record
```

```python
def list_scheduled_tasks(self, active_only: bool = False, due_before: Optional[datetime] = None, include_deleted: bool = False) -> List[Dict[str, Any]]:
    records = [copy.deepcopy(item) for item in self._get_entity_bucket('scheduled_task')['records'].values()]
    result = []
    for record in records:
        if record.get('deleted') and not include_deleted:
            continue
        if active_only and not record.get('active', True):
            continue
        if due_before and record.get('next_run_at') and record['next_run_at'] > due_before.isoformat():
            continue
        result.append(record)
    return sorted(result, key=lambda item: item.get('next_run_at') or '')
```

```python
def delete_scheduled_task(self, task_id: str) -> bool:
    existing = self.get_scheduled_task(task_id, include_deleted=True)
    if not existing:
        return False
    existing['deleted'] = True
    existing['updated_at'] = datetime.now().isoformat()
    existing['sync_status'] = 'modified'
    bucket = self._get_entity_bucket('scheduled_task')
    bucket['records'][task_id] = existing
    bucket['deleted_ids'].add(task_id)
    bucket['dirty'] = True
    return True
```

- [ ] **Step 5: Run the scheduled-task CRUD tests and verify they pass**

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_create_scheduled_task_is_visible_from_cache_before_flush tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_update_scheduled_task_uses_cache_before_flush tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_delete_scheduled_task_marks_tombstone_and_hides_default_reads tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_get_scheduled_task_can_return_deleted_tombstone_when_requested -v`
Expected: PASS

- [ ] **Step 6: Commit the scheduled-task cache-first CRUD change**

```bash
git add database/database_manager.py tests/test_database_manager_remote.py
git commit -m "feat: move scheduled-task CRUD to cache-first model"
```

### Task 4: Unify Flush Behavior for Scheduled Tasks and Tombstones

**Files:**
- Modify: `database/database_manager.py`
- Test: `tests/test_database_manager_remote.py`

- [ ] **Step 1: Add a failing test for scheduled-task flush persistence**

```python
def test_flush_cache_to_db_persists_scheduled_task_and_tombstone_state(self):
    manager = self._build_manager(remote_config={})
    manager.create_scheduled_task({
        'id': 'sched-1',
        'title': 'Flush me',
        'frequency': 'daily',
    })
    manager.flush_cache_to_db()
    manager.delete_scheduled_task('sched-1')
    manager.flush_cache_to_db()

    row = manager.get_connection().execute(
        'SELECT deleted FROM scheduled_tasks WHERE id = ?',
        ('sched-1',),
    ).fetchone()

    self.assertIsNotNone(row)
    self.assertTrue(row['deleted'])
```

- [ ] **Step 2: Run the single test and verify it fails**

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_flush_cache_to_db_persists_scheduled_task_and_tombstone_state -v`
Expected: FAIL because `flush_cache_to_db()` does not persist scheduled-task tombstones.

- [ ] **Step 3: Extend `flush_cache_to_db()` to persist scheduled tasks**

```python
for schedule in self._get_entity_bucket('scheduled_task')['records'].values():
    cursor.execute(
        '''
        INSERT OR REPLACE INTO scheduled_tasks
        (id, title, priority, urgency, importance, notes, due_date, frequency,
         week_day, month_day, quarter_day, year_month, year_day,
         next_run_at, active, deleted, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (
            schedule['id'],
            schedule['title'],
            schedule.get('priority', 'mid'),
            schedule.get('urgency', 'low'),
            schedule.get('importance', 'low'),
            schedule.get('notes', ''),
            schedule.get('due_date', ''),
            schedule['frequency'],
            schedule.get('week_day'),
            schedule.get('month_day'),
            schedule.get('quarter_day'),
            schedule.get('year_month'),
            schedule.get('year_day'),
            schedule.get('next_run_at'),
            schedule.get('active', True),
            schedule.get('deleted', False),
            schedule['created_at'],
            schedule['updated_at'],
        ),
    )
```

- [ ] **Step 4: Clear scheduled-task dirty state after a successful commit**

```python
self._get_entity_bucket('scheduled_task')['dirty'] = False
self._get_entity_bucket('scheduled_task')['deleted_ids'].clear()
```

- [ ] **Step 5: Run the flush test and the prior CRUD tests**

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_flush_cache_to_db_persists_scheduled_task_and_tombstone_state tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_create_scheduled_task_is_visible_from_cache_before_flush tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_delete_scheduled_task_marks_tombstone_and_hides_default_reads -v`
Expected: PASS

- [ ] **Step 6: Commit the unified flush behavior**

```bash
git add database/database_manager.py tests/test_database_manager_remote.py
git commit -m "feat: persist scheduled-task cache and tombstones on flush"
```

### Task 5: Move Scheduled-Task Remote Sync to Deferred Cache-Based Sync

**Files:**
- Modify: `database/database_manager.py`
- Modify: `tests/test_database_manager_remote.py`
- Test: `tests/test_database_manager_remote.py`

- [ ] **Step 1: Add failing tests for deferred remote sync**

```python
def test_create_scheduled_task_does_not_push_remote_immediately(self):
    manager = self._build_manager(remote_config={})
    manager.api_base_url = 'http://example.com'
    manager.api_token = 'token'

    with patch.object(manager, '_make_api_request', return_value={'success': True}) as request_mock:
        manager.create_scheduled_task({
            'id': 'sched-1',
            'title': 'Daily review',
            'frequency': 'daily',
        })

    request_mock.assert_not_called()
```

```python
def test_sync_scheduled_tasks_to_server_sends_delete_for_tombstones(self):
    manager = self._build_manager(remote_config={})
    manager.create_scheduled_task({
        'id': 'sched-1',
        'title': 'Delete later',
        'frequency': 'daily',
    })
    manager.flush_cache_to_db()
    manager.delete_scheduled_task('sched-1')
    manager.api_base_url = 'http://example.com'
    manager.api_token = 'token'

    with patch.object(manager, '_make_api_request', return_value={'success': True}) as request_mock:
        self.assertTrue(manager.sync_scheduled_tasks_to_server())

    request_mock.assert_called_once_with('DELETE', '/api/scheduled_tasks/sched-1')
```

- [ ] **Step 2: Run the two tests and verify they fail**

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_create_scheduled_task_does_not_push_remote_immediately tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_sync_scheduled_tasks_to_server_sends_delete_for_tombstones -v`
Expected: FAIL because scheduled-task CRUD still triggers immediate remote behavior and sync does not treat tombstones as deletes.

- [ ] **Step 3: Remove immediate remote calls from scheduled-task CRUD**

```python
# create_scheduled_task / update_scheduled_task / delete_scheduled_task
# should only update cache state and return True
```

- [ ] **Step 4: Update scheduled-task sync to read from cache and send deletes**

```python
def sync_scheduled_tasks_to_server(self) -> bool:
    if not self.api_base_url or self._remote_auth_paused:
        return not self.api_base_url

    bucket = self._get_entity_bucket('scheduled_task')
    pending = [
        copy.deepcopy(record)
        for record in bucket['records'].values()
        if record.get('sync_status') != 'synced'
    ]
    for record in pending:
        if record.get('deleted'):
            result = self._make_api_request('DELETE', f"/api/scheduled_tasks/{record['id']}")
        else:
            result = self._make_api_request('POST', '/api/scheduled_tasks', self._serialize_scheduled_task_for_api(record))
        if result:
            bucket['records'][record['id']]['sync_status'] = 'synced'
            bucket['dirty'] = True
    return True
```

- [ ] **Step 5: Run the deferred-sync tests and existing scheduled-task sync tests**

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_create_scheduled_task_does_not_push_remote_immediately tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_sync_scheduled_tasks_to_server_sends_delete_for_tombstones tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_sync_scheduled_tasks_to_server_serializes_active_as_boolean -v`
Expected: PASS

- [ ] **Step 6: Commit the deferred sync change**

```bash
git add database/database_manager.py tests/test_database_manager_remote.py
git commit -m "feat: defer scheduled-task remote sync to explicit sync paths"
```

### Task 6: Update Scheduler Writes to Stay Cache-Only Until Flush

**Files:**
- Modify: `core/scheduler.py`
- Modify: `tests/test_database_manager_remote.py`
- Test: `tests/test_database_manager_remote.py`

- [ ] **Step 1: Add a failing test for scheduler cache-only writes**

```python
def test_scheduler_spawn_updates_cache_without_immediate_flush(self):
    manager = self._build_manager(remote_config={})
    manager.create_scheduled_task({
        'id': 'sched-1',
        'title': 'Review',
        'frequency': 'daily',
        'next_run_at': '2026-04-01T00:00:00',
        'active': True,
    })
    manager.flush_cache_to_db()

    scheduler = TaskScheduler()
    scheduler.db_manager = manager

    spawned = scheduler.check_and_spawn_scheduled_tasks(now=datetime.fromisoformat('2026-04-01T00:05:00'))

    self.assertEqual(spawned, 1)
    self.assertIsNotNone(manager.get_scheduled_task('sched-1'))
    self.assertGreater(len(manager.load_tasks(all_tasks=True)), 0)

    task_row = manager.get_connection().execute(
        "SELECT id FROM tasks WHERE id LIKE 'scheduled_sched-1_%'"
    ).fetchone()
    self.assertIsNone(task_row)
```

- [ ] **Step 2: Run the single test and verify it fails**

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_scheduler_spawn_updates_cache_without_immediate_flush -v`
Expected: FAIL because the scheduler currently calls `flush_cache_to_db()` immediately after spawning tasks.

- [ ] **Step 3: Remove the scheduler-side immediate flush assumption**

```python
if spawned_count > 0:
    logger.info(f"Successfully spawned {spawned_count} scheduled tasks")
return spawned_count
```

Keep the task creation and scheduled-task update paths cache-only.

- [ ] **Step 4: Run the scheduler test and verify it passes**

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_scheduler_spawn_updates_cache_without_immediate_flush -v`
Expected: PASS

- [ ] **Step 5: Commit the scheduler change**

```bash
git add core/scheduler.py tests/test_database_manager_remote.py
git commit -m "feat: keep scheduler writes cache-only until flush"
```

### Task 7: Run Full Verification and Document Residual Risks

**Files:**
- Modify: `tests/test_database_manager_remote.py`
- Modify: `database/database_manager.py`
- Modify: `core/scheduler.py`
- Test: `tests/test_database_manager_remote.py`

- [ ] **Step 1: Run the focused regression suite**

Run: `python -m unittest tests.test_database_manager_remote -v`
Expected: PASS for all cache-first, deferred-sync, and remote-conflict tests.

- [ ] **Step 2: Run a project grep to confirm no immediate scheduled-task remote push remains**

Run: `rg -n "create_scheduled_task\(|update_scheduled_task\(|delete_scheduled_task\(|/api/scheduled_tasks|flush_cache_to_db\(" database core tests`
Expected: Only explicit sync paths should perform remote `/api/scheduled_tasks` writes, and scheduler code should not force an immediate flush after spawn.

- [ ] **Step 3: Fix any remaining naming or type mismatches found during verification**

```python
# Example final-state consistency checks:
# - get_scheduled_task(task_id, include_deleted=False)
# - list_scheduled_tasks(..., include_deleted=False)
# - all scheduled-task cache records carry deleted + sync_status fields
```

- [ ] **Step 4: Re-run the focused regression suite**

Run: `python -m unittest tests.test_database_manager_remote -v`
Expected: PASS

- [ ] **Step 5: Commit the final verified implementation**

```bash
git add database/database_manager.py core/scheduler.py tests/test_database_manager_remote.py
git commit -m "feat: unify entity cache and defer local and remote sync"
```
