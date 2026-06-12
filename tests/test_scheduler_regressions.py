"""定时任务回归测试：时区时间、到期偏移、编辑回填、数据库迁移、配置字段合并、空固定到期日"""

import json
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from core.scheduler import (
    AddScheduleDialog,
    ScheduledTaskDialog,
    TaskScheduler,
    to_naive_local,
)
from config import config_manager
from database.database_manager import DatabaseManager


WORKSPACE_TMP_ROOT = os.path.join(os.getcwd(), ".tmp-tests")
os.makedirs(WORKSPACE_TMP_ROOT, exist_ok=True)


class ToNaiveLocalTests(unittest.TestCase):
    """时区时间：带时区的时间应统一转换为无时区本地时间"""

    def test_aware_datetime_becomes_naive_local(self):
        aware = datetime(2026, 6, 1, 8, 0, tzinfo=timezone(timedelta(hours=8)))
        result = to_naive_local(aware)
        self.assertIsNone(result.tzinfo, "转换结果应不带时区信息")
        self.assertEqual(
            result,
            aware.astimezone().replace(tzinfo=None),
            "应转换到本地时间后再去掉时区",
        )

    def test_naive_datetime_passes_through(self):
        naive = datetime(2026, 6, 1, 8, 0)
        self.assertIs(to_naive_local(naive), naive)

    def test_none_passes_through(self):
        self.assertIsNone(to_naive_local(None))

    def test_calculate_next_run_time_with_aware_base_is_comparable_to_now(self):
        """回归：带时区 created_at 的定时任务编辑频率时与 datetime.now() 比较抛 TypeError"""
        aware_base = datetime(2026, 1, 1, 9, 30, tzinfo=timezone.utc)
        for frequency in ("daily", "weekly", "monthly", "quarterly", "yearly"):
            next_run = TaskScheduler.calculate_next_run_time(
                frequency=frequency,
                base_time=aware_base,
                created_time=aware_base,
            )
            self.assertIsNone(
                next_run.tzinfo,
                f"{frequency}: 计算结果应为无时区时间",
            )
            # 不应抛出 TypeError: can't compare offset-naive and offset-aware datetimes
            self.assertIsInstance(next_run <= datetime.now(), bool)

    def test_resolve_edit_base_time_normalizes_aware_created_at(self):
        record = {"created_at": "2026-01-01T09:30:00+08:00"}
        base_time, changed = ScheduledTaskDialog._resolve_edit_base_time(record, "")
        self.assertFalse(changed)
        self.assertIsNone(base_time.tzinfo, "编辑基准时间应为无时区本地时间")


class DueOffsetTests(unittest.TestCase):
    """到期偏移：触发后 N 天到期的推算与规范化"""

    def test_offset_days_added_to_trigger_time(self):
        trigger = datetime(2026, 6, 12, 10, 0)
        schedule = {"due_offset_days": 3, "due_date": "2020-01-01"}
        self.assertEqual(
            TaskScheduler._resolve_spawned_due_date(schedule, trigger),
            "2026-06-15",
            "配置了偏移时应使用 触发时间 + N 天",
        )

    def test_offset_zero_means_due_on_trigger_day(self):
        trigger = datetime(2026, 6, 12, 10, 0)
        schedule = {"due_offset_days": 0, "due_date": ""}
        self.assertEqual(
            TaskScheduler._resolve_spawned_due_date(schedule, trigger), "2026-06-12"
        )

    def test_missing_offset_falls_back_to_fixed_due_date(self):
        trigger = datetime(2026, 6, 12, 10, 0)
        for missing in (None, ""):
            schedule = {"due_offset_days": missing, "due_date": "2026-07-01"}
            self.assertEqual(
                TaskScheduler._resolve_spawned_due_date(schedule, trigger),
                "2026-07-01",
                "未配置偏移时应回退到固定到期日期",
            )

    def test_invalid_offset_falls_back_to_fixed_due_date(self):
        trigger = datetime(2026, 6, 12, 10, 0)
        schedule = {"due_offset_days": "abc", "due_date": "2026-07-01"}
        self.assertEqual(
            TaskScheduler._resolve_spawned_due_date(schedule, trigger), "2026-07-01"
        )

    def test_normalize_offset_days(self):
        normalize = ScheduledTaskDialog._normalize_offset_days
        self.assertIsNone(normalize(None))
        self.assertIsNone(normalize(""))
        self.assertIsNone(normalize("abc"))
        self.assertEqual(normalize("3"), 3)
        self.assertEqual(normalize(0), 0)
        self.assertEqual(normalize(-2), 0, "负数应被钳制为 0")


