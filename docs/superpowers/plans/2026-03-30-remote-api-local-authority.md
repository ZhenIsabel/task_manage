# Remote API Local-Authority Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the desktop app use the remote HTTP API while keeping the PC side local-authoritative and resolving remote conflicts item-by-item.

**Architecture:** Keep `database/database_manager.py` as the main coordination point. Add explicit remote bootstrap, API auth/register retry, and a generalized pending-remote-change flow that is triggered only after the UI listener is ready.

**Tech Stack:** Python, sqlite3, requests, PyQt6, unittest

---

## File Map

- Modify: `database/database_manager.py`
- Modify: `core/quadrant_widget.py`
- Modify: `config/remote_config.py`
- Create/Modify: `tests/test_database_manager_remote.py`
- Reference: `remote-api.md`
- Reference: `server/server_example.py`

### Task 1: Lock Down Remote Bootstrap Semantics

**Files:**
- Modify: `tests/test_database_manager_remote.py`
- Modify: `database/database_manager.py`

- [ ] **Step 1: Write the failing test for init behavior**

```python
def test_init_does_not_sync_remote_before_explicit_bootstrap(self):
    remote_config = {
        'api_base_url': 'http://example.com',
        'api_token': 'token',
        'username': 'alice',
    }
    with patch.object(DatabaseManager, '_make_api_request', autospec=True) as request_mock,          patch.object(DatabaseManager, 'sync_from_server', autospec=True) as sync_tasks_mock,          patch.object(DatabaseManager, 'sync_scheduled_tasks_from_server', autospec=True) as sync_scheduled_mock:
        manager = DatabaseManager(db_path=self.db_path, remote_config=remote_config, sync_interval=0, flush_interval=0)

    request_mock.assert_not_called()
    sync_tasks_mock.assert_not_called()
    sync_scheduled_mock.assert_not_called()
    manager.close_connection()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_init_does_not_sync_remote_before_explicit_bootstrap -v`
Expected: FAIL because the current code syncs too early or lacks the explicit bootstrap contract.

- [ ] **Step 3: Add explicit bootstrap entrypoint**

```python
def bootstrap_remote_sync(self) -> bool:
    if not self.api_base_url:
        logger.info("未配置远程服务器，跳过启动同步")
        return False

    health = self._make_api_request('GET', '/api/health')
    if not health:
        logger.warning("远程服务健康检查失败，保留本地数据")
        return False

    tasks_ok = self.sync_from_server()
    scheduled_ok = self.sync_scheduled_tasks_from_server()
    return tasks_ok and scheduled_ok
```

- [ ] **Step 4: Run the focused test again**

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_init_does_not_sync_remote_before_explicit_bootstrap -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_database_manager_remote.py database/database_manager.py
git commit -m "test: lock explicit remote bootstrap behavior"
```

### Task 2: Add Remote Auth Retry and User Registration

**Files:**
- Modify: `database/database_manager.py`
- Modify: `config/remote_config.py`
- Test: `tests/test_database_manager_remote.py`

- [ ] **Step 1: Write the failing auth retry test**

```python
def test_protected_request_registers_user_and_retries_after_401(self):
    remote_config = {
        'api_base_url': 'http://example.com',
        'api_token': 'token',
        'username': 'alice',
    }
    manager = DatabaseManager(db_path=self.db_path, remote_config=remote_config, sync_interval=0, flush_interval=0)

    calls = []

    def fake_request(method, url, headers=None, json=None, timeout=None):
        calls.append((method, url, headers, json))
        if url.endswith('/api/tasks') and method == 'GET' and len(calls) == 1:
            return FakeResponse(401, {'error': 'Unauthorized'}, 'unauthorized')
        if url.endswith('/api/users') and method == 'POST':
            return FakeResponse(200, {'user_id': 1, 'username': 'alice'})
        if url.endswith('/api/tasks') and method == 'GET':
            return FakeResponse(200, {'tasks': [], 'count': 0})
        raise AssertionError(f'unexpected request: {method} {url}')

    with patch('database.database_manager.requests.request', side_effect=fake_request):
        result = manager._make_api_request('GET', '/api/tasks')

    assert result == {'tasks': [], 'count': 0}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_protected_request_registers_user_and_retries_after_401 -v`
Expected: FAIL because `_make_api_request()` does not yet recover from `401`.

- [ ] **Step 3: Implement public-endpoint and register-retry helpers**

```python
def _is_public_endpoint(self, endpoint: str) -> bool:
    normalized_endpoint = f"/{endpoint.lstrip('/')}"
    return normalized_endpoint in {'/api/health', '/api/users'}


