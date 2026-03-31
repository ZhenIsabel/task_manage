import os
import tempfile
import unittest
from unittest.mock import patch

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

    def test_create_scheduled_task_keeps_local_write_when_remote_push_fails(self):
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
        request_mock.assert_called_once()
        self.assertEqual(request_mock.call_args.args[:2], ('POST', '/api/scheduled_tasks'))

    def test_sync_scheduled_tasks_from_server_keeps_local_when_remote_is_newer(self):
        manager = self._build_manager(remote_config={})
        manager.create_scheduled_task({
            'id': 'sched-1',
            'title': '本地版本',
            'frequency': 'daily',
            'notes': '保留本地',
        })
        conn = manager.get_connection()
        conn.execute(
            'UPDATE scheduled_tasks SET updated_at = ? WHERE id = ?',
            ('2026-03-30T09:00:00', 'sched-1'),
        )
        conn.commit()
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

    def test_accept_scheduled_remote_change_applies_remote_record(self):
        manager = self._build_manager(remote_config={})
        manager.create_scheduled_task({
            'id': 'sched-1',
            'title': '本地版本',
            'frequency': 'daily',
            'notes': '保留本地',
        })
        conn = manager.get_connection()
        conn.execute(
            'UPDATE scheduled_tasks SET updated_at = ? WHERE id = ?',
            ('2026-03-30T09:00:00', 'sched-1'),
        )
        conn.commit()
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
        self.assertNotIn('scheduled:sched-1', manager._pending_remote_task_changes)

    def test_reject_scheduled_remote_change_keeps_local_and_pushes_back_to_server(self):
        manager = self._build_manager(remote_config={})
        manager.create_scheduled_task({
            'id': 'sched-1',
            'title': '本地版本',
            'frequency': 'daily',
            'notes': '保留本地',
        })
        conn = manager.get_connection()
        conn.execute(
            'UPDATE scheduled_tasks SET updated_at = ? WHERE id = ?',
            ('2026-03-30T09:00:00', 'sched-1'),
        )
        conn.commit()
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

    def test_update_scheduled_task_keeps_local_write_when_remote_push_fails(self):
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
        request_mock.assert_called_once()
        self.assertEqual(request_mock.call_args.args[:2], ('POST', '/api/scheduled_tasks'))

    def test_delete_scheduled_task_keeps_local_delete_when_remote_push_fails(self):
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
        request_mock.assert_called_once_with('DELETE', '/api/scheduled_tasks/sched-1')



if __name__ == "__main__":
    unittest.main()
