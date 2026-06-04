import os
import unittest
from pathlib import Path
from unittest.mock import patch

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QLineEdit, QTableWidget, QVBoxLayout, QWidget

from core.complete_table import CompleteTableDialog
from core.history_viewer import HistoryViewer
from ui.adaptive_table import AdaptiveTextTableWidget, compute_multiline_item_size_hint


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


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
        class FakeDbManager:
            def load_tasks(self, all_tasks=False):
                return [
                    {
                        "id": "task-1",
                        "text": "任务A",
                        "completed": True,
                        "completed_date": "2026-04-04",
                        "priority": "高",
                        "notes": "第一行\n第二行",
                    }
                ]

        with patch("core.complete_table.get_db_manager", return_value=FakeDbManager()):
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
        class FakeDbManager:
            def load_tasks(self, all_tasks=False):
                return [
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

        with patch("core.complete_table.get_db_manager", return_value=FakeDbManager()):
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
        class FakeDbManager:
            def load_tasks(self, all_tasks=False):
                return [
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

        with patch("core.complete_table.get_db_manager", return_value=FakeDbManager()):
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

if __name__ == "__main__":
    unittest.main()