class EditBackfillTests(unittest.TestCase):
    """编辑回填：编辑表单默认值应忠实还原已有记录"""

    def test_unset_offset_backfills_as_empty_not_zero(self):
        meta = {"name": "due_offset_days"}
        for missing in (None, ""):
            record = {"due_offset_days": missing}
            self.assertEqual(
                ScheduledTaskDialog._extract_field_default(meta, record),
                "",
                "未配置偏移应回填为空（显示'未设置'），而不是 0",
            )

    def test_zero_offset_backfills_as_zero(self):
        meta = {"name": "due_offset_days"}
        self.assertEqual(
            ScheduledTaskDialog._extract_field_default(meta, {"due_offset_days": 0}), 0
        )

    def test_start_time_backfills_date_part_of_created_at(self):
        meta = {"name": "start_time"}
        record = {"created_at": "2026-03-05T14:30:00"}
        self.assertEqual(
            ScheduledTaskDialog._extract_field_default(meta, record), "2026-03-05"
        )

    def test_unchanged_start_date_keeps_original_timestamp(self):
        record = {"created_at": "2026-03-05T14:30:00"}
        base_time, changed = ScheduledTaskDialog._resolve_edit_base_time(
            record, "2026-03-05"
        )
        self.assertFalse(changed, "开始日期未变时应视为未修改")
        self.assertEqual(
            base_time,
            datetime(2026, 3, 5, 14, 30),
            "应沿用原始完整时间戳，避免丢失时分秒",
        )

    def test_changed_start_date_marks_modified(self):
        record = {"created_at": "2026-03-05T14:30:00"}
        base_time, changed = ScheduledTaskDialog._resolve_edit_base_time(
            record, "2026-04-01"
        )
        self.assertTrue(changed)
        self.assertEqual(base_time, datetime(2026, 4, 1))


class ScheduledTaskMigrationTests(unittest.TestCase):
    """数据库迁移：scheduled_tasks 升级路径"""

    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(dir=WORKSPACE_TMP_ROOT, suffix=".db")
        os.close(fd)
        os.remove(self.db_path)
        self.addCleanup(self._cleanup_db_file)

    def _cleanup_db_file(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def _create_legacy_db(self, with_offset_column=False, rows=()):
        """构造旧版 scheduled_tasks 表（缺少 deleted / due_offset_days 列）"""
        offset_col = "due_offset_days INTEGER," if with_offset_column else ""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            f'''
            CREATE TABLE scheduled_tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                priority TEXT,
                urgency TEXT DEFAULT '低',
                importance TEXT DEFAULT '低',
                notes TEXT,
                due_date TEXT,
                {offset_col}
                frequency TEXT NOT NULL,
                week_day INTEGER,
                month_day INTEGER,
                quarter_day INTEGER,
                year_month INTEGER,
                year_day INTEGER,
                next_run_at TIMESTAMP,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            '''
        )
        for row in rows:
            columns = ", ".join(row)
            placeholders = ", ".join("?" for _ in row)
            conn.execute(
                f"INSERT INTO scheduled_tasks ({columns}) VALUES ({placeholders})",
                tuple(row.values()),
            )
        conn.commit()
        conn.close()

    def _build_manager(self):
        manager = DatabaseManager(
            db_path=self.db_path, remote_config={}, sync_interval=0, flush_interval=0
        )
        self.addCleanup(manager.close_connection)
        return manager

    def _query(self, sql, params=()):
        conn = sqlite3.connect(self.db_path)
        try:
            return conn.execute(sql, params).fetchall()
        finally:
            conn.close()

    def test_migration_adds_missing_columns_with_null_offset(self):
        self._create_legacy_db(
            rows=[{"id": "s1", "title": "旧任务", "frequency": "monthly",
                   "due_date": "2026-07-01"}]
        )
        manager = self._build_manager()
        manager.close_connection()

        columns = [r[1] for r in self._query("PRAGMA table_info(scheduled_tasks)")]
        self.assertIn("due_offset_days", columns)
        self.assertIn("deleted", columns)
        rows = self._query(
            "SELECT due_offset_days FROM scheduled_tasks WHERE id = 's1'"
        )
        self.assertIsNone(
            rows[0][0], "旧记录的偏移应为 NULL（未配置），回退用固定到期日期"
        )

    def test_migration_resets_zero_offset_with_fixed_due_date(self):
        """回归：早期迁移把旧记录偏移回填为 0，固定到期日期被解释为'触发当天到期'"""
        self._create_legacy_db(
            with_offset_column=True,
            rows=[
                {"id": "bad", "title": "被错误回填", "frequency": "monthly",
                 "due_date": "2026-07-01", "due_offset_days": 0},
                {"id": "ok", "title": "真实偏移0", "frequency": "monthly",
                 "due_date": "", "due_offset_days": 0},
            ],
        )
        manager = self._build_manager()
        manager.close_connection()

        rows = dict(
            self._query("SELECT id, due_offset_days FROM scheduled_tasks")
        )
        self.assertIsNone(rows["bad"], "偏移 0 且有固定到期日期的记录应被还原为 NULL")
        self.assertEqual(rows["ok"], 0, "真实配置为偏移 0 天的记录应保持不变")
        version = self._query("PRAGMA user_version")[0][0]
        self.assertGreaterEqual(version, 1, "一次性修复后应推进 schema 版本")


