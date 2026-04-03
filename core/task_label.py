from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QCheckBox,
                            QLabel, QInputDialog,
                            QFrame, QSizePolicy, QDialog,
                            QLayout,QPushButton, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, pyqtSignal,  QEvent, QUrl
from PyQt6.QtGui import QColor, QCursor,  QDesktopServices
try:
    import sip  # 用于判断 PyQt 对象是否已被销毁
except Exception:
    sip = None
import os
from datetime import datetime

from .add_task_dialog import AddTaskDialog
from ui.scrollbar import FluentScrollArea
from ui.notifications import show_error, resolve_notification_host,show_success,show_warning
from ui.styles import StyleManager
from ui.degree_badges import create_degree_display_widget, build_degree_badge_stylesheet, get_status_badge_meta
from ui.ui import MyColorDialog
from config.config_manager import load_config
import logging
logger = logging.getLogger(__name__)  # 自动获取模块名

class TaskLabel(QWidget):
    """任务标签类，表示一个工作项"""
    deleteRequested = pyqtSignal(object)
    statusChanged = pyqtSignal(object)
    _editable_fields_cache = None

    @classmethod
    def get_editable_fields(cls, field_definitions=None):
        """获取可编辑字段，优先使用调用方传入的预加载配置。"""
        if field_definitions is not None:
            return field_definitions

        if cls._editable_fields_cache is None:
            config = load_config()
            fields = config.get('task_fields', [])
            if not fields:
                # 如果配置中没有字段定义，使用默认字段
                fields = [
                    {"name": "text",      "label": "任务内容", "type": "text",  "required": True},
                    {"name": "due_date",  "label": "到期日期", "type": "date",  "required": False},
                    {"name": "urgency",   "label": "紧急程度", "type": "select", "required": False, "options": ["高", "低"]},
                    {"name": "importance","label": "重要程度", "type": "select", "required": False, "options": ["高", "低"]},
                    {"name": "notes",     "label": "备注",     "type": "multiline",  "required": False},
                    {"name": "directory","label": "目录","type": "file", "required": False},
                    {"name":"create_date","label":"创建日期","type":"date","required":False},
                    {"name":"completed_date","label":"完成日期","type":"date","required":False}
                ]
            cls._editable_fields_cache = fields

        return cls._editable_fields_cache
    
    @staticmethod
    def _format_detail_notes_html(notes):
        if notes is None:
            return ""
        return str(notes).replace("\n", "<br>")
    def __init__(self, task_id, color,completed=False, parent=None, field_definitions=None, **fields):
        try:
            super().__init__(parent)
        except Exception as e:
            logger.error(f"任务标签初始化失败 (task_id: {task_id}): {str(e)}", exc_info=True)
            raise
        self.task_id = task_id
        self.setObjectName("task_label_root")
        self.color = QColor(color)

        # ---- 自动把 EDITABLE_FIELDS 里声明的 key 赋成属性 ----
        self._field_definitions = list(self.get_editable_fields(field_definitions))
        for meta in self._field_definitions:
            key = meta["name"]
            setattr(self, key, fields.get(key, ""))  # 添加默认值

        # 初始化拖拽状态
        self.dragging = False
        self.drag_start_position = None
        self._draggable = False  # 初始化 _draggable 属性，默认为不可拖动
        
        # 到期状态
        self.is_overdue = False

        
        # 如果你想限制最小宽度：
        self.setMinimumWidth(80)
        
        # 详情浮窗
        self.detail_popup = None
        
        # 设置布局
        layout = QVBoxLayout()
        
        # 添加复选框
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(completed) # 默认不勾选
        self.checkbox.stateChanged.connect(self.on_status_changed)
        
        # 添加文本标签
        self.label = QLabel(getattr(self, 'text', ''))  # 使用属性获取文本
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.label.setObjectName("TagText")  # ★ 关键：给 QLabel 起名，这样才能用 setStyleSheet 来设置样式
        # 让文字 pill 根据文本长度扩展宽度，高度跟随文本行高
        self.label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # 添加到期日期标签（如果有）
        self.due_date_label = None
        if self.due_date:
            self.due_date_label = QLabel(f"到期: {self.due_date}")
            self.due_date_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            style_manager = StyleManager()
            self.due_date_label.setStyleSheet(style_manager.get_stylesheet("due_date_label"))
        
        # 将复选框和标签放在同一行
        title_layout = QHBoxLayout()
        title_layout.addWidget(self.checkbox)
        title_layout.addWidget(self.label)
        # title_layout.addStretch()
        title_layout.setContentsMargins(0, 0, 0, 0)   # 内边距全部清 0
        title_layout.setSpacing(4)                    # 复选框 <-> pill 间距 4 px
        
        layout.addLayout(title_layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        # if self.due_date_label:
        #     layout.addWidget(self.due_date_label)
        
        self.setLayout(layout)
        self._ensure_subtle_shadow()
        
        # 初始化时检查到期状态
        self.check_overdue_status()
        
        self.update_appearance()
        
        # 文本可能改动时，随时调整标签尺寸
        self.label.adjustSize()
        self.layout().setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        # 设置鼠标追踪
        self.setMouseTracking(True)

    def _ensure_subtle_shadow(self):
        """给任务标签增加一层很淡的悬浮感，不改变原有布局。"""
        effect = self.graphicsEffect()
        if not isinstance(effect, QGraphicsDropShadowEffect):
            effect = QGraphicsDropShadowEffect(self)
            self.setGraphicsEffect(effect)

        effect.setBlurRadius(8)
        effect.setOffset(0, 2)
        effect.setColor(QColor(0, 0, 0, 58))
    
    def update_appearance(self):
        """更新标签外观"""
        try:
            if self.checkbox.isChecked(): # 🔥🔥🔥用真实勾选状态
                bg_color = QColor(200, 200, 200)  # 灰色背景
                text_color = QColor(100, 100, 100)  # 深灰色文字
            else:
                bg_color = self.color
                text_color = QColor(0, 0, 0) if self.color.lightness() > 128 else QColor(255, 255, 255)
        except Exception as e:
            logger.error(f"更新任务标签外观失败 (task_id: {self.task_id}): {str(e)}", exc_info=True)
            return
        style_manager = StyleManager()
        indicator_size = 14  # 和字体高度差不多

        # 获取样式模板并格式化
        stylesheet_template = style_manager.get_stylesheet("task_label")
        
        # 根据到期状态选择样式
        if self.is_overdue and not self.checkbox.isChecked():
            # 到期任务使用带橙色描边的样式
            stylesheet_template = style_manager.get_stylesheet("task_label_overdue")
        
        stylesheet = stylesheet_template.format(
            bg_color_red=bg_color.red(),
            bg_color_green=bg_color.green(),
            bg_color_blue=bg_color.blue(),
            text_color_red=text_color.red(),
            text_color_green=text_color.green(),
            text_color_blue=text_color.blue(),
            indicator_size=indicator_size
        )
        self.setStyleSheet(stylesheet)
        self._ensure_subtle_shadow()
    
    def on_status_changed(self, state):
        """复选框状态改变时的处理"""
        # 更新外观
        self.update_appearance()
        
        # 如果detail_popup存在，刷新里面的状态文字
        if hasattr(self, 'status_label') and self.status_label:
            self.update_status_label()

        # 更新completed_date
        if self.checkbox.isChecked():
            self.completed_date = datetime.now().strftime('%Y-%m-%d')
            logger.info(f"任务 {self.task_id} 已完成")
        else:
            self.completed_date = ""
            logger.info(f"任务 {self.task_id} 完成状态取消")
        
        # 重新检查到期状态（完成的任务不应该显示为到期）
        self.check_overdue_status()
        
        # 触发保存信号
        self.statusChanged.emit(self)
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        try:
            if event.button() == Qt.MouseButton.LeftButton and getattr(self, '_draggable', True):
                self.dragging = True
                self.drag_start_position = event.pos()
        except Exception as e:
            logger.error(f"鼠标按下事件处理失败 (task_id: {self.task_id}): {str(e)}", exc_info=True)
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        try:
            if self.dragging and (event.buttons() & Qt.MouseButton.LeftButton):
                # 计算移动距离
                delta = event.pos() - self.drag_start_position
                new_pos = self.pos() + delta
                
                # 添加边界限制，防止拖动到 x<20, y<20 的位置
                if new_pos.x() < 20:
                    new_pos.setX(20)
                if new_pos.y() < 20:
                    new_pos.setY(20)
                    
                self.move(new_pos)
                event.accept()
        except Exception as e:
            logger.error(f"鼠标移动事件处理失败 (task_id: {self.task_id}): {str(e)}", exc_info=True)
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.MouseButton.LeftButton and self.dragging:
            self.dragging = False
            # 触发状态改变信号，以便保存位置和更新urgency/importance
            self.statusChanged.emit(self)
    
    def mouseDoubleClickEvent(self, event):
        """鼠标双击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            dialog = QInputDialog(self)
            dialog.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            dialog.setInputMode(QInputDialog.InputMode.TextInput)
            dialog.setLabelText("任务内容:")
            dialog.setTextValue(self.text)
            dialog.setWindowTitle("编辑任务")
    
    def set_draggable(self, draggable):
        """设置任务标签是否可拖动"""
        self._draggable = draggable
        # 可能还需要更新鼠标样式或其他视觉提示
        self.setCursor(Qt.CursorShape.SizeAllCursor if draggable else Qt.CursorShape.ArrowCursor)

    def set_overdue_status(self, is_overdue):
        """设置任务的到期状态"""
        if self.is_overdue != is_overdue:
            self.is_overdue = is_overdue
            # 更新外观以显示到期状态
            self.update_appearance()
            logger.debug(f"任务 {self.task_id} 到期状态更新: {is_overdue}")

    def check_overdue_status(self):
        """检查并更新任务的到期状态"""
        if hasattr(self, 'due_date') and self.due_date:
            try:
                from datetime import datetime
                due_date = datetime.strptime(self.due_date, '%Y-%m-%d').date()
                today = datetime.now().date()
                is_overdue = due_date <= today
                self.set_overdue_status(is_overdue)
            except ValueError as e:
                logger.warning(f"任务 {self.task_id} 的到期日期格式错误: {self.due_date}, 错误: {e}")

    def contextMenuEvent(self, event):
        """右键菜单事件"""
        try:
            parent = self.parent()
            # 关闭全局的 popup
            if hasattr(parent, "current_detail_popup") and parent.current_detail_popup:
                parent.current_detail_popup.hide()
                parent.current_detail_popup.deleteLater()
                parent.current_detail_popup = None

            # 创建新的
            self.create_detail_popup()
            self.position_detail_popup()
            self.detail_popup.show()
            self.detail_popup.raise_()

            # 记录到全局
            if hasattr(parent, "current_detail_popup"):
                parent.current_detail_popup = self.detail_popup
        except Exception as e:
            logger.error(f"右键菜单事件处理失败 (task_id: {self.task_id}): {str(e)}", exc_info=True)

    def edit_task(self):
        """编辑任务内容"""
        # 获取当前字段配置
        task_fields = []
        for meta in self._field_definitions:
            value = getattr(self, meta["name"], "") or ""  # 双重空值保护
            task_fields.append(dict(meta, default=value))

        # 如果没有找到字段配置，使用默认字段
        if not task_fields:
            task_fields = [
                {'name': 'text', 'label': '任务内容', 'type': 'text', 'required': True},
                {'name': 'due_date', 'label': '到期日期', 'type': 'date', 'required': False}
            ]

        dialog = AddTaskDialog(self, task_fields=task_fields)
        # 3) 如果点击「确定」就取回数据
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return                          # 点了取消

        # 从对话框中获取字段值
        task_data = dialog.get_data()   # ← 只要这一行就拿到全部字段值

        # 检查必填
        for f in task_fields:
            if f.get("required") and not task_data.get(f["name"]):
                show_warning(self,"提示",f"{f['label']} 为必填项")
                return

        # 更新任务数据
        for meta in self._field_definitions:
            key = meta["name"]
            if key in task_data:
                setattr(self, key, task_data[key])
        # 特殊处理标签文本更新
        self.label.setText(self.text)
        
        # 更新到期日期标签
        if hasattr(self, 'due_date_label') and self.due_date_label:
            if self.due_date:
                self.due_date_label.setText(f"到期: {self.due_date}")
            else:
                self.due_date_label.setText("")
        
        # 重新检查到期状态
        self.check_overdue_status()
        
        # 触发保存
        self.statusChanged.emit(self)
    
    def change_color(self):
        """更改标签颜色"""
        color_dialog = MyColorDialog(self.color, self)
        color_dialog.setWindowTitle("选择标签颜色")
        if color_dialog.exec() == QDialog.DialogCode.Accepted:
            color = color_dialog.selectedColor()
            if color.isValid():
                self.color = color
                self.update_appearance()
                # 触发保存信号
                self.statusChanged.emit(self)
    
    def get_data(self):
        """获取标签数据"""
        data = {
            'id': self.task_id,
            'color': self.color.name(),
            'position': {'x': self.pos().x(), 'y': self.pos().y()},
            'completed': self.checkbox.isChecked(),
        }
        
        # 添加所有可编辑字段
        for meta in self._field_definitions:
            key = meta["name"]
            value = getattr(self, key, "")
            data[key] = value if value is not None else ""

        return data
        
    def position_detail_popup(self):
        """调整详情弹出窗口的位置"""
        if not self.detail_popup:
            return
            
        # 获取鼠标相对于屏幕的位置
        cursor_pos = QCursor.pos()
        
        # 将屏幕坐标转换为父窗口的坐标
        parent_pos = self.parent().mapFromGlobal(cursor_pos)
        
        # 计算弹出窗口的宽高
        popup_width = self.detail_popup.width()
        popup_height = self.detail_popup.height()
        
        # 设置弹出窗口位置（使用相对于父窗口的坐标）
        self.detail_popup.move(parent_pos)
        
        # 确保弹出窗口不会超出父窗口边界
        parent_width = self.parent().width()
        parent_height = self.parent().height()
        
        if parent_pos.x() + popup_width > parent_width:
            parent_pos.setX(parent_width - popup_width)
        
        if parent_pos.y() + popup_height > parent_height:
            parent_pos.setY(parent_height - popup_height)
            
        # 设置最终位置
        self.detail_popup.move(parent_pos)
    
    def create_detail_popup(self):
        """创建详情弹出窗口"""
        style_manager = StyleManager()
        parent_widget = self.parent()
        self.detail_popup = QFrame(parent_widget if parent_widget else self)
        self.detail_popup.setObjectName("task_detail_popup")
        self.detail_popup.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.detail_popup.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.detail_popup.setStyleSheet(style_manager.get_stylesheet("detail_popup").format())

        layout = QVBoxLayout(self.detail_popup)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        title_text = self.text
        if isinstance(self.text, tuple):
            title_text = self.text[0]

        header_section = QWidget(self.detail_popup)
        header_section.setObjectName("detail_header_section")
        header_layout = QHBoxLayout(header_section)
        header_layout.setContentsMargins(10, 8, 10, 8)
        header_layout.setSpacing(8)

        title_label = QLabel(title_text, header_section)
        title_label.setObjectName("detail_title_text")
        title_label.setWordWrap(True)
        title_label.setStyleSheet(style_manager.get_stylesheet("detail_title_label"))
        header_layout.addWidget(title_label, 1)

        color_button = QPushButton(header_section)
        color_button.setObjectName("detail_color_button")
        color_button.setFixedSize(24, 24)
        color_button.setStyleSheet(style_manager.get_stylesheet("color_button").format(button_color=self.color.name()))
        color_button.clicked.connect(self.change_color)
        header_layout.addWidget(color_button, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(header_section)

        button_row = QWidget(self.detail_popup)
        button_row.setObjectName("detail_button_row")
        button_layout = QHBoxLayout(button_row)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(6)

        for label, handler in [
            ("目录", self.open_directory),
            ("编辑", self.edit_task),
            ("历史记录", self.show_history),
            ("删除", self.handle_delete),
        ]:
            button = QPushButton(label, button_row)
            button.setStyleSheet(style_manager.get_stylesheet("detail_popup_button").format())
            button.clicked.connect(handler)
            button_layout.addWidget(button)
        layout.addWidget(button_row)

        if self.due_date:
            due_section = QWidget(self.detail_popup)
            due_section.setObjectName("detail_section_card")
            due_layout = QHBoxLayout(due_section)
            due_layout.setContentsMargins(10, 8, 10, 8)
            due_layout.setSpacing(2)

            due_label = QLabel("ddl", due_section)
            due_label.setObjectName("detail_field_label")
            due_value = QLabel(str(self.due_date), due_section)
            due_value.setObjectName("detail_field_value")
            due_layout.addWidget(due_label)
            due_layout.addWidget(due_value)
            layout.addWidget(due_section)

        meta_section = QWidget(self.detail_popup)
        meta_section.setObjectName("detail_meta_section")
        meta_layout = QVBoxLayout(meta_section)
        meta_layout.setContentsMargins(10, 8, 10, 8)
        meta_layout.setSpacing(6)

        meta_title = QLabel("任务状态", meta_section)
        meta_title.setObjectName("detail_field_label")
        meta_layout.addWidget(meta_title)

        meta_row = QWidget(meta_section)
        meta_row.setObjectName("detail_meta_row")
        meta_row_layout = QHBoxLayout(meta_row)
        meta_row_layout.setContentsMargins(0, 0, 0, 0)
        meta_row_layout.setSpacing(6)

        if hasattr(self, 'urgency') and self.urgency:
            urgency_widget = create_degree_display_widget('urgency', self.urgency, parent=meta_row)
            urgency_widget.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
            meta_row_layout.addWidget(urgency_widget)

        if hasattr(self, 'importance') and self.importance:
            importance_widget = create_degree_display_widget('importance', self.importance, parent=meta_row)
            importance_widget.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
            meta_row_layout.addWidget(importance_widget)

        self.status_label = QLabel(meta_row)
        self.status_label.setObjectName("detail_status_badge")
        self.status_label.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.update_status_label()
        meta_row_layout.addWidget(self.status_label)
        meta_row_layout.addStretch()
        meta_layout.addWidget(meta_row)
        layout.addWidget(meta_section)

        if self.notes:
            notes_section = QWidget(self.detail_popup)
            notes_section.setObjectName("detail_notes_section")
            notes_layout = QVBoxLayout(notes_section)
            notes_layout.setContentsMargins(10, 8, 10, 8)
            notes_layout.setSpacing(4)

            notes_title = QLabel("备注", notes_section)
            notes_title.setObjectName("detail_field_label")
            notes_layout.addWidget(notes_title)

            notes_html = self._format_detail_notes_html(self.notes)
            notes_label = QLabel(notes_section)
            notes_label.setObjectName("detail_notes_content")
            notes_label.setText(f"<span>{notes_html}</span>")
            notes_label.setTextFormat(Qt.TextFormat.RichText)
            notes_label.setWordWrap(True)
            notes_label.setStyleSheet("padding: 0; color: #1f1f1f; background: transparent; border: none;")

            scroll_area = FluentScrollArea(notes_section)
            scroll_area.setObjectName("detail_notes_scroll")
            scroll_area.setWidget(notes_label)
            scroll_area.setWidgetResizable(True)
            scroll_area.setMaximumHeight(96)
            scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            notes_layout.addWidget(scroll_area)
            layout.addWidget(notes_section)

        created_section = QWidget(self.detail_popup)
        created_section.setObjectName("detail_created_section")
        created_layout = QHBoxLayout(created_section)
        created_layout.setContentsMargins(10, 0, 10, 0)
        created_layout.setSpacing(2)

        created_label = QLabel("创建时间", created_section)
        created_label.setObjectName("detail_small_label")
        created_value = QLabel(str(self.create_date), created_section)
        created_value.setObjectName("detail_small_value")
        created_layout.addWidget(created_label)
        created_layout.addWidget(created_value)
        layout.addWidget(created_section)

        self.detail_popup.setFixedWidth(250)
        self.detail_popup.adjustSize()
        self.detail_popup.hide()
        self.detail_popup.installEventFilter(self)
        self.parent().installEventFilter(self)

    def eventFilter(self, obj, event):
        parent = self.parent()
        global_popup = getattr(parent, "current_detail_popup", None)

        # 安全检测：global_popup 可能已被 deleteLater 销毁
        def _is_popup_valid(widget):
            if widget is None:
                return False
            if sip:
                try:
                    if sip.isdeleted(widget):
                        return False
                except Exception:
                    # sip 不可用或判断异常时，走后续 try 保护
                    pass
            # 最后再试探性访问一个轻量属性确保未崩
            try:
                _ = widget.isVisible()
            except Exception:
                return False
            return True

        popup_valid = _is_popup_valid(global_popup)
        if not popup_valid and hasattr(parent, "current_detail_popup"):
            # 清理父级上悬挂的引用，避免后续再次访问
            try:
                if getattr(parent, "current_detail_popup", None) is global_popup:
                    parent.current_detail_popup = None
            except Exception:
                pass

        # 只处理全局弹窗
        if popup_valid and obj == global_popup:
            if event.type() == QEvent.Type.MouseButtonPress:
                # 点击了popup的内部，不关
                return False
        else:
            # 如果有全局弹窗且显示
            if popup_valid:
                try:
                    if global_popup.isVisible() and event.type() == QEvent.Type.MouseButtonPress:
                        # 如果点击位置不在全局弹窗上，关闭它
                        try:
                            click_point = event.globalPosition().toPoint()
                        except Exception:
                            return super().eventFilter(obj, event)
                        if not global_popup.geometry().contains(click_point):
                            global_popup.hide()
                            return True  # 消耗这个事件
                except Exception:
                    # 如果这里再抛异常，兜底清理引用
                    try:
                        if hasattr(parent, "current_detail_popup") and parent.current_detail_popup is global_popup:
                            parent.current_detail_popup = None
                    except Exception:
                        pass
        return super().eventFilter(obj, event)

    def handle_delete(self):
        """处理删除任务"""
        from qfluentwidgets import MessageBox
        host = resolve_notification_host(self) or self
        dialog = MessageBox(
            parent=host,
            title="删除",
            content="确定要删除这个任务吗？\n删除后无法恢复。",
        ).exec()
        
        if dialog==True:
            # 使用数据库管理器进行逻辑删除
            try:
                from database.database_manager import get_db_manager
                db_manager = get_db_manager()
                success = db_manager.delete_task(self.task_id)
                if success:
                    if self.detail_popup:
                        self.detail_popup.hide()   # ✅ 先隐藏掉 detail_popup
                        self.detail_popup.deleteLater()  # （可选）彻底释放内存
                        self.detail_popup = None
                    # 同步清理父级的全局弹窗引用，避免悬挂
                    try:
                        parent = self.parent()
                        if parent and getattr(parent, "current_detail_popup", None):
                            if parent.current_detail_popup is not None:
                                # 如果父级引用的正是我们刚刚删除的弹窗，置空
                                parent.current_detail_popup = None
                    except Exception:
                        pass
                    self.deleteRequested.emit(self)  # 再发出删除自己的信号
                else:
                    show_error(self, "删除失败", "删除任务失败，请重试")
            except Exception as e:
                logger.error(f"删除任务失败: {str(e)}")
                show_error(self, "删除失败", f"删除任务失败: {str(e)}")

    def update_status_label(self):
        """刷新状态文字"""
        if not hasattr(self, 'status_label') or self.status_label is None:
            return
        meta = get_status_badge_meta(self.checkbox.isChecked())
        self.status_label.setText(meta["display_text"])
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(build_degree_badge_stylesheet(meta))

    def show_history(self):
        """显示历史记录"""
        if self.detail_popup:
            self.detail_popup.hide()
        
        # 获取当前任务数据
        task_data = self.get_data()
        
        # 显示历史记录查看器
        from .history_viewer import HistoryViewer
        history_dialog = HistoryViewer(task_data, self.parent())
        history_dialog.exec()
    
    def open_directory(self):
        """打开目录"""
        if self.task_id:
            # 容错：目录字段可能为 None 或空
            directory = (self.directory or "").strip()
            if directory:
                if os.path.exists(directory):
                    QDesktopServices.openUrl(QUrl.fromLocalFile(directory))
                    if self.detail_popup:
                        self.detail_popup.hide()
                else:
                    show_warning(self,title="目录",content=f"尝试打开不存在的目录：{directory}")
                    logger.warning(f"尝试打开不存在的目录：{directory}")
            else:
                show_warning(self,title="目录",content="未配置目录路径")
                logger.warning("尝试打开空目录路径")
                


