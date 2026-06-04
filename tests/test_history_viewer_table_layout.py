import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class _Win32Stub(types.ModuleType):
    def __getattr__(self, name):
        return 0


for _module_name in ("win32api", "win32con", "win32gui", "win32print"):
    sys.modules.setdefault(_module_name, _Win32Stub(_module_name))

_shellcon = _Win32Stub("shellcon")
_shell_module = types.ModuleType("win32comext.shell")
_shell_module.shellcon = _shellcon
sys.modules.setdefault("win32comext", types.ModuleType("win32comext"))
sys.modules.setdefault("win32comext.shell", _shell_module)

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QLineEdit, QTableWidget, QVBoxLayout, QWidget

from core.complete_table import CompleteTableDialog
from core.history_viewer import HistoryViewer
from ui.adaptive_table import AdaptiveTextTableWidget, compute_multiline_item_size_hint


class FakeCompletedTasksDbManager:
    def __init__(self, tasks):
        self.tasks = list(tasks)
        self.page_calls = []
        self.count_calls = []
        self.id_calls = []

    def load_tasks(self, all_tasks=False):
        raise AssertionError("已完成任务弹窗不应再通过 load_tasks(all_tasks=True) 全量加载")

    def _filtered_tasks(self, search_query=""):
        keywords = [keyword.casefold() for keyword in str(search_query or "").split() if keyword]
        if not keywords:
            return list(self.tasks)
        return [
            task
            for task in self.tasks
            if all(keyword in task.get("text", "").casefold() for keyword in keywords)
        ]

    def load_completed_tasks_page(self, limit=100, offset=0, search_query=""):
        self.page_calls.append(
            {"limit": limit, "offset": offset, "search_query": search_query}
        )
        return self._filtered_tasks(search_query)[offset:offset + limit]

    def count_completed_tasks(self, search_query=""):
        self.count_calls.append(search_query)
        return len(self._filtered_tasks(search_query))

    def load_completed_task_ids(self, search_query=""):
        self.id_calls.append(search_query)
        return [task["id"] for task in self._filtered_tasks(search_query)]


class FakeHistoryDbManager:
    def __init__(self, records):
        self.records = list(records)
        self.page_calls = []
        self.full_history_calls = []

    def count_task_history(self, task_id):
        return len([record for record in self.records if record["task_id"] == task_id])

    def get_task_history_page(self, task_id, limit=100, offset=0):
        self.page_calls.append({"task_id": task_id, "limit": limit, "offset": offset})
        selected = [
            record
            for record in self.records
            if record["task_id"] == task_id
        ][offset:offset + limit]
        grouped = {}
        for record in selected:
            grouped.setdefault(record["field_name"], []).append(
                {
                    "timestamp": record["timestamp"],
                    "action": record["action"],
                    "value": record["value"],
                }
            )
        return grouped

    def get_task_history(self, task_id):
        self.full_history_calls.append(task_id)
        grouped = {}
        for record in self.records:
            if record["task_id"] != task_id:
                continue
            grouped.setdefault(record["field_name"], []).append(
                {
                    "timestamp": record["timestamp"],
                    "action": record["action"],
                    "value": record["value"],
                }
            )
        return grouped


class FakeCompletedTasksStaleCountDbManager:
    def __init__(self):
        self.page_calls = []
        self.id_calls = []

    def count_completed_tasks(self, search_query=""):
        return 3

    def load_completed_tasks_page(self, limit=100, offset=0, search_query=""):
        self.page_calls.append({"limit": limit, "offset": offset, "search_query": search_query})
        if offset == 0:
            return [
                {"id": "task-1", "text": "任务一", "completed_date": "2026-04-04", "notes": ""},
                {"id": "task-2", "text": "任务二", "completed_date": "2026-04-03", "notes": ""},
            ][:limit]
        return []

    def load_completed_task_ids(self, search_query=""):
        self.id_calls.append(search_query)
        return ["task-1", "task-2"]


