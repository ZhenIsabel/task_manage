import unittest
from pathlib import Path


class PanelFormStyleIntegrationTests(unittest.TestCase):
    def _read(self, rel_path: str) -> str:
        repo_root = Path(__file__).resolve().parents[1]
        return (repo_root / rel_path).read_text(encoding='utf-8')

    def test_shared_panel_form_style_should_be_defined(self):
        styles_py = self._read('ui/styles.py')
        self.assertIn(
            '"panel_form_controls"',
            styles_py,
            'ui/styles.py 应定义共享的 panel_form_controls 样式',
        )
        self.assertIn(
            'QTimeEdit',
            styles_py,
            '共享表单样式应覆盖时间输入控件',
        )
        self.assertIn(
            'QSpinBox',
            styles_py,
            '共享表单样式应覆盖数字输入控件',
        )

    def test_settings_panel_should_use_shared_form_style(self):
        settings_dialog_py = self._read('core/settings_dialog.py')
        self.assertIn(
            'get_stylesheet("settings_panel")',
            settings_dialog_py,
            '设置对话框应接入 settings_panel 样式以覆盖滑块和复选框',
        )

    def test_settings_panel_stylesheet_should_define_slider_and_checkbox_rules(self):
        styles_py = self._read('ui/styles.py')
        self.assertIn(
            '"settings_panel"',
            styles_py,
            'ui/styles.py 应定义 settings_panel 样式',
        )
        self.assertIn(
            'QSlider::groove:horizontal',
            styles_py,
            'settings_panel 应覆盖滑块轨道样式',
        )
        self.assertIn(
            'QCheckBox',
            styles_py,
            'settings_panel 应覆盖复选框样式',
        )

    def test_settings_panel_stylesheet_should_format_without_key_error(self):
        styles_py = self._read('ui/styles.py')
        marker = '"settings_panel": """'
        start = styles_py.index(marker) + len(marker)
        end = styles_py.index('"panel_form_controls": PANEL_FORM_CONTROLS_STYLE,', start)
        settings_panel_template = styles_py[start:end]

        try:
            settings_panel_template.format()
        except KeyError as exc:
            self.fail(f'settings_panel 样式不应在 format() 时抛出 KeyError: {exc}')

    def test_add_task_dialog_should_use_shared_form_style(self):
        add_task_dialog_py = self._read('core/add_task_dialog.py')
        self.assertIn(
            'get_stylesheet("panel_form_controls")',
            add_task_dialog_py,
            '新建/编辑任务面板应接入共享表单控件样式',
        )

    def test_dialog_shell_styles_should_scope_controls_under_named_panel(self):
        styles_py = self._read('ui/styles.py')
        self.assertIn('QWidget#dialog_panel', styles_py)

    def test_settings_styles_should_scope_controls_under_named_panel(self):
        styles_py = self._read('ui/styles.py')
        self.assertIn('QWidget#settings_panel', styles_py)
        self.assertIn('QWidget#settings_panel QLabel', styles_py)
        self.assertIn('QWidget#settings_panel QCheckBox', styles_py)

    def test_dialog_panels_should_declare_stable_object_names(self):
        add_task_dialog_py = self._read('core/add_task_dialog.py')
        settings_dialog_py = self._read('core/settings_dialog.py')
        history_viewer_py = self._read('core/history_viewer.py')

        self.assertIn('panel.setObjectName("dialog_panel")', add_task_dialog_py)
        self.assertIn('panel.setObjectName("settings_panel")', settings_dialog_py)
        self.assertIn('panel.setObjectName("dialog_panel")', history_viewer_py)


    def test_task_label_styles_should_scope_to_task_label_root(self):
        styles_py = self._read('ui/styles.py')
        task_label_py = self._read('core/task_label.py')

        self.assertIn('QWidget#task_label_root', styles_py)
        self.assertIn('QWidget#task_label_root QLabel#TagText', styles_py)
        self.assertIn('QWidget#task_label_root QCheckBox', styles_py)
        self.assertIn('self.setObjectName("task_label_root")', task_label_py)


    def test_detail_popup_should_define_scoped_win11_card_styles(self):
        styles_py = self._read('ui/styles.py')
        task_label_py = self._read('core/task_label.py')

        self.assertIn('QFrame#task_detail_popup QWidget#detail_section_card', styles_py)
        self.assertIn('setObjectName("detail_header_section")', task_label_py)
        self.assertIn('setObjectName("detail_meta_section")', task_label_py)
        self.assertIn('setObjectName("detail_notes_section")', task_label_py)
    def test_task_label_base_style_should_keep_tag_text_border_radius(self):
        styles_py = self._read('ui/styles.py')
        marker = 'QWidget#task_label_root QLabel#TagText {{'
        start = styles_py.index(marker)
        end = styles_py.index('            }}', start)
        tag_text_rule = styles_py[start:end]

        self.assertIn('border-radius: 10px;', tag_text_rule)

if __name__ == '__main__':
    unittest.main()


