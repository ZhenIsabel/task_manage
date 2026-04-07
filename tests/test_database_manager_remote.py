import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from core.quadrant_widget import QuadrantWidget
from config.remote_config import RemoteConfigManager
from database.database_manager import DatabaseManager


WORKSPACE_TMP_ROOT = os.path.join(os.getcwd(), ".tmp-tests")
os.makedirs(WORKSPACE_TMP_ROOT, exist_ok=True)


class FakeResponse:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


class DatabaseManagerRemoteTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(dir=WORKSPACE_TMP_ROOT, suffix=".db")
        os.close(fd)
        os.remove(self.db_path)
        self.addCleanup(self._cleanup_db_file)

    def _cleanup_db_file(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def _build_manager(self, remote_config=None, sync_interval=0):
        manager = DatabaseManager(
            db_path=self.db_path,
            remote_config=remote_config or {},
            sync_interval=sync_interval,
            flush_interval=0,
        )
        self.addCleanup(manager.close_connection)
        return manager

    def test_init_does_not_sync_remote_before_explicit_bootstrap(self):
        remote_config = {
            "api_base_url": "http://example.com",
            "api_token": "token",
            "username": "alice",
        }
        with patch.object(DatabaseManager, "_make_api_request", autospec=True) as request_mock,              patch.object(DatabaseManager, "sync_from_server", autospec=True) as sync_tasks_mock,              patch.object(DatabaseManager, "sync_scheduled_tasks_from_server", autospec=True) as sync_scheduled_mock,              patch.object(DatabaseManager, "start_periodic_sync", autospec=True) as start_sync_mock:
            self._build_manager(remote_config=remote_config, sync_interval=180)

        request_mock.assert_not_called()
        sync_tasks_mock.assert_not_called()
        sync_scheduled_mock.assert_not_called()
        start_sync_mock.assert_not_called()

    def test_protected_request_registers_user_and_retries_after_401(self):
        remote_config = {
            "api_base_url": "http://example.com",
            "api_token": "token",
            "username": "alice",
        }
        manager = self._build_manager(remote_config=remote_config)

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

        self.assertEqual(result, {'tasks': [], 'count': 0})

    def test_explicit_bootstrap_runs_remote_health_check_and_sync(self):
        remote_config = {
            "api_base_url": "http://example.com",
            "api_token": "token",
            "username": "alice",
        }
        with patch.object(DatabaseManager, "_make_api_request", autospec=True, return_value={'status': 'ok'}) as request_mock,              patch.object(DatabaseManager, 'sync_from_server', autospec=True, return_value=True) as sync_tasks_mock,              patch.object(DatabaseManager, 'sync_scheduled_tasks_from_server', autospec=True, return_value=True) as sync_scheduled_mock,              patch.object(DatabaseManager, 'start_periodic_sync', autospec=True) as start_sync_mock:
            manager = self._build_manager(remote_config=remote_config, sync_interval=180)
            start_sync_mock.assert_not_called()
            manager.bootstrap_remote_sync()

        request_mock.assert_any_call(manager, 'GET', '/api/health')
        sync_tasks_mock.assert_called_once_with(manager)
        sync_scheduled_mock.assert_called_once_with(manager)
        start_sync_mock.assert_called_once_with(manager, 180)

    def test_get_task_history_prefers_remote_history(self):
        remote_config = {
            "api_base_url": "http://example.com",
            "api_token": "token",
            "username": "alice",
        }
        manager = self._build_manager(remote_config=remote_config)
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

        self.assertEqual(history, remote_history['history'])

    def test_create_scheduled_task_keeps_local_write_without_immediate_remote_push(self):
        manager = self._build_manager(remote_config={})
        manager.api_base_url = 'http://example.com'
        manager.api_token = 'token'
        schedule_data = {
            'id': 'sched-1',
            'title': '每日回顾',
            'frequency': 'daily',
            'notes': '本地优先保存',
        }

        with patch.object(manager, '_make_api_request', return_value=None) as request_mock:
            result = manager.create_scheduled_task(schedule_data)

        self.assertTrue(result)
        self.assertIsNotNone(manager.get_scheduled_task('sched-1'))
        request_mock.assert_not_called()

    def test_create_scheduled_task_is_visible_from_cache_before_flush(self):
        manager = self._build_manager(remote_config={})

        result = manager.create_scheduled_task({
            'id': 'sched-cache-create',
            'title': '缓存创建',
            'frequency': 'daily',
        })

        self.assertTrue(result)
        self.assertIsNotNone(manager.get_scheduled_task('sched-cache-create'))
        self.assertEqual(
            [task['id'] for task in manager.list_scheduled_tasks()],
            ['sched-cache-create'],
        )

        row = manager.get_connection().execute(
            'SELECT id FROM scheduled_tasks WHERE id = ?',
            ('sched-cache-create',),
        ).fetchone()
        self.assertIsNone(row)

    def test_update_scheduled_task_uses_cache_before_flush(self):
        manager = self._build_manager(remote_config={})
        manager.create_scheduled_task({
            'id': 'sched-cache-update',
            'title': '原始标题',
            'frequency': 'daily',
        })
        manager.flush_cache_to_db()

        result = manager.update_scheduled_task('sched-cache-update', {'title': '缓存标题'})

        self.assertTrue(result)
        self.assertEqual(manager.get_scheduled_task('sched-cache-update')['title'], '缓存标题')

        row = manager.get_connection().execute(
            'SELECT title FROM scheduled_tasks WHERE id = ?',
            ('sched-cache-update',),
        ).fetchone()
        self.assertEqual(row['title'], '原始标题')

    def test_delete_scheduled_task_hides_from_reads_before_flush(self):
        manager = self._build_manager(remote_config={})
        manager.create_scheduled_task({
            'id': 'sched-cache-delete',
            'title': '待删除任务',
            'frequency': 'daily',
        })
        manager.flush_cache_to_db()

        result = manager.delete_scheduled_task('sched-cache-delete')

        self.assertTrue(result)
        self.assertIsNone(manager.get_scheduled_task('sched-cache-delete'))
        self.assertEqual(
            [task['id'] for task in manager.list_scheduled_tasks()],
            [],
        )

        row = manager.get_connection().execute(
            'SELECT id FROM scheduled_tasks WHERE id = ?',
            ('sched-cache-delete',),
        ).fetchone()
        self.assertIsNotNone(row)

    def test_database_manager_loads_scheduled_tasks_into_entity_cache(self):
        manager = self._build_manager(remote_config={})
        conn = manager.get_connection()
        conn.execute(
            '''
            INSERT INTO scheduled_tasks
            (id, title, frequency, active, deleted, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            ('sched-cache-loaded', '已加载任务', 'daily', True, False, '2026-04-01T00:00:00', '2026-04-01T00:00:00'),
        )
        conn.commit()

        manager._load_all_entities_to_cache()

        self.assertIn('sched-cache-loaded', manager._entity_cache['scheduled_task']['records'])

    def test_get_scheduled_task_can_return_deleted_tombstone_when_requested(self):
        manager = self._build_manager(remote_config={})
        manager.create_scheduled_task({
            'id': 'sched-cache-tombstone',
            'title': '墓碑任务',
            'frequency': 'daily',
        })
        manager.flush_cache_to_db()
        manager.delete_scheduled_task('sched-cache-tombstone')

        self.assertIsNone(manager.get_scheduled_task('sched-cache-tombstone'))
        deleted_record = manager.get_scheduled_task('sched-cache-tombstone', include_deleted=True)
        self.assertIsNotNone(deleted_record)
        self.assertTrue(deleted_record['deleted'])

    def test_sync_scheduled_tasks_from_server_adds_remote_record_to_cache_before_flush(self):
        manager = self._build_manager(remote_config={})
        manager.api_base_url = 'http://example.com'

        with patch.object(manager, '_make_api_request', return_value={
            'scheduled_tasks': [{
                'id': 'sched-remote',
                'title': '远端任务',
                'frequency': 'daily',
                'notes': '远端下发',
                'updated_at': '2026-03-30T10:00:00',
                'created_at': '2026-03-30T09:00:00',
            }]
        }):
            result = manager.sync_scheduled_tasks_from_server()

        self.assertTrue(result)
        self.assertEqual(manager.get_scheduled_task('sched-remote')['title'], '远端任务')
        row = manager.get_connection().execute(
            'SELECT id FROM scheduled_tasks WHERE id = ?',
            ('sched-remote',),
        ).fetchone()
        self.assertIsNone(row)

    def test_sync_scheduled_tasks_from_server_keeps_local_when_remote_is_newer(self):
        manager = self._build_manager(remote_config={})
        manager.create_scheduled_task({
            'id': 'sched-1',
            'title': '本地版本',
            'frequency': 'daily',
            'notes': '保留本地',
            'updated_at': '2026-03-30T09:00:00',
            'created_at': '2026-03-30T08:00:00',
        })
        manager._save_scheduled_task_to_cache(
            manager.get_scheduled_task('sched-1', include_deleted=True),
            sync_status='synced',
        )
        manager.api_base_url = 'http://example.com'

        with patch.object(manager, '_make_api_request', return_value={
            'scheduled_tasks': [{
                'id': 'sched-1',
                'title': '远端版本',
                'frequency': 'daily',
                'notes': '远端变更',
                'updated_at': '2026-03-30T10:00:00',
            }]
        }):
            manager.sync_scheduled_tasks_from_server()

        self.assertEqual(manager.get_scheduled_task('sched-1')['title'], '本地版本')
        self.assertIn('scheduled:sched-1', manager._pending_remote_task_changes)
        self.assertEqual(
            manager._pending_remote_task_changes['scheduled:sched-1']['entity_type'],
            'scheduled_task',
        )

    def test_sync_scheduled_tasks_from_server_prefers_recent_local_update_without_pending_confirmation(self):
        manager = self._build_manager(remote_config={})
        manager.create_scheduled_task({
            'id': 'sched-1',
            'title': '本地版本',
            'frequency': 'daily',
            'notes': '刚刚改过',
            'updated_at': '2026-03-30T09:57:00',
            'created_at': '2026-03-30T08:00:00',
        })
        manager.api_base_url = 'http://example.com'
        frozen_now = datetime.fromisoformat('2026-03-30T10:00:00')

        with patch('database.database_manager.datetime') as datetime_mock, patch.object(manager, '_make_api_request', return_value={
            'scheduled_tasks': [{
                'id': 'sched-1',
                'title': '远端版本',
                'frequency': 'daily',
                'notes': '远端变更',
                'updated_at': '2026-03-30T10:30:00',
            }]
        }):
            datetime_mock.now.return_value = frozen_now
            datetime_mock.fromisoformat.side_effect = lambda value: datetime.fromisoformat(value.replace('Z', '+00:00'))
            manager.sync_scheduled_tasks_from_server()

        self.assertEqual(manager.get_scheduled_task('sched-1')['title'], '本地版本')
        self.assertEqual(manager.get_scheduled_task('sched-1')['sync_status'], 'modified')
        self.assertEqual(manager.get_scheduled_task('sched-1')['updated_at'], '2026-03-30T10:00:00')
        self.assertNotIn('scheduled:sched-1', manager._pending_remote_task_changes)

    def test_sync_scheduled_tasks_from_server_ignores_updated_at_only_change(self):
        manager = self._build_manager(remote_config={})
        manager.create_scheduled_task({
            'id': 'sched-1',
            'title': '每周复盘',
            'frequency': 'weekly',
            'notes': '内容未变',
            'updated_at': '2026-03-30T09:00:00',
            'created_at': '2026-03-30T08:00:00',
        })
        manager._save_scheduled_task_to_cache(
            manager.get_scheduled_task('sched-1', include_deleted=True),
            sync_status='synced',
        )
        manager.api_base_url = 'http://example.com'

        with patch.object(manager, '_make_api_request', return_value={
            'scheduled_tasks': [{
                'id': 'sched-1',
                'title': '每周复盘',
                'frequency': 'weekly',
                'notes': '内容未变',
                'updated_at': '2026-03-30T10:00:00',
            }]
        }):
            result = manager.sync_scheduled_tasks_from_server()

        self.assertTrue(result)
        self.assertEqual(manager.get_scheduled_task('sched-1')['updated_at'], '2026-03-30T09:00:00')
        self.assertNotIn('scheduled:sched-1', manager._pending_remote_task_changes)

    def test_accept_scheduled_remote_change_applies_remote_record(self):
        manager = self._build_manager(remote_config={})
        manager.create_scheduled_task({
            'id': 'sched-1',
            'title': '本地版本',
            'frequency': 'daily',
            'notes': '保留本地',
            'updated_at': '2026-03-30T09:00:00',
            'created_at': '2026-03-30T08:00:00',
        })
        manager.flush_cache_to_db()
        manager._save_scheduled_task_to_cache(
            manager.get_scheduled_task('sched-1', include_deleted=True),
            sync_status='synced',
        )
        manager.api_base_url = 'http://example.com'

        with patch.object(manager, '_make_api_request', return_value={
            'scheduled_tasks': [{
                'id': 'sched-1',
                'title': '远端版本',
                'frequency': 'daily',
                'notes': '远端变更',
                'updated_at': '2026-03-30T10:00:00',
            }]
        }):
            manager.sync_scheduled_tasks_from_server()

        result = manager.resolve_pending_remote_task_changes(['scheduled:sched-1'], [])

        self.assertTrue(result)
        self.assertEqual(manager.get_scheduled_task('sched-1')['title'], '远端版本')
        row = manager.get_connection().execute(
            'SELECT title FROM scheduled_tasks WHERE id = ?',
            ('sched-1',),
        ).fetchone()
        self.assertEqual(row['title'], '本地版本')
        self.assertNotIn('scheduled:sched-1', manager._pending_remote_task_changes)

    def test_reject_scheduled_remote_change_keeps_local_and_pushes_back_to_server(self):
        manager = self._build_manager(remote_config={})
        manager.create_scheduled_task({
            'id': 'sched-1',
            'title': '本地版本',
            'frequency': 'daily',
            'notes': '保留本地',
            'updated_at': '2026-03-30T09:00:00',
            'created_at': '2026-03-30T08:00:00',
        })
        manager.flush_cache_to_db()
        manager._save_scheduled_task_to_cache(
            manager.get_scheduled_task('sched-1', include_deleted=True),
            sync_status='synced',
        )
        manager.api_base_url = 'http://example.com'

        with patch.object(manager, '_make_api_request', return_value={
            'scheduled_tasks': [{
                'id': 'sched-1',
                'title': '远端版本',
                'frequency': 'daily',
                'notes': '远端变更',
                'updated_at': '2026-03-30T10:00:00',
            }]
        }):
            manager.sync_scheduled_tasks_from_server()

        with patch.object(manager, '_make_api_request', return_value={'success': True}) as request_mock:
            result = manager.resolve_pending_remote_task_changes([], ['scheduled:sched-1'])

        self.assertTrue(result)
        self.assertEqual(manager.get_scheduled_task('sched-1')['title'], '本地版本')
        row = manager.get_connection().execute(
            'SELECT title FROM scheduled_tasks WHERE id = ?',
            ('sched-1',),
        ).fetchone()
        self.assertEqual(row['title'], '本地版本')
        self.assertNotIn('scheduled:sched-1', manager._pending_remote_task_changes)
        request_mock.assert_called_once()
        self.assertEqual(request_mock.call_args.args[:2], ('POST', '/api/scheduled_tasks'))
        self.assertEqual(request_mock.call_args.args[2]['title'], '本地版本')


    def test_get_task_history_falls_back_to_local_when_remote_unavailable(self):
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

        with patch.object(manager, '_make_api_request', return_value=None):
            history = manager.get_task_history('task-1')

        self.assertEqual(history['text'][0]['value'], '本地任务')

    def test_bootstrap_remote_sync_does_not_start_periodic_sync_when_health_check_fails(self):
        remote_config = {
            "api_base_url": "http://example.com",
            "api_token": "token",
            "username": "alice",
        }
        with patch.object(DatabaseManager, '_make_api_request', autospec=True, return_value=None) as request_mock,              patch.object(DatabaseManager, 'sync_from_server', autospec=True) as sync_tasks_mock,              patch.object(DatabaseManager, 'sync_scheduled_tasks_from_server', autospec=True) as sync_scheduled_mock,              patch.object(DatabaseManager, 'start_periodic_sync', autospec=True) as start_sync_mock:
            manager = self._build_manager(remote_config=remote_config, sync_interval=180)
            result = manager.bootstrap_remote_sync()

        self.assertFalse(result)
        request_mock.assert_called_once_with(manager, 'GET', '/api/health')
        sync_tasks_mock.assert_not_called()
        sync_scheduled_mock.assert_not_called()
        start_sync_mock.assert_not_called()

    def test_sync_scheduled_tasks_to_server_serializes_active_as_boolean(self):
        manager = self._build_manager(remote_config={})
        manager.create_scheduled_task({
            'id': 'sched-1',
            'title': '每日回顾',
            'frequency': 'daily',
        })
        manager.api_base_url = 'http://example.com'
        manager.api_token = 'token'

        with patch.object(manager, '_make_api_request', return_value={'success': True}) as request_mock:
            result = manager.sync_scheduled_tasks_to_server()

        self.assertTrue(result)
        self.assertTrue(request_mock.call_args.args[2]['active'])
        self.assertIsInstance(request_mock.call_args.args[2]['active'], bool)

    def test_update_scheduled_task_keeps_local_write_without_immediate_remote_push(self):
        manager = self._build_manager(remote_config={})
        manager.create_scheduled_task({
            'id': 'sched-1',
            'title': '原始标题',
            'frequency': 'daily',
            'notes': '原始备注',
        })
        manager.api_base_url = 'http://example.com'
        manager.api_token = 'token'

        with patch.object(manager, '_make_api_request', return_value=None) as request_mock:
            result = manager.update_scheduled_task('sched-1', {'title': '更新标题'})

        self.assertTrue(result)
        self.assertEqual(manager.get_scheduled_task('sched-1')['title'], '更新标题')
        request_mock.assert_not_called()


    def test_delete_scheduled_task_keeps_local_delete_without_immediate_remote_push(self):
        manager = self._build_manager(remote_config={})
        manager.create_scheduled_task({
            'id': 'sched-1',
            'title': '待删除',
            'frequency': 'daily',
        })
        manager.api_base_url = 'http://example.com'
        manager.api_token = 'token'

        with patch.object(manager, '_make_api_request', return_value=None) as request_mock:
            result = manager.delete_scheduled_task('sched-1')

        self.assertTrue(result)
        self.assertIsNone(manager.get_scheduled_task('sched-1'))
        self.assertTrue(manager.get_scheduled_task('sched-1', include_deleted=True)['deleted'])
        request_mock.assert_not_called()


    def test_database_manager_logger_does_not_propagate_to_root_logger(self):
        from database.database_manager import logger as db_logger

        self.assertFalse(db_logger.propagate)

    def test_make_api_request_stops_repeated_auth_retry_after_failed_registration(self):
        remote_config = {
            "api_base_url": "http://example.com",
            "api_token": "token",
            "username": "alice",
        }
        manager = self._build_manager(remote_config=remote_config)

        calls = []

        def fake_request(method, url, headers=None, json=None, timeout=None):
            calls.append((method, url, headers, json))
            if url.endswith('/api/tasks') and method == 'GET':
                return FakeResponse(401, {'error': 'Unauthorized'}, 'unauthorized')
            if url.endswith('/api/users') and method == 'POST':
                return FakeResponse(500, {'error': 'boom'}, 'boom')
            raise AssertionError(f'unexpected request: {method} {url}')

        with patch('database.database_manager.requests.request', side_effect=fake_request):
            first_result = manager._make_api_request('GET', '/api/tasks')
            second_result = manager._make_api_request('GET', '/api/tasks')

        self.assertIsNone(first_result)
        self.assertIsNone(second_result)
        self.assertEqual(
            calls,
            [
                ('GET', 'http://example.com/api/tasks', {'Content-Type': 'application/json', 'Authorization': 'Bearer token'}, None),
                ('POST', 'http://example.com/api/users', {'Content-Type': 'application/json'}, {'username': 'alice', 'api_token': 'token'}),
            ],
        )


    def test_bootstrap_remote_sync_does_not_start_periodic_sync_when_initial_sync_fails(self):
        remote_config = {
            "api_base_url": "http://example.com",
            "api_token": "token",
            "username": "alice",
        }
        with patch.object(DatabaseManager, '_make_api_request', autospec=True, return_value={'status': 'ok'}) as request_mock,              patch.object(DatabaseManager, 'sync_from_server', autospec=True, return_value=False) as sync_tasks_mock,              patch.object(DatabaseManager, 'sync_scheduled_tasks_from_server', autospec=True, return_value=False) as sync_scheduled_mock,              patch.object(DatabaseManager, 'start_periodic_sync', autospec=True) as start_sync_mock:
            manager = self._build_manager(remote_config=remote_config, sync_interval=180)
            result = manager.bootstrap_remote_sync()

        self.assertFalse(result)
        request_mock.assert_called_once_with(manager, 'GET', '/api/health')
        sync_tasks_mock.assert_called_once_with(manager)
        sync_scheduled_mock.assert_called_once_with(manager)
        start_sync_mock.assert_not_called()


    def test_bootstrap_remote_sync_opens_settings_when_username_missing(self):
        widget = QuadrantWidget.__new__(QuadrantWidget)
        widget._is_closing = False
        widget._sync_refresh_pending = False
        widget.load_tasks = Mock()
        widget.show_settings = Mock()
        widget.db_manager = Mock()
        widget.db_manager.api_base_url = 'http://example.com'
        widget.db_manager.api_token = 'token'
        widget.db_manager.username = ''

        with patch('core.quadrant_widget.QMessageBox.warning') as warning_mock:
            QuadrantWidget._bootstrap_remote_sync(widget)

        warning_mock.assert_called_once()
        widget.show_settings.assert_called_once()
        widget.db_manager.bootstrap_remote_sync.assert_not_called()
        widget.load_tasks.assert_not_called()

    def test_remote_config_manager_persists_enabled_flag(self):
        fd, config_path = tempfile.mkstemp(dir=WORKSPACE_TMP_ROOT, suffix='.json')
        os.close(fd)
        os.remove(config_path)
        self.addCleanup(lambda: os.path.exists(config_path) and os.remove(config_path))

        manager = RemoteConfigManager(config_file=config_path)
        self.assertTrue(
            manager.set_server_config(
                'http://example.com',
                'token',
                username='alice',
                enabled=False,
            )
        )

        reloaded = RemoteConfigManager(config_file=config_path)
        config = reloaded.get_server_config()
        self.assertEqual(config['api_base_url'], 'http://example.com')
        self.assertEqual(config['api_token'], 'token')
        self.assertEqual(config['username'], 'alice')
        self.assertFalse(config['enabled'])

    def test_database_manager_treats_disabled_remote_config_as_local_mode(self):
        manager = self._build_manager(
            remote_config={
                'enabled': False,
                'api_base_url': 'http://example.com',
                'api_token': 'token',
                'username': 'alice',
            },
            sync_interval=180,
        )

        self.assertFalse(manager.remote_enabled)
        self.assertEqual(manager.api_base_url, '')
        self.assertEqual(manager.api_token, '')
        self.assertEqual(manager.username, '')


    def test_sync_from_server_ignores_updated_at_only_change(self):
        manager = self._build_manager(remote_config={})
        manager.save_task({
            'id': 'task-1',
            'text': '写周报',
            'notes': '内容未变',
            'completed': False,
            'completed_date': '',
            'deleted': False,
            'priority': '中',
            'urgency': '低',
            'importance': '高',
            'directory': '',
            'create_date': '',
            'position': {'x': 120, 'y': 180},
            'updated_at': '2026-03-30T09:00:00',
            'created_at': '2026-03-30T08:00:00',
        })
        manager.api_base_url = 'http://example.com'

        with patch.object(manager, '_make_api_request', return_value={
            'tasks': [{
                'id': 'task-1',
                'text': '写周报',
                'notes': '内容未变',
                'completed': False,
                'completed_date': '',
                'deleted': False,
                'priority': '中',
                'urgency': '低',
                'importance': '高',
                'directory': '',
                'create_date': '',
                'position': {'x': 120, 'y': 180},
                'updated_at': '2026-03-30T10:00:00',
                'created_at': '2026-03-30T08:00:00',
            }],
            'count': 1,
        }):
            result = manager.sync_from_server()

        self.assertTrue(result)
        self.assertEqual(
            manager._cache_task_to_task_data(manager._task_cache['task-1'])['updated_at'],
            '2026-03-30T09:00:00',
        )
        self.assertNotIn('task:task-1', manager._pending_remote_task_changes)

    def test_recent_local_task_conflict_skips_confirmation_and_still_uploads_with_other_pending_changes(self):
        manager = self._build_manager(remote_config={})
        manager.save_task({
            'id': 'task-1',
            'text': '本地任务',
            'notes': '五分钟内改过',
            'completed': False,
            'completed_date': '',
            'deleted': False,
            'priority': '中',
            'urgency': '低',
            'importance': '高',
            'directory': '',
            'create_date': '',
            'position': {'x': 120, 'y': 180},
            'updated_at': '2026-03-30T09:57:00',
            'created_at': '2026-03-30T08:00:00',
        })
        manager.save_task({
            'id': 'task-2',
            'text': '普通冲突任务',
            'notes': '等待确认',
            'completed': False,
            'completed_date': '',
            'deleted': False,
            'priority': '中',
            'urgency': '低',
            'importance': '中',
            'directory': '',
            'create_date': '',
            'position': {'x': 160, 'y': 220},
            'updated_at': '2026-03-30T08:00:00',
            'created_at': '2026-03-30T07:00:00',
        })
        manager._save_task_to_cache(manager._cache_task_to_task_data(manager._task_cache['task-2']), 'synced')
        manager.api_base_url = 'http://example.com'
        manager.add_task_sync_listener(lambda changes: None)
        frozen_now = datetime.fromisoformat('2026-03-30T10:00:00')

        def fake_api_request(method, path, payload=None):
            if method == 'GET' and path == '/api/tasks':
                return {
                    'tasks': [
                        {
                            'id': 'task-1',
                            'text': '远端任务',
                            'notes': '远端改过',
                            'completed': False,
                            'completed_date': '',
                            'deleted': False,
                            'priority': '中',
                            'urgency': '低',
                            'importance': '高',
                            'directory': '',
                            'create_date': '',
                            'position': {'x': 120, 'y': 180},
                            'updated_at': '2026-03-30T10:30:00',
                            'created_at': '2026-03-30T08:00:00',
                        },
                        {
                            'id': 'task-2',
                            'text': '远端冲突任务',
                            'notes': '远端改过',
                            'completed': False,
                            'completed_date': '',
                            'deleted': False,
                            'priority': '高',
                            'urgency': '高',
                            'importance': '高',
                            'directory': '',
                            'create_date': '',
                            'position': {'x': 160, 'y': 220},
                            'updated_at': '2026-03-30T10:20:00',
                            'created_at': '2026-03-30T07:00:00',
                        },
                    ],
                    'count': 2,
                }
            if method == 'POST' and path == '/api/tasks':
                return {'success': True}
            raise AssertionError(f'unexpected request: {method} {path}')

        with patch('database.database_manager.datetime') as datetime_mock, patch.object(manager, '_make_api_request', side_effect=fake_api_request) as request_mock:
            datetime_mock.now.return_value = frozen_now
            datetime_mock.fromisoformat.side_effect = lambda value: datetime.fromisoformat(value.replace('Z', '+00:00'))

            sync_from_result = manager.sync_from_server()
            sync_to_result = manager.sync_to_server()

        self.assertTrue(sync_from_result)
        self.assertTrue(sync_to_result)
        self.assertEqual(manager._task_cache['task-1']['text'], '本地任务')
        self.assertEqual(manager._task_cache['task-1']['sync_status'], 'synced')
        self.assertEqual(manager._task_cache['task-1']['updated_at'], '2026-03-30T10:00:00')
        self.assertNotIn('task:task-1', manager._pending_remote_task_changes)
        self.assertIn('task:task-2', manager._pending_remote_task_changes)
        self.assertEqual(request_mock.call_args_list[-1].args[:2], ('POST', '/api/tasks'))
        uploaded_payload = request_mock.call_args_list[-1].args[2]
        self.assertEqual(uploaded_payload['id'], 'task-1')
        self.assertEqual(uploaded_payload['text'], '本地任务')
        self.assertEqual(uploaded_payload['notes'], '五分钟内改过')
        self.assertEqual(uploaded_payload['updated_at'], '2026-03-30T10:00:00')
        self.assertEqual(uploaded_payload['sync_status'], 'modified')
        self.assertEqual(uploaded_payload['position'], {'x': 120, 'y': 180})

    def test_delete_task_keeps_local_tombstone_without_immediate_remote_sync(self):
        manager = self._build_manager(remote_config={})
        manager.save_task({
            'id': 'task-1',
            'text': '写周报',
            'notes': '待删除',
            'completed': False,
            'completed_date': '',
            'deleted': False,
            'priority': '中',
            'urgency': '低',
            'importance': '高',
            'directory': '',
            'create_date': '',
            'position': {'x': 120, 'y': 180},
            'updated_at': '2026-03-30T09:00:00',
            'created_at': '2026-03-30T08:00:00',
        })
        manager.api_base_url = 'http://example.com'
        manager.api_token = 'token'

        with patch('database.database_manager.threading.Thread') as thread_mock:
            result = manager.delete_task('task-1')

        self.assertTrue(result)
        self.assertTrue(manager._task_cache['task-1']['deleted'])
        self.assertEqual(manager._task_cache['task-1']['sync_status'], 'modified')
        thread_mock.assert_not_called()

    def test_quadrant_widget_builds_task_change_view_model_with_only_diff_fields(self):
        widget = QuadrantWidget.__new__(QuadrantWidget)
        change = {
            'id': 'task:task-1',
            'entity_type': 'task',
            'change_type': 'update',
            'title': '写周报',
            'local_record': {
                'id': 'task-1',
                'text': '写周报',
                'notes': '本地备注',
                'completed': False,
                'completed_date': '',
                'deleted': False,
                'urgency': '低',
                'importance': '高',
                'due_date': '',
            },
            'remote_record': {
                'id': 'task-1',
                'text': '写周报',
                'notes': '远程备注',
                'completed': True,
                'completed_date': '2026-04-01T10:00:00',
                'deleted': False,
                'urgency': '低',
                'importance': '高',
                'due_date': '',
            },
        }

        view_model = QuadrantWidget._build_remote_change_view_model(widget, change)

        self.assertEqual(view_model['change_type_label'], '修改')
        self.assertEqual(view_model['title'], '写周报')
        self.assertIn('备注：本地备注', view_model['local_text'])
        self.assertIn('备注：远程备注', view_model['remote_text'])
        self.assertIn('已完成：否', view_model['local_text'])
        self.assertIn('已完成：是', view_model['remote_text'])
        self.assertIn('完成时间：-', view_model['local_text'])
        self.assertIn('完成时间：2026-04-01 10:00:00', view_model['remote_text'])
        self.assertNotIn('紧急度：', view_model['local_text'])
        self.assertNotIn('重要度：', view_model['remote_text'])

    def test_quadrant_widget_builds_scheduled_change_view_model_with_only_diff_fields(self):
        widget = QuadrantWidget.__new__(QuadrantWidget)
        change = {
            'id': 'scheduled:sched-1',
            'entity_type': 'scheduled_task',
            'change_type': 'update',
            'title': '每周复盘',
            'local_record': {
                'id': 'sched-1',
                'title': '每周复盘',
                'frequency': 'weekly',
                'next_run_at': '2026-04-08T09:00:00',
                'notes': '不变备注',
                'active': True,
            },
            'remote_record': {
                'id': 'sched-1',
                'title': '每周复盘',
                'frequency': 'monthly',
                'next_run_at': '2026-05-01T09:00:00',
                'notes': '不变备注',
                'active': True,
            },
        }

        view_model = QuadrantWidget._build_remote_change_view_model(widget, change)

        self.assertEqual(view_model['change_type_label'], '修改')
        self.assertEqual(view_model['title'], '【定时任务】每周复盘')
        self.assertIn('频率：每周', view_model['local_text'])
        self.assertIn('频率：每月', view_model['remote_text'])
        self.assertIn('下次执行时间：2026-04-08 09:00:00', view_model['local_text'])
        self.assertIn('下次执行时间：2026-05-01 09:00:00', view_model['remote_text'])
        self.assertNotIn('备注：', view_model['local_text'])
        self.assertNotIn('启用：', view_model['remote_text'])

    def test_quadrant_widget_collects_remote_change_choices_and_flags_missing_rows(self):
        widget = QuadrantWidget.__new__(QuadrantWidget)
        accepted_ids, rejected_ids, missing_ids = QuadrantWidget._collect_remote_change_choices(widget, [
            {'id': 'task:1', 'local_selected': False, 'remote_selected': False},
            {'id': 'task:2', 'local_selected': True, 'remote_selected': False},
            {'id': 'task:3', 'local_selected': False, 'remote_selected': True},
            {'id': 'task:4', 'local_selected': True, 'remote_selected': True},
        ])

        self.assertEqual(accepted_ids, ['task:3'])
        self.assertEqual(rejected_ids, ['task:2'])
        self.assertEqual(missing_ids, ['task:1', 'task:4'])

    def test_quadrant_widget_apply_remote_change_selection_requires_each_row_to_choose_one_side(self):
        widget = QuadrantWidget.__new__(QuadrantWidget)
        widget.db_manager = Mock()
        widget.load_tasks = Mock()

        with patch('core.quadrant_widget.QMessageBox.warning') as warning_mock:
            result = QuadrantWidget._apply_remote_change_selection(widget, [
                {'id': 'task:1', 'local_selected': False, 'remote_selected': False},
            ])

        self.assertFalse(result)
        warning_mock.assert_called_once()
        widget.db_manager.resolve_pending_remote_task_changes.assert_not_called()
        widget.load_tasks.assert_not_called()

    def test_quadrant_widget_apply_remote_change_selection_submits_local_and_remote_choices(self):
        widget = QuadrantWidget.__new__(QuadrantWidget)
        widget.db_manager = Mock()
        widget.db_manager.resolve_pending_remote_task_changes.return_value = True
        widget.db_manager.api_base_url = 'http://example.com'
        widget.db_manager.sync_to_server.return_value = True
        widget.load_tasks = Mock()

        with patch('core.quadrant_widget.QMessageBox.warning') as warning_mock:
            result = QuadrantWidget._apply_remote_change_selection(widget, [
                {'id': 'task:1', 'local_selected': True, 'remote_selected': False},
                {'id': 'scheduled:sched-1', 'local_selected': False, 'remote_selected': True},
            ])

        self.assertTrue(result)
        warning_mock.assert_not_called()
        widget.db_manager.resolve_pending_remote_task_changes.assert_called_once_with(['scheduled:sched-1'], ['task:1'])
        self.assertEqual(widget.db_manager.flush_cache_to_db.call_count, 2)
        widget.db_manager.sync_to_server.assert_called_once()
        widget.load_tasks.assert_called_once()

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
        widget.load_tasks.assert_not_called()

    def test_task_label_get_editable_fields_uses_cached_config(self):
        from core.task_label import TaskLabel

        TaskLabel._editable_fields_cache = None
        self.addCleanup(lambda: setattr(TaskLabel, '_editable_fields_cache', None))
        fake_fields = [{'name': 'text', 'label': '任务内容', 'type': 'text', 'required': True}]

        with patch('core.task_label.load_config', return_value={'task_fields': fake_fields}) as load_config_mock:
            first = TaskLabel.get_editable_fields()
            second = TaskLabel.get_editable_fields()

        self.assertEqual(first, fake_fields)
        self.assertEqual(second, fake_fields)
        load_config_mock.assert_called_once()

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
            'updated_at': '2026-04-01T10:00:00',
            'created_at': '2026-04-01T09:00:00',
        }]), patch('core.quadrant_widget.TaskLabel', return_value=fake_task):
            QuadrantWidget.load_tasks(widget)

        self.assertEqual(widget.setUpdatesEnabled.call_args_list[0].args, (False,))
        self.assertEqual(widget.setUpdatesEnabled.call_args_list[-1].args, (True,))
        self.assertEqual(len(widget.tasks), 1)

if __name__ == "__main__":
    unittest.main()
