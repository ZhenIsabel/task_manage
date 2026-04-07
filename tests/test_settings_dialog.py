import os
import unittest

from PyQt6.QtCore import QEvent, QPoint, QPointF, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QApplication, QCheckBox, QLineEdit, QSlider, QSpinBox

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from core.settings_dialog import SettingsDialog
from ui.ui import MyColorDialog


def _sample_color_ranges():
    return {
        "q1": {"hue_range": 30, "saturation_range": 20, "value_range": 20},
        "q2": {"hue_range": 30, "saturation_range": 20, "value_range": 20},
        "q3": {"hue_range": 30, "saturation_range": 20, "value_range": 20},
        "q4": {"hue_range": 30, "saturation_range": 20, "value_range": 20},
    }


def _sample_initial():
    return {
        "config": {
            "size": {"width": 640, "height": 480},
            "ui": {"border_radius": 10},
            "color_ranges": _sample_color_ranges(),
        },
        "remote_config": {
            "enabled": True,
            "api_base_url": "http://example.com",
            "api_token": "secret-token",
            "username": "alice",
        },
    }


class SettingsDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_visual_controls_trigger_preview_changed(self):
        """视觉控制项变更会触发 previewChanged，且载荷仅含可预览字段（size / ui）。"""
        initial = _sample_initial()
        dlg = SettingsDialog(None, initial=initial)
        payloads = []
        dlg.previewChanged.connect(lambda p: payloads.append(dict(p)))

        dlg.findChild(QSpinBox, "settings_width_spin").setValue(800)
        self.app.processEvents()

        self.assertTrue(payloads, "调节宽度后应发出 previewChanged")
        last = payloads[-1]
        self.assertIn("size", last)
        self.assertIn("ui", last)
        self.assertNotIn("remote_config", last)
        self.assertEqual(last["size"]["width"], 800)
        self.assertEqual(last["size"]["height"], 480)
        self.assertEqual(last["ui"]["border_radius"], 10)
        self.assertIn("color_ranges", last)
        self.assertEqual(last["color_ranges"]["q1"]["hue_range"], 30)

        dlg.findChild(QSpinBox, "settings_height_spin").setValue(600)
        self.app.processEvents()
        self.assertEqual(payloads[-1]["size"]["height"], 600)

        dlg.findChild(QSpinBox, "settings_border_radius_spin").setValue(20)
        self.app.processEvents()
        self.assertEqual(payloads[-1]["ui"]["border_radius"], 20)

    def test_color_range_sliders_emit_preview_with_color_ranges(self):
        """调节象限颜色范围滑块会发出 previewChanged，且载荷含完整 color_ranges。"""
        initial = _sample_initial()
        dlg = SettingsDialog(None, initial=initial)
        payloads = []
        dlg.previewChanged.connect(lambda p: payloads.append(dict(p)))

        dlg.findChild(QSlider, "settings_q1_hue_range_slider").setValue(45)
        self.app.processEvents()

        self.assertTrue(payloads, "调节色相滑块后应发出 previewChanged")
        last = payloads[-1]
        self.assertIn("color_ranges", last)
        self.assertEqual(last["color_ranges"]["q1"]["hue_range"], 45)
        self.assertEqual(last["color_ranges"]["q1"]["saturation_range"], 20)
        self.assertEqual(last["color_ranges"]["q1"]["value_range"], 20)

        dlg.findChild(QSlider, "settings_q2_saturation_range_slider").setValue(40)
        self.app.processEvents()
        self.assertEqual(payloads[-1]["color_ranges"]["q2"]["saturation_range"], 40)

        dlg.findChild(QSlider, "settings_q3_value_range_slider").setValue(60)
        self.app.processEvents()
        self.assertEqual(payloads[-1]["color_ranges"]["q3"]["value_range"], 60)

    def test_get_result_returns_config_and_remote_config(self):
        """get_result 顶层包含 config 与 remote_config。"""
        initial = _sample_initial()
        dlg = SettingsDialog(None, initial=initial)

        dlg.findChild(QSpinBox, "settings_width_spin").setValue(900)
        dlg.findChild(QSpinBox, "settings_height_spin").setValue(700)
        dlg.findChild(QSpinBox, "settings_border_radius_spin").setValue(8)
        self.app.processEvents()

        result = dlg.get_result()
        self.assertIn("config", result)
        self.assertIn("remote_config", result)
        cfg = result["config"]
        self.assertEqual(cfg["size"]["width"], 900)
        self.assertEqual(cfg["size"]["height"], 700)
        self.assertEqual(cfg["ui"]["border_radius"], 8)
        self.assertIn("color_ranges", cfg)
        self.assertEqual(cfg["color_ranges"]["q1"]["hue_range"], 30)

        remote = result["remote_config"]
        for key in ("enabled", "api_base_url", "api_token", "username"):
            self.assertIn(key, remote)

    def test_remote_config_four_fields_read_and_write(self):
        """remote_config 四字段可从 initial 读出，并随控件写回 get_result。"""
        initial = _sample_initial()
        dlg = SettingsDialog(None, initial=initial)

        r0 = dlg.get_result()["remote_config"]
        self.assertTrue(r0["enabled"])
        self.assertEqual(r0["api_base_url"], "http://example.com")
        self.assertEqual(r0["api_token"], "secret-token")
        self.assertEqual(r0["username"], "alice")

        dlg.findChild(QCheckBox, "settings_remote_enabled_checkbox").setChecked(False)
        dlg.findChild(QLineEdit, "settings_remote_api_base_url_edit").setText("https://api.test")
        dlg.findChild(QLineEdit, "settings_remote_api_token_edit").setText("new-tok")
        dlg.findChild(QLineEdit, "settings_remote_username_edit").setText("bob")
        self.app.processEvents()

        r1 = dlg.get_result()["remote_config"]
        self.assertFalse(r1["enabled"])
        self.assertEqual(r1["api_base_url"], "https://api.test")
        self.assertEqual(r1["api_token"], "new-tok")
        self.assertEqual(r1["username"], "bob")

    def test_invalid_initial_numbers_use_defaults_and_clamp(self):
        """损坏或非数字的尺寸/圆角配置不得抛错，应回退默认或钳制到 SpinBox 范围内。"""
        initial = {
            "config": {
                "size": {"width": "not-a-number", "height": 99999},
                "ui": {"border_radius": {}},
                "color_ranges": {
                    "q1": {"hue_range": "x", "saturation_range": 9999, "value_range": -1},
                },
            },
            "remote_config": {},
        }
        dlg = SettingsDialog(None, initial=initial)
        self.assertEqual(dlg.findChild(QSpinBox, "settings_width_spin").value(), 1000)
        self.assertEqual(dlg.findChild(QSpinBox, "settings_height_spin").value(), 2000)
        self.assertEqual(dlg.findChild(QSpinBox, "settings_border_radius_spin").value(), 15)
        self.assertEqual(dlg.findChild(QSlider, "settings_q1_hue_range_slider").value(), 30)
        self.assertEqual(dlg.findChild(QSlider, "settings_q1_saturation_range_slider").value(), 20)
        self.assertEqual(dlg.findChild(QSlider, "settings_q1_value_range_slider").value(), 20)

    def test_task_label_color_dialog_should_not_force_a_custom_stylesheet(self):
        """详情入口的颜色面板应与设置页保持一致，不再单独套用自定义 QSS。"""
        dlg = MyColorDialog()
        self.addCleanup(dlg.deleteLater)

        self.assertEqual(
            dlg.styleSheet(),
            "",
            "任务详情入口的颜色对话框不应再强制挂载 color_dialog 样式",
        )

    def test_frameless_drag_mouse_handlers_move_dialog(self):
        """直接调用与 AddTaskDialog 一致的拖动三事件，窗口左上角应随拖动偏移。"""
        dlg = SettingsDialog(None, initial=_sample_initial())
        dlg.move(200, 200)
        self.app.processEvents()

        lp0 = QPoint(5, 5)
        gp0 = dlg.mapToGlobal(lp0)
        dlg.mousePressEvent(
            QMouseEvent(
                QEvent.Type.MouseButtonPress,
                QPointF(lp0),
                QPointF(lp0),
                QPointF(gp0),
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
            )
        )

        lp1 = QPoint(105, 5)
        gp1 = dlg.mapToGlobal(lp1)
        dlg.mouseMoveEvent(
            QMouseEvent(
                QEvent.Type.MouseMove,
                QPointF(lp1),
                QPointF(lp1),
                QPointF(gp1),
                Qt.MouseButton.NoButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
            )
        )

        self.assertEqual(dlg.pos().x(), 300)
        self.assertEqual(dlg.pos().y(), 200)

        dlg.mouseReleaseEvent(
            QMouseEvent(
                QEvent.Type.MouseButtonRelease,
                QPointF(lp1),
                QPointF(lp1),
                QPointF(gp1),
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.NoButton,
                Qt.KeyboardModifier.NoModifier,
            )
        )


if __name__ == "__main__":
    unittest.main()
