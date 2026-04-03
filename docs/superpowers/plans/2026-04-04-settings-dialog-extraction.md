# 设置对话框拆分 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `QuadrantWidget` 内联的设置窗口拆到独立的 `SettingsDialog(QDialog)` 文件中，同时保留颜色、尺寸、圆角的实时预览，并支持取消回滚与确定持久化。

**Architecture:** 新增 `core/settings_dialog.py` 承载设置 UI、工作态配置和实时预览信号；`QuadrantWidget` 只负责打开对话框、应用预览、提交最终设置、在取消时回滚原始视觉配置。远程配置和自动刷新继续在确认时保存，视觉类设置在编辑时只更新运行态、不写盘。

**Tech Stack:** Python 3、PyQt6、`unittest`、`pytest`、项目现有 `StyleManager` / `RemoteConfigManager`

---

### Task 1: 提取独立 `SettingsDialog` 并用测试锁定对话框行为

**Files:**
- Create: `core/settings_dialog.py`
- Create: `tests/test_settings_dialog.py`
- Modify: `ui/styles.py:289-360` only if the existing `settings_panel` style cannot be reused as-is

- [ ] **Step 1: Write the failing test**

```python
import os
import unittest

from PyQt6.QtWidgets import QApplication

from core.settings_dialog import SettingsDialog


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class SettingsDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _build_config(self):
        return {
            'quadrants': {
                'q1': {'color': '#FF6B6B', 'opacity': 0.8},
                'q2': {'color': '#4ECDC4', 'opacity': 0.8},
                'q3': {'color': '#FFE66D', 'opacity': 0.8},
                'q4': {'color': '#6D8EA0', 'opacity': 0.7},
            },
            'color_ranges': {
                'q1': {'hue_range': 30, 'saturation_range': 20, 'value_range': 20},
                'q2': {'hue_range': 30, 'saturation_range': 20, 'value_range': 20},
                'q3': {'hue_range': 30, 'saturation_range': 20, 'value_range': 20},
                'q4': {'hue_range': 30, 'saturation_range': 20, 'value_range': 20},
            },
            'size': {'width': 800, 'height': 600},
            'position': {'x': 100, 'y': 100},
            'ui': {'border_radius': 15},
            'auto_refresh': {'enabled': True, 'refresh_time': '00:02:00'},
        }

    def test_visual_controls_should_emit_preview_payload(self):
        dialog = SettingsDialog(
            config_snapshot=self._build_config(),
            remote_config_snapshot={'enabled': True, 'api_base_url': '', 'api_token': '', 'username': ''},
        )
        payloads = []
        dialog.previewChanged.connect(payloads.append)

        dialog.opacity_sliders['q1'].setValue(65)
        dialog.width_spin.setValue(960)
        dialog.border_radius_spin.setValue(22)

        self.assertGreaterEqual(len(payloads), 3)
        self.assertEqual(payloads[-1]['size']['width'], 960)
        self.assertEqual(payloads[-1]['ui']['border_radius'], 22)
        self.assertAlmostEqual(payloads[0]['quadrants']['q1']['opacity'], 0.65, places=2)

    def test_get_result_should_return_working_config_and_remote_config(self):
        dialog = SettingsDialog(
            config_snapshot=self._build_config(),
            remote_config_snapshot={'enabled': False, 'api_base_url': '', 'api_token': '', 'username': ''},
        )

        dialog.height_spin.setValue(720)
        dialog.remote_enabled_checkbox.setChecked(True)
        dialog.remote_url_edit.setText('http://example.com')
        dialog.remote_username_edit.setText('alice')
        dialog.remote_token_edit.setText('token')

        result = dialog.get_result()

        self.assertEqual(result['config']['size']['height'], 720)
        self.assertTrue(result['remote_config']['enabled'])
        self.assertEqual(result['remote_config']['api_base_url'], 'http://example.com')
        self.assertEqual(result['remote_config']['username'], 'alice')
        self.assertEqual(result['remote_config']['api_token'], 'token')


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_settings_dialog.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.settings_dialog'` or `ImportError: cannot import name 'SettingsDialog'`

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

