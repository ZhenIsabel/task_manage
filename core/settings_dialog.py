from __future__ import annotations

from copy import deepcopy

from PyQt6.QtCore import Qt, QTime, pyqtSignal
from PyQt6.QtGui import QColor, QMouseEvent
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


def _coerce_int_in_range(raw, default, lo, hi):
    if raw is None:
        return default
    try:
        n = int(raw)
    except (TypeError, ValueError):
        try:
            n = int(float(raw))
        except (TypeError, ValueError):
            return default
    return max(lo, min(hi, n))


def _coerce_float_in_range(raw, default, lo, hi):
    if raw is None:
        return default
    try:
        f = float(raw)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, f))


_DEFAULT_QUADRANT_COLORS = {
    "q1": {"color": "#FF6B6B", "opacity": 0.15},
    "q2": {"color": "#4ECDC4", "opacity": 0.15},
    "q3": {"color": "#FFD93D", "opacity": 0.15},
    "q4": {"color": "#95E1D3", "opacity": 0.15},
}

_DEFAULT_COLOR_RANGE = {"hue_range": 30, "saturation_range": 20, "value_range": 20}

QUADRANT_NAMES = {
    "q1": "重要且紧急（右上）",
    "q2": "重要不紧急（左上）",
    "q3": "不重要但紧急（右下）",
    "q4": "不重要不紧急（左下）",
}


def _normalize_quadrants(raw):
    raw = raw or {}
    out = {}
    for q in ("q1", "q2", "q3", "q4"):
        d = _DEFAULT_QUADRANT_COLORS[q]
        src = raw.get(q) if isinstance(raw.get(q), dict) else {}
        out[q] = {
            "color": src.get("color", d["color"]),
            "opacity": _coerce_float_in_range(src.get("opacity"), d["opacity"], 0.0, 1.0),
        }
    return out


def _coerce_int_default_on_oob(raw, default, lo, hi):
    """可解析为 int 且在 [lo, hi] 内则采用，否则返回 default（越界不钳制，直接回退）。"""
    if raw is None:
        return default
    try:
        n = int(raw)
    except (TypeError, ValueError):
        try:
            n = int(float(raw))
        except (TypeError, ValueError):
            return default
    if n < lo or n > hi:
        return default
    return n


def _normalize_color_ranges(raw):
    raw = raw or {}
    out = {}
    for q in ("q1", "q2", "q3", "q4"):
        base = dict(_DEFAULT_COLOR_RANGE)
        src = raw.get(q) if isinstance(raw.get(q), dict) else {}
        base["hue_range"] = _coerce_int_default_on_oob(
            src.get("hue_range"), base["hue_range"], 0, 180
        )
        base["saturation_range"] = _coerce_int_default_on_oob(
            src.get("saturation_range"), base["saturation_range"], 0, 255
        )
        base["value_range"] = _coerce_int_default_on_oob(
            src.get("value_range"), base["value_range"], 0, 255
        )
        out[q] = base
    return out


