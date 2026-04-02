import json
import os
import webbrowser
import socket
import time
import threading
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QColorDialog, QSlider,  QMessageBox, QDialog,
                            QTabWidget, QFormLayout, QSpinBox,  QMenu, QTimeEdit, QLabel, QCheckBox, QScrollArea, QLineEdit)
from PyQt6.QtCore import Qt, QPoint,  QRect, QTimer,QUrl, QTime, pyqtSignal
from PyQt6.QtWidgets import QApplication,QFileDialog
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont,  QPainterPath, QLinearGradient, QAction
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    HAS_WEBENGINE = True
except Exception:
    HAS_WEBENGINE = False


from .task_label import TaskLabel
from config.config_manager import save_config, save_tasks
from config.remote_config import RemoteConfigManager
from .add_task_dialog import AddTaskDialog
from ui.styles import StyleManager
from database.database_manager import get_db_manager
from ui.ui import apply_drop_shadow
from gantt.app import gantt_app

import logging
logger = logging.getLogger(__name__)  # 自动获取模块名

class QuadrantWidget(QWidget):
    remote_sync_refresh_requested = pyqtSignal(object)
    remote_bootstrap_finished = pyqtSignal(bool)

    """四象限窗口部件"""
    def __init__(self, config, parent=None, ui_manager=None):
        try:
            logger.debug("正在初始化四象限窗口...")
            super().__init__(parent)
        except Exception as e:
            logger.error(f"四象限窗口初始化失败: {str(e)}", exc_info=True)
            raise
        self.config = config
        self.ui_manager = ui_manager  # 添加UI管理器引用
        self.edit_mode = False
        self.tasks = []
        self.undo_stack = []
        self.db_manager = get_db_manager()
        self._is_closing = False
        self._sync_refresh_pending = False
        self.remote_sync_refresh_requested.connect(self._show_remote_sync_confirmation)
        self.remote_bootstrap_finished.connect(self._on_remote_bootstrap_finished)
        self.db_manager.add_task_sync_listener(self._handle_remote_sync)
        QTimer.singleShot(0, self._bootstrap_remote_sync)
        
        # 设置为无边框、保持在底层且作为桌面级窗口
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint  | Qt.WindowType.Tool)
        # 设置窗口为透明背景
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
       
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

        self.scheduled_task_button = QPushButton("定时任务", self)
        self.scheduled_task_button.clicked.connect(self.scheduled_task)
        self.scheduled_task_button.setVisible(False)  # 初始隐藏
        self.scheduled_task_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # 添加导出未完成任务按钮
        self.export_tasks_button = QPushButton("导出任务", self)
        # 新增：创建菜单
        self.export_menu = QMenu(self.export_tasks_button)
        # 主动设置菜单样式，确保生效
        self.export_menu.setStyleSheet(style_manager.get_stylesheet("menu"))
        self.action_export_unfinished = QAction("导出在办", self)
        self.action_export_all = QAction("导出所有", self)
        self.action_export_summary = QAction("导出概要", self)
        self.export_menu.addAction(self.action_export_unfinished)
        self.export_menu.addAction(self.action_export_all)
        self.export_menu.addAction(self.action_export_summary)
        self.export_tasks_button.setMenu(self.export_menu)
        # 绑定动作
        self.action_export_unfinished.triggered.connect(self.export_unfinished_tasks)
        self.action_export_all.triggered.connect(self.export_all_tasks)
        self.action_export_summary.triggered.connect(self.export_summary)
        self.export_tasks_button.setVisible(False)  # 初始隐藏
        self.export_tasks_button.setCursor(Qt.CursorShape.PointingHandCursor)

        # self.undo_button = QPushButton("撤销", self)
        # self.undo_button.clicked.connect(self.undo_action)
        # self.undo_button.setVisible(False)  # 初始隐藏
        # self.undo_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # self.gantt_button = QPushButton("甘特", self)
        # self.gantt_button.clicked.connect(self.show_gantt_dialog)
        # self.gantt_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.complete_button = QPushButton("完成", self)
        self.complete_button.clicked.connect(self.show_complete_dialog)
        self.complete_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.settings_button = QPushButton("设置", self)
        self.settings_button.clicked.connect(self.show_settings)
        self.settings_button.setVisible(False)  # 初始隐藏
        self.settings_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self.exit_button = QPushButton("退出", self)
        self.exit_button.clicked.connect(self.close)
        self.exit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # 添加按钮到布局
        self.control_layout.addWidget(self.edit_button)
        self.control_layout.addWidget(self.add_task_button)
        self.control_layout.addWidget(self.scheduled_task_button)
        self.control_layout.addWidget(self.export_tasks_button)
        # self.control_layout.addWidget(self.undo_button)
        # self.control_layout.addWidget(self.gantt_button)
        self.control_layout.addWidget(self.complete_button)
        self.control_layout.addWidget(self.settings_button)
        self.control_layout.addWidget(self.exit_button)
        
        # 添加控制面板阴影效果
        apply_drop_shadow(self.control_widget, blur_radius=10, color=QColor(0, 0, 0, 50), offset_x=0, offset_y=0)
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
        
        # 确保控制面板始终可见
        self.control_widget.show()

        # 新增：定时保存控件位置
        self.save_timer = QTimer(self)
        self.save_timer.timeout.connect(self.periodic_save_config)
        self.save_timer.start(20000)  # 每20秒保存一次

        self._position_dirty = False  # 标记位置是否有变动

        # 新增：记录当前显示的 detail_popup
        self.current_detail_popup = None
        

        # 新增：空白区域长按拖动窗口的状态与计时器
        self.long_press_timer = QTimer(self)
        self.long_press_timer.setSingleShot(True)
        self.long_press_timer.setInterval(500)  # 0.5秒长按
        self.long_press_timer.timeout.connect(self._enable_blank_drag)
        self._pending_blank_drag = False
        self._blank_drag_active = False
        self._blank_drag_offset = None
        
    def set_to_bottom_layer(self):
        """将窗口设置为底层（仅在启动时调用）"""
        try:
            # 检查是否有Windows API支持
            try:
                import win32gui
                import win32con
                
                # 获取窗口句柄
                hwnd = int(self.winId())
                if hwnd:
                    # 将窗口设置为底层
                    win32gui.SetWindowPos(hwnd, win32con.HWND_BOTTOM, 0, 0, 0, 0, 
                                         win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)
                    logger.info("窗口已设置为底层")
                else:
                    logger.warning("无法获取窗口句柄")
            except ImportError:
                logger.warning("Windows API 不可用，无法设置窗口层级")
        except Exception as e:
            logger.warning(f"设置窗口底层失败: {e}")
    

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
        try:
            painter = QPainter(self)
        except Exception as e:
            logger.error(f"绘制事件失败: {str(e)}", exc_info=True)
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)  # 抗锯齿
        
        # 获取窗口尺寸
        width = self.width()
        height = self.height()

        # 强制清空背景为完全透明，避免 Qt/样式残留导致外侧灰边/透明框。
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(0, 0, width, height, QColor(0, 0, 0, 0))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        
        # 计算十字线的位置
        h_line_y = height // 2
        v_line_x = width // 2
        
        # 获取圆角半径
        border_radius = self.config.get('ui', {}).get('border_radius', 15)
        
        # 计算内部四象限区域（留出边距）
        margin = 0
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
            # 仅当在空白区域时才准备进入长按拖动
            local_pos = event.position().toPoint()
            if self._is_blank_area(local_pos):
                self._pending_blank_drag = True
                self._blank_drag_active = False
                # 记录与窗口左上角的偏移
                self._blank_drag_offset = event.globalPosition().toPoint() - self.pos()
                self.long_press_timer.start()
                event.accept()
            else:
                # 非空白区域，保持原有其他控件交互
                event.ignore()
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
            if self._blank_drag_active and self._blank_drag_offset is not None:
                self.move(event.globalPosition().toPoint() - self._blank_drag_offset)
                event.accept()
            else:
                event.ignore()
        else:
            event.ignore()

    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        if self.long_press_timer.isActive():
            self.long_press_timer.stop()
        self._pending_blank_drag = False
        self._blank_drag_active = False
        self._blank_drag_offset = None
        event.accept()

    def _enable_blank_drag(self):
        """长按计时到达后，启用窗口拖动"""
        if self._pending_blank_drag:
            self._blank_drag_active = True

    def _is_blank_area(self, local_pos):
        """判断点击位置是否为象限面板空白处（不含任务与控制面板）"""
        child = self.childAt(local_pos)
        if child is None:
            return True
        # 控制面板或其子控件
        w = child
        while w is not None:
            if w is self.control_widget:
                return False
            w = w.parentWidget()
        # 任务标签或其子控件
        w = child
        from .task_label import TaskLabel as _TaskLabel
        while w is not None:
            if isinstance(w, _TaskLabel):
                return False
            w = w.parentWidget()
        return True
    
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
        edit_mode_children = ["add_task_button", "export_tasks_button","settings_button","scheduled_task_button"]
        # if len(self.undo_stack) > 0:
        #     edit_mode_children.append("undo_button")
        
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
        from .color_utils import ColorUtils
        
        width = self.width()
        height = self.height()
        h_line_y = height // 2
        v_line_x = width // 2
        
        if pos.x() >= v_line_x and pos.y() < h_line_y:
            # 第一象限：重要且紧急（右上）
            quadrant = 'q1'
        elif pos.x() < v_line_x and pos.y() < h_line_y:
            # 第二象限：重要不紧急（左上）
            quadrant = 'q2'
        elif pos.x() >= v_line_x and pos.y() >= h_line_y:
            # 第三象限：不重要但紧急（右下）
            quadrant = 'q3'
        else:
            # 第四象限：不重要不紧急（左下）
            quadrant = 'q4'
        
        # 使用颜色工具类生成随机颜色
        color = ColorUtils.get_quadrant_random_color(quadrant, self.config)
        return quadrant, color
    
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
        pass
        
        # # 收集当前状态
        # current_state = {
        #     'tasks': [],  # 任务信息
        #     'config': json.loads(json.dumps(self.config)),  # 深拷贝配置
        #     'control_panel': {
        #         'x': self.control_widget.x(),
        #         'y': self.control_widget.y()
        #     }
        # }
        
        # # 保存所有任务的信息和位置
        # for task in self.tasks:
        #     task_data = task.get_data()
        #     task_data['x'] = task.x()
        #     task_data['y'] = task.y()
        #     current_state['tasks'].append(task_data)
        
        # # 添加到撤销栈
        # self.undo_stack.append(current_state)
        
        # # 限制撤销栈大小为5
        # if len(self.undo_stack) > 5:
        #     self.undo_stack.pop(0)  # 移除最旧的状态
        
        # # 确保撤销按钮在编辑模式下可见
        # if self.edit_mode:
        #     if self.ui_manager:
        #         # self.ui_manager.batch_toggle_widgets(["undo_button"], True, animate=False)
        #         self.ui_manager.adjust_container_size("control_panel")
        #         self.ui_manager.ensure_widget_in_bounds("control_panel")
        #     else:
        #         # self.undo_button.setVisible(True)
        #         self.control_widget.adjustSize()
        #         self.control_widget.updateGeometry()
            
        # logger.debug(f"状态已保存，撤销栈大小: {len(self.undo_stack)}")

    def undo_action(self):
        """撤销上一次操作"""
        pass
        # if not self.undo_stack:
        #     logger.debug("撤销栈为空，无法撤销")
        #     return
            
        # logger.debug("正在执行撤销操作...")
        
        # # 弹出最近的状态
        # previous_state = self.undo_stack.pop()
        
        # # 恢复配置
        # self.config = previous_state['config']
        
        # # 恢复控制面板位置
        # control_panel = previous_state.get('control_panel', {})
        # if control_panel:
        #     self.control_widget.move(control_panel['x'], control_panel['y'])
        
        # # 清除当前所有任务
        # for task in self.tasks:
        #     task.deleteLater()
        # self.tasks.clear()
        
        # # 恢复任务
        # for task_data in previous_state['tasks']:
        #     # 提取位置信息
        #     x = task_data.pop('x', 0)
        #     y = task_data.pop('y', 0)
            
        #     # 创建任务
        #     task_id = task_data.get('task_id', f"task_{len(self.tasks)}_{datetime.now().strftime('%Y%m%d%H%M%S')}")
        #     color = task_data.pop('color', '#FFFFFF')
        #     completed = task_data.pop('completed', False)
            
        #     # 创建任务标签
        #     task = TaskLabel(
        #         task_id=task_id,
        #         color=color,
        #         parent=self,
        #         completed=completed,
        #         **task_data
        #     )
            
        #     # 设置任务位置
        #     task.move(x, y)
            
        #     # 连接信号
        #     task.deleteRequested.connect(self.delete_task)
        #     task.statusChanged.connect(self.save_tasks)
            
        #     # 显示任务
        #     task.show()
            
        #     # 添加到任务列表
        #     self.tasks.append(task)
        
        # # 更新界面
        # self.update()
        
        # # 如果撤销栈为空，隐藏撤销按钮
        # if not self.undo_stack:
        #     self.undo_button.setVisible(False)
        #     # 更新控制面板尺寸
        #     self.control_widget.adjustSize()
        #     self.control_widget.updateGeometry()
        
            
        # 保存当前状态
        self.save_tasks()
        # self.save_config()
        
        logger.debug(f"撤销完成，剩余撤销栈大小: {len(self.undo_stack)}")
    
    def _apply_remote_config_to_db_manager(self, remote_config: dict):
        """将远程配置同步到当前数据库管理器实例。"""
        self.db_manager.remote_config = dict(remote_config)
        self.db_manager.remote_enabled = remote_config.get('enabled', bool(remote_config.get('api_base_url', '')))
        if self.db_manager.remote_enabled:
            self.db_manager.api_base_url = remote_config.get('api_base_url', '')
            self.db_manager.api_token = remote_config.get('api_token', '')
            self.db_manager.username = remote_config.get('username', '')
        else:
            self.db_manager.api_base_url = ''
            self.db_manager.api_token = ''
            self.db_manager.username = ''

        if hasattr(self.db_manager, '_reset_remote_auth_state'):
            self.db_manager._reset_remote_auth_state()

    def show_settings(self, initial_tab: str = ''):
        """显示设置对话框 - 采用add_task_dialog样式"""
        # ❶ 直接把 QDialog 设为「无边框」窗口
        dialog = QDialog(self, flags=Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        # 不再使用透明背景，避免弹窗外侧出现可透底的透明区域
        dialog.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        border_radius = self.config.get('ui', {}).get('border_radius', 15)
        dialog.setStyleSheet(f"QDialog {{ background-color: white; border-radius: {border_radius}px; }}")
        
        # ------- 外层透明壳，什么都不画 ------- #
        
        # ❸ 真正的白色圆角面板
        panel = QWidget(dialog)
        panel.setObjectName("panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(30, 30, 30, 30)
        panel_layout.setSpacing(20)
        
        # 样式改为用 styles.py 的 StyleManager 管理
        style_manager = StyleManager()
        # 使用 add_task_dialog 的样式表
        add_task_dialog_stylesheet = style_manager.get_stylesheet("add_task_dialog").format()
        panel.setStyleSheet(add_task_dialog_stylesheet)
        
        # 阴影
        apply_drop_shadow(panel, blur_radius=8, color=QColor(0, 0, 0, 60), offset_x=0, offset_y=0)
        
        # 创建标签页
        tab_widget = QTabWidget()
        # 为标签页添加样式
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #dddddd;
                background-color: white;
                border-radius: 8px;
            }
            QTabBar::tab {
                background-color: #f5f5f5;
                color: #333;
                border: 1px solid #dddddd;
                border-bottom: none;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-family: '微软雅黑';
                font-size: 13px;
            }
            QTabBar::tab:selected {
                background-color: white;
                color: #4ECDC4;
                font-weight: bold;
            }
        """)
        
        # 创建颜色设置页
        color_widget = QWidget()
        color_layout = QFormLayout(color_widget)
        color_layout.setSpacing(15)
        color_layout.setContentsMargins(20, 20, 20, 20)
        
        # 为每个象限创建颜色选择器和透明度滑块
        quadrant_names = {
            'q1': "重要且紧急（右上）",
            'q2': "重要不紧急（左上）",
            'q3': "不重要但紧急（右下）",
            'q4': "不重要不紧急（左下）"
        }
        
        color_buttons = {}
        opacity_sliders = {}
        hue_range_spins = {}
        saturation_range_spins = {}
        value_range_spins = {}
        
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
            
            # 色相范围设置
            hue_range_spin = QSlider(Qt.Orientation.Horizontal)
            hue_range_spin.setRange(0, 180)
            hue_range_spin.setValue(self.config.get('color_ranges', {}).get(q_id, {}).get('hue_range', 30))
            hue_range_spin.valueChanged.connect(lambda value, qid=q_id: self.change_color_range(qid, 'hue_range', value))
            hue_range_spins[q_id] = hue_range_spin
            
            # 饱和度范围设置
            saturation_range_spin = QSlider(Qt.Orientation.Horizontal)
            saturation_range_spin.setRange(0, 255)
            saturation_range_spin.setValue(self.config.get('color_ranges', {}).get(q_id, {}).get('saturation_range', 20))
            saturation_range_spin.valueChanged.connect(lambda value, qid=q_id: self.change_color_range(qid, 'saturation_range', value))
            saturation_range_spins[q_id] = saturation_range_spin
            
            # 明度范围设置
            value_range_spin = QSlider(Qt.Orientation.Horizontal)
            value_range_spin.setRange(0, 255)
            value_range_spin.setValue(self.config.get('color_ranges', {}).get(q_id, {}).get('value_range', 20))
            value_range_spin.valueChanged.connect(lambda value, qid=q_id: self.change_color_range(qid, 'value_range', value))
            value_range_spins[q_id] = value_range_spin
            
            # 添加到布局
            color_layout.addRow(f"{q_name} 颜色:", color_btn)
            color_layout.addRow(f"{q_name} 透明度:", opacity_slider)
            color_layout.addRow(f"{q_name} 色相范围:", hue_range_spin)
            color_layout.addRow(f"{q_name} 饱和度范围:", saturation_range_spin)
            color_layout.addRow(f"{q_name} 明度范围:", value_range_spin)
        
        # 创建大小设置页
        size_widget = QWidget()
        size_layout = QFormLayout(size_widget)
        size_layout.setSpacing(15)
        size_layout.setContentsMargins(20, 20, 20, 20)
        
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
        ui_layout.setSpacing(15)
        ui_layout.setContentsMargins(20, 20, 20, 20)

        # 远程设置
        remote_widget = QWidget()
        remote_layout = QFormLayout(remote_widget)
        remote_layout.setSpacing(15)
        remote_layout.setContentsMargins(20, 20, 20, 20)

        remote_config_manager = RemoteConfigManager()
        remote_config = remote_config_manager.get_server_config()

        remote_enabled_checkbox = QCheckBox("启用远程同步")
        remote_enabled_checkbox.setChecked(remote_config.get('enabled', bool(remote_config.get('api_base_url', ''))))

        remote_url_edit = QLineEdit(remote_config.get('api_base_url', ''))
        remote_url_edit.setPlaceholderText("http://example.com")

        remote_username_edit = QLineEdit(remote_config.get('username', ''))
        remote_username_edit.setPlaceholderText("用户名")

        remote_token_edit = QLineEdit(remote_config.get('api_token', ''))
        remote_token_edit.setPlaceholderText("API Token")

        remote_hint_label = QLabel("关闭远程同步后，下次启动将不会检测远程服务器。")
        remote_hint_label.setStyleSheet("color: #666; font-size: 11px;")
        remote_hint_label.setWordWrap(True)
        
        # 圆角设置
        border_radius_spin = QSpinBox()
        border_radius_spin.setRange(0, 50)
        border_radius_spin.setValue(self.config.get('ui', {}).get('border_radius', 15))
        border_radius_spin.valueChanged.connect(lambda value: self.update_ui_config('border_radius', value))
        
        # 自动刷新设置
        auto_refresh_checkbox = QCheckBox("启用自动刷新")
        auto_refresh_config = self.config.get('auto_refresh', {})
        auto_refresh_checkbox.setChecked(auto_refresh_config.get('enabled', True))
        auto_refresh_checkbox.stateChanged.connect(lambda state: self.update_auto_refresh_config('enabled', state == Qt.CheckState.Checked.value))
        
        # 刷新时间设置
        refresh_time_edit = QTimeEdit()
        refresh_time_edit.setDisplayFormat("HH:mm:ss")
        refresh_time_str = auto_refresh_config.get('refresh_time', '00:02:00')
        try:
            hour, minute, second = map(int, refresh_time_str.split(':'))
            refresh_time_edit.setTime(QTime(hour, minute, second))
        except:
            refresh_time_edit.setTime(QTime(0, 2, 0))
        refresh_time_edit.timeChanged.connect(lambda time: self.update_auto_refresh_config('refresh_time', time.toString("HH:mm:ss")))
        
        # 添加说明标签
        refresh_label = QLabel("每天在设定时间自动刷新页面并检查定时任务")
        refresh_label.setStyleSheet("color: #666; font-size: 11px;")
        refresh_label.setWordWrap(True)
        
        # 添加到布局
        size_layout.addRow("宽度:", width_spin)
        size_layout.addRow("高度:", height_spin)
        ui_layout.addRow("圆角半径:", border_radius_spin)
        ui_layout.addRow("", QLabel(""))  # 添加空行分隔
        ui_layout.addRow(auto_refresh_checkbox)
        ui_layout.addRow("刷新时间:", refresh_time_edit)
        ui_layout.addRow("", refresh_label)

        remote_layout.addRow(remote_enabled_checkbox)
        remote_layout.addRow("服务器地址:", remote_url_edit)
        remote_layout.addRow("用户名:", remote_username_edit)
        remote_layout.addRow("访问令牌:", remote_token_edit)
        remote_layout.addRow("", remote_hint_label)
        
        # 添加标签页
        tab_widget.addTab(color_widget, "颜色设置")
        tab_widget.addTab(size_widget, "大小设置")
        tab_widget.addTab(ui_widget, "界面设置")
        tab_widget.addTab(remote_widget, "远程设置")

        if initial_tab == 'remote':
            tab_widget.setCurrentWidget(remote_widget)
        
        # 将标签页添加到面板布局
        panel_layout.addWidget(tab_widget)
        
        # 添加确定按钮
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")

        def save_settings_and_accept():
            remote_config_payload = {
                'enabled': remote_enabled_checkbox.isChecked(),
                'api_base_url': remote_url_edit.text().strip(),
                'api_token': remote_token_edit.text().strip(),
                'username': remote_username_edit.text().strip(),
            }
            if not remote_config_manager.save_config(remote_config_payload):
                QMessageBox.warning(self, "保存失败", "远程配置保存失败，请稍后重试。")
                return

            self._apply_remote_config_to_db_manager(remote_config_payload)
            dialog.accept()

        ok_button.clicked.connect(save_settings_and_accept)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        panel_layout.addLayout(button_layout)
        
        # ❹ 自动根据内容调大小，再把"壳"和"面板"都居中放
        # 外圈透明壳/留白去掉：把“壳”尺寸与真实面板对齐
        shadow_margin = 0
        # 让 panel 先自适应内容
        panel.setMinimumWidth(600)
        panel_layout.activate()
        panel.adjustSize()
        # 让壳与面板对齐
        dialog.resize(panel.width() + shadow_margin * 2, panel.height() + shadow_margin * 2)
        # 把面板放回壳左上角
        panel.move(shadow_margin, shadow_margin)
        
        # ❺ 实现拖动窗口（因为没了系统标题栏）
        dialog._drag_pos = None
        
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

        # 读取数据库
        try:
            db_manager=get_db_manager()
            all_tasks_data=db_manager.load_tasks(all_tasks=True)
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
        # test
        logger.info(all_tasks_data[0])
        for task_data in all_tasks_data:
            # 可选：如果你只想导出未被删除的任务，加上下面一行
            # if task_data.get('deleted', False): continue

            row = {
                '任务名': task_data.get('text'),
                '到期日期': task_data.get('due_date'),
                '优先级': task_data.get('priority'),
                '备注': task_data.get('notes'),
                '目录': task_data.get('directory'),
                '创建日期': task_data.get('created_at'),
                '完成状态': '已完成' if task_data.get('completed', False) else '未完成',
                '完成日期': task_data.get('completed_date', ''),
                '删除状态': '已删除' if task_data.get('deleted', False) else ''
            }
            rows.append(row)

        if not rows:
            logger.info("导出任务失败：没有有效任务可导出")
            QMessageBox.information(self, "导出任务", "没有有效任务可导出")
            return

        # 定义列的顺序
        column_order = [
            '任务名', '到期日期', '优先级', '备注', '目录', '创建日期',
            '完成状态', '完成日期', '删除状态'
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

    def _is_port_open(self, host='127.0.0.1', port=5000) -> bool:
        '''
        检测gantt服务是否启动
        '''
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.2)
        try:
            s.connect((host, port))
            s.close()
            return True
        except OSError:
            return False

    def _start_gantt_server_if_needed(self) -> bool:
        """
        如果 127.0.0.1:5000 没在跑，则启动 gantt/app.py 里的 Flask。
        同时设置 DB_PATH，指向项目内的 database/tasks.db
        """
        # 计算项目根目录（quadrant_widget.py 在 core/，根目录是其上一级）
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        # 指定数据库路径（你的 app.py 里默认就是 ./database/tasks.db）
        db_path = os.path.join(root_dir, 'database', 'tasks.db')
        os.environ.setdefault('DB_PATH', db_path)

        if self._is_port_open():
            return True
        def _run():
            # 不用调试/不重载；放后台线程跑
            
            gantt_app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

        t = threading.Thread(target=_run, daemon=True)
        t.start()

        # 简单等待最多 3 秒让服务起来（不强制，起不来也会回退到浏览器）
        for _ in range(30):
            if self._is_port_open():
                return True
            time.sleep(0.1)
        return self._is_port_open()


    def show_gantt_dialog(self):
        """
        打开一个弹窗，上面嵌入本地 index.html（frappe-gantt 页面），下方有“关闭”按钮。
        - 优先使用 QWebEngineView 内嵌；如果未安装，则回退到系统浏览器打开。
        - index.html 路径可按需修改 / 做成配置项。
        """
        # 启动gantt服务
        url = "http://127.0.0.1:5000/"
        self._start_gantt_server_if_needed()
        if not HAS_WEBENGINE:
            # 没有 WebEngine 就直接用系统浏览器打开
            webbrowser.open_new_tab(url)
            return
        # 无边框 + 透明背景
        dlg = QDialog(self, flags=Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        # 不再使用透明背景，避免弹窗外侧出现可透底的透明区域
        dlg.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        border_radius = self.config.get('ui', {}).get('border_radius', 15)
        dlg.setStyleSheet(f"QDialog {{ background-color: white; border-radius: {border_radius}px; }}")
        dlg.setWindowTitle("甘特图")
        dlg.setModal(True)
        
        # 外层透明壳
        outer_layout = QVBoxLayout(dlg)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # 白色圆角面板
        panel = QWidget(dlg)
        panel.setObjectName("panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(10, 10, 10, 10)
        panel_layout.setSpacing(10)
        
        # 使用统一样式
        style_manager = StyleManager()
        add_task_dialog_stylesheet = style_manager.get_stylesheet("add_task_dialog").format()
        panel.setStyleSheet(add_task_dialog_stylesheet)
        
        # 内部内容
        view = QWebEngineView(dlg)
        view.setUrl(QUrl(url))
        view.setMinimumSize(900, 600)
        panel_layout.addWidget(view)

        # 下方按钮行
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("关闭", panel)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(dlg.accept)
        btn_row.addWidget(close_btn)

        # 组装布局
        panel_layout.addWidget(view, stretch=1)
        panel_layout.addLayout(btn_row)

        # 将 panel 放入外层 layout
        outer_layout.addWidget(panel)

        # 让窗口大小跟随面板内容，避免固定尺寸造成外圈留白
        dlg.adjustSize()
        dlg.exec()

    def show_complete_dialog(self):
        """显示已完成任务对话框"""
        from .complete_table import CompleteTableDialog
        
        dialog = CompleteTableDialog(self)
        dialog.exec()

    def update_ui_config(self, key, value):
        """更新UI配置"""
        if 'ui' not in self.config:
            self.config['ui'] = {}
        self.config['ui'][key] = value
        self.save_config()
        
        # 如果更改了圆角半径，立即更新界面
        if key == 'border_radius':
            self.update()
    
    def update_auto_refresh_config(self, key, value):
        """更新自动刷新配置"""
        if 'auto_refresh' not in self.config:
            self.config['auto_refresh'] = {}
        self.config['auto_refresh'][key] = value
        self.save_config()
        logger.info(f"自动刷新配置已更新: {key} = {value}")
    
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
    
    def change_color_range(self, quadrant_id, range_type, value):
        """更改颜色范围设置"""
        # 确保color_ranges配置存在
        if 'color_ranges' not in self.config:
            self.config['color_ranges'] = {}
        if quadrant_id not in self.config['color_ranges']:
            self.config['color_ranges'][quadrant_id] = {}
        
        # 更新范围值
        self.config['color_ranges'][quadrant_id][range_type] = value
        self.save_config()
        
        logger.info(f"更新象限 {quadrant_id} 的 {range_type} 范围为 {value}")
    
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
    
    def _handle_remote_sync(self, change_summaries):
        """后台同步发现远程修改后，投递一次主线程确认。"""
        if not change_summaries or self._is_closing or self._sync_refresh_pending:
            return
        self._sync_refresh_pending = True
        self.remote_sync_refresh_requested.emit(change_summaries)

    def _bootstrap_remote_sync(self):
        """在界面监听器就绪后显式触发远程同步。"""
        if self._is_closing or not getattr(self.db_manager, 'api_base_url', ''):
            return

        if (not getattr(self.db_manager, 'username', '').strip()) or (not getattr(self.db_manager, 'api_token', '').strip()):
            QMessageBox.warning(self, "远程配置不完整", "远程同步已暂停。请在设置面板的“远程设置”页补全远程服务器、用户名和访问令牌。")
            self.show_settings('remote')
            return

        threading.Thread(target=self._run_bootstrap_remote_sync, daemon=True).start()

    def _run_bootstrap_remote_sync(self):
        """后台执行启动远程同步，并将结果投递回主线程。"""
        try:
            sync_ok = self.db_manager.bootstrap_remote_sync()
        except Exception as e:
            logger.error(f"启动后远程同步失败: {str(e)}")
            sync_ok = False

        if not self._is_closing:
            self.remote_bootstrap_finished.emit(sync_ok)

    def _on_remote_bootstrap_finished(self, sync_ok):
        """处理后台启动同步的完成回调。"""
        logger.info(f"启动后远程同步结果: {sync_ok}")
        if sync_ok and (not self._sync_refresh_pending):
            self.load_tasks()

    def _get_remote_change_type_label(self, change_type):
        if change_type == 'create':
            return '新增'
        if change_type == 'delete':
            return '删除'
        return '修改'

    def _format_remote_change_datetime(self, value):
        text = str(value or '').strip()
        if not text:
            return '-'
        text = text.replace('T', ' ')
        if '.' in text:
            text = text.split('.', 1)[0]
        return text

    def _format_remote_change_frequency(self, value):
        mapping = {
            'daily': '每天',
            'weekly': '每周',
            'monthly': '每月',
            'quarterly': '每季度',
            'yearly': '每年',
        }
        text = str(value or '').strip()
        if not text:
            return '-'
        return mapping.get(text, text)

    def _format_remote_change_boolean(self, value):
        if value in (None, ''):
            return '-'
        return '是' if bool(value) else '否'

    def _format_remote_change_week_day(self, value):
        mapping = {
            1: '周一',
            2: '周二',
            3: '周三',
            4: '周四',
            5: '周五',
            6: '周六',
            7: '周日',
        }
        if value in (None, ''):
            return '-'
        try:
            return mapping.get(int(value), str(value))
        except (TypeError, ValueError):
            return str(value)

    def _format_remote_change_position(self, record):
        if not record:
            return '-'
        x = record.get('position_x')
        y = record.get('position_y')
        if x in (None, '') and y in (None, ''):
            return '-'
        return f'x={x}, y={y}'

    def _get_remote_change_field_specs(self, entity_type):
        if entity_type == 'scheduled_task':
            return [
                ('标题', lambda record: str(record.get('title') or '').strip() or '-'),
                ('优先级', lambda record: str(record.get('priority') or '').strip() or '-'),
                ('紧急度', lambda record: str(record.get('urgency') or '').strip() or '-'),
                ('重要度', lambda record: str(record.get('importance') or '').strip() or '-'),
                ('备注', lambda record: str(record.get('notes') or '').strip() or '-'),
                ('截止日期', lambda record: str(record.get('due_date') or '').strip() or '-'),
                ('频率', lambda record: self._format_remote_change_frequency(record.get('frequency'))),
                ('每周', lambda record: self._format_remote_change_week_day(record.get('week_day'))),
                ('每月', lambda record: str(record.get('month_day') or '').strip() or '-'),
                ('每季度', lambda record: str(record.get('quarter_day') or '').strip() or '-'),
                ('每年月份', lambda record: str(record.get('year_month') or '').strip() or '-'),
                ('每年日期', lambda record: str(record.get('year_day') or '').strip() or '-'),
                ('下次执行时间', lambda record: self._format_remote_change_datetime(record.get('next_run_at'))),
                ('启用', lambda record: self._format_remote_change_boolean(record.get('active'))),
                ('更新时间', lambda record: self._format_remote_change_datetime(record.get('updated_at'))),
            ]

        return [
            ('标题', lambda record: str(record.get('text') or '').strip() or '-'),
            ('备注', lambda record: str(record.get('notes') or '').strip() or '-'),
            ('截止日期', lambda record: str(record.get('due_date') or '').strip() or '-'),
            ('优先级', lambda record: str(record.get('priority') or '').strip() or '-'),
            ('紧急度', lambda record: str(record.get('urgency') or '').strip() or '-'),
            ('重要度', lambda record: str(record.get('importance') or '').strip() or '-'),
            ('目录', lambda record: str(record.get('directory') or '').strip() or '-'),
            ('创建日期', lambda record: str(record.get('create_date') or '').strip() or '-'),
            ('颜色', lambda record: str(record.get('color') or '').strip() or '-'),
            ('位置', lambda record: self._format_remote_change_position(record)),
            ('已完成', lambda record: self._format_remote_change_boolean(record.get('completed'))),
            ('完成时间', lambda record: self._format_remote_change_datetime(record.get('completed_date'))),
            ('已删除', lambda record: self._format_remote_change_boolean(record.get('deleted'))),
            ('更新时间', lambda record: self._format_remote_change_datetime(record.get('updated_at'))),
        ]

    def _build_remote_change_record_lines(self, change, record):
        if not record:
            return '-'

        lines = []
        for label, formatter in self._get_remote_change_field_specs(change.get('entity_type')):
            value = formatter(record)
            if value == '-':
                continue
            if label in {'已完成', '已删除', '启用'} and value == '否':
                continue
            lines.append(f'{label}：{value}')
        return '\n'.join(lines) if lines else '-'

    def _build_remote_change_diff_lines(self, change, local_record, remote_record):
        differences = []
        for label, formatter in self._get_remote_change_field_specs(change.get('entity_type')):
            local_value = formatter(local_record or {}) if local_record else '-'
            remote_value = formatter(remote_record or {}) if remote_record else '-'
            if local_value == remote_value:
                continue
            differences.append((label, local_value, remote_value))
        return differences

    def _build_remote_change_view_model(self, change):
        local_record = change.get('local_record')
        remote_record = change.get('remote_record')
        change_type = change.get('change_type', 'update')
        title = change.get('title') or ''
        if not title:
            if change.get('entity_type') == 'scheduled_task':
                title = (remote_record or {}).get('title') or (local_record or {}).get('title') or f"定时任务 {change.get('entity_id') or change.get('id', '')}"
            else:
                title = (remote_record or {}).get('text') or (local_record or {}).get('text') or f"任务 {change.get('entity_id') or change.get('id', '')}"
        if change.get('entity_type') == 'scheduled_task':
            title = f'【定时任务】{title}'

        if change_type == 'create':
            local_text = '-'
            remote_text = self._build_remote_change_record_lines(change, remote_record)
        elif change_type == 'delete':
            local_text = self._build_remote_change_record_lines(change, local_record)
            remote_text = '-'
        else:
            differences = self._build_remote_change_diff_lines(change, local_record, remote_record)
            if differences:
                local_text = '\n'.join(f'{label}：{local_value}' for label, local_value, _ in differences)
                remote_text = '\n'.join(f'{label}：{remote_value}' for label, _, remote_value in differences)
            else:
                local_text = '-'
                remote_text = '-'

        return {
            'id': change.get('id', ''),
            'change_type_label': self._get_remote_change_type_label(change_type),
            'title': title,
            'local_text': local_text,
            'remote_text': remote_text,
        }

    def _collect_remote_change_choices(self, selection_rows):
        accepted_ids = []
        rejected_ids = []
        missing_ids = []
        for row in selection_rows:
            local_selected = bool(row.get('local_selected'))
            remote_selected = bool(row.get('remote_selected'))
            if local_selected == remote_selected:
                missing_ids.append(row.get('id'))
            elif remote_selected:
                accepted_ids.append(row.get('id'))
            else:
                rejected_ids.append(row.get('id'))
        return accepted_ids, rejected_ids, missing_ids

    def _apply_remote_change_selection(self, selection_rows):
        accepted_ids, rejected_ids, missing_ids = self._collect_remote_change_choices(selection_rows)
        if missing_ids:
            QMessageBox.warning(self, '选择不完整', '还有未勾选的冲突，请为每条记录选择接受本地或接受远程。')
            return False

        success = self.db_manager.resolve_pending_remote_task_changes(accepted_ids, rejected_ids)
        if not success:
            QMessageBox.warning(self, '同步失败', '处理远程修改失败，请稍后重试。')
            return False

        self.db_manager.flush_cache_to_db()
        if rejected_ids and getattr(self.db_manager, 'api_base_url', ''):
            sync_ok = self.db_manager.sync_to_server()
            logger.info(f'远程修改确认后回写本地版本结果: {sync_ok}')
            self.db_manager.flush_cache_to_db()

        self.load_tasks()
        return True

    def _show_remote_sync_confirmation(self, change_summaries):
        """弹出远程修改确认窗口。"""
        if self._is_closing:
            self._sync_refresh_pending = False
            return

        dialog = QDialog(self)
        dialog.setWindowTitle('远程修改确认')
        dialog.setModal(True)
        dialog.resize(980, 520)

        layout = QVBoxLayout(dialog)
        message = QLabel('检测到远程修改。请为每条记录选择接受本地或接受远程，未完成选择前无法保存。')
        message.setWordWrap(True)
        layout.addWidget(message)

        scroll_area = QScrollArea(dialog)
        scroll_area.setWidgetResizable(True)
        table_container = QWidget()
        table_layout = QGridLayout(table_container)
        table_layout.setContentsMargins(8, 8, 8, 8)
        table_layout.setHorizontalSpacing(12)
        table_layout.setVerticalSpacing(10)
        table_layout.setColumnStretch(0, 0)
        table_layout.setColumnStretch(1, 2)
        table_layout.setColumnStretch(2, 3)
        table_layout.setColumnStretch(3, 3)

        headers = ['变更', '任务标题', '本地', '远程']
        for column, header_text in enumerate(headers):
            header = QLabel(header_text)
            header.setStyleSheet('font-weight: 600; color: #334155; padding: 4px 0;')
            table_layout.addWidget(header, 0, column)

        selection_rows = []

        def bind_exclusive(source_checkbox, target_checkbox):
            source_checkbox.toggled.connect(
                lambda checked, other=target_checkbox: other.setChecked(False) if checked and other.isChecked() else None
            )

        for row_index, change in enumerate(change_summaries, start=1):
            view_model = self._build_remote_change_view_model(change)

            tag_label = QLabel(view_model['change_type_label'])
            tag_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tag_label.setStyleSheet(
                'background-color: #e2e8f0; color: #1e293b; border-radius: 8px; padding: 2px 8px; font-size: 12px;'
            )

            title_label = QLabel(view_model['title'])
            title_label.setWordWrap(True)
            title_label.setStyleSheet('font-weight: 500; color: #0f172a;')
            title_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

            local_checkbox = QCheckBox('接受本地')
            remote_checkbox = QCheckBox('接受远程')
            bind_exclusive(local_checkbox, remote_checkbox)
            bind_exclusive(remote_checkbox, local_checkbox)

            local_text = QLabel(view_model['local_text'])
            local_text.setWordWrap(True)
            local_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            local_text.setStyleSheet('color: #1f2937;')

            remote_text = QLabel(view_model['remote_text'])
            remote_text.setWordWrap(True)
            remote_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            remote_text.setStyleSheet('color: #1f2937;')

            local_cell = QWidget()
            local_cell.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            local_cell.setStyleSheet('background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;')
            local_layout = QVBoxLayout(local_cell)
            local_layout.setContentsMargins(8, 8, 8, 8)
            local_layout.setSpacing(6)
            local_layout.addWidget(local_checkbox)
            local_layout.addWidget(local_text)

            remote_cell = QWidget()
            remote_cell.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            remote_cell.setStyleSheet('background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;')
            remote_layout = QVBoxLayout(remote_cell)
            remote_layout.setContentsMargins(8, 8, 8, 8)
            remote_layout.setSpacing(6)
            remote_layout.addWidget(remote_checkbox)
            remote_layout.addWidget(remote_text)

            table_layout.addWidget(tag_label, row_index, 0, alignment=Qt.AlignmentFlag.AlignTop)
            table_layout.addWidget(title_label, row_index, 1)
            table_layout.addWidget(local_cell, row_index, 2)
            table_layout.addWidget(remote_cell, row_index, 3)

            selection_rows.append({
                'id': view_model['id'],
                'local_checkbox': local_checkbox,
                'remote_checkbox': remote_checkbox,
            })

        scroll_area.setWidget(table_container)
        layout.addWidget(scroll_area)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        cancel_button = QPushButton('取消', dialog)
        confirm_button = QPushButton('保存', dialog)
        cancel_button.clicked.connect(dialog.reject)

        def confirm_selection():
            result = self._apply_remote_change_selection([
                {
                    'id': row['id'],
                    'local_selected': row['local_checkbox'].isChecked(),
                    'remote_selected': row['remote_checkbox'].isChecked(),
                }
                for row in selection_rows
            ])
            if result:
                dialog.accept()

        confirm_button.clicked.connect(confirm_selection)
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(confirm_button)
        layout.addLayout(button_layout)

        try:
            if dialog.exec() != QDialog.DialogCode.Accepted:
                logger.info('用户取消了远程修改确认')
                return
        finally:
            self._sync_refresh_pending = False
    def load_tasks(self):
        """从数据库加载任务并刷新主面板。"""
        logger.info("正在从数据库加载任务...")
        self.setUpdatesEnabled(False)

        try:
            # 清除当前所有任务
            for task in self.tasks:
                task.deleteLater()
            self.tasks.clear()

            from config.config_manager import load_tasks_with_history
            tasks_data = load_tasks_with_history()
            field_definitions = self.config.get('task_fields', [])

            for task_data in tasks_data:
                task_fields = {
                    field['name']: task_data.get(field['name'], "" if field.get('required') else None)
                    for field in field_definitions
                }
                task = TaskLabel(
                    task_id=task_data['id'],
                    color=task_data['color'],
                    parent=self,
                    completed=task_data['completed'],
                    field_definitions=field_definitions,
                    **task_fields,
                )
                task.updated_at = task_data.get('updated_at', '')
                task.created_at = task_data.get('created_at', '')

                if 'position' in task_data:
                    task.move(task_data['position']['x'], task_data['position']['y'])

                task.deleteRequested.connect(self.delete_task)
                task.statusChanged.connect(self.save_tasks)
                task.show()
                self.tasks.append(task)

            logger.info(f"成功加载了 {len(self.tasks)} 个任务")
        except Exception as e:
            logger.error(f"加载任务失败: {str(e)}")
            QMessageBox.warning(self, "加载失败", f"加载任务失败: {str(e)}")
        finally:
            self._sync_refresh_pending = False
            self.setUpdatesEnabled(True)

    def save_tasks(self, task=None):
        """保存任务到数据库。"""
        tasks_to_save = self.tasks if task is None else [task]
        save_tasks(tasks_to_save, self)

    def scheduled_task(self):
        """定时任务"""
        from .scheduler import ScheduledTaskDialog
        logger.info("定时任务")
        scheduled_task_dialog = ScheduledTaskDialog(self)
        scheduled_task_dialog.exec()

    def export_summary(self):
        """导出概要"""
        from .export_summary_dialog import ExportSummaryDialog
        logger.info("打开导出概要对话框")
        dialog = ExportSummaryDialog(self)
        dialog.exec()

    def closeEvent(self, event):
        """关闭事件。"""
        logger.info("正在关闭程序...")
        self._is_closing = True
        self.save_config()

        try:
            db_manager = self.db_manager if getattr(self, 'db_manager', None) else get_db_manager()
            db_manager.remove_task_sync_listener(self._handle_remote_sync)
            db_manager.flush_cache_to_db()
            if getattr(db_manager, 'api_base_url', ''):
                sync_ok = db_manager.sync_to_server()
                logger.info(f"退出前远程同步结果: {sync_ok}")
                db_manager.flush_cache_to_db()
            db_manager.close_connection()
        except Exception as e:
            logger.error(f"退出时写盘/同步失败: {str(e)}")

        logger.info("程序关闭前的保存/同步操作完成，即将退出")
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().quit()

        event.accept()