class ConfigFieldMergeTests(unittest.TestCase):
    """配置字段合并：补齐升级新增字段，但不得改写用户自定义表单"""

    def setUp(self):
        fd, self.config_path = tempfile.mkstemp(
            dir=WORKSPACE_TMP_ROOT, suffix=".json"
        )
        os.close(fd)
        self.addCleanup(self._cleanup)

    def _cleanup(self):
        if os.path.exists(self.config_path):
            os.remove(self.config_path)

    def _load_with_user_config(self, user_config):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(user_config, f, ensure_ascii=False)
        with patch.object(config_manager, "CONFIG_FILE", self.config_path):
            return config_manager.load_config()

    def test_removed_task_field_is_not_reinserted(self):
        """回归：用户已从 task_fields 移除的 priority 字段被合并重新插回"""
        user_config = {
            "task_fields": [
                {"name": "text", "label": "任务内容", "type": "text", "required": True},
                {"name": "notes", "label": "备注", "type": "text", "required": False},
            ]
        }
        merged = self._load_with_user_config(user_config)
        names = [f["name"] for f in merged["task_fields"]]
        self.assertNotIn("priority", names, "用户移除的字段不应被默认配置补回")
        self.assertNotIn("due_date", names, "task_fields 应完全尊重用户配置")
        self.assertEqual(names, ["text", "notes"], "字段顺序应保持用户配置")

    def test_schedule_fields_backfill_new_default_fields(self):
        """旧版 schedule_task_fields 应补齐升级新增的 due_offset_days"""
        user_config = {
            "schedule_task_fields": [
                {"name": "title", "label": "任务标题", "type": "text", "required": True},
                {"name": "frequency", "label": "频率", "type": "select",
                 "options": ["daily"], "default": "daily", "required": True},
            ]
        }
        merged = self._load_with_user_config(user_config)
        names = [f["name"] for f in merged["schedule_task_fields"]]
        self.assertIn("due_offset_days", names, "升级新增字段应被补齐")
        self.assertEqual(names[0], "title", "用户已有字段顺序应保留")

    def test_missing_field_lists_fall_back_to_defaults(self):
        merged = self._load_with_user_config({})
        self.assertEqual(
            merged["task_fields"], config_manager.DEFAULT_CONFIG["task_fields"]
        )
        self.assertEqual(
            merged["schedule_task_fields"],
            config_manager.DEFAULT_CONFIG["schedule_task_fields"],
        )


class EmptyDueDateDialogTests(unittest.TestCase):
    """空固定到期日：日期控件应能表达并保持空值"""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _make_dialog(self, default_value):
        fields = [
            {"name": "due_date", "label": "到期日期", "type": "date",
             "required": False, "default": default_value},
        ]
        return AddScheduleDialog(None, fields)

    def test_empty_due_date_stays_empty(self):
        """回归：编辑无固定到期日的旧任务时，日期被静默改成当天"""
        dialog = self._make_dialog("")
        data = dialog.get_data()
        self.assertEqual(
            data["due_date"], "",
            "默认值为空时控件应保持未选择状态，而不是当天日期",
        )
        today = datetime.now().strftime("%Y-%m-%d")
        self.assertNotEqual(data["due_date"], today)

    def test_existing_due_date_is_backfilled(self):
        dialog = self._make_dialog("2026-07-01")
        self.assertEqual(dialog.get_data()["due_date"], "2026-07-01")

    def test_invalid_default_treated_as_empty(self):
        dialog = self._make_dialog("not-a-date")
        self.assertEqual(dialog.get_data()["due_date"], "")


if __name__ == "__main__":
    unittest.main()