def _build_api_headers(self, endpoint: str) -> Dict[str, str]:
    headers = {'Content-Type': 'application/json'}
    if (not self._is_public_endpoint(endpoint)) and self.api_token:
        headers['Authorization'] = f'Bearer {self.api_token}'
    return headers


def _register_remote_user(self) -> bool:
    if self._remote_user_registration_attempted:
        return False
    self._remote_user_registration_attempted = True
    if not self.api_base_url or not self.username or not self.api_token:
        logger.warning("缺少远程注册所需的 username 或 api_token，跳过自动注册")
        return False
    response = requests.request(
        method='POST',
        url=f"{self.api_base_url.rstrip('/')}/api/users",
        headers=self._build_api_headers('/api/users'),
        json={'username': self.username, 'api_token': self.api_token},
        timeout=30,
    )
    return response.status_code in (200, 201, 409)
```

- [ ] **Step 4: Update request flow to retry once after registration**

```python
if response.status_code == 401 and retry_on_auth_failure and (not self._is_public_endpoint(endpoint)):
    logger.warning(f"API鉴权失败，尝试自动注册用户后重试: {endpoint}")
    if self._register_remote_user():
        return self._make_api_request(method, endpoint, data, retry_on_auth_failure=False)
    logger.error("自动注册远程用户失败，无法重试业务请求")
    return None
```

- [ ] **Step 5: Add username support to config tool**

```python
def set_server_config(self, api_base_url: str, api_token: str, username: str = '') -> bool:
    config = {
        'api_base_url': api_base_url,
        'api_token': api_token,
    }
    if username:
        config['username'] = username
    return self.save_config(config)
```

- [ ] **Step 6: Run the focused tests**

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_protected_request_registers_user_and_retries_after_401 -v`
Expected: PASS

Run: `python -m py_compile database/database_manager.py config/remote_config.py tests/test_database_manager_remote.py`
Expected: no output

- [ ] **Step 7: Commit**

```bash
git add database/database_manager.py config/remote_config.py tests/test_database_manager_remote.py
git commit -m "feat: add remote auth bootstrap and register retry"
```

### Task 3: Route Startup Sync Through the UI Listener

**Files:**
- Modify: `core/quadrant_widget.py`
- Modify: `database/database_manager.py`
- Test: `tests/test_database_manager_remote.py`

- [ ] **Step 1: Write the failing bootstrap test**

```python
def test_explicit_bootstrap_runs_remote_health_check_and_sync(self):
    remote_config = {
        'api_base_url': 'http://example.com',
        'api_token': 'token',
        'username': 'alice',
    }
    with patch.object(DatabaseManager, '_make_api_request', autospec=True, return_value={'status': 'ok'}) as request_mock,          patch.object(DatabaseManager, 'sync_from_server', autospec=True, return_value=True) as sync_tasks_mock,          patch.object(DatabaseManager, 'sync_scheduled_tasks_from_server', autospec=True, return_value=True) as sync_scheduled_mock:
        manager = DatabaseManager(db_path=self.db_path, remote_config=remote_config, sync_interval=0, flush_interval=0)
        manager.bootstrap_remote_sync()

    request_mock.assert_any_call(manager, 'GET', '/api/health')
    sync_tasks_mock.assert_called_once_with(manager)
    sync_scheduled_mock.assert_called_once_with(manager)
    manager.close_connection()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_explicit_bootstrap_runs_remote_health_check_and_sync -v`
Expected: FAIL before the explicit bootstrap path is wired.

- [ ] **Step 3: Trigger bootstrap only after listener registration**

```python
self.remote_sync_refresh_requested.connect(self._show_remote_sync_confirmation)
self.db_manager.add_task_sync_listener(self._handle_remote_sync)
QTimer.singleShot(0, self._bootstrap_remote_sync)
```

```python
def _bootstrap_remote_sync(self):
    if self._is_closing or not getattr(self.db_manager, 'api_base_url', ''):
        return
    sync_ok = self.db_manager.bootstrap_remote_sync()
    logger.info(f"启动后远程同步结果: {sync_ok}")
    if sync_ok and not self._sync_refresh_pending:
        self.load_tasks()
```

