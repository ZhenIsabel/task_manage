# Startup and Main Panel Performance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the most visible startup latency by moving startup sync off the UI thread and trimming avoidable local main-panel load cost.

**Architecture:** Keep the current `QuadrantWidget` and `TaskLabel` structure, but change the execution model of startup sync and the field-definition resolution path used during task widget creation. Lock the behavior with focused tests before changing code.

**Tech Stack:** Python, PyQt6, unittest, threading

---

## File Map

**Create:**
- `docs/superpowers/specs/2026-04-01-startup-main-panel-performance-design.md`
- `docs/superpowers/plans/2026-04-01-startup-main-panel-performance.md`

**Modify:**
- `core/quadrant_widget.py`
- `core/task_label.py`
- `tests/test_database_manager_remote.py`

### Task 1: Make startup remote bootstrap asynchronous

**Files:**
- Modify: `tests/test_database_manager_remote.py`
- Modify: `core/quadrant_widget.py`
- Test: `tests/test_database_manager_remote.py`

- [ ] **Step 1: Write the failing test for background bootstrap scheduling**

```python
def test_bootstrap_remote_sync_starts_background_thread_when_remote_is_configured(self):
    widget = QuadrantWidget.__new__(QuadrantWidget)
    widget._is_closing = False
    widget._sync_refresh_pending = False
    widget.load_tasks = Mock()
    widget.show_settings = Mock()
    widget.db_manager = Mock()
    widget.db_manager.api_base_url = 'http://example.com'
    widget.db_manager.api_token = 'token'
    widget.db_manager.username = 'alice'

    fake_thread = Mock()
    with patch('core.quadrant_widget.threading.Thread', return_value=fake_thread) as thread_mock:
        QuadrantWidget._bootstrap_remote_sync(widget)

    thread_mock.assert_called_once()
    fake_thread.start.assert_called_once()
    widget.db_manager.bootstrap_remote_sync.assert_not_called()
```

- [ ] **Step 2: Run the single test and verify it fails**

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_bootstrap_remote_sync_starts_background_thread_when_remote_is_configured -v`
Expected: FAIL because `_bootstrap_remote_sync()` currently runs `bootstrap_remote_sync()` inline.

- [ ] **Step 3: Implement the async bootstrap handoff**

```python
def _bootstrap_remote_sync(self):
    if self._is_closing or not getattr(self.db_manager, 'api_base_url', ''):
        return
    if (not getattr(self.db_manager, 'username', '').strip()) or (not getattr(self.db_manager, 'api_token', '').strip()):
        QMessageBox.warning(...)
        self.show_settings('remote')
        return
    threading.Thread(target=self._run_bootstrap_remote_sync, daemon=True).start()
```

```python
def _run_bootstrap_remote_sync(self):
    sync_ok = self.db_manager.bootstrap_remote_sync()
    if not self._is_closing:
        self.remote_bootstrap_finished.emit(sync_ok)
```

- [ ] **Step 4: Add and wire the completion signal handler**

```python
remote_bootstrap_finished = pyqtSignal(bool)
```

```python
self.remote_bootstrap_finished.connect(self._on_remote_bootstrap_finished)
```

```python
def _on_remote_bootstrap_finished(self, sync_ok):
    logger.info(f"启动后远程同步结果: {sync_ok}")
    if sync_ok and not self._sync_refresh_pending:
        self.load_tasks()
```

- [ ] **Step 5: Run the new test and the existing missing-username test**

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_bootstrap_remote_sync_starts_background_thread_when_remote_is_configured tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_bootstrap_remote_sync_opens_settings_when_username_missing -v`
Expected: PASS

### Task 2: Cache task field definitions and batch main-panel rebuilds

**Files:**
- Modify: `tests/test_database_manager_remote.py`
- Modify: `core/task_label.py`
- Modify: `core/quadrant_widget.py`
- Test: `tests/test_database_manager_remote.py`

- [ ] **Step 1: Write the failing test for cached editable fields**