class SettingsDialog(QDialog):
    """独立设置对话框。视觉属性变更通过 previewChanged 实时通知父窗口；
    确定后由调用方通过 get_result() 拿到完整配置。"""

    previewChanged = pyqtSignal(dict)

    def __init__(self, parent=None, initial=None):
        super().__init__(parent, flags=Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        initial = initial or {}
        cfg = initial.get("config") or {}

        self._working_quadrants = _normalize_quadrants(cfg.get("quadrants"))
        self._working_size = dict(cfg.get("size") or {})
        self._working_ui = dict(cfg.get("ui") or {})
        self._working_auto_refresh = dict(cfg.get("auto_refresh") or {})
        self._working_color_ranges = _normalize_color_ranges(cfg.get("color_ranges"))
        self._working_remote = dict(initial.get("remote_config") or {})

        self._drag_pos = None
        self._build_ui(initial.get("initial_tab", ""))

    # ------------------------------------------------------------------ UI
    def _build_ui(self, initial_tab: str) -> None:
        panel = QWidget(self)
        panel.setObjectName("settings_panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(30, 30, 30, 30)
        panel_layout.setSpacing(20)

        style_manager = StyleManager()
        shell = style_manager.get_stylesheet("dialog_panel_shell").format()
        settings_sheet = style_manager.get_stylesheet("settings_panel").format()
        panel.setStyleSheet(shell + settings_sheet)

        tab_widget = QTabWidget()
        tab_widget.setStyleSheet(
            "QTabWidget::pane { border: 1px solid #dddddd; background-color: white; border-radius: 8px; }"
            "QTabBar::tab { background-color: #f5f5f5; color: #333; border: 1px solid #dddddd; "
            "border-bottom: none; padding: 10px 20px; margin-right: 2px; "
            "border-top-left-radius: 8px; border-top-right-radius: 8px; "
            "font-family: '微软雅黑'; font-size: 13px; }"
            "QTabBar::tab:selected { background-color: white; color: #4ECDC4; font-weight: bold; }"
        )

        color_tab = self._build_color_tab()
        size_tab = self._build_size_tab()
        ui_tab = self._build_ui_tab()
        remote_tab = self._build_remote_tab()

        tab_widget.addTab(color_tab, "颜色设置")
        tab_widget.addTab(size_tab, "大小设置")
        tab_widget.addTab(ui_tab, "界面设置")
        tab_widget.addTab(remote_tab, "远程设置")

        if initial_tab == "remote":
            tab_widget.setCurrentWidget(remote_tab)

        self._tab_widget = tab_widget
        panel_layout.addWidget(tab_widget)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(ok_btn)
        btn_row.addWidget(cancel_btn)
        panel_layout.addLayout(btn_row)

        panel.setMinimumWidth(600)
        panel_layout.activate()
        panel.adjustSize()
        self.resize(panel.width(), panel.height())
        panel.move(0, 0)

    # ---- 颜色标签页 ----
    def _build_color_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        self._color_buttons: dict[str, QPushButton] = {}
        self._opacity_sliders: dict[str, QSlider] = {}
        self._color_range_sliders: dict[str, dict[str, QSlider]] = {}

        for q_id, q_name in QUADRANT_NAMES.items():
            qdata = self._working_quadrants[q_id]

            color_btn = QPushButton()
            color_btn.setStyleSheet(f"background-color: {qdata['color']}; border-radius: 15px;")
            color_btn.setFixedSize(30, 30)
            color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            color_btn.clicked.connect(lambda _checked, qid=q_id: self._choose_color(qid))
            self._color_buttons[q_id] = color_btn

            opacity_slider = QSlider(Qt.Orientation.Horizontal)
            opacity_slider.setRange(1, 100)
            opacity_slider.setValue(int(qdata["opacity"] * 100))
            opacity_slider.valueChanged.connect(
                lambda val, qid=q_id: self._set_opacity(qid, val)
            )
            self._opacity_sliders[q_id] = opacity_slider

            cr = self._working_color_ranges[q_id]
            hue_s = QSlider(Qt.Orientation.Horizontal)
            hue_s.setObjectName(f"settings_{q_id}_hue_range_slider")
            hue_s.setRange(0, 180)
            hue_s.setValue(cr["hue_range"])
            hue_s.valueChanged.connect(
                lambda v, qid=q_id: self._set_color_range(qid, "hue_range", v)
            )

            sat_s = QSlider(Qt.Orientation.Horizontal)
            sat_s.setObjectName(f"settings_{q_id}_saturation_range_slider")
            sat_s.setRange(0, 255)
            sat_s.setValue(cr["saturation_range"])
            sat_s.valueChanged.connect(
                lambda v, qid=q_id: self._set_color_range(qid, "saturation_range", v)
            )

            val_s = QSlider(Qt.Orientation.Horizontal)
            val_s.setObjectName(f"settings_{q_id}_value_range_slider")
            val_s.setRange(0, 255)
            val_s.setValue(cr["value_range"])
            val_s.valueChanged.connect(
                lambda v, qid=q_id: self._set_color_range(qid, "value_range", v)
            )

            self._color_range_sliders[q_id] = {
                "hue_range": hue_s,
                "saturation_range": sat_s,
                "value_range": val_s,
            }

            layout.addRow(f"{q_name} 颜色:", color_btn)
            layout.addRow(f"{q_name} 透明度:", opacity_slider)
            layout.addRow(f"{q_name} 色相范围:", hue_s)
            layout.addRow(f"{q_name} 饱和度范围:", sat_s)
            layout.addRow(f"{q_name} 明度范围:", val_s)

        return widget

    # ---- 大小标签页 ----
    def _build_size_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        self._width_spin = QSpinBox()
        self._width_spin.setObjectName("settings_width_spin")
        self._width_spin.setRange(300, 2000)
        self._width_spin.setValue(
            _coerce_int_in_range(self._working_size.get("width"), 1000, 300, 2000)
        )
        self._width_spin.valueChanged.connect(lambda v: self._set_size("width", v))

        self._height_spin = QSpinBox()
        self._height_spin.setObjectName("settings_height_spin")
        self._height_spin.setRange(300, 2000)
        self._height_spin.setValue(
            _coerce_int_in_range(self._working_size.get("height"), 800, 300, 2000)
        )
        self._height_spin.valueChanged.connect(lambda v: self._set_size("height", v))

        layout.addRow("宽度:", self._width_spin)
        layout.addRow("高度:", self._height_spin)
        return widget

    # ---- 界面标签页 ----
    def _build_ui_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        self._border_radius_spin = QSpinBox()
        self._border_radius_spin.setObjectName("settings_border_radius_spin")
        self._border_radius_spin.setRange(0, 50)
        self._border_radius_spin.setValue(
            _coerce_int_in_range(self._working_ui.get("border_radius"), 15, 0, 50)
        )
        self._border_radius_spin.valueChanged.connect(self._set_border_radius)

        ar = self._working_auto_refresh
        self._auto_refresh_checkbox = QCheckBox("启用自动刷新")
        self._auto_refresh_checkbox.setChecked(ar.get("enabled", True))

        self._refresh_time_edit = QTimeEdit()
        self._refresh_time_edit.setDisplayFormat("HH:mm:ss")
        rts = ar.get("refresh_time", "00:02:00")
        try:
            h, m, s = map(int, rts.split(":"))
            self._refresh_time_edit.setTime(QTime(h, m, s))
        except Exception:
            self._refresh_time_edit.setTime(QTime(0, 2, 0))

        hint = QLabel("每天在设定时间自动刷新页面并检查定时任务")
        hint.setStyleSheet("color: #666; font-size: 11px;")
        hint.setWordWrap(True)

        layout.addRow("圆角半径:", self._border_radius_spin)
        layout.addRow("", QLabel(""))
        layout.addRow(self._auto_refresh_checkbox)
        layout.addRow("刷新时间:", self._refresh_time_edit)
        layout.addRow("", hint)
        return widget

    # ---- 远程标签页 ----
    def _build_remote_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        r = self._working_remote
        self._remote_enabled = QCheckBox("启用远程同步")
        self._remote_enabled.setObjectName("settings_remote_enabled_checkbox")
        self._remote_enabled.setChecked(bool(r.get("enabled", False)))

        self._remote_url = QLineEdit(str(r.get("api_base_url", "")))
        self._remote_url.setObjectName("settings_remote_api_base_url_edit")
        self._remote_url.setPlaceholderText("http://example.com")

        self._remote_username = QLineEdit(str(r.get("username", "")))
        self._remote_username.setObjectName("settings_remote_username_edit")
        self._remote_username.setPlaceholderText("用户名")

        self._remote_token = QLineEdit(str(r.get("api_token", "")))
        self._remote_token.setObjectName("settings_remote_api_token_edit")
        self._remote_token.setPlaceholderText("API Token")

        hint = QLabel("关闭远程同步后，下次启动将不会检测远程服务器。")
        hint.setStyleSheet("color: #666; font-size: 11px;")
        hint.setWordWrap(True)

        layout.addRow(self._remote_enabled)
        layout.addRow("服务器地址:", self._remote_url)
        layout.addRow("用户名:", self._remote_username)
        layout.addRow("访问令牌:", self._remote_token)
        layout.addRow("", hint)
        return widget

    # ----------------------------------------------- Drag (frameless window)
    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, e: QMouseEvent):
        if self._drag_pos and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e: QMouseEvent):
        self._drag_pos = None

    # ----------------------------------------------- Internal setters
    def _choose_color(self, q_id: str) -> None:
        cur = QColor(self._working_quadrants[q_id]["color"])
        dlg = QColorDialog(cur, self)
        dlg.setWindowTitle("选择象限颜色")
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name = dlg.selectedColor().name()
            self._working_quadrants[q_id]["color"] = name
            self._color_buttons[q_id].setStyleSheet(
                f"background-color: {name}; border-radius: 15px;"
            )
            self._emit_preview()

    def _set_opacity(self, q_id: str, value: int) -> None:
        self._working_quadrants[q_id]["opacity"] = value / 100.0
        self._emit_preview()

    def _set_color_range(self, q_id: str, key: str, value: int) -> None:
        self._working_color_ranges[q_id][key] = value
        self._emit_preview()

    def _set_size(self, dim: str, value: int) -> None:
        self._working_size[dim] = value
        self._emit_preview()

    def _set_border_radius(self, value: int) -> None:
        self._working_ui["border_radius"] = value
        self._emit_preview()

    # ----------------------------------------------- Preview payload
    def _preview_payload(self) -> dict:
        return {
            "quadrants": deepcopy(self._working_quadrants),
            "size": dict(self._working_size),
            "ui": dict(self._working_ui),
            "color_ranges": deepcopy(self._working_color_ranges),
        }

    def _emit_preview(self) -> None:
        self.previewChanged.emit(self._preview_payload())

    # ----------------------------------------------- Result (called after accept)
    def get_result(self) -> dict:
        return {
            "config": {
                "quadrants": deepcopy(self._working_quadrants),
                "size": dict(self._working_size),
                "ui": dict(self._working_ui),
                "color_ranges": deepcopy(self._working_color_ranges),
                "auto_refresh": {
                    "enabled": self._auto_refresh_checkbox.isChecked(),
                    "refresh_time": self._refresh_time_edit.time().toString("HH:mm:ss"),
                },
            },
            "remote_config": {
                "enabled": self._remote_enabled.isChecked(),
                "api_base_url": self._remote_url.text().strip(),
                "api_token": self._remote_token.text().strip(),
                "username": self._remote_username.text().strip(),
            },
        }
