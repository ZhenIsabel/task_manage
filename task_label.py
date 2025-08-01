from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, 
                            QLabel, QLineEdit, QInputDialog, QGraphicsDropShadowEffect,
                            QMenu, QFrame, QScrollArea, QSizePolicy, QDialog, QColorDialog, QMessageBox,
                            QLayout,QPushButton)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QPoint, QEvent, QUrl
from PyQt6.QtGui import QColor, QCursor, QAction, QDesktopServices
import os

from add_task_dialog import AddTaskDialog
from styles import MyColorDialog, WarningPopup, StyleManager
from config_manager import load_config
import logging
logger = logging.getLogger(__name__)  # 自动获取模块名

class TaskLabel(QWidget):
    """任务标签类，表示一个工作项"""
    deleteRequested = pyqtSignal(object)
    statusChanged = pyqtSignal(object)

    @classmethod
    def get_editable_fields(cls):
        """从配置中获取可编辑字段"""
        config = load_config()
        fields = config.get('task_fields', [])
        if not fields:
            # 如果配置中没有字段定义，使用默认字段
            fields = [
                {"name": "text",      "label": "任务内容", "type": "text",  "required": True},
                {"name": "due_date",  "label": "到期日期", "type": "date",  "required": False},
                {"name": "priority",  "label": "优先级",   "type": "select", "required": False, "options": ["高", "中", "低"]},
                {"name": "notes",     "label": "备注",     "type": "multiline",  "required": False},
                {"name": "directory","label": "目录","type": "file", "required": False},
                {"name":"create_date","label":"创建日期","type":"date","required":False}
            ]
        return fields
    
    def __init__(self, task_id, color,completed=False, parent=None,  **fields):
        super().__init__(parent)
        self.task_id = task_id
        self.color = QColor(color)

        # ---- 自动把 EDITABLE_FIELDS 里声明的 key 赋成属性 ----
        for meta in self.get_editable_fields():
            key = meta["name"]
            setattr(self, key, fields.get(key, ""))  # 添加默认值

        # 初始化拖拽状态
        self.dragging = False
        self.drag_start_position = None
        self._draggable = False  # 初始化 _draggable 属性，默认为不可拖动

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
            self.due_date_label.setStyleSheet("font-size: 10px;")
        
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
        self.update_appearance()
        
        # 文本可能改动时，随时调整标签尺寸
        self.label.adjustSize()
        self.layout().setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        # 设置鼠标追踪
        self.setMouseTracking(True)
    
    def update_appearance(self):
        """更新标签外观"""
        if self.checkbox.isChecked(): # 🔥🔥🔥用真实勾选状态
            bg_color = QColor(200, 200, 200)  # 灰色背景
            text_color = QColor(100, 100, 100)  # 深灰色文字
        else:
            bg_color = self.color
            text_color = QColor(0, 0, 0) if self.color.lightness() > 128 else QColor(255, 255, 255)
        style_manager = StyleManager()
        indicator_size = 14  # 和字体高度差不多

        # 获取样式模板并格式化
        stylesheet_template = style_manager.get_stylesheet("task_label")
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
        
        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(3, 3)
        self.setGraphicsEffect(shadow)
    
    def on_status_changed(self, state):
        """复选框状态改变时的处理"""
        self.update_appearance()
        self.statusChanged.emit(self)

        # 如果detail_popup存在，刷新里面的状态文字
        if hasattr(self, 'status_label') and self.status_label:
            self.update_status_label()
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton and getattr(self, '_draggable', True):
            self.dragging = True
            self.drag_start_position = event.pos()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
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
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.MouseButton.LeftButton and self.dragging:
            self.dragging = False
    
    def mouseDoubleClickEvent(self, event):
        """鼠标双击事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            dialog = QInputDialog(self)
            dialog.setWindowFlags(Qt.WindowType.FramelessWindowHint)
            dialog.setInputMode(QInputDialog.InputMode.TextInput)
            dialog.setLabelText("任务内容:")
            dialog.setTextValue(self.text)
            dialog.setWindowTitle("编辑任务")
            
            # if dialog.exec() == QDialog.DialogCode.Accepted:
            #     self.text = dialog.textValue()
            #     self.label.setText(self.text)
    
    def set_draggable(self, draggable):
        """设置任务标签是否可拖动"""
        self._draggable = draggable
        # 可能还需要更新鼠标样式或其他视觉提示
        self.setCursor(Qt.CursorShape.SizeAllCursor if draggable else Qt.CursorShape.ArrowCursor)

    def contextMenuEvent(self, event):
        """右键菜单事件"""
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

    def edit_task(self):
        """编辑任务内容"""
        # 获取当前字段配置
        task_fields = []
        for meta in self.get_editable_fields():
            value = getattr(self, meta["name"], "") or ""  # 双重空值保护
            task_fields.append(dict(meta, default=value))

        # 如果没有找到字段配置，使用默认字段
        if not task_fields:
            task_fields = [
                {'name': 'text', 'label': '任务内容', 'type': 'text', 'required': True},
                {'name': 'due_date', 'label': '到期日期', 'type': 'date', 'required': False}
            ]

        dialog= AddTaskDialog(self, task_fields=task_fields)
            # 3) 如果点击「确定」就取回数据
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return                          # 点了取消

        # 从对话框中获取字段值
        task_data = dialog.get_data()   # ← 只要这一行就拿到全部字段值

        # 检查必填
        for f in task_fields:
            if f.get("required") and not task_data.get(f["name"]):
                QMessageBox.warning(self, "提示", f"{f['label']} 为必填项")
                return

        # 更新任务数据
        for meta in self.get_editable_fields():
            key = meta["name"]
            if key in task_data:
                setattr(self, key, task_data[key])
        # 特殊处理标签文本更新
        self.label.setText(self.text)
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
    
    def get_data(self):
        """获取标签数据"""
        data = {
                'id': self.task_id,
                'color': self.color.name(),
                'position': {'x': self.pos().x(), 'y': self.pos().y()},
                'completed': self.checkbox.isChecked(),
                'date': datetime.now().strftime('%Y-%m-%d')
            }
        
        # 如果任务刚被标记为完成，记录完成日期
        if self.checkbox.isChecked():
            data['completed_date'] = datetime.now().strftime('%Y-%m-%d')
        
        for meta in self.get_editable_fields():
            key = meta["name"]
            data[key] = getattr(self, key, "")

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
        # 创建一个无边框窗口作为弹出窗口
        self.detail_popup = QFrame(self.parent())
        self.detail_popup.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.detail_popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.detail_popup.setStyleSheet(style_manager.get_stylesheet("detail_popup").format())
        
        # 设置阴影效果
        shadow = QGraphicsDropShadowEffect(self.detail_popup)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(3, 3)
        self.detail_popup.setGraphicsEffect(shadow)
        
        # 创建布局
        layout = QVBoxLayout(self.detail_popup)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        
        # 标题 - 任务内容
        # 创建标题行布局
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)

        # 确保使用正确的文本内容（字符串而非元组）
        title_text = self.text
        if isinstance(self.text, tuple):
            title_text = self.text[0]
        title_label = QLabel(title_text)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: black;")
        title_layout.addWidget(title_label)
        
        # 更改颜色按钮
        color_button = QPushButton()
        color_button.setFixedSize(24, 24)
        color_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.color.name()};
                border: 2px solid #bbb;
                border-radius: 6px;
                margin: 0 2px;
            }}
            QPushButton:hover {{
                border: 2px solid #4ECDC4;
            }}
        """)
        color_button.clicked.connect(self.change_color)
        title_layout.addWidget(color_button)
        layout.addLayout(title_layout)

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        # 打开目录按钮
        open_dir_button = QPushButton("目录")
        open_dir_button.clicked.connect(self.open_directory)
        open_dir_button.setStyleSheet(style_manager.get_stylesheet("task_label_button").format())
        button_layout.addWidget(open_dir_button)

        # 编辑按钮
        edit_button = QPushButton("编辑")
        edit_button.clicked.connect(self.edit_task)
        edit_button.setStyleSheet(style_manager.get_stylesheet("task_label_button").format())
        button_layout.addWidget(edit_button)

        # 查看历史记录按钮
        history_button = QPushButton("历史记录")
        history_button.clicked.connect(self.show_history)
        history_button.setStyleSheet(style_manager.get_stylesheet("task_label_button").format())
        button_layout.addWidget(history_button)

        # 删除按钮
        delete_button = QPushButton("删除")
        delete_button.clicked.connect(self.handle_delete)
        delete_button.setStyleSheet(style_manager.get_stylesheet("task_label_button").format())
        button_layout.addWidget(delete_button)

        # 把按钮布局加到主 layout
        layout.addLayout(button_layout)

        # 添加所有可用的任务信息
        if self.due_date:
            due_date_label = QLabel(f"<b>到期日期:</b> {self.due_date}")
            layout.addWidget(due_date_label)
        
        if self.priority:
            priority_label = QLabel(f"<b>优先级:</b> {self.priority}")
            layout.addWidget(priority_label)
        
        if self.notes:
            notes_html = self.notes.replace('\n', '<br>')
            notes_label = QLabel(f"<b>备注:</b><br>{notes_html}")
            notes_label.setTextFormat(Qt.TextFormat.RichText)
            notes_label.setWordWrap(True)
            notes_label.setStyleSheet("padding: 5px; color: black;")
            
            # 使用滚动区域显示长文本
            scroll_area = QScrollArea()
            scroll_area.setWidget(notes_label)
            scroll_area.setWidgetResizable(True)
            scroll_area.setMaximumHeight(100)
            scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            layout.addWidget(scroll_area)
        
        # 完成状态
        self.status_label = QLabel()
        self.update_status_label()  # 单独用一个方法来设置文字
        layout.addWidget(self.status_label)
        
        # 创建日期
        date_label = QLabel(f"<b>创建于:</b> {self.create_date}")
        layout.addWidget(date_label)
        
        self.detail_popup.setFixedWidth(250)
        self.detail_popup.adjustSize()  # 确保窗口大小适合内容
        
        # 确保初始状态为隐藏
        self.detail_popup.hide()
        # 安装事件过滤器，以便在详情窗口关闭时隐藏它
        self.detail_popup.installEventFilter(self)
        # 在父窗口（通常是QuadrantWidget）上也装上过滤器
        self.parent().installEventFilter(self)

    def eventFilter(self, obj, event):
        parent = self.parent()
        global_popup = getattr(parent, "current_detail_popup", None)

        # 只处理全局弹窗
        if obj == global_popup:
            if event.type() == QEvent.Type.MouseButtonPress:
                # 点击了popup的内部，不关
                return False
        else:
            # 如果有全局弹窗且显示
            if global_popup and global_popup.isVisible():
                if event.type() == QEvent.Type.MouseButtonPress:
                    # 如果点击位置不在全局弹窗上，关闭它
                    if not global_popup.geometry().contains(event.globalPosition().toPoint()):
                        global_popup.hide()
                        return True  # 消耗这个事件
        return super().eventFilter(obj, event)

    def handle_delete(self):
        """处理删除任务"""
        if self.detail_popup:
            self.detail_popup.hide()   # ✅ 先隐藏掉 detail_popup
            self.detail_popup.deleteLater()  # （可选）彻底释放内存
            self.detail_popup = None

        self.deleteRequested.emit(self)  # 再发出删除自己的信号

    def update_status_label(self):
        """刷新状态文字"""
        if not hasattr(self, 'status_label') or self.status_label is None:
            return
        status_text = "已完成" if self.checkbox.isChecked() else "未完成"
        status_color = "#4ECDC4" if self.checkbox.isChecked() else "#FF6B6B"
        self.status_label.setText(f"<b>状态:</b> <font color='{status_color}'>{status_text}</font>")

    def show_history(self):
        """显示历史记录"""
        if self.detail_popup:
            self.detail_popup.hide()
        
        # 获取当前任务数据
        task_data = self.get_data()
        
        # 显示历史记录查看器
        from history_viewer import HistoryViewer
        history_dialog = HistoryViewer(task_data, self.parent())
        history_dialog.exec()
    
    def open_directory(self):
        """打开目录"""
        if self.task_id:
            directory = os.path.join(self.directory)
            if os.path.exists(directory):
                QDesktopServices.openUrl(QUrl.fromLocalFile(directory))
                self.detail_popup.hide()
            else:
                popup = WarningPopup(self, "目录不存在！")
                logger.warning(f"尝试打开不存在的目录：{directory}")
                popup.exec()
            
        def change_color(self):
            """更改标签颜色"""
            color_dialog = MyColorDialog(self.color, self)
            color_dialog.setWindowTitle("选择标签颜色")
            if color_dialog.exec() == QDialog.DialogCode.Accepted:
                color = color_dialog.selectedColor()
                if color.isValid():
                    self.color = color
                    self.update_appearance()
                    # 更新色块按钮颜色
                    if hasattr(self, 'detail_popup') and self.detail_popup:
                        # 找到色块按钮并更新其样式
                        for btn in self.detail_popup.findChildren(QPushButton):
                            if btn.fixedWidth() == 24 and btn.fixedHeight() == 24:
                                btn.setStyleSheet(f"""
                                    QPushButton {{
                                        background-color: {self.color.name()};
                                        border: 2px solid #bbb;
                                        border-radius: 6px;
                                        margin: 0 2px;
                                    }}
                                    QPushButton:hover {{
                                        border: 2px solid #4ECDC4;
                                    }}
                                """)