import os
import unittest
from pathlib import Path

from PyQt6.QtCore import QDate, QPoint, QAbstractAnimation
from PyQt6.QtWidgets import QApplication

from ui import fluent


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class FluentDatePickerMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _read(self, rel_path: str) -> str:
        repo_root = Path(__file__).resolve().parents[1]
        return (repo_root / rel_path).read_text(encoding="utf-8")

    def test_create_calendar_picker_should_round_trip_dates(self):
        picker = fluent.create_calendar_picker()
        target_date = QDate(2026, 4, 3)

        fluent.set_date_on_picker(picker, target_date)

        self.assertEqual(
            fluent.get_date_from_picker(picker),
            target_date,
            "统一日期控件 helper 应能正确写入并读回日期",
        )

    def test_create_calendar_picker_should_patch_popup_shell(self):
        if not fluent.FLUENT_AVAILABLE:
            self.skipTest("qfluentwidgets 不可用时无需验证 CalendarView 去壳补丁")

        fluent.create_calendar_picker()

        from qfluentwidgets.components.date_time.calendar_view import CalendarView  # type: ignore

        view = CalendarView()
        margins = view.hBoxLayout.contentsMargins()

        self.assertEqual(
            (margins.left(), margins.top(), margins.right(), margins.bottom()),
            (0, 0, 0, 0),
            "CalendarView 外层边距应被清零，避免出现额外外壳",
        )
        self.assertIsNone(
            view.stackedWidget.graphicsEffect(),
            "CalendarView 阴影应被移除，避免弹层外再包一层壳",
        )

    def test_create_calendar_picker_should_disable_popup_animation(self):
        if not fluent.FLUENT_AVAILABLE:
            self.skipTest("qfluentwidgets 不可用时无需验证 CalendarView 动画补丁")

        fluent.create_calendar_picker()

        from qfluentwidgets.components.date_time.calendar_view import CalendarView  # type: ignore

        view = CalendarView()
        view.exec(QPoint(0, 0))

        self.assertEqual(
            view.opacityAni.duration(),
            0,
            "CalendarView 透明度动画应禁用",
        )
        self.assertEqual(
            view.slideAni.duration(),
            0,
            "CalendarView 位移动画应禁用",
        )
        self.assertEqual(
            view.aniGroup.state(),
            QAbstractAnimation.State.Stopped,
            "CalendarView 不应启动动画组",
        )
        view.close()

    def test_fluent_combobox_should_patch_popup_shell(self):
        if not fluent.FLUENT_AVAILABLE:
            self.skipTest("qfluentwidgets 不可用时无需验证 ComboBox 去壳补丁")

        combo = fluent.ComboBox()
        combo.addItems(["高", "低"])
        menu = combo._createComboMenu()
        margins = menu.hBoxLayout.contentsMargins()

        self.assertEqual(
            (margins.left(), margins.top(), margins.right(), margins.bottom()),
            (0, 0, 0, 0),
            "ComboBoxMenu 外层边距应被清零，避免出现额外外壳",
        )
        self.assertIsNone(
            menu.view.graphicsEffect(),
            "ComboBoxMenu 阴影应被移除，避免下拉列表外再包一层壳",
        )
        menu.close()
        combo.deleteLater()

    def test_fluent_combobox_should_shorten_popup_animation(self):
        if not fluent.FLUENT_AVAILABLE:
            self.skipTest("qfluentwidgets 不可用时无需验证 ComboBox 动画时长补丁")

        combo = fluent.ComboBox()
        combo.addItems(["高", "低"])
        menu = combo._createComboMenu()
        menu.exec(QPoint(0, 0))

        self.assertEqual(
            menu.aniManager.ani.duration(),
            fluent.COMBOBOX_POPUP_ANIMATION_DURATION_MS,
            "ComboBox 下拉动画时长应使用统一的较短配置",
        )
        menu.close()
        combo.deleteLater()

    def test_core_dialogs_should_use_fluent_calendar_picker_helpers(self):
        for rel_path in (
            "core/add_task_dialog.py",
            "core/scheduler.py",
            "core/export_summary_dialog.py",
        ):
            source = self._read(rel_path)
            self.assertNotIn(
                "QDateEdit()",
                source,
                f"{rel_path} 应迁移为 Fluent CalendarPicker",
            )
            self.assertTrue(
                "get_date_from_picker" in source or "get_date_string_from_picker" in source,
                f"{rel_path} 应统一通过 helper 读取日期",
            )


if __name__ == "__main__":
    unittest.main()
