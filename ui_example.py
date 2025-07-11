#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UIManager 使用示例
展示如何使用 UIManager 来管理各种控件行为
"""

from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
import sys

from ui import UIManager

class ExampleWindow(QMainWindow):
    """示例窗口，展示UIManager的使用"""
    
    def __init__(self):
        super().__init__()
        self.ui_manager = UIManager()
        self.setup_ui()
        self.setup_ui_manager()
        self.setup_connections()
        
    def setup_ui(self):
        """设置UI界面"""
        self.setWindowTitle("UIManager 使用示例")
        self.setGeometry(100, 100, 800, 600)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建布局
        layout = QVBoxLayout(central_widget)
        
        # 创建控制按钮区域
        control_layout = QHBoxLayout()
        
        # 创建各种按钮
        self.show_button = QPushButton("显示所有控件")
        self.hide_button = QPushButton("隐藏所有控件")
        self.toggle_button = QPushButton("切换显示")
        self.animate_button = QPushButton("动画效果")
        self.info_button = QPushButton("显示信息")
        
        # 添加到控制布局
        control_layout.addWidget(self.show_button)
        control_layout.addWidget(self.hide_button)
        control_layout.addWidget(self.toggle_button)
        control_layout.addWidget(self.animate_button)
        control_layout.addWidget(self.info_button)
        
        layout.addLayout(control_layout)
        
        # 创建演示控件
        self.demo_widget1 = QLabel("演示控件 1 - 这是一个标签")
        self.demo_widget1.setStyleSheet("background-color: #FF6B6B; color: white; padding: 20px; border-radius: 10px;")
        self.demo_widget1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.demo_widget2 = QLabel("演示控件 2 - 另一个标签")
        self.demo_widget2.setStyleSheet("background-color: #4ECDC4; color: white; padding: 20px; border-radius: 10px;")
        self.demo_widget2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.demo_widget3 = QSlider(Qt.Orientation.Horizontal)
        self.demo_widget3.setStyleSheet("background-color: #FFE66D; padding: 20px; border-radius: 10px;")
        
        # 添加到主布局
        layout.addWidget(self.demo_widget1)
        layout.addWidget(self.demo_widget2)
        layout.addWidget(self.demo_widget3)
        
        # 创建状态显示标签
        self.status_label = QLabel("状态: 所有控件已显示")
        self.status_label.setStyleSheet("background-color: #6D8EA0; color: white; padding: 10px; border-radius: 5px;")
        layout.addWidget(self.status_label)
        
    def setup_ui_manager(self):
        """设置UI管理器"""
        # 注册所有控件到UI管理器
        self.ui_manager.register_widget("demo_widget1", self.demo_widget1, "visible")
        self.ui_manager.register_widget("demo_widget2", self.demo_widget2, "visible")
        self.ui_manager.register_widget("demo_widget3", self.demo_widget3, "visible")
        self.ui_manager.register_widget("status_label", self.status_label, "visible")
        
        # 设置控件属性
        self.ui_manager.set_widget_property("demo_widget1", "type", "label")
        self.ui_manager.set_widget_property("demo_widget1", "color", "#FF6B6B")
        self.ui_manager.set_widget_property("demo_widget2", "type", "label")
        self.ui_manager.set_widget_property("demo_widget2", "color", "#4ECDC4")
        self.ui_manager.set_widget_property("demo_widget3", "type", "slider")
        self.ui_manager.set_widget_property("demo_widget3", "color", "#FFE66D")
        
        # 注册事件处理器
        self.ui_manager.register_event_handler("demo_widget1", "click", self.on_widget1_click)
        self.ui_manager.register_event_handler("demo_widget2", "click", self.on_widget2_click)
        
    def setup_connections(self):
        """设置信号连接"""
        # 连接按钮信号
        self.show_button.clicked.connect(self.show_all_widgets)
        self.hide_button.clicked.connect(self.hide_all_widgets)
        self.toggle_button.clicked.connect(self.toggle_widgets)
        self.animate_button.clicked.connect(self.animate_widgets)
        self.info_button.clicked.connect(self.show_widgets_info)
        
        # 连接UI管理器的信号
        self.ui_manager.widget_state_changed.connect(self.on_widget_state_changed)
        self.ui_manager.animation_finished.connect(self.on_animation_finished)
        
        # 连接演示控件的点击事件
        self.demo_widget1.mousePressEvent = lambda e: self.on_widget1_click()
        self.demo_widget2.mousePressEvent = lambda e: self.on_widget2_click()
        
    def show_all_widgets(self):
        """显示所有控件"""
        self.ui_manager.show_widget("demo_widget1", animate=True)
        self.ui_manager.show_widget("demo_widget2", animate=True)
        self.ui_manager.show_widget("demo_widget3", animate=True)
        self.ui_manager.show_widget("status_label", animate=True)
        self.update_status("所有控件已显示")
        
    def hide_all_widgets(self):
        """隐藏所有控件"""
        self.ui_manager.hide_widget("demo_widget1", animate=True)
        self.ui_manager.hide_widget("demo_widget2", animate=True)
        self.ui_manager.hide_widget("demo_widget3", animate=True)
        self.ui_manager.hide_widget("status_label", animate=True)
        self.update_status("所有控件已隐藏")
        
    def toggle_widgets(self):
        """切换控件显示状态"""
        self.ui_manager.toggle_widget_visibility("demo_widget1", animate=True)
        self.ui_manager.toggle_widget_visibility("demo_widget2", animate=True)
        self.ui_manager.toggle_widget_visibility("demo_widget3", animate=True)
        self.update_status("控件状态已切换")
        
    def animate_widgets(self):
        """演示动画效果"""
        # 依次淡入淡出控件
        self.ui_manager.fade_out_widget("demo_widget1", duration=500)
        
        # 使用定时器创建序列动画
        QTimer.singleShot(500, lambda: self.ui_manager.fade_in_widget("demo_widget1", duration=500))
        QTimer.singleShot(1000, lambda: self.ui_manager.fade_out_widget("demo_widget2", duration=500))
        QTimer.singleShot(1500, lambda: self.ui_manager.fade_in_widget("demo_widget2", duration=500))
        QTimer.singleShot(2000, lambda: self.ui_manager.fade_out_widget("demo_widget3", duration=500))
        QTimer.singleShot(2500, lambda: self.ui_manager.fade_in_widget("demo_widget3", duration=500))
        
        self.update_status("动画效果演示中...")
        
    def show_widgets_info(self):
        """显示控件信息"""
        info = self.ui_manager.get_all_widgets_info()
        info_text = "控件信息:\n"
        for name, data in info.items():
            info_text += f"- {name}: {data['state']}, 可见: {data['visible']}, 启用: {data['enabled']}\n"
        self.status_label.setText(info_text)
        
    def on_widget1_click(self):
        """控件1点击事件"""
        self.ui_manager.set_widget_property("demo_widget1", "click_count", 
                                          self.ui_manager.get_widget_property("demo_widget1", "click_count", 0) + 1)
        self.demo_widget1.setText(f"演示控件 1 - 点击次数: {self.ui_manager.get_widget_property('demo_widget1', 'click_count')}")
        
    def on_widget2_click(self):
        """控件2点击事件"""
        self.ui_manager.set_widget_property("demo_widget2", "click_count", 
                                          self.ui_manager.get_widget_property("demo_widget2", "click_count", 0) + 1)
        self.demo_widget2.setText(f"演示控件 2 - 点击次数: {self.ui_manager.get_widget_property('demo_widget2', 'click_count')}")
        
    def on_widget_state_changed(self, widget_name, new_state):
        """控件状态改变回调"""
        print(f"控件 {widget_name} 状态改变为: {new_state}")
        
    def on_animation_finished(self, widget_name):
        """动画完成回调"""
        print(f"控件 {widget_name} 动画完成")
        
    def update_status(self, message):
        """更新状态显示"""
        self.status_label.setText(f"状态: {message}")
        
    def closeEvent(self, event):
        """关闭事件"""
        self.ui_manager.cleanup()
        event.accept()

def main():
    """主函数"""
    app = QApplication(sys.argv)
    
    # 创建示例窗口
    window = ExampleWindow()
    window.show()
    
    # 运行应用
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 