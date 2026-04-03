import unittest
from pathlib import Path


class PanelFormStyleIntegrationTests(unittest.TestCase):
    def _read(self, rel_path: str) -> str:
        repo_root = Path(__file__).resolve().parents[1]
        return (repo_root / rel_path).read_text(encoding="utf-8")

    def test_shared_panel_form_style_should_be_defined(self):
        styles_py = self._read("ui/styles.py")
        self.assertIn(
            '"panel_form_controls"',
            styles_py,
            "ui/styles.py 应定义共享的 panel_form_controls 样式",
        )
        self.assertIn(
            "QTimeEdit",
            styles_py,
            "共享表单样式应覆盖时间输入控件",
        )
        self.assertIn(
            "QSpinBox",
            styles_py,
            "共享表单样式应覆盖数字输入控件",
        )

    def test_settings_panel_should_use_shared_form_style(self):
        quadrant_widget_py = self._read("core/quadrant_widget.py")
        self.assertIn(
            'get_stylesheet("settings_panel")',
            quadrant_widget_py,
            "设置面板应接入 settings_panel 样式以覆盖滑块和复选框",
        )

    def test_settings_panel_stylesheet_should_define_slider_and_checkbox_rules(self):
        styles_py = self._read("ui/styles.py")
        self.assertIn(
            '"settings_panel"',
            styles_py,
            "ui/styles.py 应定义 settings_panel 样式",
        )
        self.assertIn(
            "QSlider::groove:horizontal",
            styles_py,
            "settings_panel 应覆盖滑块轨道样式",
        )
        self.assertIn(
            "QCheckBox {{",
            styles_py,
            "settings_panel 应覆盖复选框样式",
        )

    def test_settings_panel_stylesheet_should_format_without_key_error(self):
        styles_py = self._read("ui/styles.py")
        marker = '"settings_panel": """'
        start = styles_py.index(marker) + len(marker)
        end = styles_py.index('""" + PANEL_FORM_CONTROLS_STYLE + BASE_SCROLLBAR_STYLE,', start)
        settings_panel_template = styles_py[start:end]

        try:
            settings_panel_template.format()
        except KeyError as exc:
            self.fail(f"settings_panel 样式不应在 format() 时抛出 KeyError: {exc}")

    def test_add_task_dialog_should_use_shared_form_style(self):
        add_task_dialog_py = self._read("core/add_task_dialog.py")
        self.assertIn(
            'get_stylesheet("panel_form_controls")',
            add_task_dialog_py,
            "新建/编辑任务面板应接入共享表单控件样式",
        )


if __name__ == "__main__":
    unittest.main()
