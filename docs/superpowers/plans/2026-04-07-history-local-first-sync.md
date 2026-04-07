# History Local-First Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make history UI read only from local SQLite data while extending the existing conflict-resolution flow to append missing history locally first and then push missing local history to the remote server.

**Architecture:** Keep `get_task_history()` as a pure local read path and move all remote-history handling into the existing pending-change acceptance/rejection flow. Reuse the current task conflict machinery in `DatabaseManager` by attaching history snapshots to pending changes, merging them with de-duplication when a decision is made, and only pushing remote updates after local state is finalized.

**Tech Stack:** Python, sqlite3, unittest, existing `DatabaseManager` sync flow

---

### Task 1: Lock the new history-read behavior with tests

**Files:**
- Modify: `tests/test_database_manager_remote.py`
- Test: `tests/test_database_manager_remote.py`

- [ ] **Step 1: Write the failing tests**

```python
    def test_get_task_history_uses_local_history_even_when_remote_history_exists(self):
        remote_config = {
            "api_base_url": "http://example.com",
            "api_token": "token",
            "username": "alice",
        }
        manager = self._build_manager(remote_config=remote_config)
        conn = manager.get_connection()
        conn.execute(
            'INSERT INTO task_history (task_id, field_name, field_value, action, timestamp) VALUES (?, ?, ?, ?, ?)',
            ('task-1', 'text', '本地任务', 'update', '2026-03-30T09:00:00'),
        )
        conn.commit()

        with patch.object(manager, '_make_api_request', return_value={
            'history': {'text': [{'value': '远端任务', 'timestamp': '2026-04-01T09:00:00', 'action': 'update'}]}
        }):
            history = manager.get_task_history('task-1')

        self.assertEqual(history['text'][0]['value'], '本地任务')

    def test_accept_remote_change_merges_remote_history_into_local_before_flush(self):
        manager = self._build_manager(remote_config={})
        manager.save_task({
            'id': 'task-1',
            'text': '本地版本',
            'notes': '本地备注',
            'due_date': '',
            'priority': '低',
            'urgency': '低',
            'importance': '低',
            'directory': '',
            'create_date': '2026-03-30',
            'position': {'x': 100, 'y': 100},
            'completed': False,
            'completed_date': '',
            'deleted': False,
        })
        manager.flush_cache_to_db()
        manager.get_connection().execute(
            'INSERT OR IGNORE INTO task_history (task_id, field_name, field_value, action, timestamp) VALUES (?, ?, ?, ?, ?)',
            ('task-1', 'text', '本地版本', 'update', '2026-03-30T09:00:00'),
        )
        manager.get_connection().commit()

        manager._pending_remote_task_changes['task:task-1'] = {
            'change_key': 'task:task-1',
            'entity_type': 'task',
            'entity_id': 'task-1',
            'title': '任务 task-1',
            'change_type': 'update',
            'local_record': {'id': 'task-1', 'text': '本地版本', 'notes': '本地备注'},
            'remote_record': {'id': 'task-1', 'text': '远端版本', 'notes': '远端备注', 'position': {'x': 100, 'y': 100}},
            'local_history': {
                'text': [{'value': '本地版本', 'timestamp': '2026-03-30T09:00:00', 'action': 'update'}]
            },
            'remote_history': {
                'text': [{'value': '远端版本', 'timestamp': '2026-04-01T09:00:00', 'action': 'update'}]
            },
        }

        result = manager.resolve_pending_remote_task_changes(['task:task-1'], [])

        self.assertTrue(result)
        merged = manager.get_task_history('task-1')
        self.assertEqual(
            [item['timestamp'] for item in merged['text']],
            ['2026-03-30T09:00:00', '2026-04-01T09:00:00'],
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_get_task_history_uses_local_history_even_when_remote_history_exists tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_accept_remote_change_merges_remote_history_into_local_before_flush -v`

Expected: at least one FAIL showing current code still prefers remote history or does not merge history on accept.

### Task 2: Implement local-only history reads and history merge helpers

**Files:**
- Modify: `database/database_manager.py`
- Test: `tests/test_database_manager_remote.py`

- [ ] **Step 1: Add helper methods for local history normalization and merge**

```python
    def _load_local_task_history(self, task_id: str) -> Dict[str, List[Dict[str, Any]]]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            '''
                SELECT field_name, field_value, action, timestamp
                FROM task_history
                WHERE task_id = ?
                ORDER BY timestamp ASC
            ''',
            (task_id,),
        )
        history_records = cursor.fetchall()

        field_history: Dict[str, List[Dict[str, Any]]] = {}
        for record in history_records:
            field_name = record['field_name']
            field_history.setdefault(field_name, []).append({
                'value': record['field_value'],
                'timestamp': record['timestamp'],
                'action': record['action'],
            })
        return field_history

    def _merge_history_dicts(self, *history_sets: Optional[Dict[str, List[Dict[str, Any]]]]) -> Dict[str, List[Dict[str, Any]]]:
        merged: Dict[str, List[Dict[str, Any]]] = {}
        seen = set()
        for history in history_sets:
            if not history:
                continue
            for field_name, records in history.items():
                bucket = merged.setdefault(field_name, [])
                for record in records or []:
                    key = (
                        field_name,
                        str(record.get('timestamp', '') or ''),
                        str(record.get('action', '') or ''),
                        str(record.get('value', '') or ''),
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    bucket.append({
                        'value': str(record.get('value', '') or ''),
                        'timestamp': str(record.get('timestamp', '') or ''),
                        'action': str(record.get('action', 'update') or 'update'),
                    })
        for field_name in merged:
            merged[field_name].sort(key=lambda item: item.get('timestamp', ''))
        return merged
```

