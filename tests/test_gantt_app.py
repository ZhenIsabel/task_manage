"""甘特图 Flask 服务：日期解析与 /tasks 路由映射规则"""

import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from gantt import app as gantt_module
from gantt.app import gantt_app, parse_date


class ParseDateTests(unittest.TestCase):
    def test_supported_formats_normalize_to_iso(self):
        for raw in ("2025-10-01", "2025/10/01", "2025-10-01 12:00:00", "2025/10/01 12:00:00"):
            with self.subTest(raw=raw):
                self.assertEqual(parse_date(raw), "2025-10-01")

    def test_empty_and_invalid_values_return_none(self):
        for raw in (None, "", "10/01/2025", "明天", "2025-13-40"):
            with self.subTest(raw=raw):
                self.assertIsNone(parse_date(raw))


class TasksRouteTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.addCleanup(self._cleanup)
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            CREATE TABLE tasks (
                id TEXT PRIMARY KEY,
                text TEXT,
                notes TEXT,
                create_date TEXT,
                due_date TEXT,
                completed INTEGER,
                deleted INTEGER,
                color TEXT
            )
            """
        )
        conn.commit()
        conn.close()
        patcher = patch.object(gantt_module, "DB_PATH", self.db_path)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = gantt_app.test_client()

    def _cleanup(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def _insert(self, **kw):
        row = {
            "id": "t1", "text": "任务", "notes": "", "create_date": "2026-06-01",
            "due_date": "2026-06-10", "completed": 0, "deleted": 0, "color": "#FF0000",
        }
        row.update(kw)
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO tasks (id, text, notes, create_date, due_date, completed, deleted, color)"
            " VALUES (:id, :text, :notes, :create_date, :due_date, :completed, :deleted, :color)",
            row,
        )
        conn.commit()
        conn.close()

    def test_maps_task_row_to_frappe_gantt_shape(self):
        self._insert()
        payload = self.client.get("/tasks").get_json()
        self.assertEqual(len(payload), 1)
        task = payload[0]
        self.assertEqual(task["id"], "t1")
        self.assertEqual(task["name"], "任务")
        self.assertEqual(task["start"], "2026-06-01")
        self.assertEqual(task["end"], "2026-06-10")
        self.assertEqual(task["progress"], 0)
        self.assertEqual(task["color"], "#FF0000")

    def test_deleted_and_completed_tasks_are_excluded(self):
        self._insert(id="gone", deleted=1)
        self._insert(id="done", completed=1)
        self._insert(id="kept")
        payload = self.client.get("/tasks").get_json()
        self.assertEqual([t["id"] for t in payload], ["kept"])

    def test_missing_due_date_defaults_to_start_plus_three_days(self):
        self._insert(id="no-due", create_date="2026-06-01", due_date=None)
        payload = self.client.get("/tasks").get_json()
        self.assertEqual(payload[0]["end"], "2026-06-04")

    def test_missing_create_date_defaults_to_today(self):
        self._insert(id="no-start", create_date=None, due_date=None)
        payload = self.client.get("/tasks").get_json()
        today = datetime.today().strftime("%Y-%m-%d")
        self.assertEqual(payload[0]["start"], today)
        self.assertEqual(
            payload[0]["end"],
            (datetime.today() + timedelta(days=3)).strftime("%Y-%m-%d"),
        )

    def test_blank_text_and_color_fall_back(self):
        self._insert(id="fallback", text=None, color=None)
        payload = self.client.get("/tasks").get_json()
        self.assertEqual(payload[0]["name"], "fallback")
        self.assertEqual(payload[0]["color"], "#4ECDC4")


if __name__ == "__main__":
    unittest.main()
