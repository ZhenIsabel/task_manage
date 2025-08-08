import json
import os
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QColorDialog, QSlider, 
                            QLabel, QGridLayout, QSizePolicy, QCheckBox, QLineEdit, QInputDialog, 
                            QMessageBox, QDialog,
                            QTabWidget, QFormLayout, QSpinBox, QDateEdit, QMenu)
from PyQt6.QtCore import Qt, QPoint, QSize, QRect, QPropertyAnimation, QEasingCurve, QTimer, QDate
from PyQt6.QtWidgets import QApplication,QFileDialog
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QCursor, QPainterPath, QLinearGradient, QAction

from task_label import TaskLabel
from config_manager import save_config, save_tasks, TASKS_FILE
from add_task_dialog import AddTaskDialog
from styles import StyleManager
from database_manager import get_db_manager
from ui import apply_drop_shadow
import logging
logger = logging.getLogger(__name__)  # 自动获取模块名

class QuadrantWidget(QWidget):
    """四象限窗口部件"""
    def __init__(self, config, parent=None, ui_manager=None):
        logger.debug("正在初始化四象限窗口...")
        super().__init__(parent)
        self.config = config
        self.ui_manager = ui_manager  # 添加UI管理器引用
        self.edit_mode = False
        self.tasks = []
        self.undo_stack = []
        
        # 设置为无边框、保持在底层且作为桌面级窗口
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnBottomHint | Qt.WindowType.Tool)
        # 设置窗口为透明背景
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # 允许鼠标事件穿透到桌面
        if hasattr(Qt, 'WA_TransparentForMouseEvents'):
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        # 设置窗口不在显示桌面时隐藏
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # 设置大小和位置
        self.resize(config['size']['width'], config['size']['height'])
        self.move(config['position']['x'], config['position']['y'])

        # 将窗口居中显示
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        center_x = screen_geometry.center().x() - self.width() // 2
        center_y = screen_geometry.center().y() - self.height() // 2
        self.move(center_x, center_y)

        # 更新配置文件里的位置
        self.config['position']['x'] = center_x
        self.config['position']['y'] = center_y
        self.save_config()
        
        # 创建布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)  # 增加边距使界面更宽敞
        
        # 创建控制按钮区域 - 美化控制面板
        self.control_widget = QWidget(self)
        # 确保样式表背景可绘制
        self.control_widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.control_layout = QHBoxLayout(self.control_widget)
        self.control_layout.setSpacing(10)  # 增加按钮间距
        
        # 设置控制面板样式
        style_manager = StyleManager()
        # 指定对象名供样式选择器匹配
        self.control_widget.setObjectName("control_panel")
        self.control_widget.setStyleSheet(style_manager.get_stylesheet("control_panel"))
        
        # 确保控制面板可见（设置透明度>0）
        self.control_widget.setProperty("opacity", 1.0)

        # 添加按钮
        self.edit_button = QPushButton("正在查看" if not self.edit_mode else "正在编辑", self)
        self.edit_button.clicked.connect(self.toggle_edit_mode)
        self.edit_button.setCursor(Qt.CursorShape.PointingHandCursor)  # 鼠标悬停时显示手型光标
        
        self.add_task_button = QPushButton("添加任务", self)
        self.add_task_button.clicked.connect(self.add_task)
        self.add_task_button.setVisible(False)  # 初始隐藏
        self.add_task_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # 添加导出未完成任务按钮
        self.export_tasks_button = QPushButton("导出任务", self)
        # 新增：创建菜单
        self.export_menu = QMenu(self.export_tasks_button)
        # 主动设置菜单样式，确保生效
        self.export_menu.setStyleSheet(style_manager.get_stylesheet("menu"))
        self.action_export_unfinished = QAction("导出在办", self)
        self.action_export_all = QAction("导出所有", self)
        self.export_menu.addAction(self.action_export_unfinished)
        self.export_menu.addAction(self.action_export_all)
        self.export_tasks_button.setMenu(self.export_menu)
        # 绑定动作
        self.action_export_unfinished.triggered.connect(self.export_unfinished_tasks)
        self.action_export_all.triggered.connect(self.export_all_tasks)
        self.export_tasks_button.setVisible(False)  # 初始隐藏
        self.export_tasks_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.undo_button = QPushButton("撤销", self)
        self.undo_button.clicked.connect(self.undo_action)
        self.undo_button.setVisible(False)  # 初始隐藏
        self.undo_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.settings_button = QPushButton("设置", self)
        self.settings_button.clicked.connect(self.show_settings)
        self.settings_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.exit_button = QPushButton("退出", self)
        self.exit_button.clicked.connect(self.close)
        self.exit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # 添加按钮到布局
        self.control_layout.addWidget(self.edit_button)
        self.control_layout.addWidget(self.add_task_button)
        self.control_layout.addWidget(self.export_tasks_button)
        self.control_layout.addWidget(self.undo_button)
        self.control_layout.addWidget(self.settings_button)
        self.control_layout.addWidget(self.exit_button)
        
        # 添加控制面板阴影效果
        apply_drop_shadow(self.control_widget, blur_radius=20, color=QColor(0, 0, 0, 100), offset_x=0, offset_y=0)
        # 设置控制面板为悬浮式
        self.control_widget.setParent(self)
        # 自动计算初始尺寸
        self.control_widget.adjustSize()  
        control_width = self.control_widget.width()
        control_height = self.control_widget.height()
        # 从配置读取保存的位置
        control_x = self.config.get('control_panel', {}).get('x', 20)
        control_y = self.config.get('control_panel', {}).get('y', 20)
        self.control_widget.setGeometry(control_x, control_y, control_width, control_height)
        
        # 新增鼠标事件处理绑定
        self.control_widget.mousePressEvent = self.handle_control_press
        self.control_widget.mouseMoveEvent = self.handle_control_move
        self.control_widget.mouseReleaseEvent = self.handle_control_release
        
        # 创建一个布局用于四象限区域
        self.quadrant_layout = QVBoxLayout()
        self.quadrant_layout.addStretch()
        
        # 将四象限布局添加到主布局
        self.main_layout.addLayout(self.quadrant_layout)

        # 确保控制面板始终可见
        self.control_widget.show()

        # 新增：定时保存控件位置
        self.save_timer = QTimer(self)
        self.save_timer.timeout.connect(self.periodic_save_config)
        self.save_timer.start(20000)  # 每20秒保存一次

        self._position_dirty = False  # 标记位置是否有变动

        # 新增：记录当前显示的 detail_popup
        self.current_detail_popup = None

    def periodic_save_config(self):
        """定期保存控件位置"""
        if self._position_dirty:
            self.config.setdefault('control_panel', {})
            self.config['control_panel']['x'] = self.control_widget.x()
            self.config['control_panel']['y'] = self.control_widget.y()
            self.save_config()
            self._position_dirty = False

    # 三个控制面板拖动处理方法（新增代码）
    def handle_control_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.control_drag_start_pos = event.globalPosition().toPoint()
            self.control_original_pos = self.control_widget.pos()
            event.accept()

    def handle_control_move(self, event):
        if hasattr(self, 'control_drag_start_pos'):
            delta = event.globalPosition().toPoint() - self.control_drag_start_pos
            new_pos = self.control_original_pos + delta
            
            # 限制控制面板在窗口范围内
            max_x = self.width() - self.control_widget.width() 
            max_y = self.height() - self.control_widget.height()
            new_pos.setX(max(20, min(new_pos.x(), max_x)))
            new_pos.setY(max(20, min(new_pos.y(), max_y)))
        
            self.control_widget.move(new_pos)
            self._position_dirty = True  # 标记有变动
            # 强制重绘父窗口区域
            self.update()
            self.control_widget.update() 
            
            event.accept()

    def handle_control_release(self, event):
        if hasattr(self, 'control_drag_start_pos'):
            # 保存位置到配置文件（新增代码）
            self.config.setdefault('control_panel', {})
            self.config['control_panel']['x'] = self.control_widget.x()
            self.config['control_panel']['y'] = self.control_widget.y()
            # 不再立即保存，只标记
            self._position_dirty = True
            del self.control_drag_start_pos
        event.accept()

    
    def paintEvent(self, event):
        """绘制事件 - 美化版本"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)  # 抗锯齿
        
        # 获取窗口尺寸
        width = self.width()
        height = self.height()
        
        # 计算十字线的位置
        h_line_y = height // 2
        v_line_x = width // 2
        
        # 获取圆角半径
        border_radius = self.config.get('ui', {}).get('border_radius', 15)
        
        # 绘制整体背景 - 半透明
        painter.setBrush(QBrush(QColor(245, 245, 245, 30)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, width, height, border_radius, border_radius)
        
        # 计算内部四象限区域（留出边距）
        margin = 10
        inner_h_line_y = h_line_y
        inner_v_line_x = v_line_x
        
        # 绘制四个象限的背景 - 使用圆角矩形
        # 第一象限：重要且紧急（右上）
        q1_color = QColor(self.config['quadrants']['q1']['color'])
        q1_color.setAlphaF(self.config['quadrants']['q1']['opacity'])
        painter.setBrush(QBrush(q1_color))
        painter.setPen(Qt.PenStyle.NoPen)
        q1_path = QPainterPath()
        q1_path.moveTo(inner_v_line_x, margin)
        q1_path.lineTo(width - margin - border_radius, margin)
        q1_path.arcTo(width - margin - border_radius * 2, margin, border_radius * 2, border_radius * 2, 90, -90)
        q1_path.lineTo(width - margin, inner_h_line_y)
        q1_path.lineTo(inner_v_line_x, inner_h_line_y)
        q1_path.closeSubpath()
        painter.drawPath(q1_path)
        
        # 第二象限：重要不紧急（左上）
        q2_color = QColor(self.config['quadrants']['q2']['color'])
        q2_color.setAlphaF(self.config['quadrants']['q2']['opacity'])
        painter.setBrush(QBrush(q2_color))
        q2_path = QPainterPath()
        q2_path.moveTo(margin + border_radius, margin)
        q2_path.arcTo(margin, margin, border_radius * 2, border_radius * 2, 90, 90)
        q2_path.lineTo(margin, inner_h_line_y)
        q2_path.lineTo(inner_v_line_x, inner_h_line_y)
        q2_path.lineTo(inner_v_line_x, margin)
        q2_path.closeSubpath()
        painter.drawPath(q2_path)
        
        # 第三象限：不重要但紧急（右下）
        q3_color = QColor(self.config['quadrants']['q3']['color'])
        q3_color.setAlphaF(self.config['quadrants']['q3']['opacity'])
        painter.setBrush(QBrush(q3_color))
        q3_path = QPainterPath()
        q3_path.moveTo(inner_v_line_x, inner_h_line_y)
        q3_path.lineTo(width - margin, inner_h_line_y)
        q3_path.lineTo(width - margin, height - margin - border_radius)
        q3_path.arcTo(width - margin - border_radius * 2, height - margin - border_radius * 2, border_radius * 2, border_radius * 2, 0, -90)
        q3_path.lineTo(inner_v_line_x, height - margin)
        q3_path.closeSubpath()
        painter.drawPath(q3_path)
        
        # 第四象限：不重要不紧急（左下）
        q4_color = QColor(self.config['quadrants']['q4']['color'])
        q4_color.setAlphaF(self.config['quadrants']['q4']['opacity'])
        painter.setBrush(QBrush(q4_color))
        q4_path = QPainterPath()
        q4_path.moveTo(inner_v_line_x, inner_h_line_y)
        q4_path.lineTo(inner_v_line_x, height - margin)
        q4_path.lineTo(margin + border_radius, height - margin)
        q4_path.arcTo(margin, height - margin - border_radius * 2, border_radius * 2, border_radius * 2, -90, -90)
        q4_path.lineTo(margin, inner_h_line_y)
        q4_path.closeSubpath()
        painter.drawPath(q4_path)
        
        # 绘制十字线 - 使用渐变效果
        h_gradient = QLinearGradient(0, h_line_y, width, h_line_y)
        h_gradient.setColorAt(0, QColor(0, 0, 0, 150))
        h_gradient.setColorAt(0.5, QColor(0, 0, 0, 200))
        h_gradient.setColorAt(1, QColor(0, 0, 0, 150))
        
        v_gradient = QLinearGradient(v_line_x, 0, v_line_x, height)
        v_gradient.setColorAt(0, QColor(0, 0, 0, 150))
        v_gradient.setColorAt(0.5, QColor(0, 0, 0, 200))
        v_gradient.setColorAt(1, QColor(0, 0, 0, 150))
        
        # 水平线
        painter.setPen(QPen(h_gradient, 2))
        painter.drawLine(margin, h_line_y, width - margin, h_line_y)
        
        # 垂直线
        painter.setPen(QPen(v_gradient, 2))
        painter.drawLine(v_line_x, margin, v_line_x, height - margin)
        
        # 绘制标签 - 使用更好的字体和阴影效果
        font_family = self.config.get('ui', {}).get('font_family', '微软雅黑')
        font = QFont(font_family)
        font.setBold(True)
        font.setPointSize(10)
        painter.setFont(font)
        
        # 设置文字阴影
        text_color = QColor(255, 255, 255, 220)
        shadow_color = QColor(0, 0, 0, 100)
        shadow_offset = 1
        
        # 绘制象限标签 - 带阴影效果
        # 重要且紧急
        painter.setPen(shadow_color)
        painter.drawText(QRect(width - 150 + shadow_offset, 10 + shadow_offset, 140, 30), Qt.AlignmentFlag.AlignRight, "重要且紧急")
        painter.setPen(text_color)
        painter.drawText(QRect(width - 150, 10, 140, 30), Qt.AlignmentFlag.AlignRight, "重要且紧急")
        
        # 重要不紧急
        painter.setPen(shadow_color)
        painter.drawText(QRect(10 + shadow_offset, 10 + shadow_offset, 140, 30), Qt.AlignmentFlag.AlignLeft, "重要不紧急")
        painter.setPen(text_color)
        painter.drawText(QRect(10, 10, 140, 30), Qt.AlignmentFlag.AlignLeft, "重要不紧急")
        
        # 不重要但紧急
        painter.setPen(shadow_color)
        painter.drawText(QRect(width - 150 + shadow_offset, height - 40 + shadow_offset, 140, 30), Qt.AlignmentFlag.AlignRight, "不重要但紧急")
        painter.setPen(text_color)
        painter.drawText(QRect(width - 150, height - 40, 140, 30), Qt.AlignmentFlag.AlignRight, "不重要但紧急")
        
        # 不重要不紧急
        painter.setPen(shadow_color)
        painter.drawText(QRect(10 + shadow_offset, height - 40 + shadow_offset, 140, 30), Qt.AlignmentFlag.AlignLeft, "不重要不紧急")
        painter.setPen(text_color)
        painter.drawText(QRect(10, height - 40, 140, 30), Qt.AlignmentFlag.AlignLeft, "不重要不紧急")
        
        # 绘制坐标轴标签 - 带阴影效果
        # 紧急
        painter.setPen(shadow_color)
        painter.drawText(QRect(width - 60 + shadow_offset, h_line_y - 25 + shadow_offset, 50, 20), Qt.AlignmentFlag.AlignCenter, "紧急")
        painter.setPen(text_color)
        painter.drawText(QRect(width - 60, h_line_y - 25, 50, 20), Qt.AlignmentFlag.AlignCenter, "紧急")
        
        # 不紧急
        painter.setPen(shadow_color)
        painter.drawText(QRect(10 + shadow_offset, h_line_y - 25 + shadow_offset, 50, 20), Qt.AlignmentFlag.AlignCenter, "不紧急")
        painter.setPen(text_color)
        painter.drawText(QRect(10, h_line_y - 25, 50, 20), Qt.AlignmentFlag.AlignCenter, "不紧急")
        
        # 重要
        painter.setPen(shadow_color)
        painter.drawText(QRect(v_line_x - 30 + shadow_offset, 10 + shadow_offset, 60, 20), Qt.AlignmentFlag.AlignCenter, "重要")
        painter.setPen(text_color)
        painter.drawText(QRect(v_line_x - 30, 10, 60, 20), Qt.AlignmentFlag.AlignCenter, "重要")
        
        # 不重要
        painter.setPen(shadow_color)
        painter.drawText(QRect(v_line_x - 30 + shadow_offset, height - 30 + shadow_offset, 60, 20), Qt.AlignmentFlag.AlignCenter, "不重要")
        painter.setPen(text_color)
        painter.drawText(QRect(v_line_x - 30, height - 30, 60, 20), Qt.AlignmentFlag.AlignCenter, "不重要")
    

    def center_control_panel(self):
        # 获取控制面板尺寸
        control_width = self.control_widget.width()
        control_height = self.control_widget.height()
        
        # 计算中心位置并限制在窗口范围内
        center_x = max(0, (self.width() - control_width) // 2)  # 确保不小于0
        center_y = max(0, (self.height() - control_height) // 2)
        
        # 更新位置并保存到配置
        self.control_widget.move(center_x, center_y)
        self.config['control_panel']['x'] = center_x
        self.config['control_panel']['y'] = center_y
        self._position_dirty = True # 标记控制面板位置有变动

    def mouseDoubleClickEvent(self, event):
        """鼠标双击事件"""
        if not self.edit_mode:
            self.toggle_edit_mode()
        else:
            # 在编辑模式下双击创建任务，在双击位置创建
            self.create_task_at_position(event.pos())
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            # 右键点击空白区域时召唤控制面板
            click_pos = event.position().toPoint()  # 注意这里是相对于当前窗口的局部位置
            
            # 让控制面板居中对齐到鼠标点击位置
            control_width = self.control_widget.width()
            control_height = self.control_widget.height()
            new_x = click_pos.x() - control_width // 2
            new_y = click_pos.y() - control_height // 2
            
            # 限制在窗口范围内（避免超出）
            new_x = max(0, min(new_x, self.width() - control_width))+20
            new_y = max(0, min(new_y, self.height() - control_height))+20
            
            self.control_widget.move(new_x, new_y)
            
            # 保存位置
            self.config.setdefault('control_panel', {})
            self.config['control_panel']['x'] = new_x
            self.config['control_panel']['y'] = new_y
            self._position_dirty = True  # 标记位置有变动
            
            # 确保控制面板显示
            self.control_widget.show()

            event.accept()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.pos()
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
    
    def toggle_edit_mode(self):
        """切换编辑模式"""
        # 更新按钮文本
        self.edit_mode = not self.edit_mode
        self.edit_button.setText("正在编辑" if self.edit_mode else "正在查看")
        
        # 更新任务的可拖动状态
        for task in self.tasks:
            task.set_draggable(self.edit_mode)
        
        # 使用UI管理器的通用批量操作方法
        # 定义需要切换的子控件
        edit_mode_children = ["add_task_button", "export_tasks_button"]
        if len(self.undo_stack) > 0:
            edit_mode_children.append("undo_button")
        
        # 批量切换控件显示状态
        self.ui_manager.batch_toggle_widgets(edit_mode_children, self.edit_mode, animate=False)
        
        # 调整控制面板大小
        self.ui_manager.adjust_container_size("control_panel")
        
        # 确保控制面板在边界内
        self.ui_manager.ensure_widget_in_bounds("control_panel")

        # 保存当前状态到配置
        self.config['edit_mode'] = self.edit_mode
    
    def add_task(self):
        """添加新任务 - 在窗口中央创建"""
        # 在窗口中央位置创建任务
        center_pos = QPoint(self.width() // 2, self.height()//2)
        self.create_task_at_position(center_pos)
        
    def create_task_at_position(self, position):
        """在指定位置创建新任务"""
        # 从配置中获取任务字段定义
        task_fields = self.config.get('task_fields', [])
        
        dialog = AddTaskDialog(self, task_fields)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return                          # 点了取消

        # 从对话框中获取字段值
        task_data = dialog.get_data()   # ← 只要这一行就拿到全部字段值
        
        # 检查必填
        for f in task_fields:
            if f.get("required") and not task_data.get(f["name"]):
                QMessageBox.warning(self, "提示", f"{f['label']} 为必填项")
                return
                
        # 使用传入的位置确定在哪个象限
        local_pos = position
        
        # 确定象限和颜色
        quadrant, color = self.get_quadrant_at_position(local_pos)

        # 根据象限确定优先级
        if task_data['priority']=="default":
            if quadrant in ["q1"]:
                task_data['priority'] = "高"
            elif quadrant in ["q2","q3"]:
                task_data['priority'] = "中"
            else:
                task_data['priority'] = "低"
        
        # 创建任务ID
        task_id = f"task_{len(self.tasks)}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 保存当前状态到撤销栈
        self.save_undo_state()
        
        # 创建新任务标签
        exclude_keys = {"task_id", "color", "parent", "completed"}
        field_values = {k: v for k, v in task_data.items() if k not in exclude_keys}
        task = TaskLabel(
            task_id=task_id,
            color=color,
            parent=self,
            completed=False,
            **field_values
        )
        # 设置可拖动状态
        if self.edit_mode:
            task.set_draggable(True)
        
        # 设置任务位置并连接信号
        task.move(local_pos.x() - 75, local_pos.y() - 40)  # 居中放置
        task.deleteRequested.connect(self.delete_task)
        task.statusChanged.connect(self.save_tasks)
        
        # 先显示任务，确保立即可见
        task.show()
        
        # 添加到任务列表
        self.tasks.append(task)
        
        # 保存任务
        self.save_tasks()
    
    def get_quadrant_at_position(self, pos):
        """根据位置确定象限和颜色"""
        width = self.width()
        height = self.height()
        h_line_y = height // 2
        v_line_x = width // 2
        
        if pos.x() >= v_line_x and pos.y() < h_line_y:
            # 第一象限：重要且紧急（右上）
            return 'q1', self.config['quadrants']['q1']['color']
        elif pos.x() < v_line_x and pos.y() < h_line_y:
            # 第二象限：重要不紧急（左上）
            return 'q2', self.config['quadrants']['q2']['color']
        elif pos.x() >= v_line_x and pos.y() >= h_line_y:
            # 第三象限：不重要但紧急（右下）
            return 'q3', self.config['quadrants']['q3']['color']
        else:
            # 第四象限：不重要不紧急（左下）
            return 'q4', self.config['quadrants']['q4']['color']
    
    def delete_task(self, task):
        """逻辑删除任务（从界面隐藏，但保留在数据文件中）"""
        # 保存当前状态到撤销栈
        self.save_undo_state()
        
        # 从列表中移除任务（只是从界面隐藏）
        if task in self.tasks:
            self.tasks.remove(task)
            task.deleteLater()
            
            # 保存任务 - 这会触发逻辑删除，任务会被标记为deleted=True
            self.save_tasks()
    
    def save_undo_state(self):
        """保存当前状态到撤销栈"""
        logger.debug("正在保存当前状态到撤销栈...")
        
        # 收集当前状态
        current_state = {
            'tasks': [],  # 任务信息
            'config': json.loads(json.dumps(self.config)),  # 深拷贝配置
            'control_panel': {
                'x': self.control_widget.x(),
                'y': self.control_widget.y()
            }
        }
        
        # 保存所有任务的信息和位置
        for task in self.tasks:
            task_data = task.get_data()
            task_data['x'] = task.x()
            task_data['y'] = task.y()
            current_state['tasks'].append(task_data)
        
        # 添加到撤销栈
        self.undo_stack.append(current_state)
        
        # 限制撤销栈大小为5
        if len(self.undo_stack) > 5:
            self.undo_stack.pop(0)  # 移除最旧的状态
        
        # 确保撤销按钮在编辑模式下可见
        if self.edit_mode:
            if self.ui_manager:
                self.ui_manager.batch_toggle_widgets(["undo_button"], True, animate=False)
                self.ui_manager.adjust_container_size("control_panel")
                self.ui_manager.ensure_widget_in_bounds("control_panel")
            else:
                self.undo_button.setVisible(True)
                self.control_widget.adjustSize()
                self.control_widget.updateGeometry()
            
        logger.debug(f"状态已保存，撤销栈大小: {len(self.undo_stack)}")

    def undo_action(self):
        """撤销上一次操作"""
        if not self.undo_stack:
            logger.debug("撤销栈为空，无法撤销")
            return
            
        logger.debug("正在执行撤销操作...")
        
        # 弹出最近的状态
        previous_state = self.undo_stack.pop()
        
        # 恢复配置
        self.config = previous_state['config']
        
        # 恢复控制面板位置
        control_panel = previous_state.get('control_panel', {})
        if control_panel:
            self.control_widget.move(control_panel['x'], control_panel['y'])
        
        # 清除当前所有任务
        for task in self.tasks:
            task.deleteLater()
        self.tasks.clear()
        
        # 恢复任务
        for task_data in previous_state['tasks']:
            # 提取位置信息
            x = task_data.pop('x', 0)
            y = task_data.pop('y', 0)
            
            # 创建任务
            task_id = task_data.get('task_id', f"task_{len(self.tasks)}_{datetime.now().strftime('%Y%m%d%H%M%S')}")
            color = task_data.pop('color', '#FFFFFF')
            completed = task_data.pop('completed', False)
            
            # 创建任务标签
            task = TaskLabel(
                task_id=task_id,
                color=color,
                parent=self,
                completed=completed,
                **task_data
            )
            
            # 设置任务位置
            task.move(x, y)
            
            # 连接信号
            task.deleteRequested.connect(self.delete_task)
            task.statusChanged.connect(self.save_tasks)
            
            # 显示任务
            task.show()
            
            # 添加到任务列表
            self.tasks.append(task)
        
        # 更新界面
        self.update()
        
        # 如果撤销栈为空，隐藏撤销按钮
        if not self.undo_stack:
            self.undo_button.setVisible(False)
            # 更新控制面板尺寸
            self.control_widget.adjustSize()
            self.control_widget.updateGeometry()
        
            
        # 保存当前状态
        self.save_tasks()
        # self.save_config()
        
        logger.debug(f"撤销完成，剩余撤销栈大小: {len(self.undo_stack)}")
    
    def show_settings(self):
        """显示设置对话框 - 美化版"""
        dialog = QDialog(self)
        dialog.setWindowTitle("设置")
        dialog.setMinimumWidth(550)  # 增加宽度
        
        style_manager = StyleManager()
        # 设置对话框样式 - 白色主题
        dialog.setStyleSheet(style_manager.get_stylesheet("settings_panel").format())
        
        # 创建标签页
        tab_widget = QTabWidget()
        
        # 创建颜色设置页
        color_widget = QWidget()
        color_layout = QFormLayout(color_widget)
        color_layout.setSpacing(20)  # 增加间距
        color_layout.setContentsMargins(30, 30, 30, 30)  # 增加边距
        
        # 为每个象限创建颜色选择器和透明度滑块
        quadrant_names = {
            'q1': "重要且紧急（右上）",
            'q2': "重要不紧急（左上）",
            'q3': "不重要但紧急（右下）",
            'q4': "不重要不紧急（左下）"
        }
        
        color_buttons = {}
        opacity_sliders = {}
        
        for q_id, q_name in quadrant_names.items():
            # 颜色选择按钮
            color_btn = QPushButton()
            color = QColor(self.config['quadrants'][q_id]['color'])
            color_btn.setStyleSheet(f"background-color: {color.name()}; border-radius: 15px;")
            color_btn.setFixedSize(30, 30)
            color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            color_btn.clicked.connect(lambda checked, qid=q_id: self.change_quadrant_color(qid))
            color_buttons[q_id] = color_btn
            
            # 透明度滑块
            opacity_slider = QSlider(Qt.Orientation.Horizontal)
            opacity_slider.setRange(1, 100)
            opacity_slider.setValue(int(self.config['quadrants'][q_id]['opacity'] * 100))
            opacity_slider.valueChanged.connect(lambda value, qid=q_id: self.change_quadrant_opacity(qid, value / 100))
            opacity_sliders[q_id] = opacity_slider
            
            # 添加到布局
            color_layout.addRow(f"{q_name} 颜色:", color_btn)
            color_layout.addRow(f"{q_name} 透明度:", opacity_slider)
        
        # 创建大小设置页
        size_widget = QWidget()
        size_layout = QFormLayout(size_widget)
        size_layout.setSpacing(20)  # 增加间距
        size_layout.setContentsMargins(30, 30, 30, 30)  # 增加边距
        
        # 宽度设置
        width_spin = QSpinBox()
        width_spin.setRange(300, 2000)
        width_spin.setValue(self.config['size']['width'])
        width_spin.valueChanged.connect(lambda value: self.change_size('width', value))
        
        # 高度设置
        height_spin = QSpinBox()
        height_spin.setRange(300, 2000)
        height_spin.setValue(self.config['size']['height'])
        height_spin.valueChanged.connect(lambda value: self.change_size('height', value))
        
        # UI设置
        ui_widget = QWidget()
        ui_layout = QFormLayout(ui_widget)
        ui_layout.setSpacing(20)  # 增加间距
        ui_layout.setContentsMargins(30, 30, 30, 30)  # 增加边距
        
        # 圆角设置
        border_radius_spin = QSpinBox()
        border_radius_spin.setRange(0, 50)
        border_radius_spin.setValue(self.config.get('ui', {}).get('border_radius', 15))
        border_radius_spin.valueChanged.connect(lambda value: self.update_ui_config('border_radius', value))
        
        # 添加到布局
        size_layout.addRow("宽度:", width_spin)
        size_layout.addRow("高度:", height_spin)
        ui_layout.addRow("圆角半径:", border_radius_spin)
        
        # 添加标签页
        tab_widget.addTab(color_widget, "颜色设置")
        tab_widget.addTab(size_widget, "大小设置")
        tab_widget.addTab(ui_widget, "界面设置")
        
        # 创建对话框布局
        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.setContentsMargins(15, 15, 15, 15)
        dialog_layout.addWidget(tab_widget)
        
        # 添加确定按钮
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        ok_button.clicked.connect(dialog.accept)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        dialog_layout.addLayout(button_layout)
        
        
        # 添加对话框阴影
        apply_drop_shadow(dialog, blur_radius=20, color=QColor(0, 0, 0, 150), offset_x=0, offset_y=0)
        
        # 设置对话框在父窗口中居中显示
        dialog.move(
            self.x() + (self.width() - dialog.width()) // 2,
            self.y() + (self.height() - dialog.height()) // 2
        )
        
        # 显示对话框
        dialog.exec()
    

    def export_unfinished_tasks(self):
        """导出未完成的任务到文本文件"""
        # 获取桌面路径作为默认保存位置
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        default_filename = os.path.join(desktop_path, "未完成任务.txt")
        
        # 打开文件保存对话框
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "保存未完成任务",
            default_filename,
            "文本文件 (*.txt);;所有文件 (*)"
        )
        
        if not filename:  # 用户取消了保存
            logger.info("用户取消了导出任务操作")
            return
            
        # 收集未完成的任务
        unfinished_tasks = []
        for i, task in enumerate(self.tasks):
            if not task.checkbox.isChecked():
                task_info = []
                # 添加序号（如果需要）
                task_info.append(f"{len(unfinished_tasks) + 1}.")
                
                # 添加标题
                if hasattr(task, 'text') and task.text:
                    task_info.append(f"{task.text}")
                
                # 添加备注
                if hasattr(task, 'notes') and task.notes:
                    task_info.append(f"\n备注: {task.notes}")
                
                if task_info:  # 只有当有内容时才添加
                    unfinished_tasks.append("".join(task_info))
        
        # 如果没有未完成的任务
        if not unfinished_tasks:
            logger.info("导出任务失败：没有未完成的任务可导出")
            QMessageBox.information(self, "导出任务", "没有未完成的任务可导出")
            return
            
        # 写入文件
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("\n\n".join(unfinished_tasks))
            logger.info(f"成功导出 {len(unfinished_tasks)} 个未完成任务到: {filename}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出任务时发生错误:\n{str(e)}")
            error_msg = f"导出任务时发生错误: {str(e)}"
            logger.error(error_msg)

    def export_all_tasks(self):
        """导出所有任务到Excel文件（包括已完成），列名为创建日期、截止日期、修改日期，后面为事项所有属性"""
        try:
            import pandas as pd
        except ImportError:
            QMessageBox.critical(self, "导出失败", "未安装pandas库，无法导出为Excel。请先安装pandas。")
            logger.error("导出失败：未安装pandas库")
            return
        
        try:
            import openpyxl
        except ImportError:
            QMessageBox.critical(self, "导出失败", "未安装openpyxl库，无法导出为Excel。请先安装openpyxl。\n\n安装命令：pip install openpyxl")
            logger.error("导出失败：未安装openpyxl库")
            return

        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        default_filename = os.path.join(desktop_path, "所有任务.xlsx")
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "保存所有任务",
            default_filename,
            "Excel文件 (*.xlsx);;所有文件 (*)"
        )
        if not filename:
            logger.info("用户取消了导出所有任务操作")
            return

        # 读取 tasks.json 文件
        try:
            with open(TASKS_FILE, 'r', encoding='utf-8') as f:
                all_tasks_data = json.load(f)
        except Exception as e:
            logger.error(f"读取任务文件失败: {str(e)}")
            QMessageBox.critical(self, "导出失败", f"读取任务文件失败: {str(e)}")
            return

        if not all_tasks_data:
            logger.info("导出任务失败：没有任务可导出")
            QMessageBox.information(self, "导出任务", "没有任务可导出")
            return

        # 获取字段配置
        field_names = [f['name'] for f in self.config.get('task_fields', [])]
        
        # 准备数据行
        rows = []
        for task_data in all_tasks_data:
            # 可选：如果你只想导出未被删除的任务，加上下面一行
            # if task_data.get('deleted', False): continue

            row = {
                '任务名': task_data.get('text_history', [{}])[-1].get('value', ''),
                '到期日期': task_data.get('due_date_history', [{}])[-1].get('value', ''),
                '优先级': task_data.get('priority_history', [{}])[-1].get('value', ''),
                '备注': task_data.get('notes_history', [{}])[-1].get('value', ''),
                '目录': task_data.get('directory_history', [{}])[-1].get('value', ''),
                '创建日期': task_data.get('create_date_history', [{}])[-1].get('value', ''),
                '完成状态': '已完成' if task_data.get('completed', False) else '未完成',
                '完成日期': task_data.get('completed_date', '')
            }
            rows.append(row)

        if not rows:
            logger.info("导出任务失败：没有有效任务可导出")
            QMessageBox.information(self, "导出任务", "没有有效任务可导出")
            return

        # 定义列的顺序
        column_order = [
            '任务名', '到期日期', '优先级', '备注', '目录', '创建日期',
            '完成状态', '完成日期', 
        ]

        try:
            # 创建DataFrame
            df = pd.DataFrame(rows)
            
            # 重新排列列的顺序
            existing_columns = [col for col in column_order if col in df.columns]
            df = df[existing_columns]
            
            # 导出到Excel
            df.to_excel(filename, index=False)
            logger.info(f"成功导出 {len(df)} 个任务到: {filename}")
            QMessageBox.information(self, "导出成功", f"成功导出 {len(df)} 个任务到:\n{filename}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出任务时发生错误:\n{str(e)}")
            logger.error(f"导出任务时发生错误: {str(e)}")


    def update_ui_config(self, key, value):
        """更新UI配置"""
        if 'ui' not in self.config:
            self.config['ui'] = {}
        self.config['ui'][key] = value
        self.save_config()
        
        # 如果更改了圆角半径，立即更新界面
        if key == 'border_radius':
            self.update()
    
    def change_quadrant_color(self, quadrant_id):
        """更改象限颜色"""
        current_color = QColor(self.config['quadrants'][quadrant_id]['color'])
        color_dialog = QColorDialog(current_color, self)
        color_dialog.setWindowTitle("选择象限颜色")
        
        if color_dialog.exec() == QDialog.DialogCode.Accepted: 
            color = color_dialog.selectedColor()
            if color.isValid():
                self.config['quadrants'][quadrant_id]['color'] = color.name()
                self.save_config()
                self.update()
    
    def change_quadrant_opacity(self, quadrant_id, opacity):
        """更改象限透明度"""
        self.config['quadrants'][quadrant_id]['opacity'] = opacity
        self.save_config()
        self.update()
    
    def change_size(self, dimension, value):
        """更改窗口大小"""
        self.config['size'][dimension] = value
        self.resize(self.config['size']['width'], self.config['size']['height'])
        self.save_config()

        # 调整控制面板位置
        self.control_widget.adjustSize()  # 确保尺寸更新
        self.center_control_panel()
        self._position_dirty = True  # 标记有变动
    
    def save_config(self):
        """保存配置到文件"""
        logger.info("正在保存配置到文件...")
        # 更新位置信息
        self.config['position']['x'] = self.x()
        self.config['position']['y'] = self.y()
        
        save_config(self.config, self)
    
    def load_tasks(self):
        """从文件加载任务（支持历史记录）"""
        logger.info("正在从文件加载任务...")
        
        # 清除当前所有任务
        for task in self.tasks:
            task.deleteLater()
        self.tasks.clear()
        
        try:
            # 使用新的历史记录加载函数
            from config_manager import load_tasks_with_history
            tasks_data = load_tasks_with_history()
            
            # 加载可见的任务
            for task_data in tasks_data:
                # 创建任务标签 - 支持所有自定义字段
                task = TaskLabel(
                                task_id=task_data['id'],
                                color=task_data['color'],
                                parent=self,
                                completed=task_data['completed'],
                                **{field['name']: task_data.get(field['name'], "" if field.get('required') else None) 
                                for field in self.config.get('task_fields', [])}
                            )
                
                # 设置位置
                if 'position' in task_data:
                    task.move(task_data['position']['x'], task_data['position']['y'])
                
                # 连接信号
                task.deleteRequested.connect(self.delete_task)
                task.statusChanged.connect(self.save_tasks)
                
                # 显示任务并添加到列表
                task.show()
                self.tasks.append(task)
            logger.info(f"成功加载了 {len(self.tasks)} 个任务")
        except Exception as e:
            logger.error(f"加载任务失败: {str(e)}")
            QMessageBox.warning(self, "加载失败", f"加载任务失败: {str(e)}")
    
    def save_tasks(self, task=None):
        """保存任务到文件"""
        save_tasks(self.tasks, self)

    def closeEvent(self, event):
        """关闭事件"""
        logger.info("正在关闭程序...")
        # 保存配置和任务
        self.save_config()
        self.save_tasks()
        
        # 退出前：确保内存缓存写盘并进行一次远程同步
        try:
            db_manager = get_db_manager()
            # 先写盘，确保数据库与缓存一致
            db_manager.flush_cache_to_db()
            # 如果配置了远程，则执行一次上传同步
            if getattr(db_manager, 'api_base_url', ''):
                sync_ok = db_manager.sync_to_server()
                logger.info(f"退出前远程同步结果: {sync_ok}")
                # 同步后的状态也写盘
                db_manager.flush_cache_to_db()
            # 关闭连接并停止后台线程
            db_manager.close_connection()
        except Exception as e:
            logger.error(f"退出时写盘/同步失败: {str(e)}")
        
        logger.info("程序关闭前的保存/同步操作完成，即将退出")
        # 确保程序完全退出
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().quit()
        
        event.accept()