- [ ] **Step 4: Run the focused test and compile UI file**

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_explicit_bootstrap_runs_remote_health_check_and_sync -v`
Expected: PASS

Run: `python -m py_compile core/quadrant_widget.py`
Expected: no output

- [ ] **Step 5: Commit**

```bash
git add core/quadrant_widget.py database/database_manager.py tests/test_database_manager_remote.py
git commit -m "feat: run remote bootstrap after ui listener registration"
```

### Task 4: Prefer Remote History and Keep Scheduled Writes Local-Authoritative

**Files:**
- Modify: `database/database_manager.py`
- Test: `tests/test_database_manager_remote.py`

- [ ] **Step 1: Write the failing history test**

```python
def test_get_task_history_prefers_remote_history(self):
    remote_config = {
        'api_base_url': 'http://example.com',
        'api_token': 'token',
        'username': 'alice',
    }
    manager = DatabaseManager(db_path=self.db_path, remote_config=remote_config, sync_interval=0, flush_interval=0)
    remote_history = {
        'task_id': 'task-1',
        'history': {
            'text': [
                {'value': '远端任务', 'timestamp': '2026-03-30T10:00:00', 'action': 'update'}
            ]
        },
    }
    with patch.object(manager, '_make_api_request', return_value=remote_history):
        history = manager.get_task_history('task-1')
    assert history == remote_history['history']
```

- [ ] **Step 2: Write the failing scheduled-write test**

```python
def test_create_scheduled_task_keeps_local_write_when_remote_push_fails(self):
    manager = DatabaseManager(db_path=self.db_path, remote_config={}, sync_interval=0, flush_interval=0)
    manager.api_base_url = 'http://example.com'
    manager.api_token = 'token'
    schedule_data = {
        'id': 'sched-1',
        'title': '每日回顾',
        'frequency': 'daily',
        'notes': '本地优先保存',
    }
    with patch.object(manager, '_make_api_request', return_value=None):
        result = manager.create_scheduled_task(schedule_data)
    assert result is True
    assert manager.get_scheduled_task('sched-1') is not None
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_get_task_history_prefers_remote_history -v`
Expected: FAIL

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_create_scheduled_task_keeps_local_write_when_remote_push_fails -v`
Expected: FAIL

- [ ] **Step 4: Implement remote-first history lookup**

```python
def get_task_history(self, task_id: str) -> Dict[str, List[Dict[str, Any]]]:
    if self.api_base_url:
        remote_result = self._make_api_request('GET', f'/api/tasks/{task_id}/history')
        if remote_result and isinstance(remote_result.get('history'), dict):
            return remote_result.get('history', {})
    # fallback to local sqlite task_history
```

- [ ] **Step 5: Implement local-first scheduled writes with best-effort remote push**

```python
def _upsert_scheduled_task_local(self, schedule_data: Dict[str, Any], commit: bool = True) -> bool:
    cursor.execute(
        '''
        INSERT OR REPLACE INTO scheduled_tasks
        (id, title, priority, urgency, importance, notes, due_date, frequency,
         week_day, month_day, quarter_day, year_month, year_day,
         next_run_at, active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
        (...),
    )
```

```python
def create_scheduled_task(self, schedule_data: Dict[str, Any]) -> bool:
    schedule_to_save = dict(schedule_data)
    schedule_to_save['created_at'] = schedule_to_save.get('created_at') or datetime.now().isoformat()
    schedule_to_save['updated_at'] = schedule_to_save.get('updated_at') or datetime.now().isoformat()
    if not self._upsert_scheduled_task_local(schedule_to_save):
        return False
    if self.api_base_url:
        self._make_api_request('POST', '/api/scheduled_tasks', schedule_to_save)
    return True
```

- [ ] **Step 6: Run focused tests and compile**

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_get_task_history_prefers_remote_history -v`
Expected: PASS

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_create_scheduled_task_keeps_local_write_when_remote_push_fails -v`
Expected: PASS

Run: `python -m py_compile database/database_manager.py tests/test_database_manager_remote.py`
Expected: no output

- [ ] **Step 7: Commit**

```bash
git add database/database_manager.py tests/test_database_manager_remote.py
git commit -m "feat: prefer remote task history and keep scheduled writes local-first"
```

### Task 5: Generalize Remote Conflict Handling for Scheduled Tasks

**Files:**
- Modify: `database/database_manager.py`
- Modify: `core/quadrant_widget.py`
- Test: `tests/test_database_manager_remote.py`

