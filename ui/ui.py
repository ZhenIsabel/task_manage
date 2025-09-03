from PyQt6.QtWidgets import QWidget, QApplication, QColorDialog, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGraphicsDropShadowEffect
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QTimer, pyqtSignal, QObject, Qt
from PyQt6.QtGui import QColor
import logging

logger = logging.getLogger(__name__)

class UIManager(QObject):
    """负责UI控件显示、隐藏、删除、动画和状态管理的类"""
    
    # 定义信号
    widget_state_changed = pyqtSignal(str, str)  # widget_name, new_state
    animation_finished = pyqtSignal(str)  # widget_name
    
    def __init__(self):
        super().__init__()  # 调用QObject的初始化
        self.visible_widgets = {}
        self.widget_states = {}
        self.widget_animations = {}
        self.widget_properties = {}  # 存储控件的自定义属性
        self.event_handlers = {}  # 存储事件处理器
        self.auto_save_timer = QTimer(self)  # 将self作为父对象
        self.auto_save_timer.timeout.connect(self._auto_save_states)
        self.auto_save_timer.start(30000)  # 30秒自动保存一次
        
    def register_widget(self, widget_name, widget, initial_state="visible", properties=None):
        """注册控件到管理器"""
        if widget:
            self.visible_widgets[widget_name] = widget
            self.widget_states[widget_name] = initial_state
            self.widget_properties[widget_name] = properties or {}
            logger.debug(f"注册控件: {widget_name}, 状态: {initial_state}")
            
            # 设置默认属性
            if hasattr(widget, 'setObjectName'):
                widget.setObjectName(widget_name)
    
    def show_widget(self, widget_name, animate=True, duration=300):
        """显示控件，支持动画"""
        if widget_name in self.visible_widgets:
            widget = self.visible_widgets[widget_name]
            if animate and hasattr(widget, 'setWindowOpacity'):
                self._animate_widget(widget_name, 'show', duration)
            else:
                widget.show()
                self.widget_states[widget_name] = "visible"
                self.widget_state_changed.emit(widget_name, "visible")
                
                # 不再自动调整父容器大小，由具体组件自己处理
                # self._adjust_parent_size(widget)
            logger.debug(f"显示控件: {widget_name}")
    
    def hide_widget(self, widget_name, animate=True, duration=300):
        """隐藏控件，支持动画"""
        if widget_name in self.visible_widgets:
            widget = self.visible_widgets[widget_name]
            if animate and hasattr(widget, 'setWindowOpacity'):
                self._animate_widget(widget_name, 'hide', duration)
            else:
                widget.hide()
                self.widget_states[widget_name] = "hidden"
                self.widget_state_changed.emit(widget_name, "hidden")
                
                # 不再自动调整父容器大小，由具体组件自己处理
                # self._adjust_parent_size(widget)
            logger.debug(f"隐藏控件: {widget_name}")
    
    def delete_widget(self, widget_name):
        """删除控件"""
        if widget_name in self.visible_widgets:
            widget = self.visible_widgets[widget_name]
            # 停止相关动画
            if widget_name in self.widget_animations:
                self.widget_animations[widget_name].stop()
                del self.widget_animations[widget_name]
            
            widget.deleteLater()
            del self.visible_widgets[widget_name]
            if widget_name in self.widget_states:
                del self.widget_states[widget_name]
            if widget_name in self.widget_properties:
                del self.widget_properties[widget_name]
            logger.debug(f"删除控件: {widget_name}")
    
    def toggle_widget_visibility(self, widget_name, animate=True):
        """切换控件可见性"""
        if widget_name in self.visible_widgets:
            widget = self.visible_widgets[widget_name]
            if widget.isVisible():
                self.hide_widget(widget_name, animate)
            else:
                self.show_widget(widget_name, animate)
    
    def set_widget_property(self, widget_name, property_name, value):
        """设置控件属性"""
        if widget_name in self.widget_properties:
            self.widget_properties[widget_name][property_name] = value
            logger.debug(f"设置控件属性: {widget_name}.{property_name} = {value}")
    
    def get_widget_property(self, widget_name, property_name, default=None):
        """获取控件属性"""
        if widget_name in self.widget_properties:
            return self.widget_properties[widget_name].get(property_name, default)
        return default
    
    def register_event_handler(self, widget_name, event_type, handler):
        """注册事件处理器"""
        if widget_name not in self.event_handlers:
            self.event_handlers[widget_name] = {}
        self.event_handlers[widget_name][event_type] = handler
        logger.debug(f"注册事件处理器: {widget_name}.{event_type}")
    
    def get_widget_state(self, widget_name):
        """获取控件状态"""
        return self.widget_states.get(widget_name, "unknown")
    
    def get_all_visible_widgets(self):
        """获取所有可见控件"""
        return {name: widget for name, widget in self.visible_widgets.items() 
                if widget.isVisible()}
    
    def get_widget_by_name(self, widget_name):
        """根据名称获取控件"""
        return self.visible_widgets.get(widget_name)
    
    def _animate_widget(self, widget_name, action, duration):
        """执行控件动画"""
        if widget_name not in self.visible_widgets:
            return
            
        widget = self.visible_widgets[widget_name]
        
        # 停止之前的动画
        if widget_name in self.widget_animations:
            self.widget_animations[widget_name].stop()
        
        # 创建新动画
        animation = QPropertyAnimation(widget, b"windowOpacity")
        animation.setDuration(duration)
        animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        if action == 'show':
            animation.setStartValue(0.0)
            animation.setEndValue(1.0)
            widget.show()
        else:  # hide
            animation.setStartValue(1.0)
            animation.setEndValue(0.0)
        
        # 动画完成后的回调
        animation.finished.connect(lambda: self._on_animation_finished(widget_name, action))
        
        # 保存动画引用
        self.widget_animations[widget_name] = animation
        animation.start()
    
    def _on_animation_finished(self, widget_name, action):
        """动画完成回调"""
        if action == 'hide' and widget_name in self.visible_widgets:
            self.visible_widgets[widget_name].hide()
            self.widget_states[widget_name] = "hidden"
        elif action == 'show':
            self.widget_states[widget_name] = "visible"
        
        self.widget_state_changed.emit(widget_name, self.widget_states[widget_name])
        self.animation_finished.emit(widget_name)
        
        # 清理动画引用
        if widget_name in self.widget_animations:
            del self.widget_animations[widget_name]
    
    def fade_in_widget(self, widget_name, duration=500):
        """淡入控件"""
        self._animate_widget(widget_name, 'show', duration)
    
    def fade_out_widget(self, widget_name, duration=500):
        """淡出控件"""
        self._animate_widget(widget_name, 'hide', duration)
    
    def set_widget_position(self, widget_name, x, y):
        """设置控件位置"""
        if widget_name in self.visible_widgets:
            widget = self.visible_widgets[widget_name]
            widget.move(x, y)
            self.set_widget_property(widget_name, 'position', {'x': x, 'y': y})
    
    def get_widget_position(self, widget_name):
        """获取控件位置"""
        if widget_name in self.visible_widgets:
            widget = self.visible_widgets[widget_name]
            pos = widget.pos()
            return {'x': pos.x(), 'y': pos.y()}
        return None
    
    def set_widget_size(self, widget_name, width, height):
        """设置控件大小"""
        if widget_name in self.visible_widgets:
            widget = self.visible_widgets[widget_name]
            widget.resize(width, height)
            self.set_widget_property(widget_name, 'size', {'width': width, 'height': height})
    
    def get_widget_size(self, widget_name):
        """获取控件大小"""
        if widget_name in self.visible_widgets:
            widget = self.visible_widgets[widget_name]
            size = widget.size()
            return {'width': size.width(), 'height': size.height()}
        return None
    
    def set_widget_enabled(self, widget_name, enabled):
        """设置控件启用状态"""
        if widget_name in self.visible_widgets:
            widget = self.visible_widgets[widget_name]
            widget.setEnabled(enabled)
            self.set_widget_property(widget_name, 'enabled', enabled)
    
    def is_widget_enabled(self, widget_name):
        """检查控件是否启用"""
        if widget_name in self.visible_widgets:
            return self.visible_widgets[widget_name].isEnabled()
        return False
    
    def batch_show_widgets(self, widget_names, animate=False, duration=300):
        """批量显示控件"""
        for widget_name in widget_names:
            if widget_name in self.visible_widgets:
                self.show_widget(widget_name, animate=animate, duration=duration)
    
    def batch_hide_widgets(self, widget_names, animate=False, duration=300):
        """批量隐藏控件"""
        for widget_name in widget_names:
            if widget_name in self.visible_widgets:
                self.hide_widget(widget_name, animate=animate, duration=duration)
    
    def batch_toggle_widgets(self, widget_names, show, animate=False, duration=300):
        """批量切换控件显示状态"""
        if show:
            self.batch_show_widgets(widget_names, animate, duration)
        else:
            self.batch_hide_widgets(widget_names, animate, duration)
    
    def adjust_container_size(self, container_name):
        """调整容器大小（通用方法）"""
        if container_name in self.visible_widgets:
            container = self.visible_widgets[container_name]
            if hasattr(container, 'adjustSize'):
                container.adjustSize()
                container.updateGeometry()
    
    def ensure_widget_in_bounds(self, widget_name, min_x=20, min_y=20):
        """确保控件在父容器边界内（通用方法）"""
        if widget_name not in self.visible_widgets:
            return
        
        widget = self.visible_widgets[widget_name]
        try:
            parent = widget.parent()
            if not parent:
                return
            
            # 获取控件当前位置和大小
            widget_x = widget.x()
            widget_y = widget.y()
            widget_width = widget.width()
            widget_height = widget.height()
            
            # 获取父容器大小
            parent_width = parent.width()
            parent_height = parent.height()
            
            # 计算最大允许位置
            max_x = parent_width - widget_width
            max_y = parent_height - widget_height
            
            # 确保不超出边界
            new_x = max(min_x, min(widget_x, max_x))
            new_y = max(min_y, min(widget_y, max_y))
            
            # 如果位置需要调整，移动控件
            if new_x != widget_x or new_y != widget_y:
                widget.move(new_x, new_y)
                logger.debug(f"调整控件位置: {widget_name} ({widget_x}, {widget_y}) -> ({new_x}, {new_y})")
                
        except Exception as e:
            logger.debug(f"调整控件位置失败: {e}")
    
    def _adjust_parent_size(self, widget):
        """调整父容器大小，用于控制面板等需要立即调整大小的场景"""
        try:
            # 查找父容器（通常是控制面板）
            parent = widget.parent()
            if parent and hasattr(parent, 'adjustSize'):
                # 只调整直接父容器，不调整主窗口
                parent.adjustSize()
                parent.updateGeometry()
                
                # 不调整主窗口，因为控制面板是悬浮的
                # 注释掉以下代码，避免影响主窗口大小
                # grandparent = parent.parent()
                # if grandparent and hasattr(grandparent, 'adjustSize'):
                #     grandparent.adjustSize()
                #     grandparent.updateGeometry()
        except Exception as e:
            logger.debug(f"调整父容器大小失败: {e}")
    
    def _auto_save_states(self):
        """自动保存控件状态"""
        # 这里可以实现状态持久化逻辑
        logger.debug("自动保存控件状态")
    
    def get_all_widgets_info(self):
        """获取所有控件信息"""
        info = {}
        for name, widget in self.visible_widgets.items():
            info[name] = {
                'state': self.widget_states.get(name, 'unknown'),
                'visible': widget.isVisible(),
                'enabled': widget.isEnabled(),
                'position': self.get_widget_position(name),
                'size': self.get_widget_size(name),
                'properties': self.widget_properties.get(name, {})
            }
        return info
    
    def cleanup(self):
        """清理资源"""
        self.auto_save_timer.stop()
        # 停止所有动画
        for animation in self.widget_animations.values():
            animation.stop()
        self.widget_animations.clear()
        logger.info("UIManager 清理完成")


