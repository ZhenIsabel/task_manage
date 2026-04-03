import os
import unittest

from PyQt6.QtWidgets import QApplication, QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from core.add_task_dialog import AddTaskDialog
from core.scheduler import AddScheduleDialog


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

        self.assertIsInstance(urgency_combo, QComboBox)
        self.assertIsInstance(importance_combo, QComboBox)
        self.assertEqual(
            urgency_combo.mapToGlobal(urgency_combo.rect().topLeft()).y(),
            importance_combo.mapToGlobal(importance_combo.rect().topLeft()).y(),
            "新增/编辑任务对话框里的紧急程度和重要程度应位于同一行",
        )

    def test_add_schedule_dialog_should_place_urgency_and_importance_on_same_row(self):
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

        self.assertIsInstance(urgency_combo, QComboBox)
        self.assertIsInstance(importance_combo, QComboBox)
        self.assertEqual(
            urgency_combo.mapToGlobal(urgency_combo.rect().topLeft()).y(),
            importance_combo.mapToGlobal(importance_combo.rect().topLeft()).y(),
            "定时任务对话框里的紧急程度和重要程度应位于同一行",
        )


if __name__ == "__main__":
    unittest.main()
