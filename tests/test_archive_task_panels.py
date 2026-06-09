import os
import sys
import types
import unittest
from unittest.mock import Mock, patch

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
from PyQt6.QtWidgets import QApplication, QDialog, QMenu, QPushButton, QWidget

from core.archive_table import ArchiveTableDialog
from core.complete_table import CompleteTableDialog
from core.deleted_table import DeletedTableDialog
from core.quadrant_widget import QuadrantWidget
from ui.adaptive_table import AdaptiveTextTableWidget


class FakeArchiveDbManager:
    def __init__(self, tasks):
        self.tasks = list(tasks)
        self.page_calls = []
        self.id_calls = []
        self.restore_calls = []
        self.flush_calls = 0

    def _filtered(self, search_query=""):
        keywords = [word.casefold() for word in str(search_query or "").split() if word]
        return [
            task
            for task in self.tasks
            if all(word in task.get("text", "").casefold() for word in keywords)
        ]

    def load_deleted_tasks_page(self, limit=100, offset=0, search_query=""):
        self.page_calls.append(
            {"limit": limit, "offset": offset, "search_query": search_query}
        )
        return self._filtered(search_query)[offset:offset + limit]

    def count_deleted_tasks(self, search_query=""):
        return len(self._filtered(search_query))

    def load_deleted_task_ids(self, search_query=""):
        self.id_calls.append(search_query)
        return [task["id"] for task in self._filtered(search_query)]

    def restore_deleted_task(self, task_id):
        self.restore_calls.append(task_id)
        before = len(self.tasks)
        self.tasks = [task for task in self.tasks if task["id"] != task_id]
        return len(self.tasks) < before

    def flush_cache_to_db(self):
        self.flush_calls += 1


class ArchiveTaskPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_restore_confirmation_uses_shared_panel_style(self):
        from core import archive_table

        self.assertTrue(
            hasattr(archive_table, "ArchiveRestoreConfirmDialog"),
            "Restore confirmation should use a project-styled dialog instead of QMessageBox.",
        )

        parent = QWidget()
        confirm_dialog = archive_table.ArchiveRestoreConfirmDialog(
            parent,
            "确定要还原选中的 2 个任务吗？",
        )
        self.addCleanup(parent.deleteLater)
        self.addCleanup(confirm_dialog.deleteLater)

        self.assertTrue(
            confirm_dialog.windowFlags() & Qt.WindowType.FramelessWindowHint
        )
        self.assertIsNotNone(confirm_dialog.findChild(QWidget, "dialog_panel"))
        self.assertEqual(confirm_dialog.confirm_button.property("buttonRole"), "primary")
        self.assertEqual(confirm_dialog.cancel_button.property("buttonRole"), "ghost")
        self.assertEqual(confirm_dialog.confirm_button.text(), "还原")
        self.assertEqual(confirm_dialog.cancel_button.text(), "取消")

    def test_completed_and_deleted_dialogs_share_archive_base(self):
        self.assertTrue(issubclass(CompleteTableDialog, ArchiveTableDialog))
        self.assertTrue(issubclass(DeletedTableDialog, ArchiveTableDialog))

    def test_deleted_dialog_uses_deleted_copy_and_updated_date_column(self):
        fake_db = FakeArchiveDbManager([])

        with patch("core.deleted_table.get_db_manager", return_value=fake_db):
            dialog = DeletedTableDialog()

        self.assertEqual(dialog.windowTitle(), "已删除事项")
        self.assertEqual(
            dialog.search_input.placeholderText(),
            "搜索已删除事项标题，多个关键字用空格分隔",
        )
        self.assertEqual(dialog.table.horizontalHeaderItem(2).text(), "删除日期")
        self.assertEqual(dialog.table.item(0, 1).text(), "暂无已删除事项")
        self.assertEqual(dialog.restore_button.text(), "还原选中事项")

    def test_deleted_dialog_load_more_reuses_table_and_selects_unloaded_matches(self):
        fake_db = FakeArchiveDbManager(
            [
                {"id": "task-1", "text": "任务一", "updated_at": "2026-06-09", "notes": ""},
                {"id": "task-2", "text": "任务二", "updated_at": "2026-06-08", "notes": ""},
                {"id": "task-3", "text": "任务三", "updated_at": "2026-06-07", "notes": ""},
            ]
        )

        with patch("core.deleted_table.get_db_manager", return_value=fake_db):
            dialog = DeletedTableDialog()
            dialog.page_size = 2
            dialog._load_archive_tasks()
            first_table = dialog.table

            dialog.select_all_button.click()
            QApplication.processEvents()
            dialog.load_more_button.click()
            QApplication.processEvents()

        self.assertIs(dialog.table, first_table)
        self.assertEqual(
            len(dialog.panel.findChildren(AdaptiveTextTableWidget)),
            1,
        )
        self.assertEqual(dialog.selected_tasks, {"task-1", "task-2", "task-3"})
        self.assertTrue(dialog.table.cellWidget(2, 0).isChecked())

    def test_deleted_dialog_restores_each_selected_task_flushes_once_and_refreshes_parent(self):
        fake_db = FakeArchiveDbManager(
            [
                {"id": "task-1", "text": "任务一", "updated_at": "2026-06-09", "notes": ""},
                {"id": "task-2", "text": "任务二", "updated_at": "2026-06-08", "notes": ""},
            ]
        )
        parent = QWidget()
        parent.config = {"ui": {"border_radius": 12}}
        parent.load_tasks = Mock()

        with patch("core.deleted_table.get_db_manager", return_value=fake_db), \
             patch(
                 "core.archive_table.ArchiveRestoreConfirmDialog.exec",
                 return_value=QDialog.DialogCode.Accepted,
             ), \
             patch("core.archive_table.show_success") as success_mock:
            dialog = DeletedTableDialog(parent)
            dialog.selected_tasks = {"task-1", "task-2", "missing"}
            dialog.restore_selected_tasks()

        self.assertCountEqual(
            fake_db.restore_calls,
            ["task-1", "task-2", "missing"],
        )
        self.assertEqual(fake_db.flush_calls, 1)
        parent.load_tasks.assert_called_once_with()
        success_mock.assert_called_once_with(
            dialog,
            "还原成功",
            "成功还原 2 个已删除事项",
        )
        self.assertEqual(dialog.selected_tasks, set())
        self.assertEqual(dialog.table.item(0, 1).text(), "暂无已删除事项")

    def test_archive_menu_contains_completed_and_deleted_actions_and_routes_each_one(self):
        host = QWidget()
        host.complete_button = QPushButton("完成", host)
        host.show_complete_dialog = Mock()
        host.show_deleted_dialog = Mock()
        style_manager = Mock()
        style_manager.get_stylesheet.return_value = "QMenu {}"

        QuadrantWidget._create_archive_menu(host, style_manager)

        self.assertEqual(
            [action.text() for action in host.archive_menu.actions()],
            ["完成", "删除"],
        )
        host.action_show_completed.trigger()
        host.action_show_deleted.trigger()
        host.show_complete_dialog.assert_called_once()
        host.show_deleted_dialog.assert_called_once()

    def test_archive_button_switches_between_direct_completed_entry_and_more_menu(self):
        host = QWidget()
        host.complete_button = QPushButton("完成", host)
        host.archive_menu = QMenu(host.complete_button)

        host.edit_mode = True
        QuadrantWidget._update_archive_button_mode(host)
        self.assertEqual(host.complete_button.text(), "更多")
        self.assertIs(host.complete_button.menu(), host.archive_menu)

        host.edit_mode = False
        QuadrantWidget._update_archive_button_mode(host)
        self.assertEqual(host.complete_button.text(), "完成")
        self.assertIsNone(host.complete_button.menu())

    def test_archive_button_click_only_opens_completed_dialog_outside_edit_mode(self):
        host = QWidget()
        host.complete_button = QPushButton("完成", host)
        host.archive_menu = QMenu(host.complete_button)
        host.show_complete_dialog = Mock()
        host._handle_archive_button_clicked = types.MethodType(
            QuadrantWidget._handle_archive_button_clicked,
            host,
        )
        host.complete_button.clicked.connect(host._handle_archive_button_clicked)

        host.edit_mode = True
        QuadrantWidget._update_archive_button_mode(host)
        host.complete_button.click()
        QApplication.processEvents()

        host.show_complete_dialog.assert_not_called()

        host.edit_mode = False
        QuadrantWidget._update_archive_button_mode(host)
        host.complete_button.click()
        QApplication.processEvents()

        host.show_complete_dialog.assert_called_once_with()

    def test_show_deleted_dialog_opens_deleted_table_dialog(self):
        host = QWidget()
        dialog = Mock()

        with patch("core.deleted_table.DeletedTableDialog", return_value=dialog) as dialog_type:
            QuadrantWidget.show_deleted_dialog(host)

        dialog_type.assert_called_once_with(host)
        dialog.exec.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
