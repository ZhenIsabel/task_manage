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

    def test_button_theme_tokens_should_be_declared_near_top_of_styles(self):
        styles_py = self._read('ui/styles.py')
        top_section = '\n'.join(styles_py.splitlines()[:60])

        self.assertIn('BUTTON_THEME_TOKENS', top_section)
        self.assertIn('accent_fill_rest', top_section)
        self.assertIn('neutral_stroke', top_section)
        self.assertIn('danger_fill_rest', top_section)

    def test_button_role_helpers_should_be_defined(self):
        styles_py = self._read('ui/styles.py')

        self.assertIn('def get_button_stylesheet(', styles_py)
        self.assertIn('def apply_button_role(', styles_py)

    def test_button_sizes_should_define_small_medium_large_tokens(self):
        styles_py = self._read('ui/styles.py')

        self.assertIn('BUTTON_SIZE_TOKENS', styles_py)
        self.assertIn('BUTTON_PADDING_TOKENS', styles_py)
        self.assertIn('"sm": 30', styles_py)
        self.assertIn('"md": 34', styles_py)
        self.assertIn('"lg": 40', styles_py)
        self.assertIn('"sm": "5px 10px"', styles_py)
        self.assertIn('"md": "7px 16px"', styles_py)
        self.assertIn('"lg": "9px 20px"', styles_py)
        self.assertIn('padding = BUTTON_PADDING_TOKENS.get(size', styles_py)

    def test_primary_dialogs_should_apply_shared_button_roles(self):
        for rel_path in (
            'core/add_task_dialog.py',
            'core/complete_table.py',
            'core/export_summary_dialog.py',
            'core/history_viewer.py',
            'core/scheduler.py',
            'core/settings_dialog.py',
            'core/task_label.py',
        ):
            content = self._read(rel_path)
            self.assertIn(
                'apply_button_role(',
                content,
                f'{rel_path} 应通过共享 helper 接入统一按钮角色样式',
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
        marker = '"settings_panel": f"""'
        start = styles_py.index(marker) + len(marker)
        end = styles_py.index('"panel_form_controls": PANEL_FORM_CONTROLS_STYLE,', start)
        settings_panel_template = styles_py[start:end]

        try:
            settings_panel_template
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

    def test_dialog_panel_form_controls_should_use_compact_white_inputs(self):
        styles_py = self._read('ui/styles.py')

        self.assertIn(
            'QWidget#dialog_panel QLineEdit',
            styles_py,
            'dialog_panel 应为自定义输入框定义单独样式',
        )
        self.assertIn(
            'QWidget#dialog_panel QTextEdit',
            styles_py,
            'dialog_panel 应为自定义输入框定义单独样式',
        )
        self.assertIn(
            'background-color: #ffffff;',
            styles_py,
            '新增/编辑任务弹窗的自定义输入框应改为纯白底',
        )
        self.assertIn(
            'min-height: 20px;',
            styles_py,
            '新增/编辑任务弹窗的单行输入框应收窄到更紧凑的高度',
        )
        self.assertIn(
            'padding: 4px 12px 5px 12px;',
            styles_py,
            '新增/编辑任务弹窗的输入框内边距应改为更紧凑的尺寸',
        )

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

    def test_task_label_styles_should_format_without_key_error(self):
        from ui.styles import StyleManager

        style_manager = StyleManager()
        format_args = {
            'bg_color_red': 78,
            'bg_color_green': 205,
            'bg_color_blue': 196,
            'text_color_red': 0,
            'text_color_green': 0,
            'text_color_blue': 0,
            'indicator_size': 14,
        }

        try:
            style_manager.get_stylesheet("task_label").format(**format_args)
            style_manager.get_stylesheet("task_label_overdue").format(**format_args)
            style_manager.get_stylesheet("color_button").format(button_color="#4ECDC4")
        except KeyError as exc:
            self.fail(f'动态样式模板不应在 format() 时抛出 KeyError: {exc}')


if __name__ == '__main__':
    unittest.main()
