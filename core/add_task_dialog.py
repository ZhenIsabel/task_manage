from PyQt6.QtCore import Qt,QDate
from PyQt6.QtWidgets import (QDialog, QWidget, QVBoxLayout,
                             QLabel, QLineEdit,
                             QPushButton, QHBoxLayout, QComboBox, QTextEdit,QFileDialog)
from PyQt6.QtGui import QMouseEvent

from ui.fluent import ComboBox, create_calendar_picker, get_date_string_from_picker, is_date_picker
from ui.notifications import show_warning
from ui.styles import StyleManager
from ui.degree_badges import is_degree_field
import logging
logger = logging.getLogger(__name__)  # 自动获取模块名

class AddTaskDialog(QDialog):
    def __init__(self, parent=None, task_fields=None):
        # ❶ 直接把 QDialog 设为「无边框」窗口
        super().__init__(parent, flags=Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        # 不再使用透明背景，避免对话框外侧出现可透底的透明区域
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        task_fields = task_fields or []
        self._task_fields = task_fields

        # ------- 外层透明壳，什么都不画 ------- #

        # ❸ 真正的白色圆角面板
        panel = QWidget(self)
        panel.setObjectName("panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(30, 30, 30, 30)
        panel_layout.setSpacing(5)

        # 样式改为用 styles.py 的 StyleManager 管理
        style_manager = StyleManager()
        # 目标面板采用“外壳 + 共享表单控件”组合，避免重复叠加规则
        add_task_dialog_stylesheet = style_manager.get_stylesheet("dialog_panel_shell").format()
        panel_form_controls_stylesheet = style_manager.get_stylesheet("panel_form_controls").format()
        panel.setStyleSheet(add_task_dialog_stylesheet + panel_form_controls_stylesheet)

        # ------- 下面放你的字段、按钮 ------- #
        self.inputs = {}
        index = 0
        while index < len(task_fields):
            field = task_fields[index]
            next_field = task_fields[index + 1] if index + 1 < len(task_fields) else None

            if self._should_group_degree_fields(field, next_field):
                self._add_degree_field_row(panel, panel_layout, field, next_field)
                index += 2
                continue

            self._add_single_field(panel, panel_layout, field)
            index += 1

        # 按钮
        btn_row = QHBoxLayout()
        ok = QPushButton("确定"); ok.clicked.connect(self._try_accept)
        cancel = QPushButton("取消"); cancel.clicked.connect(self.reject)
        btn_row.addWidget(ok); btn_row.addWidget(cancel)
        panel_layout.addLayout(btn_row)

        # ❹ 自动根据内容调大小，再把“壳”和“面板”都居中放
        # 外圈透明壳/留白去掉：把“壳”尺寸与真实面板对齐
        shadow_margin = 0
        # 让 panel 先自适应内容
        panel.setMinimumWidth(400)
        panel_layout.activate()
        panel.adjustSize()
        # 让壳与面板对齐
        self.resize(panel.width() + shadow_margin * 2, panel.height() + shadow_margin * 2)
        # 把面板放回壳左上角
        panel.move(shadow_margin, shadow_margin)
        # ❺ 可选：实现拖动窗口（因为没了系统标题栏）
        self._drag_pos = None

    def _should_group_degree_fields(self, current_field, next_field):
        return (
            current_field
            and next_field
            and current_field.get('name') == 'urgency'
            and next_field.get('name') == 'importance'
            and is_degree_field(current_field.get('name'))
            and is_degree_field(next_field.get('name'))
        )

    def _create_field_input(self, parent, field):
        default_value = field.get('default', '')
        if field['type'] == 'date':
            initial_date = QDate.fromString(default_value, "yyyy-MM-dd") if default_value else QDate.currentDate()
            return create_calendar_picker(parent, initial_date)
        if field['type'] == 'select':
            widget = ComboBox()
            for option in field.get('options', []):
                widget.addItem(option)
            if default_value and default_value in field.get('options', []):
                widget.setCurrentText(default_value)
            return widget
        if field['type'] == 'multiline':
            widget = QTextEdit()
            widget.setPlaceholderText("请输入备注...")
            widget.setMinimumHeight(100)
            if default_value:
                widget.setText(str(default_value))
            return widget
        if field['type'] == 'file':
            return None
        return QLineEdit(str(default_value))

    def _add_single_field(self, panel, parent_layout, field):
        lab = QLabel(f"{field['label']}{' *' if field.get('required') else ''}")
        parent_layout.addWidget(lab)

        if field['type'] == 'file':
            dir_layout = QHBoxLayout()
            path_edit = QLineEdit()
            path_edit.setPlaceholderText("请选择文件夹路径...")
            path_edit.setReadOnly(True)
            default_value = field.get('default', '')
            if default_value:
                path_edit.setText(str(default_value))
            btn = QPushButton("选择")
            btn.clicked.connect(lambda _, we=path_edit: self.choose_dir(we))
            dir_layout.addWidget(path_edit)
            dir_layout.addWidget(btn)
            parent_layout.addLayout(dir_layout)
            self.inputs[field['name']] = path_edit
            return

        widget = self._create_field_input(panel, field)
        parent_layout.addWidget(widget)
        self.inputs[field['name']] = widget

    def _add_degree_field_row(self, panel, parent_layout, first_field, second_field):
        row = QHBoxLayout()
        row.setSpacing(12)

        for field in (first_field, second_field):
            column_widget = QWidget(panel)
            column_layout = QVBoxLayout(column_widget)
            column_layout.setContentsMargins(0, 0, 0, 0)
            column_layout.setSpacing(5)
            column_layout.addWidget(QLabel(f"{field['label']}{' *' if field.get('required') else ''}"))
            widget = self._create_field_input(panel, field)
            column_layout.addWidget(widget)
            row.addWidget(column_widget, 1)
            self.inputs[field['name']] = widget

        parent_layout.addLayout(row)

    # ---------- 拖动实现 ----------
    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, e: QMouseEvent):
        if self._drag_pos and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e: QMouseEvent):
        self._drag_pos = None

    def choose_dir(self, widget):
        """Handle directory selection for file fields"""
        path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if path:
            widget.setText(path)


    def _try_accept(self):
        task_data = self.get_data()
        for f in self._task_fields:
            if f.get("required") and not task_data.get(f["name"]):
                show_warning(widget=self,title= "提示",content= f"{f['label']} 为必填项")
                return
        self.accept()

    def get_data(self):
        """把表单内容打包成 dict 返回"""
        data = {}
        for name, w in self.inputs.items():
            if is_date_picker(w):
                data[name] = get_date_string_from_picker(w)
            elif isinstance(w, (QComboBox, ComboBox)):
                data[name] = w.currentText()
            elif isinstance(w, QTextEdit):
                data[name] = w.toPlainText()
            else:
                data[name] = w.text()
        return data