class FakeHistoryStaleCountDbManager:
    def __init__(self):
        self.page_calls = []

    def count_task_history(self, task_id):
        return 3

    def get_task_history_page(self, task_id, limit=100, offset=0):
        self.page_calls.append({"task_id": task_id, "limit": limit, "offset": offset})
        if offset == 0:
            return {
                "text": [
                    {"timestamp": "2026-04-04T09:00:00", "action": "update", "value": "记录一"},
                    {"timestamp": "2026-04-03T09:00:00", "action": "update", "value": "记录二"},
                ][:limit]
            }
        return {}

    def get_task_history(self, task_id):
        return {}


class HistoryViewerTableLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _read(self, rel_path: str) -> str:
        repo_root = Path(__file__).resolve().parents[1]
        return (repo_root / rel_path).read_text(encoding="utf-8")

    def _wait_until(self, predicate, timeout_ms=1000, interval_ms=25):
        elapsed = 0
        while elapsed < timeout_ms:
            if predicate():
                return True
            QTest.qWait(interval_ms)
            QApplication.processEvents()
            elapsed += interval_ms
        return predicate()

    def test_history_viewer_should_build_table_through_adaptive_widget(self):
        source = self._read("core/history_viewer.py")

        self.assertIn(
            "AdaptiveTextTableWidget(",
            source,
            "历史记录弹窗应通过 ui 层的通用自适应表格组件创建表格",
        )

    def test_history_viewer_should_render_merged_history_rows_without_tuple_index_errors(self):
        viewer = HistoryViewer.__new__(HistoryViewer)
        host = QWidget()
        layout = QVBoxLayout(host)

        viewer.create_merged_history_table(
            layout,
            [
                {
                    "field": "备注",
                    "timestamp": "2026-04-04T01:37:41",
                    "action": "update",
                    "value": "第一行\n第二行",
                }
            ],
        )

        table = layout.itemAt(0).widget()
        self.assertIsInstance(table, AdaptiveTextTableWidget)
        self.assertEqual(table.rowCount(), 1)
        self.assertEqual(table.item(0, 1).text(), "备注")

    def test_scheduler_should_build_table_through_adaptive_widget(self):
        source = self._read("core/scheduler.py")
        self.assertIn(
            "AdaptiveTextTableWidget(",
            source,
            "定时任务表格应切换为 ui 层的通用自适应表格组件",
        )

    def test_complete_table_should_build_table_through_adaptive_widget(self):
        source = self._read("core/complete_table.py")
        self.assertIn(
            "AdaptiveTextTableWidget(",
            source,
            "已完成任务表格应切换为 ui 层的通用自适应表格组件",
        )
        self.assertIn(
            "rows = [",
            source,
            "已完成任务表格应先整理二维数据再创建通用表格组件",
        )
        self.assertIn(
            "rows=rows",
            source,
            "已完成任务表格应在创建通用表格组件时直接传入二维数据",
        )
        self.assertNotIn(
            "text_item = QTableWidgetItem(task.get('text', ''))",
            source,
            "已完成任务表格不应再逐个为任务内容创建 QTableWidgetItem",
        )
        self.assertNotIn(
            "notes_item = QTableWidgetItem(notes)",
            source,
            "已完成任务表格不应再逐个为备注创建 QTableWidgetItem",
        )

    def test_ui_package_should_export_adaptive_table_widget(self):
        exports = self._read("ui/__init__.py")
        self.assertIn(
            "AdaptiveTextTableWidget",
            exports,
            "ui 包应导出通用自适应表格组件，方便 core 层复用",
        )

    def test_compute_multiline_item_size_hint_should_expand_for_manual_line_breaks(self):
        table = QTableWidget()
        width = 300
        text = "第一行\n第二行\n第三行\n第四行"
        font_metrics = QFontMetrics(table.font())

        size_hint = compute_multiline_item_size_hint(font_metrics, text, width)
        expected_text_height = font_metrics.boundingRect(
            0,
            0,
            width - 16,
            10000,
            int(Qt.TextFlag.TextWordWrap),
            text,
        ).height()

        self.assertGreater(
            size_hint.height(),
            font_metrics.height() * 2,
            "带显式换行的文本应得到明显高于单行的 size hint",
        )
        self.assertGreaterEqual(
            size_hint.height(),
            expected_text_height + 16,
            "size hint 应至少覆盖换行文本的实际绘制高度和单元格内边距",
        )

    def test_adaptive_table_widget_should_apply_multiline_size_hints(self):
        table = AdaptiveTextTableWidget(
            headers=["值"],
            rows=[["第一行\n第二行\n第三行\n第四行"]],
            fixed_width_columns={0: 300},
            multiline_columns={0},
        )

        self.assertGreater(
            table.item(0, 0).sizeHint().height(),
            30,
            "通用表格组件应给多行列应用明显高于单行的 size hint",
        )

    def test_complete_table_should_reuse_same_table_instance_when_reloading(self):
        fake_db = FakeCompletedTasksDbManager(
            [
                {
                    "id": "task-1",
                    "text": "任务A",
                    "completed": True,
                    "completed_date": "2026-04-04",
                    "priority": "高",
                    "notes": "第一行\n第二行",
                }
            ]
        )

        with patch("core.complete_table.get_db_manager", return_value=fake_db):
            dialog = CompleteTableDialog()
            first_table = dialog.table

            dialog._load_completed_tasks()

            self.assertIs(
                dialog.table,
                first_table,
                "刷新已完成任务时应复用同一个表格实例，避免出现重复表头",
            )
            self.assertEqual(
                len(dialog.panel.findChildren(AdaptiveTextTableWidget)),
                1,
                "面板内应始终只有一张已完成任务表格",
            )

    def test_complete_table_should_filter_completed_tasks_by_space_separated_title_keywords(self):
        fake_db = FakeCompletedTasksDbManager(
            [
                {
                    "id": "task-1",
                    "text": "季度报告归档",
                    "completed": True,
                    "completed_date": "2026-04-04",
                    "notes": "",
                },
                {
                    "id": "task-2",
                    "text": "季度会议纪要",
                    "completed": True,
                    "completed_date": "2026-04-03",
                    "notes": "",
                },
                {
                    "id": "task-3",
                    "text": "年度报告校对",
                    "completed": True,
                    "completed_date": "2026-04-02",
                    "notes": "",
                },
            ]
        )

        with patch("core.complete_table.get_db_manager", return_value=fake_db):
            dialog = CompleteTableDialog()
            search_input = dialog.findChild(QLineEdit, "completed_task_search_input")

            self.assertIsNotNone(search_input, "已完成任务页面上方应提供标题搜索框")

            search_input.setText("季度 报告")

            self.assertTrue(
                self._wait_until(lambda: dialog.table.rowCount() == 1),
                "搜索防抖延迟结束后应刷新出匹配结果",
            )
            visible_titles = [
                dialog.table.item(row, 1).text()
                for row in range(dialog.table.rowCount())
            ]

            self.assertEqual(visible_titles, ["季度报告归档"])

    def test_complete_table_search_should_wait_before_filtering_while_input_changes(self):
        fake_db = FakeCompletedTasksDbManager(
            [
                {
                    "id": "task-1",
                    "text": "季度报告归档",
                    "completed": True,
                    "completed_date": "2026-04-04",
                    "notes": "",
                },
                {
                    "id": "task-2",
                    "text": "年度复盘",
                    "completed": True,
                    "completed_date": "2026-04-03",
                    "notes": "",
                },
            ]
        )

        with patch("core.complete_table.get_db_manager", return_value=fake_db):
            dialog = CompleteTableDialog()
            search_input = dialog.findChild(QLineEdit, "completed_task_search_input")

            search_input.setText("季度")
            QApplication.processEvents()

            self.assertEqual(
                dialog.table.rowCount(),
                2,
                "搜索框内容变化后不应立即刷新表格，应等待防抖延迟",
            )

            search_input.setText("年度")
            QTest.qWait(250)
            QApplication.processEvents()

            self.assertEqual(
                dialog.table.rowCount(),
                2,
                "搜索框仍在变化时不应触发上一次搜索",
            )

            QTest.qWait(550)
            QApplication.processEvents()

            visible_titles = [
                dialog.table.item(row, 1).text()
                for row in range(dialog.table.rowCount())
            ]
            self.assertEqual(visible_titles, ["年度复盘"])

    def test_complete_table_should_append_next_page_when_loading_more(self):
        fake_db = FakeCompletedTasksDbManager(
            [
                {"id": "task-1", "text": "任务一", "completed_date": "2026-04-04", "notes": ""},
                {"id": "task-2", "text": "任务二", "completed_date": "2026-04-03", "notes": ""},
                {"id": "task-3", "text": "任务三", "completed_date": "2026-04-02", "notes": ""},
            ]
        )

        with patch("core.complete_table.get_db_manager", return_value=fake_db):
            dialog = CompleteTableDialog()
            dialog.page_size = 2
            dialog._load_completed_tasks()

            self.assertEqual(dialog.table.rowCount(), 2)
            dialog.load_more_button.click()
            QApplication.processEvents()

            self.assertEqual(dialog.table.rowCount(), 3)
            self.assertEqual(
                [dialog.table.item(row, 1).text() for row in range(dialog.table.rowCount())],
                ["任务一", "任务二", "任务三"],
            )
            self.assertFalse(dialog.load_more_button.isEnabled())
            self.assertEqual(dialog.load_more_button.text(), "已全部加载")

    def test_complete_table_select_all_should_select_every_completed_task_not_only_loaded_rows(self):
        fake_db = FakeCompletedTasksDbManager(
            [
                {"id": "task-1", "text": "任务一", "completed_date": "2026-04-04", "notes": ""},
                {"id": "task-2", "text": "任务二", "completed_date": "2026-04-03", "notes": ""},
                {"id": "task-3", "text": "任务三", "completed_date": "2026-04-02", "notes": ""},
            ]
        )

        with patch("core.complete_table.get_db_manager", return_value=fake_db):
            dialog = CompleteTableDialog()
            dialog.page_size = 2
            dialog._load_completed_tasks()

            self.assertEqual(dialog.table.rowCount(), 2)
            dialog.select_all_button.click()
            QApplication.processEvents()

            self.assertEqual(dialog.selected_tasks, {"task-1", "task-2", "task-3"})
            self.assertTrue(dialog.table.cellWidget(0, 0).isChecked())
            self.assertTrue(dialog.table.cellWidget(1, 0).isChecked())
            self.assertEqual(dialog.select_all_button.text(), "取消全选")

    def test_complete_table_select_all_should_clear_when_live_ids_all_selected_despite_stale_count(self):
        fake_db = FakeCompletedTasksStaleCountDbManager()

        with patch("core.complete_table.get_db_manager", return_value=fake_db):
            dialog = CompleteTableDialog()
            dialog.page_size = 2
            dialog._load_completed_tasks()

            dialog.select_all_button.click()
            QApplication.processEvents()

            self.assertEqual(dialog.selected_tasks, {"task-1", "task-2"})
            self.assertEqual(dialog.select_all_button.text(), "取消全选")

            dialog.select_all_button.click()
            QApplication.processEvents()

            self.assertEqual(dialog.selected_tasks, set())
            self.assertFalse(dialog.table.cellWidget(0, 0).isChecked())
            self.assertFalse(dialog.table.cellWidget(1, 0).isChecked())
            self.assertFalse(dialog.restore_button.isEnabled())
            self.assertEqual(dialog.select_all_button.text(), "全选")

    def test_complete_table_select_all_should_use_current_search_query_and_check_loaded_more_rows(self):
        fake_db = FakeCompletedTasksDbManager(
            [
                {"id": "task-1", "text": "季度报告归档", "completed_date": "2026-04-04", "notes": ""},
                {"id": "task-2", "text": "季度会议纪要", "completed_date": "2026-04-03", "notes": ""},
                {"id": "task-3", "text": "季度报告校对", "completed_date": "2026-04-02", "notes": ""},
                {"id": "task-4", "text": "年度报告", "completed_date": "2026-04-01", "notes": ""},
            ]
        )

        with patch("core.complete_table.get_db_manager", return_value=fake_db):
            dialog = CompleteTableDialog()
            dialog.page_size = 1

            search_input = dialog.findChild(QLineEdit, "completed_task_search_input")
            search_input.setText("季度 报告")
            self.assertTrue(
                self._wait_until(
                    lambda: (
                        fake_db.page_calls[-1]["search_query"] == "季度 报告"
                        and dialog.table.rowCount() == 1
                    )
                ),
                "搜索后应先渲染匹配结果第一页",
            )

            dialog.select_all_button.click()
            QApplication.processEvents()

            self.assertEqual(dialog.selected_tasks, {"task-1", "task-3"})
            self.assertEqual(fake_db.id_calls[-1], "季度 报告")

            dialog.load_more_button.click()
            QApplication.processEvents()

            self.assertEqual(dialog.table.rowCount(), 2)
            self.assertEqual(dialog.table.item(1, 1).text(), "季度报告校对")
            self.assertTrue(dialog.table.cellWidget(1, 0).isChecked())

    def test_complete_table_should_disable_sorting_to_keep_checkboxes_aligned_with_rows(self):
        fake_db = FakeCompletedTasksDbManager(
            [
                {"id": "task-1", "text": "任务一", "completed_date": "2026-04-04", "notes": ""},
                {"id": "task-2", "text": "任务二", "completed_date": "2026-04-03", "notes": ""},
            ]
        )

        with patch("core.complete_table.get_db_manager", return_value=fake_db):
            dialog = CompleteTableDialog()

            self.assertFalse(
                dialog.table.isSortingEnabled(),
                "已完成任务表依赖数据库排序，禁用交互排序可避免复选框 task_id 与可见行错位",
            )
            self.assertEqual(dialog.table.item(0, 1).text(), "任务一")
            self.assertEqual(dialog.table.cellWidget(0, 0).property("task_id"), "task-1")

    def test_complete_table_should_disable_load_more_after_stale_count_returns_empty_page(self):
        fake_db = FakeCompletedTasksStaleCountDbManager()

        with patch("core.complete_table.get_db_manager", return_value=fake_db):
            dialog = CompleteTableDialog()
            dialog.page_size = 2
            dialog._load_completed_tasks()

            self.assertTrue(dialog.load_more_button.isEnabled())
            dialog.load_more_button.click()
            QApplication.processEvents()

            self.assertFalse(dialog.load_more_button.isEnabled())
            self.assertEqual(dialog.load_more_button.text(), "已全部加载")
            self.assertEqual(fake_db.page_calls[-1]["offset"], 2)

    def test_complete_table_search_should_reset_paging_to_first_matching_page(self):
        fake_db = FakeCompletedTasksDbManager(
            [
                {"id": "task-1", "text": "季度报告归档", "completed_date": "2026-04-04", "notes": ""},
                {"id": "task-2", "text": "季度会议纪要", "completed_date": "2026-04-03", "notes": ""},
                {"id": "task-3", "text": "年度复盘", "completed_date": "2026-04-02", "notes": ""},
            ]
        )

        with patch("core.complete_table.get_db_manager", return_value=fake_db):
            dialog = CompleteTableDialog()
            dialog.page_size = 1
            dialog._load_completed_tasks()
            dialog.load_more_button.click()
            QApplication.processEvents()

            search_input = dialog.findChild(QLineEdit, "completed_task_search_input")
            search_input.setText("年度")
            self.assertTrue(
                self._wait_until(lambda: dialog.table.item(0, 1).text() == "年度复盘"),
                "搜索后应重置 offset 并只渲染匹配结果第一页",
            )

            self.assertEqual(dialog.table.rowCount(), 1)
            self.assertEqual(fake_db.page_calls[-1]["offset"], 0)
            self.assertEqual(fake_db.page_calls[-1]["search_query"], "年度")

    def test_history_viewer_should_load_first_history_page_and_append_more(self):
        records = [
            {
                "task_id": "task-1",
                "field_name": "text",
                "timestamp": f"2026-04-{day:02d}T09:00:00",
                "action": "update",
                "value": f"记录{day}",
            }
            for day in range(30, 0, -1)
        ]
        fake_db = FakeHistoryDbManager(records)

        with patch("core.history_viewer.get_db_manager", return_value=fake_db):
            viewer = HistoryViewer({"id": "task-1", "text": "测试任务"})
            viewer.page_size = 10
            viewer.load_history_records(viewer.history_container_layout)

            self.assertEqual(viewer.history_table.rowCount(), 10)
            self.assertEqual(viewer.history_table.item(0, 3).text(), "记录30")

            viewer.load_more_button.click()
            QApplication.processEvents()

            self.assertEqual(viewer.history_table.rowCount(), 20)
            self.assertEqual(viewer.history_table.item(19, 3).text(), "记录11")
            self.assertEqual(fake_db.page_calls[-1]["offset"], 10)

    def test_history_viewer_should_disable_load_more_after_stale_count_returns_empty_page(self):
        fake_db = FakeHistoryStaleCountDbManager()

        with patch("core.history_viewer.get_db_manager", return_value=fake_db):
            viewer = HistoryViewer({"id": "task-1", "text": "测试任务"})
            viewer.page_size = 2
            viewer.load_history_records(viewer.history_container_layout)

            self.assertTrue(viewer.load_more_button.isEnabled())
            viewer.load_more_button.click()
            QApplication.processEvents()

            self.assertFalse(viewer.load_more_button.isEnabled())
            self.assertEqual(viewer.load_more_button.text(), "已全部加载")
            self.assertEqual(fake_db.page_calls[-1]["offset"], 2)

    def test_history_viewer_export_should_still_read_full_history(self):
        records = [
            {
                "task_id": "task-1",
                "field_name": "text",
                "timestamp": "2026-04-04T09:00:00",
                "action": "update",
                "value": "分页内记录",
            },
            {
                "task_id": "task-1",
                "field_name": "notes",
                "timestamp": "2026-04-01T09:00:00",
                "action": "update",
                "value": "分页外记录",
            },
        ]
        fake_db = FakeHistoryDbManager(records)

        class FakeDataFrame:
            exported_rows = None

            def __init__(self, rows):
                FakeDataFrame.exported_rows = rows

            def to_excel(self, filename, index=False):
                self.filename = filename

        fake_pandas = type("FakePandas", (), {"DataFrame": FakeDataFrame})

        with patch("core.history_viewer.get_db_manager", return_value=fake_db), \
             patch.dict(sys.modules, {"pandas": fake_pandas}), \
             patch("PyQt6.QtWidgets.QFileDialog.getSaveFileName", return_value=("history.xlsx", "Excel文件 (*.xlsx)")), \
             patch("core.history_viewer.show_success"):
            viewer = HistoryViewer({"id": "task-1", "text": "测试任务"})
            viewer.export_history()

        self.assertEqual(fake_db.full_history_calls, ["task-1"])
        self.assertEqual(len(FakeDataFrame.exported_rows), 2)

if __name__ == "__main__":
    unittest.main()
