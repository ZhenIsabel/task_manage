import os
import tempfile
import unittest
import types
from unittest.mock import patch

from database.database_manager import DatabaseManager


WORKSPACE_TMP_ROOT = os.path.join(os.getcwd(), ".tmp-tests")
os.makedirs(WORKSPACE_TMP_ROOT, exist_ok=True)


class DatabaseManagerHistorySyncTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(dir=WORKSPACE_TMP_ROOT, suffix=".db")
        os.close(fd)
        os.remove(self.db_path)
        self.addCleanup(self._cleanup_db_file)

    def _cleanup_db_file(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def _build_manager(self, remote_config=None):
        manager = DatabaseManager(
            db_path=self.db_path,
            remote_config=remote_config or {},
            sync_interval=0,
            flush_interval=0,
        )
        self.addCleanup(manager.close_connection)
        return manager

    def _config_module_stub(self):
        return types.SimpleNamespace(
            load_config=lambda: {
                'task_fields': [
                    {'name': 'text'},
                    {'name': 'due_date'},
                    {'name': 'priority'},
                    {'name': 'notes'},
                    {'name': 'urgency'},
                    {'name': 'importance'},
                    {'name': 'directory'},
                    {'name': 'create_date'},
                ]
            }
        )

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
            'history': {
                'text': [{'value': '远端任务', 'timestamp': '2026-03-30T10:00:00', 'action': 'update'}]
            }
        }) as request_mock:
            history = manager.get_task_history('task-1')

        self.assertEqual(history['text'][0]['value'], '本地任务')
        request_mock.assert_not_called()

    def test_accept_task_remote_change_merges_remote_history_into_local(self):
        manager = self._build_manager(remote_config={})
        manager.api_base_url = 'http://example.com'
        manager.api_token = 'token'
        task_payload = {
            'id': 'task-1',
            'text': '本地版本',
            'notes': '本地备注',
            'completed': False,
            'completed_date': '',
            'deleted': False,
            'priority': '中',
            'urgency': '低',
            'importance': '高',
            'directory': '',
            'create_date': '2026-03-30',
            'position': {'x': 120, 'y': 180},
            'updated_at': '2026-03-30T09:00:00',
            'created_at': '2026-03-30T08:00:00',
        }
        with patch.dict('sys.modules', {'config.config_manager': self._config_module_stub()}):
            manager._save_task_to_cache(task_payload, 'modified')
        manager.flush_cache_to_db()
        manager.get_connection().execute(
            'INSERT OR IGNORE INTO task_history (task_id, field_name, field_value, action, timestamp) VALUES (?, ?, ?, ?, ?)',
            ('task-1', 'text', '本地版本', 'update', '2026-03-30T09:00:00'),
        )
        manager.get_connection().commit()
        with patch.dict('sys.modules', {'config.config_manager': self._config_module_stub()}):
            manager._save_task_to_cache(
                task_payload,
                sync_status='synced',
            )
        manager._pending_remote_task_changes['task:task-1'] = {
            'change_key': 'task:task-1',
            'entity_type': 'task',
            'entity_id': 'task-1',
            'title': '任务 task-1',
            'change_type': 'update',
            'local_record': {
                'id': 'task-1',
                'text': '本地版本',
                'notes': '本地备注',
                'completed': False,
                'completed_date': '',
                'deleted': False,
                'priority': '中',
                'urgency': '低',
                'importance': '高',
                'directory': '',
                'create_date': '2026-03-30',
                'position': {'x': 120, 'y': 180},
                'updated_at': '2026-03-30T09:00:00',
                'created_at': '2026-03-30T08:00:00',
            },
            'remote_record': {
                'id': 'task-1',
                'text': '远端版本',
                'notes': '远端备注',
                'completed': False,
                'completed_date': '',
                'deleted': False,
                'priority': '高',
                'urgency': '高',
                'importance': '高',
                'directory': '',
                'create_date': '2026-03-31',
                'position': {'x': 160, 'y': 220},
                'updated_at': '2026-03-30T10:00:00',
                'created_at': '2026-03-30T08:00:00',
            },
        }

        def fake_api_request(method, path, payload=None, retry_on_auth_failure=True):
            if method == 'GET' and path == '/api/tasks/task-1/history':
                return {
                    'history': {
                        'text': [
                            {'value': '远端版本', 'timestamp': '2026-03-30T10:00:00', 'action': 'update'}
                        ]
                    }
                }
            raise AssertionError(f'unexpected request: {method} {path}')

        with patch.object(manager, '_make_api_request', side_effect=fake_api_request):
            result = manager.resolve_pending_remote_task_changes(['task:task-1'], [])

        self.assertTrue(result)
        history = manager.get_task_history('task-1')
        self.assertEqual(
            [item['timestamp'] for item in history['text']],
            ['2026-03-30T09:00:00', '2026-03-30T10:00:00'],
        )

    def test_sync_to_server_includes_local_history_in_task_payload(self):
        manager = self._build_manager(remote_config={})
        with patch.dict('sys.modules', {'config.config_manager': self._config_module_stub()}):
            manager._save_task_to_cache({
                'id': 'task-1',
                'text': '本地版本',
                'notes': '本地备注',
                'completed': False,
                'completed_date': '',
                'deleted': False,
                'priority': '中',
                'urgency': '低',
                'importance': '高',
                'directory': '',
                'create_date': '2026-03-30',
                'position': {'x': 120, 'y': 180},
                'updated_at': '2026-03-30T09:00:00',
                'created_at': '2026-03-30T08:00:00',
            }, 'modified')
        manager.flush_cache_to_db()
        manager.get_connection().execute(
            'INSERT OR IGNORE INTO task_history (task_id, field_name, field_value, action, timestamp) VALUES (?, ?, ?, ?, ?)',
            ('task-1', 'text', '本地版本', 'update', '2026-03-30T09:00:00'),
        )
        manager.get_connection().commit()
        manager.api_base_url = 'http://example.com'
        manager.api_token = 'token'

        with patch.object(manager, '_make_api_request', return_value={'success': True}) as request_mock:
            result = manager.sync_to_server()

        self.assertTrue(result)
        self.assertEqual(request_mock.call_args.args[:2], ('POST', '/api/tasks'))
        self.assertEqual(
            request_mock.call_args.args[2]['history']['text'][0]['timestamp'],
            '2026-03-30T09:00:00',
        )
