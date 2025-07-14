import sys
import os
import subprocess
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QCoreApplication
from styles import StyleManager

# 配置日志系统
import logging
logger = logging.getLogger(__name__)  # 自动获取模块名

class TaskManagerTray(QSystemTrayIcon):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.process = None
        
        # 设置图标 - 使用项目中的图标
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons", "app_icon.png")
        self.setIcon(QIcon(icon_path))
        self.setToolTip("四象限任务管理工具")
        
        # 添加托盘点击处理
        self.activated.connect(self.handle_tray_activate)

        # 创建右键菜单
        menu = QMenu()
        
        # 添加"打开"选项
        open_action = QAction("打开", self)
        open_action.triggered.connect(self.open_app)
        menu.addAction(open_action)
        
        # 添加分隔线
        menu.addSeparator()
        
        # 添加"退出"选项
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.exit_app)
        menu.addAction(exit_action)
        # 设置右键菜单
        self.setContextMenu(menu)
        
        # 显示图标
        self.show()
        
        # 启动主应用
        self.start_app()
        
    def start_app(self):
        """启动主应用程序"""
        try:
            # 使用pythonw.exe启动应用，不显示控制台窗口
            python_exe = sys.executable.replace("python.exe", "pythonw.exe")
            if not os.path.exists(python_exe):
                python_exe = sys.executable
                
            main_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
            
            # 检查主脚本是否存在
            if not os.path.exists(main_script):
                error_msg = f"找不到主程序文件: {main_script}"
                logger.error(error_msg)
                self.showMessage("启动失败", error_msg, QSystemTrayIcon.MessageIcon.Critical)
                return
            
            # 使用subprocess启动应用，不显示控制台窗口
            # 添加当前工作目录，确保相对路径正确
            self.process = subprocess.Popen(
                [python_exe, main_script], 
                creationflags=subprocess.CREATE_NO_WINDOW,
                cwd=os.path.dirname(os.path.abspath(__file__)),
                stdout=open(os.path.join(os.path.dirname(__file__), 'main_output.log'), 'w'), 
                stderr=subprocess.STDOUT,
                text=True,
                # 新增环境变量
                env={**os.environ, 'QT_QPA_PLATFORM_PLUGIN_PATH': os.path.join(sys.prefix, 'Lib/site-packages/PyQt6/Qt/plugins')}
            )
            
            
            # 检查进程是否成功启动
            if self.process.poll() is not None:
                error_msg = f"应用启动后立即退出，返回码: {self.process.returncode}"
                logger.error(error_msg)
                self.showMessage("启动失败", error_msg, QSystemTrayIcon.MessageIcon.Critical)
                return
                
            logger.info(f"应用已启动，PID: {self.process.pid}")
            self.showMessage("启动成功", "四象限任务管理工具已启动", QSystemTrayIcon.MessageIcon.Information)
        except Exception as e:
            error_msg = f"启动应用失败: {str(e)}"
            logger.exception(error_msg)
            self.showMessage("启动失败", error_msg, QSystemTrayIcon.MessageIcon.Critical)

    def open_app(self):
        """打开应用（如果已关闭则重新启动）"""
            # 新增进程状态检查
        if self.process and self.process.poll() is None:
            try:
                # 检查进程是否真的存活
                if sys.platform == 'win32' and HAS_WIN32:
                    process_handle = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION, 0, self.process.pid)
                    if not process_handle:
                        logger.debug("进程句柄获取失败，重置进程状态")
                        self.process = None
            except Exception:
                self.process = None
                logger.error(f"进程状态检查异常：{str(e)}") 


        if self.process is None or self.process.poll() is not None:
            logger.info("应用未运行，正在重新启动...")
            self.start_app()
        else:
            # 应用已在运行，尝试将其窗口置顶
            logger.info(f"应用已在运行，PID: {self.process.pid}")
            try:
                # 在Windows上，可以使用以下方法尝试激活窗口
                import win32gui
                import win32con
                import win32process
                
                def callback(hwnd, hwnds):
                    # 检查窗口是否可见
                    if win32gui.IsWindowVisible(hwnd):
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        # 检查窗口是否属于我们的进程
                        if pid == self.process.pid:
                            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                            win32gui.SetForegroundWindow(hwnd)
                            hwnds.append(hwnd)
                    return True
                
                hwnds = []
                win32gui.EnumWindows(callback, hwnds)
                
                if not hwnds:
                    logger.warning("找不到应用窗口，尝试重新启动...")
                    self.process.terminate()
                    self.start_app()
                else:
                    logger.info(f"已激活应用窗口，句柄: {hwnds}")
                    self.showMessage("操作成功", "已将四象限任务管理工具窗口置顶", 
                                    QSystemTrayIcon.MessageIcon.Information)
            except Exception as e:
                logger.error(f"激活窗口失败: {str(e)}，尝试重新启动...")
                self.process.terminate()
                self.start_app()
    
    def exit_app(self):
        """退出应用"""
        # 关闭主应用
        if self.process and self.process.poll() is None:
            try:
                logger.info("正在关闭主应用...")
                self.process.terminate()
                self.process.wait(timeout=3)
                logger.info("主应用已正常关闭")
            except:
                # 如果无法正常终止，强制结束
                try:
                    logger.warning("主应用无法正常关闭，正在强制结束...")
                    self.process.kill()
                    logger.info("主应用已强制关闭")
                except:
                    logger.error("无法关闭主应用")
        
        # 退出托盘应用
        logger.info("正在退出托盘应用...")
        QCoreApplication.quit()

    def handle_tray_activate(self, reason):
        """处理托盘图标交互事件"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.open_app()

if __name__ == "__main__":
    logger.info("托盘应用启动中...")
    # 创建应用
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # 关闭窗口时不退出应用
    
    # 创建托盘图标
    tray = TaskManagerTray(app)
    logger.info("托盘图标已创建")
    
    # 进入事件循环
    logger.info("进入事件循环")
    sys.exit(app.exec())