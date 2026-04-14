import os
import unittest

from PyQt6.QtWidgets import QApplication, QGraphicsDropShadowEffect, QWidget

from core.task_label import TaskLabel


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class TaskLabelShadowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_task_label_should_apply_a_subtle_drop_shadow(self):
        host = QWidget()
        label = TaskLabel(
            task_id="shadow-test",
            color="#7ED6DF",
            parent=host,
            field_definitions=[
                {"name": "text", "label": "任务内容", "type": "text", "required": True},
                {"name": "due_date", "label": "到期日期", "type": "date", "required": False},
            ],
            text="带轻阴影的任务",
            due_date="",
        )
        self.addCleanup(label.deleteLater)
        self.addCleanup(host.deleteLater)

        effect = label.graphicsEffect()

        self.assertIsInstance(
            effect,
            QGraphicsDropShadowEffect,
            "TaskLabel 应挂载一个轻量阴影效果，增强轻微悬浮层次",
        )
        self.assertLessEqual(effect.blurRadius(), 10)
        self.assertEqual(effect.xOffset(), 0.0)
        self.assertLessEqual(effect.yOffset(), 2.0)
        self.assertGreater(effect.color().alpha(), 0)
        self.assertLessEqual(effect.color().alpha(), 80)


    def test_detail_notes_formatter_should_preserve_line_breaks(self):
        self.assertEqual(
            TaskLabel._format_detail_notes_html("第一行\n第二行"),
            "第一行<br>第二行",
        )

    def test_status_toggle_should_still_save_after_detail_popup_is_deleted(self):
        host = QWidget()
        label = TaskLabel(
            task_id="deleted-popup-test",
            color="#7ED6DF",
            parent=host,
            field_definitions=[
                {"name": "text", "label": "任务内容", "type": "text", "required": True},
                {"name": "due_date", "label": "到期日期", "type": "date", "required": False},
                {"name": "notes", "label": "备注", "type": "multiline", "required": False},
                {"name": "urgency", "label": "紧急程度", "type": "select", "required": False},
                {"name": "importance", "label": "重要程度", "type": "select", "required": False},
                {"name": "create_date", "label": "创建日期", "type": "date", "required": False},
                {"name": "completed_date", "label": "完成日期", "type": "date", "required": False},
            ],
            text="销毁浮窗后仍可完成",
            due_date="",
            notes="",
            urgency="低",
            importance="高",
            create_date="2026-04-08",
            completed_date="",
        )
        self.addCleanup(label.deleteLater)
        self.addCleanup(host.deleteLater)

        saved_states = []
        label.statusChanged.connect(lambda task: saved_states.append(task.get_data()["completed"]))

        class DeletedStatusLabel:
            def setText(self, _text):
                raise RuntimeError("wrapped C/C++ object of type QLabel has been deleted")

        label.status_label = DeletedStatusLabel()

        label.checkbox.setChecked(True)

        self.assertEqual(saved_states, [True])
        self.assertEqual(label.get_data()["completed"], True)
        self.assertNotEqual(label.completed_date, "")

if __name__ == "__main__":
    unittest.main()