from copy import deepcopy

from PyQt6.QtCore import Qt, QTime, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from ui.styles import StyleManager


class SettingsDialog(QDialog):
    previewChanged = pyqtSignal(dict)

    QUADRANT_NAMES = {
        'q1': "重要且紧急（右上）",
        'q2': "重要不紧急（左上）",
        'q3': "不重要但紧急（右下）",
        'q4': "不重要不紧急（左下）",
    }

    def __init__(self, config_snapshot: dict, remote_config_snapshot: dict, initial_tab: str = '', parent=None):
        super().__init__(parent, flags=Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.working_config = deepcopy(config_snapshot)
        self.working_remote_config = deepcopy(remote_config_snapshot)

        self.color_buttons = {}
        self.opacity_sliders = {}
        self.hue_range_sliders = {}
        self.saturation_range_sliders = {}
        self.value_range_sliders = {}

        self._build_ui(initial_tab)

    def _build_ui(self, initial_tab: str) -> None:
        panel = QWidget(self)
        panel.setObjectName("panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(30, 30, 30, 30)
        panel_layout.setSpacing(20)

        style_manager = StyleManager()
        panel.setStyleSheet(
            style_manager.get_stylesheet("dialog_panel_shell").format()
            + style_manager.get_stylesheet("settings_panel").format()
        )

        tab_widget = QTabWidget()
        color_widget = QWidget()
        color_layout = QFormLayout(color_widget)

        for quadrant_id, quadrant_name in self.QUADRANT_NAMES.items():
            color_button = QPushButton()
            color_button.setFixedSize(30, 30)
            color_button.clicked.connect(
                lambda _=False, qid=quadrant_id: self._choose_quadrant_color(qid)
            )
            self.color_buttons[quadrant_id] = color_button
            self._refresh_color_button(quadrant_id)

            opacity_slider = QSlider(Qt.Orientation.Horizontal)
            opacity_slider.setRange(1, 100)
            opacity_slider.setValue(int(self.working_config['quadrants'][quadrant_id]['opacity'] * 100))
            opacity_slider.valueChanged.connect(
                lambda value, qid=quadrant_id: self._set_quadrant_opacity(qid, value)
            )
            self.opacity_sliders[quadrant_id] = opacity_slider

            color_layout.addRow(f"{quadrant_name} 颜色:", color_button)
            color_layout.addRow(f"{quadrant_name} 透明度:", opacity_slider)

        size_widget = QWidget()
        size_layout = QFormLayout(size_widget)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(300, 2000)
        self.width_spin.setValue(self.working_config['size']['width'])
        self.width_spin.valueChanged.connect(lambda value: self._set_size('width', value))

        self.height_spin = QSpinBox()
        self.height_spin.setRange(300, 2000)
        self.height_spin.setValue(self.working_config['size']['height'])
        self.height_spin.valueChanged.connect(lambda value: self._set_size('height', value))
        size_layout.addRow("宽度:", self.width_spin)
        size_layout.addRow("高度:", self.height_spin)

        ui_widget = QWidget()
        ui_layout = QFormLayout(ui_widget)
        self.border_radius_spin = QSpinBox()
        self.border_radius_spin.setRange(0, 50)
        self.border_radius_spin.setValue(self.working_config.get('ui', {}).get('border_radius', 15))
        self.border_radius_spin.valueChanged.connect(self._set_border_radius)
        ui_layout.addRow("圆角半径:", self.border_radius_spin)

        self.auto_refresh_checkbox = QCheckBox("启用自动刷新")
        self.auto_refresh_checkbox.setChecked(self.working_config.get('auto_refresh', {}).get('enabled', True))
        self.refresh_time_edit = QTimeEdit()
        self.refresh_time_edit.setDisplayFormat("HH:mm:ss")
        self.refresh_time_edit.setTime(QTime.fromString(
            self.working_config.get('auto_refresh', {}).get('refresh_time', '00:02:00'),
            "HH:mm:ss",
        ))
        self.auto_refresh_checkbox.stateChanged.connect(self._set_auto_refresh_enabled)
        self.refresh_time_edit.timeChanged.connect(self._set_refresh_time)
        ui_layout.addRow(self.auto_refresh_checkbox)
        ui_layout.addRow("刷新时间:", self.refresh_time_edit)

        remote_widget = QWidget()
        remote_layout = QFormLayout(remote_widget)
        self.remote_enabled_checkbox = QCheckBox("启用远程同步")
        self.remote_enabled_checkbox.setChecked(self.working_remote_config.get('enabled', False))
        self.remote_url_edit = QLineEdit(self.working_remote_config.get('api_base_url', ''))
        self.remote_username_edit = QLineEdit(self.working_remote_config.get('username', ''))
        self.remote_token_edit = QLineEdit(self.working_remote_config.get('api_token', ''))
        remote_layout.addRow(self.remote_enabled_checkbox)
        remote_layout.addRow("服务器地址:", self.remote_url_edit)
        remote_layout.addRow("用户名:", self.remote_username_edit)
        remote_layout.addRow("访问令牌:", self.remote_token_edit)

        tab_widget.addTab(color_widget, "颜色设置")
        tab_widget.addTab(size_widget, "大小设置")
        tab_widget.addTab(ui_widget, "界面设置")
        tab_widget.addTab(remote_widget, "远程设置")
        if initial_tab == 'remote':
            tab_widget.setCurrentWidget(remote_widget)

        button_row = QHBoxLayout()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        button_row.addStretch()
        button_row.addWidget(ok_button)
        button_row.addWidget(cancel_button)

        panel_layout.addWidget(tab_widget)
        panel_layout.addLayout(button_row)
        panel.setMinimumWidth(600)
        panel_layout.activate()
        panel.adjustSize()
        self.resize(panel.width(), panel.height())
        panel.move(0, 0)

    def _refresh_color_button(self, quadrant_id: str) -> None:
        color = self.working_config['quadrants'][quadrant_id]['color']
        self.color_buttons[quadrant_id].setStyleSheet(
            f"background-color: {color}; border-radius: 15px; border: 1px solid #ddd;"
        )

    def _emit_preview(self) -> None:
        self.previewChanged.emit(deepcopy({
            'quadrants': self.working_config['quadrants'],
            'color_ranges': self.working_config.get('color_ranges', {}),
            'size': self.working_config['size'],
            'ui': self.working_config.get('ui', {}),
        }))

    def _choose_quadrant_color(self, quadrant_id: str) -> None:
        current = QColor(self.working_config['quadrants'][quadrant_id]['color'])
        color = QColorDialog.getColor(current, self, "选择象限颜色")
        if not color.isValid():
            return
        self.working_config['quadrants'][quadrant_id]['color'] = color.name()
        self._refresh_color_button(quadrant_id)
        self._emit_preview()

    def _set_quadrant_opacity(self, quadrant_id: str, value: int) -> None:
        self.working_config['quadrants'][quadrant_id]['opacity'] = value / 100
        self._emit_preview()

    def _set_size(self, dimension: str, value: int) -> None:
        self.working_config['size'][dimension] = value
        self._emit_preview()

    def _set_border_radius(self, value: int) -> None:
        self.working_config.setdefault('ui', {})['border_radius'] = value
        self._emit_preview()

    def _set_auto_refresh_enabled(self, state: int) -> None:
        self.working_config.setdefault('auto_refresh', {})['enabled'] = (
            state == Qt.CheckState.Checked.value
        )

    def _set_refresh_time(self, time: QTime) -> None:
        self.working_config.setdefault('auto_refresh', {})['refresh_time'] = time.toString("HH:mm:ss")

    def get_result(self) -> dict:
        self.working_remote_config = {
            'enabled': self.remote_enabled_checkbox.isChecked(),
            'api_base_url': self.remote_url_edit.text().strip(),
            'api_token': self.remote_token_edit.text().strip(),
            'username': self.remote_username_edit.text().strip(),
        }
        return {
            'config': deepcopy(self.working_config),
            'remote_config': deepcopy(self.working_remote_config),
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_settings_dialog.py -v`
Expected: PASS with both new tests green

- [ ] **Step 5: Commit**

```bash
git add tests/test_settings_dialog.py core/settings_dialog.py ui/styles.py
git commit -m "$(cat <<'EOF'
test: lock settings dialog preview contract

Capture the extracted dialog's preview and result behavior first so the refactor can proceed without changing the live settings experience.
EOF
)"
```

### Task 2: 让 `QuadrantWidget` 只负责预览、提交、回滚和打开对话框

**Files:**
- Modify: `core/quadrant_widget.py:1-27`
- Modify: `core/quadrant_widget.py:761-1044`
- Modify: `core/quadrant_widget.py:1306-1392`
- Modify: `tests/test_database_manager_remote.py:556-860`

- [ ] **Step 1: Write the failing test**

```python
from copy import deepcopy
from unittest.mock import Mock, patch

from core.quadrant_widget import QuadrantWidget


def _widget_config():
    return {
        'quadrants': {
            'q1': {'color': '#FF6B6B', 'opacity': 0.8},
            'q2': {'color': '#4ECDC4', 'opacity': 0.8},
            'q3': {'color': '#FFE66D', 'opacity': 0.8},
            'q4': {'color': '#6D8EA0', 'opacity': 0.7},
        },
        'color_ranges': {
            'q1': {'hue_range': 30, 'saturation_range': 20, 'value_range': 20},
            'q2': {'hue_range': 30, 'saturation_range': 20, 'value_range': 20},
            'q3': {'hue_range': 30, 'saturation_range': 20, 'value_range': 20},
            'q4': {'hue_range': 30, 'saturation_range': 20, 'value_range': 20},
        },
        'size': {'width': 800, 'height': 600},
        'position': {'x': 100, 'y': 100},
        'control_panel': {'x': 20, 'y': 20},
        'ui': {'border_radius': 15},
        'auto_refresh': {'enabled': True, 'refresh_time': '00:02:00'},
    }


def test_apply_settings_preview_updates_runtime_state_without_persisting():
    widget = QuadrantWidget.__new__(QuadrantWidget)
    widget.config = _widget_config()
    widget.control_widget = Mock()
    widget.resize = Mock()
    widget.update = Mock()
    widget.center_control_panel = Mock()
    widget.save_config = Mock()
    widget._position_dirty = False

    QuadrantWidget.apply_settings_preview(widget, {
        'quadrants': {'q1': {'color': '#123456', 'opacity': 0.65}},
        'size': {'width': 960, 'height': 720},
        'ui': {'border_radius': 22},
    })

    assert widget.config['quadrants']['q1']['color'] == '#123456'
    assert widget.config['quadrants']['q1']['opacity'] == 0.65
    assert widget.config['size'] == {'width': 960, 'height': 720}
    assert widget.config['ui']['border_radius'] == 22
    widget.resize.assert_called_once_with(960, 720)
    widget.save_config.assert_not_called()


def test_show_settings_restores_snapshot_when_dialog_is_cancelled():
    widget = QuadrantWidget.__new__(QuadrantWidget)
    widget.config = _widget_config()
    widget.restore_settings_snapshot = Mock()
    widget.apply_settings_commit = Mock()

    fake_dialog = Mock()
    fake_dialog.exec.return_value = False
    fake_dialog.get_result.return_value = {}
    fake_dialog.previewChanged = Mock()
    fake_dialog.previewChanged.connect = Mock()

    with patch('core.quadrant_widget.RemoteConfigManager') as manager_cls, patch(
        'core.quadrant_widget.SettingsDialog',
        return_value=fake_dialog,
    ):
        manager_cls.return_value.get_server_config.return_value = {
            'enabled': False,
            'api_base_url': '',
            'api_token': '',
            'username': '',
        }
        QuadrantWidget.show_settings(widget, 'remote')

    widget.apply_settings_commit.assert_not_called()
    widget.restore_settings_snapshot.assert_called_once()


def test_show_settings_commits_dialog_result_when_accepted():
    widget = QuadrantWidget.__new__(QuadrantWidget)
    widget.config = _widget_config()
    widget.restore_settings_snapshot = Mock()
    widget.apply_settings_commit = Mock()

    fake_dialog = Mock()
    fake_dialog.exec.return_value = True
    fake_dialog.get_result.return_value = {
        'config': deepcopy(_widget_config()),
        'remote_config': {
            'enabled': True,
            'api_base_url': 'http://example.com',
            'api_token': 'token',
            'username': 'alice',
        },
    }
    fake_dialog.previewChanged = Mock()
    fake_dialog.previewChanged.connect = Mock()

    with patch('core.quadrant_widget.RemoteConfigManager') as manager_cls, patch(
        'core.quadrant_widget.SettingsDialog',
        return_value=fake_dialog,
    ):
        manager_cls.return_value.get_server_config.return_value = {
            'enabled': False,
            'api_base_url': '',
            'api_token': '',
            'username': '',
        }
        QuadrantWidget.show_settings(widget)

    widget.restore_settings_snapshot.assert_not_called()
    widget.apply_settings_commit.assert_called_once_with(fake_dialog.get_result.return_value)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_database_manager_remote.py -k "settings_preview or show_settings" -v`
Expected: FAIL with `AttributeError` for missing `apply_settings_preview` / `apply_settings_commit` / `restore_settings_snapshot`, or because `show_settings()` still tries to build the old inline dialog

- [ ] **Step 3: Write minimal implementation**

```python
from copy import deepcopy

from .settings_dialog import SettingsDialog


def show_settings(self, initial_tab: str = ''):
    original_config_snapshot = deepcopy(self.config)
    remote_config_manager = RemoteConfigManager()
    remote_config_snapshot = remote_config_manager.get_server_config()

    dialog = SettingsDialog(
        config_snapshot=original_config_snapshot,
        remote_config_snapshot=remote_config_snapshot,
        initial_tab=initial_tab,
        parent=self,
    )
    dialog.previewChanged.connect(self.apply_settings_preview)

    if dialog.exec():
        self.apply_settings_commit(dialog.get_result())
        return

    self.restore_settings_snapshot(original_config_snapshot)


def apply_settings_preview(self, payload: dict):
    self.apply_visual_settings(payload)


def apply_settings_commit(self, result: dict):
    remote_config_manager = RemoteConfigManager()
    remote_config_payload = dict(result['remote_config'])
    if not remote_config_manager.save_config(remote_config_payload):
        QMessageBox.warning(self, "保存失败", "远程配置保存失败，请稍后重试。")
        return

    self.config = deepcopy(result['config'])
    self.apply_visual_settings(self.config)
    self.save_config()
    self._apply_remote_config_to_db_manager(remote_config_payload)


def restore_settings_snapshot(self, snapshot: dict):
    self.config = deepcopy(snapshot)
    self.apply_visual_settings(self.config)


def apply_visual_settings(self, config: dict):
    quadrants = config.get('quadrants', {})
    for quadrant_id, quadrant_value in quadrants.items():
        self.config.setdefault('quadrants', {}).setdefault(quadrant_id, {}).update(quadrant_value)

    color_ranges = config.get('color_ranges', {})
    for quadrant_id, range_values in color_ranges.items():
        self.config.setdefault('color_ranges', {}).setdefault(quadrant_id, {}).update(range_values)

    if 'size' in config:
        self.config.setdefault('size', {}).update(config['size'])
        self.resize(self.config['size']['width'], self.config['size']['height'])
        self.control_widget.adjustSize()
        self.center_control_panel()
        self._position_dirty = True

    if 'ui' in config:
        self.config.setdefault('ui', {}).update(config['ui'])

    self.update()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_database_manager_remote.py -k "settings_preview or show_settings or bootstrap_remote_sync" -v`
Expected: PASS with the new settings-flow tests and the existing `_bootstrap_remote_sync()` regression tests all green

- [ ] **Step 5: Commit**

```bash
git add core/quadrant_widget.py tests/test_database_manager_remote.py
git commit -m "$(cat <<'EOF'
refactor: route settings through extracted dialog

Shrink QuadrantWidget down to preview, commit and rollback orchestration so the settings UI can evolve without bloating the main window class.
EOF
)"
```

### Task 3: 完成颜色范围与回滚细节，验证预览/提交/取消三条主路径

**Files:**
- Modify: `core/settings_dialog.py`
- Modify: `core/quadrant_widget.py:1306-1392`
- Modify: `tests/test_settings_dialog.py`
- Modify: `tests/test_database_manager_remote.py:556-860`

- [ ] **Step 1: Write the failing test**

```python
def test_visual_preview_should_include_color_ranges_and_round_trip_cancel_snapshot():
    widget = QuadrantWidget.__new__(QuadrantWidget)
    widget.config = _widget_config()
    widget.control_widget = Mock()
    widget.resize = Mock()
    widget.update = Mock()
    widget.center_control_panel = Mock()
    widget._position_dirty = False

    original = deepcopy(widget.config)
    QuadrantWidget.apply_settings_preview(widget, {
        'color_ranges': {'q1': {'hue_range': 45, 'saturation_range': 30, 'value_range': 25}},
        'size': {'width': 1000, 'height': 680},
        'ui': {'border_radius': 28},
    })
    QuadrantWidget.restore_settings_snapshot(widget, original)

    assert widget.config['color_ranges']['q1']['hue_range'] == 30
    assert widget.config['size'] == {'width': 800, 'height': 600}
    assert widget.config['ui']['border_radius'] == 15


def test_settings_dialog_should_emit_preview_for_color_range_changes():
    dialog = SettingsDialog(
        config_snapshot=self._build_config(),
        remote_config_snapshot={'enabled': False, 'api_base_url': '', 'api_token': '', 'username': ''},
    )
    payloads = []
    dialog.previewChanged.connect(payloads.append)

    dialog.hue_range_sliders['q1'].setValue(45)
    dialog.saturation_range_sliders['q1'].setValue(30)
    dialog.value_range_sliders['q1'].setValue(25)

    self.assertEqual(payloads[-1]['color_ranges']['q1']['hue_range'], 45)
    self.assertEqual(payloads[-1]['color_ranges']['q1']['saturation_range'], 30)
    self.assertEqual(payloads[-1]['color_ranges']['q1']['value_range'], 25)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_settings_dialog.py tests/test_database_manager_remote.py -k "color_range or cancel_snapshot" -v`
Expected: FAIL because color range preview controls are still incomplete or rollback does not yet restore every visual field

- [ ] **Step 3: Write minimal implementation**

```python
def _set_color_range(self, quadrant_id: str, range_type: str, value: int) -> None:
    self.working_config.setdefault('color_ranges', {}).setdefault(quadrant_id, {})[range_type] = value
    self._emit_preview()


for quadrant_id, quadrant_name in self.QUADRANT_NAMES.items():
    hue_slider = QSlider(Qt.Orientation.Horizontal)
    hue_slider.setRange(0, 180)
    hue_slider.setValue(self.working_config.get('color_ranges', {}).get(quadrant_id, {}).get('hue_range', 30))
    hue_slider.valueChanged.connect(
        lambda value, qid=quadrant_id: self._set_color_range(qid, 'hue_range', value)
    )
    self.hue_range_sliders[quadrant_id] = hue_slider

    saturation_slider = QSlider(Qt.Orientation.Horizontal)
    saturation_slider.setRange(0, 255)
    saturation_slider.setValue(self.working_config.get('color_ranges', {}).get(quadrant_id, {}).get('saturation_range', 20))
    saturation_slider.valueChanged.connect(
        lambda value, qid=quadrant_id: self._set_color_range(qid, 'saturation_range', value)
    )
    self.saturation_range_sliders[quadrant_id] = saturation_slider

    value_slider = QSlider(Qt.Orientation.Horizontal)
    value_slider.setRange(0, 255)
    value_slider.setValue(self.working_config.get('color_ranges', {}).get(quadrant_id, {}).get('value_range', 20))
    value_slider.valueChanged.connect(
        lambda value, qid=quadrant_id: self._set_color_range(qid, 'value_range', value)
    )
    self.value_range_sliders[quadrant_id] = value_slider

    color_layout.addRow(f"{quadrant_name} 色相范围:", hue_slider)
    color_layout.addRow(f"{quadrant_name} 饱和度范围:", saturation_slider)
    color_layout.addRow(f"{quadrant_name} 明度范围:", value_slider)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_settings_dialog.py tests/test_database_manager_remote.py -v`
Expected: PASS with all new settings-dialog and QuadrantWidget flow tests green

- [ ] **Step 5: Commit**

```bash
git add core/settings_dialog.py core/quadrant_widget.py tests/test_settings_dialog.py tests/test_database_manager_remote.py
git commit -m "$(cat <<'EOF'
fix: preserve live settings preview with rollback

Keep the existing responsive settings experience by previewing visual changes immediately while still rolling them back cleanly on cancel and persisting only on confirmation.
EOF
)"
```

### Task 4: 运行完整验证并做手动回归检查

**Files:**
- Modify: `core/settings_dialog.py` if verification exposes missing focus/close/cancel handling
- Modify: `core/quadrant_widget.py:761-1044` if verification exposes flow regressions

- [ ] **Step 1: Write the focused verification checklist**

```text
1. 打开设置页，拖动颜色透明度和色域滑块，主界面即时响应
2. 打开设置页，修改宽高和圆角，主界面即时响应
3. 点击取消，颜色/尺寸/圆角恢复到打开设置前
4. 点击确定，颜色/尺寸/圆角写入配置文件
5. 修改自动刷新，点击确定后配置持久化
6. 修改远程配置，点击确定后 RemoteConfigManager 和 db_manager 同步更新
7. 远程配置不完整时，`show_settings('remote')` 仍打开远程页签
```

- [ ] **Step 2: Run automated verification**

Run: `python -m pytest tests/test_settings_dialog.py tests/test_database_manager_remote.py tests/test_fluent_date_picker_migration.py -v`
Expected: PASS with no regressions in the extracted dialog flow or the existing Fluent helper migration tests

- [ ] **Step 3: Run the app for manual verification**

Run: `python main.py`
Expected: 应用正常启动；设置按钮可打开新对话框；实时预览、取消回滚、确定持久化均按 checklist 工作

- [ ] **Step 4: Fix only verification-found issues**

```python
def reject(self):
    super().reject()


def closeEvent(self, event):
    super().closeEvent(event)
```

只处理验证中真实暴露的问题，例如：
- 关闭窗口按钮没有走取消路径
- 某个滑块未触发 previewChanged
- 远程页签初始定位失效

- [ ] **Step 5: Commit**

```bash
git add core/settings_dialog.py core/quadrant_widget.py tests/test_settings_dialog.py tests/test_database_manager_remote.py
git commit -m "$(cat <<'EOF'
test: verify extracted settings dialog end to end

Close the refactor with automated and manual checks so the new dialog keeps the existing live-preview behavior without regressing remote settings flow.
EOF
)"
```