class MyColorDialog(QColorDialog):
    """自定义颜色对话框（迁移至 ui.py 管理 UI 组件）"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_custom_style()
    
    def _apply_custom_style(self):
        """应用自定义样式"""
        from ui.styles import StyleManager
        style_manager = StyleManager()
        self.setStyleSheet(style_manager.get_stylesheet("color_dialog"))


class WarningPopup(QDialog):
    """警告弹窗（迁移至 ui.py 管理 UI 组件）"""
    def __init__(self, parent=None, message=""):
        super().__init__(parent)
        self._setup_ui(message)
        self._apply_style()
    
    def _setup_ui(self, message):
        """设置UI"""
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(280, 140)
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建面板
        self.panel = QWidget()
        self.panel.setObjectName("panel")
        
        # 创建面板布局
        layout = QVBoxLayout(self.panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        text_label = QLabel(message)
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        button = QPushButton("关闭")
        button.clicked.connect(self.accept)
        button.setFixedWidth(80)
        button.setCursor(Qt.CursorShape.PointingHandCursor)

        layout.addWidget(text_label)
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # 将面板添加到主布局
        main_layout.addWidget(self.panel)
    
    def _apply_style(self):
        """应用样式"""
        from ui.styles import StyleManager
        style_manager = StyleManager()
        self.setStyleSheet(style_manager.get_stylesheet("warning_popup"))


class DeleteConfirmDialog(QDialog):
    """删除确认对话框 - 白底红按钮设计"""
    def __init__(self, parent=None, message="确定要删除这个任务吗？\n删除后无法恢复。"):
        super().__init__(parent)
        self.result = False
        self._setup_ui(message)
        self._apply_style()
    
    def _setup_ui(self, message):
        """设置UI"""
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(320, 180)
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建面板
        self.panel = QWidget()
        self.panel.setObjectName("panel")
        
        # 创建面板布局
        layout = QVBoxLayout(self.panel)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        # 标题
        title_label = QLabel("确认删除")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setObjectName("title_label")

        # 消息内容
        message_label = QLabel(message)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setObjectName("message_label")
        message_label.setWordWrap(True)

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        # 取消按钮
        cancel_button = QPushButton("取消")
        cancel_button.setObjectName("cancel_button")
        cancel_button.clicked.connect(self._on_cancel)
        cancel_button.setFixedSize(80, 35)
        cancel_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # 删除按钮
        delete_button = QPushButton("删除")
        delete_button.setObjectName("delete_button")
        delete_button.clicked.connect(self._on_delete)
        delete_button.setFixedSize(80, 35)
        delete_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(delete_button)
        button_layout.addStretch()

        layout.addWidget(title_label)
        layout.addWidget(message_label)
        layout.addLayout(button_layout)
        
        # 将面板添加到主布局
        main_layout.addWidget(self.panel)
    
    def _apply_style(self):
        """应用样式 - 使用styles.py中的样式"""
        from ui.styles import StyleManager
        style_manager = StyleManager()
        self.setStyleSheet(style_manager.get_stylesheet("delete_confirm_dialog"))
    
    def _on_cancel(self):
        """取消操作"""
        self.result = False
        self.reject()
    
    def _on_delete(self):
        """确认删除"""
        self.result = True
        self.accept()
    
    def get_result(self):
        """获取用户选择结果"""
        return self.result


def apply_drop_shadow(target_widget: QWidget,
                      blur_radius: int = 20,
                      color: QColor = QColor(0, 0, 0, 150),
                      offset_x: int = 0,
                      offset_y: int = 0) -> None:
    """为任意控件统一应用阴影效果"""
    effect = QGraphicsDropShadowEffect(target_widget)
    effect.setBlurRadius(blur_radius)
    effect.setColor(color)
    effect.setOffset(offset_x, offset_y)
    target_widget.setGraphicsEffect(effect)
