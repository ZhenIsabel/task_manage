import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
import os
from datetime import datetime, time

from config.config_manager import load_config
from core.quadrant_widget import QuadrantWidget
from ui.scrollbar import install_global_fluent_scrollbars
from ui.ui import UIManager
from core.utils import init_logging
from core.scheduler import TaskScheduler
from ui.notifications import show_error
import logging
logger = logging.getLogger(__name__)  # 自动获取模块名

class TaskManagerApp:
    """任务管理应用主类"""
    def __init__(self):
        self.app = None
        self.ui_manager = UIManager()
        self.main_window = None
        self.config = None
        self.refresh_timer = None
        self.task_scheduler = None
        # 最近一次已满足的刷新时间点（datetime）；用时间点而非日期，
        # 这样当天把刷新时间改晚后，新时间点仍会触发
        self.last_refresh_target = None
        
    def initialize(self):
        """初始化应用"""
        try:
            logger.info("程序启动中...")
            self.app = QApplication(sys.argv)
            logger.info("QApplication初始化完成")
            install_global_fluent_scrollbars(self.app)

            # 加载配置
            self.config = load_config()
            logger.info("配置加载完毕")

            # 创建主窗口
            self.main_window = QuadrantWidget(self.config, ui_manager=self.ui_manager)
            logger.info("四象限窗口创建完毕")
            
            # 注册主窗口到UI管理器
            self.ui_manager.register_widget("main_window", self.main_window, "visible")

            # 注册主窗口上的控件：(注册名/属性名, 初始状态)
            widget_registrations = [
                ("control_panel", "control_widget", "visible"),
                ("edit_button", "edit_button", "visible"),
                ("add_task_button", "add_task_button", "hidden"),
                ("export_tasks_button", "export_tasks_button", "hidden"),
                ("undo_button", "undo_button", "hidden"),
                ("settings_button", "settings_button", "visible"),
                ("complete_button", "complete_button", "visible"),
                ("exit_button", "exit_button", "visible"),
                ("scheduled_task_button", "scheduled_task_button", "hidden"),
            ]
            for name, attr, state in widget_registrations:
                widget = getattr(self.main_window, attr, None)
                if widget is not None:
                    self.ui_manager.register_widget(name, widget, state)

            # 加载任务
            self.main_window.load_tasks()
            logger.info("任务加载完毕")
            
            # 初始化任务调度器
            self.task_scheduler = TaskScheduler()
            logger.info("任务调度器初始化完成")
            
            # 启动定时刷新定时器
            self.setup_auto_refresh()
            
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
            self.ui_manager.fade_in_widget("main_window", duration=300)
    
    def on_widget_state_changed(self, widget_name, new_state):
        """控件状态改变回调"""
        logger.debug(f"控件状态改变: {widget_name} -> {new_state}")
    
    def on_animation_finished(self, widget_name):
        """动画完成回调"""
        logger.debug(f"动画完成: {widget_name}")
    
    def _get_refresh_time(self):
        """解析配置中的每日刷新时间，失败返回None"""
        refresh_time_str = self.config.get('auto_refresh', {}).get('refresh_time', '00:02:00')
        try:
            hour, minute, second = map(int, refresh_time_str.split(':'))
            return time(hour, minute, second)
        except Exception as e:
            logger.error(f"解析刷新时间失败: {refresh_time_str}, 错误: {str(e)}")
            return None

    def setup_auto_refresh(self):
        """设置自动刷新定时器"""
        try:
            auto_refresh_config = self.config.get('auto_refresh', {})
            enabled = auto_refresh_config.get('enabled', True)

            if not enabled:
                logger.info("自动刷新功能已禁用")
                return

            # 若启动时已过当日刷新时间，将该时间点视为已满足，避免启动即触发；
            # 之后若把刷新时间改到更晚，新时间点仍会正常触发
            refresh_time = self._get_refresh_time()
            now = datetime.now()
            if refresh_time is not None and now.time() >= refresh_time:
                self.last_refresh_target = datetime.combine(now.date(), refresh_time)

            # 创建定时器，每分钟检查一次
            self.refresh_timer = QTimer()
            self.refresh_timer.timeout.connect(self.check_auto_refresh)
            self.refresh_timer.start(60000)  # 每60秒检查一次

            logger.info("自动刷新定时器已启动")
        except Exception as e:
            logger.error(f"设置自动刷新失败: {str(e)}")

    def check_auto_refresh(self):
        """检查是否需要自动刷新"""
        try:
            auto_refresh_config = self.config.get('auto_refresh', {})
            if not auto_refresh_config.get('enabled', True):
                return

            refresh_time = self._get_refresh_time()
            if refresh_time is None:
                return

            now = datetime.now()

            # 已过当日刷新时间点且该时间点尚未满足过即触发；
            # 用 >= 而非精确分钟匹配，避免定时器漂移跳过目标分钟
            target = datetime.combine(now.date(), refresh_time)
            if now >= target and (self.last_refresh_target is None or self.last_refresh_target < target):
                logger.info(f"到达刷新时间: {refresh_time}，开始刷新页面并检查定时任务")
                self.do_auto_refresh()
                self.last_refresh_target = target

        except Exception as e:
            logger.error(f"检查自动刷新失败: {str(e)}")
    
    def do_auto_refresh(self):
        """执行自动刷新和定时任务检查"""
        try:
            # 1. 检查并生成到期的定时任务
            if self.task_scheduler:
                spawned_count = self.task_scheduler.check_and_spawn_scheduled_tasks()
                if spawned_count > 0:
                    logger.info(f"自动刷新：生成了 {spawned_count} 个定时任务")
            
            # 2. 刷新页面
            if self.main_window:
                self.main_window.load_tasks()
                logger.info("自动刷新：页面已刷新")
        
        except Exception as e:
            logger.error(f"执行自动刷新失败: {str(e)}")
    
    def run(self):
        """运行应用"""
        if not self.initialize():
            show_error(None, "初始化失败", "应用初始化失败，请检查日志")
            return 1
        
        try:
            # 显示主窗口
            self.show_main_window()
            logger.info("窗口显示完成，进入事件循环")
            
            # 运行应用
            return self.app.exec()
            
        except Exception as e:
            logger.error(f"程序运行错误: {str(e)}")
            show_error(None, "运行错误", f"程序运行出错：{str(e)}")
            return 1
        finally:
            # 清理资源
            if self.refresh_timer:
                self.refresh_timer.stop()
            if self.ui_manager:
                self.ui_manager.cleanup()



def start_gantt_server():
    # 延迟导入，避免主程序启动时加载 Flask
    from gantt.app import gantt_app

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