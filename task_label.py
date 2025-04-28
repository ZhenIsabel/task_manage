from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, 
                             QLabel, QLineEdit, QInputDialog, QGraphicsDropShadowEffect,
                             QMenu, QAction, QDateEdit, QFrame, QScrollArea, QSizePolicy,QDialog)
from PyQt5.QtCore import Qt, pyqtSignal, QDate,QPoint
from PyQt5.QtGui import QColor, QCursor
from PyQt5.QtWidgets import QColorDialog

from add_task_dialog import AddTaskDialog

class TaskLabel(QWidget):
    """任务标签类，表示一个工作项"""
    deleteRequested = pyqtSignal(object)
    statusChanged = pyqtSignal(object)
    EDITABLE_FIELDS = [
    {"name": "text",      "label": "任务内容", "type": "text",  "required": True},
    {"name": "due_date",  "label": "到期日期", "type": "date",  "required": False},
    {"name": "priority",  "label": "优先级",   "type": "text",  "required": False},
    {"name": "notes",     "label": "备注",     "type": "text",  "required": False},
]
    
    def __init__(self, task_id, text, color, parent=None, completed=False,  **fields):
        super().__init__(parent)
        self.task_id = task_id
        self.text = text
        self.color = QColor(color)
        self.completed = completed

        # ---- 自动把 EDITABLE_FIELDS 里声明的 key 赋成属性 ----
        for meta in self.EDITABLE_FIELDS:
            key = meta["name"]
            setattr(self, key, fields.get(key))   # 没传就是 None

        # 初始化拖拽状态
        self.dragging = False
        self.drag_start_position = None
        self.setFixedSize(150, 80)
        
        # 详情浮窗
        self.detail_popup = None
        
        # 设置布局
        layout = QVBoxLayout()
        
        # 添加复选框
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(completed)
        self.checkbox.stateChanged.connect(self.on_status_changed)
        
        # 添加文本标签
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignCenter)
        
        # 添加到期日期标签（如果有）
        self.due_date_label = None
        if self.due_date:
            self.due_date_label = QLabel(f"到期: {self.due_date}")
            self.due_date_label.setAlignment(Qt.AlignRight)
            self.due_date_label.setStyleSheet("font-size: 10px;")
        
        # 将控件添加到布局
        checkbox_layout = QHBoxLayout()
        checkbox_layout.addWidget(self.checkbox)
        checkbox_layout.addStretch()
        
        layout.addLayout(checkbox_layout)
        layout.addWidget(self.label)
        # if self.due_date_label:
        #     layout.addWidget(self.due_date_label)
        
        self.setLayout(layout)
        self.update_appearance()
        
        # 设置鼠标追踪
        self.setMouseTracking(True)
    
    def update_appearance(self):
        """更新标签外观"""
        if self.completed:
            bg_color = QColor(200, 200, 200)  # 灰色背景
            text_color = QColor(100, 100, 100)  # 深灰色文字
        else:
            bg_color = self.color
            text_color = QColor(0, 0, 0) if self.color.lightness() > 128 else QColor(255, 255, 255)
        
        # 设置样式表 - 改进外观
        self.setStyleSheet(f"""
            QWidget {{
                background-color: rgba({bg_color.red()}, {bg_color.green()}, {bg_color.blue()}, 0.85);
                border-radius: 10px;
                border: none;
                box-shadow: 3px 3px 5px rgba(0, 0, 0, 0.3);
            }}
            QLabel {{
                color: rgb({text_color.red()}, {text_color.green()}, {text_color.blue()});
                font-weight: bold;
                font-family: '微软雅黑';
                padding: 2px;
            }}
            QCheckBox {{
                spacing: 5px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid gray;
            }}
            QCheckBox::indicator:checked {{
                background-color: #4ECDC4;
                border: 2px solid #4ECDC4;
                image: url(check.png);
            }}
        """)
        
        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(3, 3)
        self.setGraphicsEffect(shadow)
    
    def on_status_changed(self, state):
        """复选框状态改变时的处理"""
        self.completed = (state == Qt.Checked)
        self.update_appearance()
        self.statusChanged.emit(self)
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_start_position = event.pos()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if self.dragging and (event.buttons() & Qt.LeftButton):
            # 计算移动距离
            delta = event.pos() - self.drag_start_position
            new_pos = self.pos() + delta
            self.move(new_pos)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton and self.dragging:
            self.dragging = False
    
    def mouseDoubleClickEvent(self, event):
        """鼠标双击事件"""
        if event.button() == Qt.LeftButton:
            # 编辑标签文本 - 使用无边框对话框
            dialog = QInputDialog(self)
            dialog.setWindowFlags(Qt.FramelessWindowHint)
            dialog.setInputMode(QInputDialog.TextInput)
            dialog.setLabelText("任务内容:")
            dialog.setTextValue(self.text)
            dialog.setWindowTitle("编辑任务")
            
            if dialog.exec_() == QDialog.Accepted:
                self.text = dialog.textValue()
                self.label.setText(self.text)
    
    def contextMenuEvent(self, event):
        """右键菜单事件"""
        menu = QMenu(self)
        
        # 编辑操作
        edit_action = QAction("编辑", self)
        edit_action.triggered.connect(self.edit_task)
        
        # 更改颜色操作
        color_action = QAction("更改颜色", self)
        color_action.triggered.connect(self.change_color)
        
        # 删除操作
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self.deleteRequested.emit(self))
        
        # 添加操作到菜单
        menu.addAction(edit_action)
        menu.addAction(color_action)
        menu.addAction(delete_action)
        
        # 显示菜单
        menu.exec_(event.globalPos())
    
    def edit_task(self):
        """编辑任务内容"""
        # 获取当前字段配置
        task_fields = []
        # 1) 动态把元数据转成 task_fields，默认值取自身属性
        for meta in self.EDITABLE_FIELDS:
            value = getattr(self, meta["name"], "")
            task_fields.append(
                dict(meta, default=value)   # 拷贝 meta 并加 default
            )


        # 如果没有找到字段配置，使用默认字段
        if not task_fields:
            task_fields = [
                {'name': 'text', 'label': '任务内容', 'type': 'text', 'required': True},
                {'name': 'due_date', 'label': '到期日期', 'type': 'date', 'required': False}
            ]

        dialog= AddTaskDialog(self, task_fields=task_fields)
            # 3) 如果点击「确定」就取回数据
        if dialog.exec_() != QDialog.Accepted:
            return                          # 点了取消

        # 从对话框中获取字段值
        task_data = dialog.get_data()   # ← 只要这一行就拿到全部字段值

        # 检查必填
        for f in task_fields:
            if f.get("required") and not task_data.get(f["name"]):
                QMessageBox.warning(self, "提示", f"{f['label']} 为必填项")
                return

        # 更新任务数据
        self.text=task_data.get('text', ''),
        self.due_date=task_data.get('due_date'),
        self.priority=task_data.get('priority'),
        self.notes=task_data.get('notes')
        
    
    def change_color(self):
        """更改标签颜色"""
        color_dialog = QColorDialog(self.color, self)
        color_dialog.setWindowTitle("选择标签颜色")
        if color_dialog.exec_() == QDialog.Accepted:
            color = color_dialog.selectedColor()
            if color.isValid():
                self.color = color
                self.update_appearance()
    
    def get_data(self):
        """获取标签数据"""
        return {
            'id': self.task_id,
            'text': self.text,
            'color': self.color.name(),
            'position': {'x': self.pos().x(), 'y': self.pos().y()},
            'completed': self.completed,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'due_date': self.due_date,
            'priority': self.priority,
            'notes': self.notes
        }
        
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

    def enterEvent(self, event):
        """鼠标进入控件区域时显示详情"""
        # 如果详情窗口不存在，创建一个
        if not self.detail_popup:
            self.create_detail_popup()
        
        # 调整位置并显示
        self.position_detail_popup()
        self.detail_popup.show()
        
        # 确保详情弹出窗口保持在前台
        self.detail_popup.raise_()
    
    def leaveEvent(self, event):
        """鼠标离开控件区域时隐藏详情"""
        if self.detail_popup and self.detail_popup.isVisible():
            self.detail_popup.hide()
    
    def create_detail_popup(self):
        """创建详情弹出窗口"""
        # 创建一个无边框窗口作为弹出窗口
        self.detail_popup = QFrame(self.parent())
        self.detail_popup.setWindowFlags(Qt.FramelessWindowHint)
        self.detail_popup.setAttribute(Qt.WA_TranslucentBackground)
        self.detail_popup.setStyleSheet("""
            QFrame {
                background-color: #ECECEC;
                border-radius: 10px;
                border: 1px solid rgba(100, 100, 100, 0.5);
            }
            QLabel {
                color: black;
                font-family: '微软雅黑';
                padding: 4px;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
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
        title_label = QLabel(self.text)
        title_label.setWordWrap(True)
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: black;")
        layout.addWidget(title_label)
        
        # 添加所有可用的任务信息
        if self.due_date:
            due_date_label = QLabel(f"<b>到期日期:</b> {self.due_date}")
            layout.addWidget(due_date_label)
        
        if self.priority:
            priority_label = QLabel(f"<b>优先级:</b> {self.priority}")
            layout.addWidget(priority_label)
        
        if self.notes:
            notes_title = QLabel("<b>备注:</b>")
            layout.addWidget(notes_title)
            
            notes_label = QLabel(self.notes)
            notes_label.setWordWrap(True)
            notes_label.setStyleSheet("padding: 5px; background-color: rgba(70, 70, 70, 0.5); border-radius: 5px; color: black;")
            
            # 使用滚动区域显示长文本
            scroll_area = QScrollArea()
            scroll_area.setWidget(notes_label)
            scroll_area.setWidgetResizable(True)
            scroll_area.setMaximumHeight(100)
            scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            layout.addWidget(scroll_area)
        
        # 完成状态
        status_text = "已完成" if self.completed else "未完成"
        status_color = "#4ECDC4" if self.completed else "#FF6B6B"
        status_label = QLabel(f"<b>状态:</b> <font color='{status_color}'>{status_text}</font>")
        layout.addWidget(status_label)
        
        # 创建日期
        date_label = QLabel(f"<b>创建于:</b> {datetime.now().strftime('%Y-%m-%d')}")
        layout.addWidget(date_label)
        
        self.detail_popup.setFixedWidth(250)
        self.detail_popup.adjustSize()  # 确保窗口大小适合内容
        
        # 确保初始状态为隐藏
        self.detail_popup.hide()
