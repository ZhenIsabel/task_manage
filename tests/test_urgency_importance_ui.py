import os
import sys
import types
import unittest

from PyQt6.QtWidgets import QApplication, QComboBox, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from core.add_task_dialog import AddTaskDialog
from ui.fluent import ComboBox as FluentComboBox


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class UrgencyImportanceUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_degree_badge_meta_should_map_copy_and_palette(self):
        from ui.degree_badges import get_degree_badge_meta

        urgency_low = get_degree_badge_meta("urgency", "低")
        urgency_high = get_degree_badge_meta("urgency", "高")
        importance_low = get_degree_badge_meta("importance", "低")
        importance_high = get_degree_badge_meta("importance", "高")

        self.assertEqual(urgency_low["display_text"], "不紧急")
        self.assertEqual(urgency_high["display_text"], "很紧急")
        self.assertEqual(importance_low["display_text"], "不重要")
        self.assertEqual(importance_high["display_text"], "很重要")
        self.assertEqual(urgency_low["temperature"], "cool")
        self.assertEqual(urgency_high["temperature"], "warm")
        self.assertEqual(importance_low["temperature"], "cool")
        self.assertEqual(importance_high["temperature"], "warm")

    def test_add_task_dialog_should_place_urgency_and_importance_on_same_row(self):
        dialog = AddTaskDialog(
            task_fields=[
                {"name": "text", "label": "任务内容", "type": "text", "required": True},
                {"name": "urgency", "label": "紧急程度", "type": "select", "options": ["高", "低"], "default": "低"},
                {"name": "importance", "label": "重要程度", "type": "select", "options": ["高", "低"], "default": "低"},
            ]
        )
        self.addCleanup(dialog.close)

        dialog.show()
        self.app.processEvents()

        urgency_combo = dialog.inputs["urgency"]
        importance_combo = dialog.inputs["importance"]

        self.assertIsInstance(urgency_combo, (QComboBox, FluentComboBox))
        self.assertIsInstance(importance_combo, (QComboBox, FluentComboBox))
        self.assertEqual(
            urgency_combo.mapToGlobal(urgency_combo.rect().topLeft()).y(),
            importance_combo.mapToGlobal(importance_combo.rect().topLeft()).y(),
            "新增/编辑任务对话框里的紧急程度和重要程度应位于同一行",
        )

    def test_add_schedule_dialog_should_place_urgency_and_importance_on_same_row(self):
        if "requests" not in sys.modules:
            sys.modules["requests"] = types.SimpleNamespace()

        from core.scheduler import AddScheduleDialog

        dialog = AddScheduleDialog(
            task_fields=[
                {"name": "title", "label": "任务标题", "type": "text", "required": True},
                {"name": "urgency", "label": "紧急程度", "type": "select", "options": ["高", "低"], "default": "低"},
                {"name": "importance", "label": "重要程度", "type": "select", "options": ["高", "低"], "default": "低"},
            ]
        )
        self.addCleanup(dialog.close)

        dialog.show()
        self.app.processEvents()

        urgency_combo = dialog.inputs["urgency"]
        importance_combo = dialog.inputs["importance"]

        self.assertIsInstance(urgency_combo, (QComboBox, FluentComboBox))
        self.assertIsInstance(importance_combo, (QComboBox, FluentComboBox))
        self.assertEqual(
            urgency_combo.mapToGlobal(urgency_combo.rect().topLeft()).y(),
            importance_combo.mapToGlobal(importance_combo.rect().topLeft()).y(),
            "定时任务对话框里的紧急程度和重要程度应位于同一行",
        )

    def test_add_schedule_dialog_should_use_compact_shadowed_non_fluent_inputs(self):
        if "requests" not in sys.modules:
            sys.modules["requests"] = types.SimpleNamespace()

        from core.scheduler import AddScheduleDialog

        dialog = AddScheduleDialog(
            task_fields=[
                {"name": "title", "label": "任务标题", "type": "text", "required": True},
                {"name": "notes", "label": "备注", "type": "multiline", "required": False},
            ]
        )
        self.addCleanup(dialog.close)

        dialog.show()
        self.app.processEvents()

        title_input = dialog.inputs["title"]
        notes_input = dialog.inputs["notes"]

        self.assertLessEqual(
            title_input.height(),
            31,
            "定时任务弹窗的单行输入框应缩窄到与新增/编辑任务一致",
        )
        self.assertLessEqual(
            notes_input.minimumHeight(),
            72,
            "定时任务弹窗的多行输入框也应同步收窄",
        )

        for widget in (title_input, notes_input):
            effect = widget.graphicsEffect()
            self.assertIsInstance(
                effect,
                QGraphicsDropShadowEffect,
                "定时任务弹窗的自定义输入框也应带有一层很窄的底部阴影",
            )
            self.assertEqual(effect.offset().y(), 0.5)
            self.assertLessEqual(effect.blurRadius(), 4.0)

    def test_add_task_dialog_should_center_directory_picker_button_with_path_input(self):
        dialog = AddTaskDialog(
            task_fields=[
                {"name": "directory", "label": "目录", "type": "file", "required": False},
            ]
        )
        self.addCleanup(dialog.close)

        dialog.show()
        self.app.processEvents()

        path_input = dialog.inputs["directory"]
        choose_button = next(
            button for button in dialog.findChildren(QPushButton) if button.text() == "选择"
        )

        self.assertEqual(
            path_input.mapToGlobal(path_input.rect().center()).y(),
            choose_button.mapToGlobal(choose_button.rect().center()).y(),
            "目录路径输入框和选择按钮应按垂直中线对齐",
        )

    def test_add_task_dialog_should_use_compact_shadowed_non_fluent_inputs(self):
        dialog = AddTaskDialog(
            task_fields=[
                {"name": "text", "label": "任务内容", "type": "text", "required": True},
                {"name": "notes", "label": "备注", "type": "multiline", "required": False},
            ]
        )
        self.addCleanup(dialog.close)

        dialog.show()
        self.app.processEvents()

        text_input = dialog.inputs["text"]
        notes_input = dialog.inputs["notes"]

        self.assertLessEqual(
            text_input.height(),
            31,
            "新增/编辑任务弹窗的单行输入框应缩窄到原先的大约 2/3 高度",
        )
        self.assertLessEqual(
            notes_input.minimumHeight(),
            72,
            "新增/编辑任务弹窗的多行输入框也应同步收窄",
        )

        for widget in (text_input, notes_input):
            effect = widget.graphicsEffect()
            self.assertIsInstance(
                effect,
                QGraphicsDropShadowEffect,
                "自定义输入框应带有一层很窄的底部阴影",
            )
            self.assertEqual(effect.offset().y(), 0.5)
            self.assertLessEqual(effect.blurRadius(), 4.0)


if __name__ == "__main__":
    unittest.main()
