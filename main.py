import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
import os,threading

from config.config_manager import load_config
from core.quadrant_widget import QuadrantWidget
from ui.ui import UIManager
from gantt.app import gantt_app
from core.utils import init_logging
import logging
logger = logging.getLogger(__name__)  # 自动获取模块名

class TaskManagerApp:
    """任务管理应用主类"""
    def __init__(self):
        self.app = None
        self.ui_manager = UIManager()
        self.main_window = None
        self.config = None
        
    def initialize(self):
        """初始化应用"""
        try:
            logger.info("程序启动中...")
            self.app = QApplication(sys.argv)
            logger.info("QApplication初始化完成")

            # 加载配置
            self.config = load_config()
            logger.info("配置加载完毕")

            # 创建主窗口
            self.main_window = QuadrantWidget(self.config, ui_manager=self.ui_manager)
            logger.info("四象限窗口创建完毕")
            
            # 注册主窗口到UI管理器
            self.ui_manager.register_widget("main_window", self.main_window, "visible")
            
            # 注册控制面板
            if hasattr(self.main_window, 'control_widget'):
                self.ui_manager.register_widget("control_panel", self.main_window.control_widget, "visible")
            
            # 注册编辑按钮
            if hasattr(self.main_window, 'edit_button'):
                self.ui_manager.register_widget("edit_button", self.main_window.edit_button, "visible")
            
            # 注册添加任务按钮
            if hasattr(self.main_window, 'add_task_button'):
                self.ui_manager.register_widget("add_task_button", self.main_window.add_task_button, "hidden")
            
            # 注册导出任务按钮
            if hasattr(self.main_window, 'export_tasks_button'):
                self.ui_manager.register_widget("export_tasks_button", self.main_window.export_tasks_button, "hidden")
            
            # 注册撤销按钮
            if hasattr(self.main_window, 'undo_button'):
                self.ui_manager.register_widget("undo_button", self.main_window.undo_button, "hidden")
            
            # 注册设置按钮
            if hasattr(self.main_window, 'settings_button'):
                self.ui_manager.register_widget("settings_button", self.main_window.settings_button, "visible")
            
            # 注册完成按钮
            if hasattr(self.main_window, 'complete_button'):
                self.ui_manager.register_widget("complete_button", self.main_window.complete_button, "visible")
            
            # 注册退出按钮
            if hasattr(self.main_window, 'exit_button'):
                self.ui_manager.register_widget("exit_button", self.main_window.exit_button, "visible")

            # 加载任务
            self.main_window.load_tasks()
            logger.info("任务加载完毕")
            
            # 连接UI管理器的信号
            self.ui_manager.widget_state_changed.connect(self.on_widget_state_changed)
            self.ui_manager.animation_finished.connect(self.on_animation_finished)
            
            return True
            
        except Exception as e:
            logger.error(f"初始化失败: {str(e)}")
            return False
    
    def show_main_window(self):
        """显示主窗口"""
        if self.main_window:
            # 使用UI管理器的淡入效果
            self.ui_manager.fade_in_widget("main_window", duration=500)
            # 在窗口显示后设置为底层
            self.main_window.start_bottom_layer_timer()
    
    def on_widget_state_changed(self, widget_name, new_state):
        """控件状态改变回调"""
        logger.debug(f"控件状态改变: {widget_name} -> {new_state}")
    
    def on_animation_finished(self, widget_name):
        """动画完成回调"""
        logger.debug(f"动画完成: {widget_name}")
    
    def run(self):
        """运行应用"""
        if not self.initialize():
            QMessageBox.critical(None, "初始化失败", "应用初始化失败，请检查日志")
            return 1
        
        try:
            # 显示主窗口
            self.show_main_window()
            logger.info("窗口显示完成，进入事件循环")
            
            # 运行应用
            return self.app.exec()
            
        except Exception as e:
            logger.error(f"程序运行错误: {str(e)}")
            QMessageBox.critical(None, "运行错误", f"程序运行出错：{str(e)}")
            return 1
        finally:
            # 清理资源
            if self.ui_manager:
                self.ui_manager.cleanup()



def start_gantt_server():
    # 彻底静音 stdout/stderr，避免 click.echo flush 失败
    sys.stdout = open(os.devnull, "w")
    sys.stderr = open(os.devnull, "w")

    # 禁掉 Flask 的启动横幅
    try:
        from flask import cli as flask_cli
        flask_cli.show_server_banner = lambda *a, **k: None
    except Exception:
        pass

    gantt_app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)


if __name__ == "__main__":
    # 初始化日志
    init_logging()
    # threading.Thread(target=start_gantt_server, daemon=True).start()
    # 创建并运行应用
    app = TaskManagerApp()
    sys.exit(app.run())