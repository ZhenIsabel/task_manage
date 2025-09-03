from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, 
                            QLabel, QLineEdit, QInputDialog,
                            QMenu, QFrame, QScrollArea, QSizePolicy, QDialog, QColorDialog, QMessageBox,
                            QLayout,QPushButton)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QPoint, QEvent, QUrl
from PyQt6.QtGui import QColor, QCursor, QAction, QDesktopServices
try:
    import sip  # 用于判断 PyQt 对象是否已被销毁
except Exception:
    sip = None
import os

from .add_task_dialog import AddTaskDialog
from ui.styles import StyleManager
from ui.ui import MyColorDialog, WarningPopup, apply_drop_shadow
from config.config_manager import load_config
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
                {"name":"create_date","label":"创建日期","type":"date","required":False},
                {"name":"completed_date","label":"完成日期","type":"date","required":False}
            ]
        return fields
    
    def __init__(self, task_id, color,completed=False, parent=None,  **fields):
        try:
            super().__init__(parent)
        except Exception as e:
            logger.error(f"任务标签初始化失败 (task_id: {task_id}): {str(e)}", exc_info=True)
            raise
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
        
        # 初始化时检查到期状态
        self.check_overdue_status()
        
        self.update_appearance()
        
        # 文本可能改动时，随时调整标签尺寸
        self.label.adjustSize()
        self.layout().setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        # 设置鼠标追踪
        self.setMouseTracking(True)
    
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
        
        # 添加阴影效果
        apply_drop_shadow(self, blur_radius=8, color=QColor(0, 0, 0, 20), offset_x=2, offset_y=3)
    
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
        for meta in self.get_editable_fields():
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
                QMessageBox.warning(self, "提示", f"{f['label']} 为必填项")
                return

        # 更新任务数据
        for meta in self.get_editable_fields():
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
        for meta in self.get_editable_fields():
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
        # 创建一个无边框窗口作为弹出窗口
        parent_widget = self.parent()
        # 保护性判断：确保父级存在
        self.detail_popup = QFrame(parent_widget if parent_widget else self)
        self.detail_popup.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.detail_popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.detail_popup.setStyleSheet(style_manager.get_stylesheet("detail_popup").format())
        
        # 设置阴影效果
        apply_drop_shadow(self.detail_popup, blur_radius=10, color=QColor(0, 0, 0, 60), offset_x=2, offset_y=2)
        
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
        title_label.setStyleSheet(style_manager.get_stylesheet("detail_title_label"))
        title_layout.addWidget(title_label)
        
        # 更改颜色按钮
        color_button = QPushButton()
        color_button.setFixedSize(24, 24)
        color_button.setStyleSheet(StyleManager().get_stylesheet("color_button").format(button_color=self.color.name()))
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
        from ui.ui import DeleteConfirmDialog
        
        dialog = DeleteConfirmDialog(self, '确定要删除这个任务吗？\n删除后无法恢复。')
        dialog.exec()
        
        if dialog.get_result():
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
                    QMessageBox.warning(self, "删除失败", "删除任务失败，请重试")
            except Exception as e:
                logger.error(f"删除任务失败: {str(e)}")
                QMessageBox.warning(self, "删除失败", f"删除任务失败: {str(e)}")

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
                    popup = WarningPopup(self, "目录不存在！")
                    logger.warning(f"尝试打开不存在的目录：{directory}")
                    popup.exec()
            else:
                popup = WarningPopup(self, "未配置目录路径！")
                logger.warning("尝试打开空目录路径")
                popup.exec()