- [ ] **Step 1: Write a failing test for scheduled-task remote conflict preservation**

```python
def test_sync_scheduled_tasks_from_server_keeps_local_when_remote_is_newer(self):
    manager = DatabaseManager(db_path=self.db_path, remote_config={}, sync_interval=0, flush_interval=0)
    manager.create_scheduled_task({
        'id': 'sched-1',
        'title': '本地版本',
        'frequency': 'daily',
        'updated_at': '2026-03-30T09:00:00',
    })
    manager.api_base_url = 'http://example.com'
    with patch.object(manager, '_make_api_request', return_value={
        'scheduled_tasks': [{
            'id': 'sched-1',
            'title': '远端版本',
            'frequency': 'daily',
            'updated_at': '2026-03-30T10:00:00',
        }]
    }):
        manager.sync_scheduled_tasks_from_server()

    assert manager.get_scheduled_task('sched-1')['title'] == '本地版本'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_sync_scheduled_tasks_from_server_keeps_local_when_remote_is_newer -v`
Expected: FAIL because the current implementation overwrites or does not yet queue conflicts.

- [ ] **Step 3: Extend pending remote change model to include entity type**

```python
{
    'change_key': 'scheduled:sched-1',
    'entity_type': 'scheduled_task',
    'entity_id': 'sched-1',
    'change_type': 'update',
    'title': '每周复盘',
    'local_record': {...},
    'remote_record': {...},
}
```

- [ ] **Step 4: Update scheduled-task pull path to queue conflicts instead of overwriting**

```python
if not local_task:
    self._upsert_scheduled_task_local(task_data, commit=False)
elif task_data.get('updated_at', '') > local_task_dict.get('updated_at', ''):
    pending_changes[change_key] = {
        'entity_type': 'scheduled_task',
        'entity_id': task_data['id'],
        'change_type': 'update',
        'title': task_data.get('title', task_data['id']),
        'local_record': local_task_dict,
        'remote_record': task_data,
    }
```

- [ ] **Step 5: Update conflict-apply and reject logic**

```python
if change['entity_type'] == 'scheduled_task':
    self._upsert_scheduled_task_local(change['remote_record'])
else:
    self._save_task_to_cache(change['remote_record'], 'synced')
```

```python
if change['entity_type'] == 'scheduled_task' and change.get('local_record'):
    self._make_api_request('POST', '/api/scheduled_tasks', change['local_record'])
```

- [ ] **Step 6: Reuse the existing dialog labels for scheduled changes**

```python
if change.get('entity_type') == 'scheduled_task':
    prefix = f"[定时任务][{prefix}]"
else:
    prefix = f"[{prefix}]"
checkbox = QCheckBox(f"{prefix} {title}")
```

- [ ] **Step 7: Run focused tests and smoke compile**

Run: `python -m unittest tests.test_database_manager_remote -v`
Expected: PASS

Run: `python -m py_compile database/database_manager.py core/quadrant_widget.py tests/test_database_manager_remote.py`
Expected: no output

- [ ] **Step 8: Commit**

```bash
git add database/database_manager.py core/quadrant_widget.py tests/test_database_manager_remote.py
git commit -m "feat: unify remote conflict handling for scheduled tasks"
```

### Task 6: Final Verification

**Files:**
- Modify: none unless verification exposes issues
- Test: `tests/test_database_manager_remote.py`

- [ ] **Step 1: Run regression suite**

Run: `python -m unittest tests.test_database_manager_remote -v`
Expected: all tests PASS

- [ ] **Step 2: Run syntax verification for touched modules**

Run: `python -m py_compile database/database_manager.py core/quadrant_widget.py config/remote_config.py tests/test_database_manager_remote.py`
Expected: no output

- [ ] **Step 3: Manual smoke test checklist**

```text
1. 无远端配置启动应用，确认本地功能不变。
2. 配置 api_base_url + username + api_token 后启动应用。
3. 观察 UI 在监听器就绪后再触发远端同步。
4. 构造普通任务冲突，逐条选择本地/远端。
5. 构造定时任务冲突，确认不会静默覆盖本地。
6. 断网后新增/编辑/删除本地任务，确认本地仍可正常使用。
```

- [ ] **Step 4: Final commit**

```bash
git add database/database_manager.py core/quadrant_widget.py config/remote_config.py tests/test_database_manager_remote.py
git commit -m "feat: complete local-authoritative remote api sync flow"
```
