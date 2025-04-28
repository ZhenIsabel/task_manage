import json
import os
from datetime import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QColorDialog, QSlider, 
                             QLabel, QGridLayout, QSizePolicy, QCheckBox, QLineEdit, QInputDialog, 
                             QMessageBox, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QDialog,
                             QTabWidget, QFormLayout, QSpinBox, QDateEdit)
from PyQt5.QtCore import Qt, QPoint, QSize, QRect, QPropertyAnimation, QEasingCurve, QTimer, QDate
from PyQt5.QtGui import QColor, QPainter, QPen, QBrush, QFont, QCursor, QPainterPath, QLinearGradient

from task_label import TaskLabel
from config_manager import save_config, save_tasks, TASKS_FILE
from add_task_dialog import AddTaskDialog

class QuadrantWidget(QWidget):
    """四象限窗口部件"""
    def __init__(self, config, parent=None):
        print("正在初始化四象限窗口...")
        super().__init__(parent)
        self.config = config
        self.edit_mode = False
        self.tasks = []
        self.undo_stack = []
        
        # 设置窗口属性 - 增强桌面融合效果
        if self.config.get('ui', {}).get('desktop_mode', True):
            # 设置为无边框、保持在底层且作为桌面级窗口
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnBottomHint | Qt.Tool)
            # 设置窗口为透明背景
            self.setAttribute(Qt.WA_TranslucentBackground)
            # 允许鼠标事件穿透到桌面
            if hasattr(Qt, 'WA_TransparentForMouseEvents'):
                self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
            # 设置窗口不在显示桌面时隐藏
            self.setAttribute(Qt.WA_ShowWithoutActivating)
        else:
            # 普通窗口模式
            self.setWindowFlags(Qt.FramelessWindowHint)
            self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 设置大小和位置
        self.resize(config['size']['width'], config['size']['height'])
        self.move(config['position']['x'], config['position']['y'])
        
        # 创建布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)  # 增加边距使界面更宽敞
        
        # 创建控制按钮区域 - 美化控制面板
        self.control_widget = QWidget(self)
        self.control_layout = QHBoxLayout(self.control_widget)
        self.control_layout.setSpacing(10)  # 增加按钮间距
        
        # 设置控制面板样式
        self.control_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(40, 40, 40, 0.7);
                border-radius: 15px;
                padding: 5px;
            }
            QPushButton {
                background-color: rgba(60, 60, 60, 0.8);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 15px;
                font-family: '微软雅黑';
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(80, 80, 80, 0.9);
            }
            QPushButton:pressed {
                background-color: rgba(100, 100, 100, 1.0);
            }
        """)
        
        # 确保控制面板可见（设置透明度>0）
        self.control_widget.setProperty("opacity", 1.0)

        # 添加按钮
        self.edit_button = QPushButton("编辑模式" if not self.edit_mode else "查看模式", self)
        self.edit_button.clicked.connect(self.toggle_edit_mode)
        self.edit_button.setCursor(Qt.PointingHandCursor)  # 鼠标悬停时显示手型光标
        
        self.add_task_button = QPushButton("添加任务", self)
        self.add_task_button.clicked.connect(self.add_task)
        self.add_task_button.setVisible(False)  # 初始隐藏
        self.add_task_button.setCursor(Qt.PointingHandCursor)
        
        self.undo_button = QPushButton("撤销", self)
        self.undo_button.clicked.connect(self.undo_action)
        self.undo_button.setVisible(False)  # 初始隐藏
        self.undo_button.setCursor(Qt.PointingHandCursor)
        
        self.settings_button = QPushButton("设置", self)
        self.settings_button.clicked.connect(self.show_settings)
        self.settings_button.setCursor(Qt.PointingHandCursor)
        
        self.exit_button = QPushButton("退出", self)
        self.exit_button.clicked.connect(self.close)
        self.exit_button.setCursor(Qt.PointingHandCursor)
        
        # 添加按钮到布局
        self.control_layout.addWidget(self.edit_button)
        self.control_layout.addWidget(self.add_task_button)
        self.control_layout.addWidget(self.undo_button)
        self.control_layout.addWidget(self.settings_button)
        self.control_layout.addWidget(self.exit_button)
        
        # 添加控制面板阴影效果
        control_shadow = QGraphicsDropShadowEffect(self)
        control_shadow.setBlurRadius(20)
        control_shadow.setColor(QColor(0, 0, 0, 100))
        control_shadow.setOffset(0, 0)
        self.control_widget.setGraphicsEffect(control_shadow)
        
        # 添加控制面板到主布局
        # 先创建一个单独的布局用于控制面板
        self.control_container = QVBoxLayout()
        self.control_container.addWidget(self.control_widget)
        self.control_container.addStretch()
        
        # 创建一个布局用于四象限区域
        self.quadrant_layout = QVBoxLayout()
        self.quadrant_layout.addStretch()
        
        # 将四象限布局添加到主布局
        self.main_layout.addLayout(self.control_container)
        self.main_layout.addLayout(self.quadrant_layout)

    
    def paintEvent(self, event):
        """绘制事件 - 美化版本"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)  # 抗锯齿
        
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
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, width, height, border_radius, border_radius)
        
        # 计算内部四象限区域（留出边距）
        margin = 10
        inner_width = width - 2 * margin
        inner_height = height - 2 * margin
        inner_h_line_y = h_line_y
        inner_v_line_x = v_line_x
        
        # 绘制四个象限的背景 - 使用圆角矩形
        # 第一象限：重要且紧急（右上）
        q1_color = QColor(self.config['quadrants']['q1']['color'])
        q1_color.setAlphaF(self.config['quadrants']['q1']['opacity'])
        painter.setBrush(QBrush(q1_color))
        painter.setPen(Qt.NoPen)
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
        painter.drawText(QRect(width - 150 + shadow_offset, 10 + shadow_offset, 140, 30), Qt.AlignRight, "重要且紧急")
        painter.setPen(text_color)
        painter.drawText(QRect(width - 150, 10, 140, 30), Qt.AlignRight, "重要且紧急")
        
        # 重要不紧急
        painter.setPen(shadow_color)
        painter.drawText(QRect(10 + shadow_offset, 10 + shadow_offset, 140, 30), Qt.AlignLeft, "重要不紧急")
        painter.setPen(text_color)
        painter.drawText(QRect(10, 10, 140, 30), Qt.AlignLeft, "重要不紧急")
        
        # 不重要但紧急
        painter.setPen(shadow_color)
        painter.drawText(QRect(width - 150 + shadow_offset, height - 40 + shadow_offset, 140, 30), Qt.AlignRight, "不重要但紧急")
        painter.setPen(text_color)
        painter.drawText(QRect(width - 150, height - 40, 140, 30), Qt.AlignRight, "不重要但紧急")
        
        # 不重要不紧急
        painter.setPen(shadow_color)
        painter.drawText(QRect(10 + shadow_offset, height - 40 + shadow_offset, 140, 30), Qt.AlignLeft, "不重要不紧急")
        painter.setPen(text_color)
        painter.drawText(QRect(10, height - 40, 140, 30), Qt.AlignLeft, "不重要不紧急")
        
        # 绘制坐标轴标签 - 带阴影效果
        # 紧急
        painter.setPen(shadow_color)
        painter.drawText(QRect(width - 60 + shadow_offset, h_line_y - 25 + shadow_offset, 50, 20), Qt.AlignCenter, "紧急")
        painter.setPen(text_color)
        painter.drawText(QRect(width - 60, h_line_y - 25, 50, 20), Qt.AlignCenter, "紧急")
        
        # 不紧急
        painter.setPen(shadow_color)
        painter.drawText(QRect(10 + shadow_offset, h_line_y - 25 + shadow_offset, 50, 20), Qt.AlignCenter, "不紧急")
        painter.setPen(text_color)
        painter.drawText(QRect(10, h_line_y - 25, 50, 20), Qt.AlignCenter, "不紧急")
        
        # 重要
        painter.setPen(shadow_color)
        painter.drawText(QRect(v_line_x - 30 + shadow_offset, 10 + shadow_offset, 60, 20), Qt.AlignCenter, "重要")
        painter.setPen(text_color)
        painter.drawText(QRect(v_line_x - 30, 10, 60, 20), Qt.AlignCenter, "重要")
        
        # 不重要
        painter.setPen(shadow_color)
        painter.drawText(QRect(v_line_x - 30 + shadow_offset, height - 30 + shadow_offset, 60, 20), Qt.AlignCenter, "不重要")
        painter.setPen(text_color)
        painter.drawText(QRect(v_line_x - 30, height - 30, 60, 20), Qt.AlignCenter, "不重要")
    
    def mouseDoubleClickEvent(self, event):
        """鼠标双击事件"""
        if not self.edit_mode:
            self.toggle_edit_mode()
        else:
            # 在编辑模式下双击创建任务，在双击位置创建
            self.create_task_at_position(event.pos())
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def toggle_edit_mode(self):
        """切换编辑模式"""
        self.edit_mode = not self.edit_mode
        self.edit_button.setText("查看模式" if self.edit_mode else "编辑模式")
        self.add_task_button.setVisible(self.edit_mode)
        self.undo_button.setVisible(self.edit_mode)
        
        # 保存当前状态到配置
        self.config['edit_mode'] = self.edit_mode
        self.save_config()
    
    def add_task(self):
        """添加新任务 - 在窗口中央创建"""
        # 在窗口中央位置创建任务
        center_pos = QPoint(self.width() // 2, self.height()//2)
        self.create_task_at_position(center_pos)
        
    def create_task_at_position(self, position):
        """在指定位置创建新任务"""
        # 从配置中获取任务字段定义
        task_fields = self.config.get('task_fields', [])
        # 如果没有找到自定义字段配置，使用默认字段
        if not task_fields:
            task_fields = [
                {'name': 'text', 'label': '任务内容', 'type': 'text', 'required': True},
                {'name': 'due_date', 'label': '到期日期', 'type': 'date', 'required': False}
            ]
        
        dialog = AddTaskDialog(self, task_fields)
        if dialog.exec_() != QDialog.Accepted:
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
        
        # 创建任务ID
        task_id = f"task_{len(self.tasks)}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 保存当前状态到撤销栈
        self.save_undo_state()
        
        # 创建新任务标签
        task = TaskLabel(
            task_id=task_id, 
            text=task_data.get('text', ''),
            color=color, 
            parent=self,
            completed=False, 
            due_date=task_data.get('due_date'),
            priority=task_data.get('priority'),
            notes=task_data.get('notes')
        )
        
        # 设置任务位置并连接信号
        task.move(local_pos.x() - 75, local_pos.y() - 40)  # 居中放置
        task.deleteRequested.connect(self.delete_task)
        task.statusChanged.connect(self.save_tasks)
        
        # 先显示任务，确保立即可见
        task.show()
        
        # 添加动画效果
        if self.config.get('ui', {}).get('animation_enabled', True):
            # 创建并设置透明度效果
            task_opacity = QGraphicsOpacityEffect(task)
            task_opacity.setOpacity(0.0)
            task.setGraphicsEffect(task_opacity)
            
            # 创建淡入动画
            fade_in = QPropertyAnimation(task_opacity, b"opacity")
            fade_in.setDuration(500)  # 0.5秒淡入
            fade_in.setStartValue(0.0)
            fade_in.setEndValue(1.0)
            fade_in.setEasingCurve(QEasingCurve.InOutQuad)
            # 保存动画对象的引用，防止被垃圾回收
            task.fade_animation = fade_in
            # 确保任务立即可见
            task.update()
            fade_in.start()
        
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
        """删除任务"""
        # 保存当前状态到撤销栈
        self.save_undo_state()
        
        # 从列表中移除任务
        if task in self.tasks:
            self.tasks.remove(task)
            task.deleteLater()
            
            # 保存任务 - 不需要再添加回列表
            self.save_tasks()
    
    def save_undo_state(self):
        """保存当前状态到撤销栈"""
        tasks_data = [task.get_data() for task in self.tasks]
        self.undo_stack.append(tasks_data)
        
        # 限制撤销栈大小
        if len(self.undo_stack) > 10:
            self.undo_stack.pop(0)
    
    def undo_action(self):
        """撤销上一个操作"""
        if self.undo_stack:
            # 获取上一个状态
            previous_state = self.undo_stack.pop()
            
            # 清除当前所有任务
            for task in self.tasks:
                task.deleteLater()
            self.tasks.clear()
            
            # 恢复上一个状态的任务
            for task_data in previous_state:
                task = TaskLabel(
                    task_data['id'],
                    task_data['text'],
                    task_data['color'],
                    self,
                    task_data['completed']
                )
                task.move(task_data['position']['x'], task_data['position']['y'])
                task.deleteRequested.connect(self.delete_task)
                task.statusChanged.connect(self.save_tasks)
                task.show()
                self.tasks.append(task)
            
            # 添加到任务列表
            self.tasks.append(task)
            
            # 保存任务
            self.save_tasks()
    
    def show_settings(self):
        """显示设置对话框 - 美化版"""
        dialog = QDialog(self)
        dialog.setWindowTitle("设置")
        dialog.setMinimumWidth(550)  # 增加宽度
        
        # 设置对话框样式 - 白色主题
        dialog.setStyleSheet("""
            QDialog {
                background-color: white;
                border-radius: 15px;
                border: 1px solid #e0e0e0;
            }
            QTabWidget::pane {
                border: 1px solid #e0e0e0;
                background-color: white;
                border-radius: 8px;
            }
            QTabBar::tab {
                background-color: #f5f5f5;
                color: #505050;
                border: 1px solid #e0e0e0;
                border-bottom: none;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-family: '微软雅黑';
            }
            QTabBar::tab:selected {
                background-color: white;
                color: #4ECDC4;
                font-weight: bold;
            }
            QLabel {
                color: #505050;
                font-family: '微软雅黑';
                font-size: 13px;
            }
            QSpinBox {
                background-color: #f5f5f5;
                color: #505050;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                padding: 8px;
                min-height: 24px;
            }
            QSlider::groove:horizontal {
                height: 8px;
                background: #e0e0e0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #4ECDC4;
                width: 16px;
                height: 16px;
                margin: -4px 0;
                border-radius: 8px;
            }
            QPushButton {
                background-color: #4ECDC4;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-family: '微软雅黑';
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45B8B0;
            }
            QCheckBox {
                color: #505050;
                font-family: '微软雅黑';
                padding: 5px;
            }
        """)
        
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
            color_btn.setCursor(Qt.PointingHandCursor)
            color_btn.clicked.connect(lambda checked, qid=q_id: self.change_quadrant_color(qid))
            color_buttons[q_id] = color_btn
            
            # 透明度滑块
            opacity_slider = QSlider(Qt.Horizontal)
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
        
        # 动画效果开关
        animation_checkbox = QCheckBox()
        animation_checkbox.setChecked(self.config.get('ui', {}).get('animation_enabled', True))
        animation_checkbox.stateChanged.connect(lambda state: self.update_ui_config('animation_enabled', state == Qt.Checked))
        
        # 桌面融合模式开关
        desktop_mode_checkbox = QCheckBox()
        desktop_mode_checkbox.setChecked(self.config.get('ui', {}).get('desktop_mode', True))
        desktop_mode_checkbox.stateChanged.connect(lambda state: self.update_ui_config('desktop_mode', state == Qt.Checked))
        
        # 添加到布局
        size_layout.addRow("宽度:", width_spin)
        size_layout.addRow("高度:", height_spin)
        ui_layout.addRow("圆角半径:", border_radius_spin)
        ui_layout.addRow("启用动画效果:", animation_checkbox)
        ui_layout.addRow("桌面融合模式:", desktop_mode_checkbox)
        
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
        dialog_shadow = QGraphicsDropShadowEffect(dialog)
        dialog_shadow.setBlurRadius(20)
        dialog_shadow.setColor(QColor(0, 0, 0, 150))
        dialog_shadow.setOffset(0, 0)
        dialog.setGraphicsEffect(dialog_shadow)
        
        # 设置对话框在父窗口中居中显示
        dialog.move(
            self.x() + (self.width() - dialog.width()) // 2,
            self.y() + (self.height() - dialog.height()) // 2
        )
        
        # 显示对话框
        dialog.exec_()
    
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
        
        if color_dialog.exec_() == QDialog.Accepted:
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
    
    def save_config(self):
        """保存配置到文件"""
        print("正在保存配置到文件...")
        # 更新位置信息
        self.config['position']['x'] = self.x()
        self.config['position']['y'] = self.y()
        
        save_config(self.config, self)
    
    def save_tasks(self, task=None):
        """保存任务到文件"""
        save_tasks(self.tasks, self)
    
    def load_tasks(self):
        """从文件加载任务"""
        print("正在从文件加载任务...")
        if not os.path.exists(TASKS_FILE):
            print("任务文件不存在，跳过加载")
            return
        
        try:
            print("正在读取任务文件...")
            with open(TASKS_FILE, 'r', encoding='utf-8') as f:
                tasks_data = json.load(f)
            
            # 获取当前日期
            today = datetime.now().strftime('%Y-%m-%d')
            
            # 清除当前所有任务
            for task in self.tasks:
                task.deleteLater()
            self.tasks.clear()
            
            # 加载未完成的任务或当天完成的任务
            for task_data in tasks_data:
                # 跳过已完成且不是今天完成的任务
                if task_data['completed'] and task_data.get('date', '') != today:
                    continue
                
                # 创建任务标签 - 支持所有自定义字段
                task = TaskLabel(
                    task_id=task_data['id'],
                    text=task_data['text'],
                    color=task_data['color'],
                    parent=self,
                    completed=task_data['completed'],
                    due_date=task_data.get('due_date', None),
                    priority=task_data.get('priority', None),
                    notes=task_data.get('notes', None)
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
            print(f"成功加载了 {len(self.tasks)} 个任务")
        except Exception as e:
            print(f"加载任务失败: {str(e)}")
            QMessageBox.warning(self, "加载失败", f"加载任务失败: {str(e)}")
    
    def closeEvent(self, event):
        """关闭事件"""
        print("正在关闭程序...")
        # 保存配置和任务
        self.save_config()
        self.save_tasks()
        print("程序关闭前的保存操作已完成")
        
        # 添加以下代码确保程序完全退出
        from PyQt5.QtWidgets import QApplication
        QApplication.instance().quit()
        
        event.accept()