- [ ] **Step 2: Update `get_task_history()` to only read local history**

```python
    def get_task_history(self, task_id: str) -> Dict[str, List[Dict[str, Any]]]:
        try:
            self.flush_cache_to_db()
            return self._load_local_task_history(task_id)
        except Exception as e:
            logger.error(f"获取任务历史记录失败: {str(e)}")
            return {}
```

- [ ] **Step 3: Run targeted tests to verify history reads now pass**

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_get_task_history_uses_local_history_even_when_remote_history_exists tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_get_task_history_falls_back_to_local_when_remote_unavailable -v`

Expected: PASS

### Task 3: Thread history through the existing conflict acceptance flow

**Files:**
- Modify: `database/database_manager.py`
- Test: `tests/test_database_manager_remote.py`

- [ ] **Step 1: Attach local and remote history snapshots to pending task conflicts**

```python
    def _build_remote_change(self, local_task: Optional[Dict[str, Any]], remote_task: Dict[str, Any]) -> Dict[str, Any]:
        local_task_data = self._cache_task_to_task_data(local_task)
        entity_id = remote_task['id']
        title = remote_task.get('text') or (local_task_data.get('text') if local_task_data else '') or f"任务 {entity_id}"
        remote_history = self._fetch_remote_task_history(entity_id)
        local_history = self._load_local_task_history(entity_id)
        return {
            ...
            'local_history': local_history,
            'remote_history': remote_history,
        }
```

- [ ] **Step 2: Merge accepted remote history into local state before marking synced**

```python
    def _apply_remote_change_locked(self, change: Dict[str, Any]) -> None:
        if change.get('entity_type') == 'scheduled_task':
            ...
            return

        entity_id = change['entity_id']
        merged_history = self._merge_history_dicts(
            change.get('local_history'),
            change.get('remote_history'),
        )
        self._save_task_to_cache(change['remote_record'], 'synced')
        self._replace_task_history_locked(entity_id, merged_history)
        change['history_push_payload'] = self._build_missing_history_payload(
            merged_history,
            change.get('remote_history'),
        )
```

- [ ] **Step 3: Preserve local-final-first ordering during accepted/rejected resolution**

```python
            with self._cache_lock:
                ...
                for change_key in pending_ids & accepted_set:
                    change = self._pending_remote_task_changes[change_key]
                    self._apply_remote_change_locked(change)
                    accepted_changes.append(copy.deepcopy(change))
                ...
            self.flush_cache_to_db()
            for change in accepted_changes:
                self._push_task_history_to_remote(change)
```

- [ ] **Step 4: Run targeted tests to verify accepted conflicts merge local and remote history**

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_accept_remote_change_merges_remote_history_into_local_before_flush -v`

Expected: PASS

### Task 4: Push missing local history after local finalization

**Files:**
- Modify: `database/database_manager.py`
- Test: `tests/test_database_manager_remote.py`

- [ ] **Step 1: Add remote-history fetch and push helpers behind the existing API client**

```python
    def _fetch_remote_task_history(self, task_id: str) -> Dict[str, List[Dict[str, Any]]]:
        if not self.api_base_url:
            return {}
        remote_result = self._make_api_request('GET', f'/api/tasks/{task_id}/history')
        if remote_result and isinstance(remote_result.get('history'), dict):
            return remote_result.get('history', {})
        return {}

    def _build_missing_history_payload(self, final_history, remote_history):
        ...

    def _push_task_history_to_remote(self, change: Dict[str, Any]) -> None:
        ...
```
 
- [ ] **Step 2: Add a test proving accepted local-final state pushes only missing local history**

```python
    def test_accept_remote_change_pushes_missing_local_history_after_local_merge(self):
        ...
        with patch.object(manager, '_make_api_request', return_value={'success': True}) as request_mock:
            result = manager.resolve_pending_remote_task_changes(['task:task-1'], [])

        self.assertTrue(result)
        history_calls = [
            call for call in request_mock.call_args_list
            if call.args[:2] == ('POST', '/api/tasks/task-1/history')
        ]
        self.assertEqual(len(history_calls), 1)
```

- [ ] **Step 3: Run targeted tests for the remote history push path**

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_accept_remote_change_pushes_missing_local_history_after_local_merge -v`

Expected: PASS

### Task 5: Run the focused regression suite

**Files:**
- Test: `tests/test_database_manager_remote.py`

- [ ] **Step 1: Run the full remote database manager test module**

Run: `python -m unittest tests.test_database_manager_remote -v`

Expected: PASS with 0 failures
