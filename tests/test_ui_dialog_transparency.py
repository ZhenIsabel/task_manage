import unittest
from pathlib import Path


class UIDialogTransparencyTests(unittest.TestCase):
    def _read(self, rel_path: str) -> str:
        repo_root = Path(__file__).resolve().parents[1]
        return (repo_root / rel_path).read_text(encoding="utf-8")

    def test_dialogs_should_not_use_WA_TranslucentBackground(self):
        """
        只覆盖“弹窗/详情框”这类组件，不覆盖主象限窗口。
        依据需求：移除各种无边框弹窗外侧那圈透明空白壳。
        """
        # ui/ui.py: WarningPopup & DeleteConfirmDialog
        ui_py = self._read("ui/ui.py")
        self.assertNotIn(
            "self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)",
            ui_py,
            "ui/ui.py 仍然存在弹窗使用 WA_TranslucentBackground 的设置",
        )

        # core/add_task_dialog.py
        add_task_dialog_py = self._read("core/add_task_dialog.py")
        self.assertNotIn(
            "self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)",
            add_task_dialog_py,
            "core/add_task_dialog.py 仍然存在 WA_TranslucentBackground 设置",
        )

        # core/scheduler.py
        scheduler_py = self._read("core/scheduler.py")
        self.assertNotIn(
            "self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)",
            scheduler_py,
            "core/scheduler.py 仍然存在 WA_TranslucentBackground 设置",
        )

        # core/quadrant_widget.py: 仅移除 show_settings/show_gantt_dialog 内对话框的 translucent
        quadrant_widget_py = self._read("core/quadrant_widget.py")
        self.assertNotIn(
            'dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)',
            quadrant_widget_py,
            "core/quadrant_widget.py 的 show_settings 弹窗仍使用 WA_TranslucentBackground",
        )
        self.assertNotIn(
            'dlg.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)',
            quadrant_widget_py,
            "core/quadrant_widget.py 的 show_gantt_dialog 弹窗仍使用 WA_TranslucentBackground",
        )

        # core/history_viewer.py
        history_viewer_py = self._read("core/history_viewer.py")
        self.assertNotIn(
            "self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)",
            history_viewer_py,
            "core/history_viewer.py 仍然存在 WA_TranslucentBackground 设置",
        )

        # core/export_summary_dialog.py
        export_summary_dialog_py = self._read("core/export_summary_dialog.py")
        self.assertNotIn(
            "self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)",
            export_summary_dialog_py,
            "core/export_summary_dialog.py 仍然存在 WA_TranslucentBackground 设置",
        )

        # core/complete_table.py
        complete_table_py = self._read("core/complete_table.py")
        self.assertNotIn(
            "self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)",
            complete_table_py,
            "core/complete_table.py 仍然存在 WA_TranslucentBackground 设置",
        )

        # core/task_label.py: detail_popup
        task_label_py = self._read("core/task_label.py")
        self.assertNotIn(
            "self.detail_popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)",
            task_label_py,
            "core/task_label.py 的 detail_popup 仍然存在 WA_TranslucentBackground 设置",
        )


if __name__ == "__main__":
    unittest.main()