```python
def test_task_label_get_editable_fields_uses_cached_config(self):
    from core.task_label import TaskLabel

    TaskLabel._editable_fields_cache = None
    fake_fields = [{'name': 'text', 'label': '任务内容', 'type': 'text', 'required': True}]

    with patch('core.task_label.load_config', return_value={'task_fields': fake_fields}) as load_config_mock:
        first = TaskLabel.get_editable_fields()
        second = TaskLabel.get_editable_fields()

    self.assertEqual(first, fake_fields)
    self.assertEqual(second, fake_fields)
    load_config_mock.assert_called_once()
```

- [ ] **Step 2: Run the single test and verify it fails**

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_task_label_get_editable_fields_uses_cached_config -v`
Expected: FAIL because `get_editable_fields()` currently reloads config on every call.

- [ ] **Step 3: Write the failing test for batched task rebuilds**

```python
def test_load_tasks_batches_updates_while_rebuilding_task_widgets(self):
    widget = QuadrantWidget.__new__(QuadrantWidget)
    widget.tasks = []
    widget.config = {'task_fields': [{'name': 'text', 'required': True}]}
    widget._sync_refresh_pending = False
    widget.setUpdatesEnabled = Mock()

    fake_task = Mock()
    with patch('config.config_manager.load_tasks_with_history', return_value=[{
        'id': 'task-1',
        'color': '#4ECDC4',
        'completed': False,
        'text': '写周报',
        'position': {'x': 10, 'y': 10},
    }]), patch('core.quadrant_widget.TaskLabel', return_value=fake_task):
        QuadrantWidget.load_tasks(widget)

    self.assertEqual(widget.setUpdatesEnabled.call_args_list[0].args, (False,))
    self.assertEqual(widget.setUpdatesEnabled.call_args_list[-1].args, (True,))
```

- [ ] **Step 4: Run the batching test and verify it fails**

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_load_tasks_batches_updates_while_rebuilding_task_widgets -v`
Expected: FAIL because `load_tasks()` currently rebuilds without update batching.

- [ ] **Step 5: Add cache-aware field resolution to `TaskLabel`**

```python
class TaskLabel(QWidget):
    _editable_fields_cache = None

    @classmethod
    def get_editable_fields(cls, field_definitions=None):
        if field_definitions is not None:
            return field_definitions
        if cls._editable_fields_cache is None:
            config = load_config()
            cls._editable_fields_cache = config.get('task_fields', []) or [...]
        return cls._editable_fields_cache
```

- [ ] **Step 6: Update `QuadrantWidget.load_tasks()` to reuse field definitions and batch updates**

```python
field_definitions = self.config.get('task_fields', [])
self.setUpdatesEnabled(False)
try:
    ...
    task = TaskLabel(..., field_definitions=field_definitions, **task_fields)
finally:
    self.setUpdatesEnabled(True)
```

- [ ] **Step 7: Run the two new tests**

Run: `python -m unittest tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_task_label_get_editable_fields_uses_cached_config tests.test_database_manager_remote.DatabaseManagerRemoteTests.test_load_tasks_batches_updates_while_rebuilding_task_widgets -v`
Expected: PASS

### Task 3: Run verification

**Files:**
- Modify: `core/quadrant_widget.py`
- Modify: `core/task_label.py`
- Modify: `tests/test_database_manager_remote.py`
- Test: `tests/test_database_manager_remote.py`

- [ ] **Step 1: Run the focused regression suite**

Run: `python -m unittest tests.test_database_manager_remote -v`
Expected: PASS

- [ ] **Step 2: Grep for the removed hot path**

Run: `rg -n "load_config\(" core/task_label.py core/quadrant_widget.py`
Expected: `TaskLabel` no longer reloads config on every constructor call in the main-panel load path.

- [ ] **Step 3: Manual verification**

Check:

1. main window appears quickly with local data,
2. slow remote bootstrap no longer freezes the UI,
3. successful remote bootstrap still refreshes the task list.

Expected: faster perceived startup without functional regression.

## Spec Coverage Check

This plan covers:

- startup sync background execution,
- task field metadata reuse,
- batched main-panel rebuilds,
- automated plus manual verification.

It intentionally excludes:

- scheduled-task panel table optimization.
