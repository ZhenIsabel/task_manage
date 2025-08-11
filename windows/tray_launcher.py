import sys
import os
import subprocess
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QCoreApplication

# 确保项目根目录在模块搜索路径中
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Windows API 导入（用于窗口管理）
try:
    import win32gui
    import win32con
    import win32process
    import win32api
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

# 配置日志系统
from core.utils import init_logging
import logging
logger = logging.getLogger(__name__)

class TaskManagerTray(QSystemTrayIcon):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.process = None
        
        
        # 设置图标 - 使用项目根目录下的图标
        self.project_root = PROJECT_ROOT
        icon_path = os.path.join(PROJECT_ROOT, "icons", "app_icon.png")
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
        
        # # 添加"置顶"选项
        # bring_to_front_action = QAction("置顶", self)
        # bring_to_front_action.triggered.connect(self.bring_to_front)
        # menu.addAction(bring_to_front_action)
        
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
                
            main_script = os.path.join(PROJECT_ROOT, "main.py")
            
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
                cwd=PROJECT_ROOT,
                stderr=subprocess.STDOUT,
                text=True,
                # 新增环境变量
                env={**os.environ, 'QT_QPA_PLATFORM_PLUGIN_PATH': os.path.join(sys.prefix, 'Lib/site-packages/PyQt6/Qt/plugins')}
            )
            
            
            # 检查进程是否成功启动
            if self.process.poll() is not None:
                error_msg = f"应用启动后立即退出，返回码: {self.process.returncode}"
                logger.error(error_msg)
                return
                
            logger.info(f"应用已启动，PID: {self.process.pid}")
        except Exception as e:
            error_msg = f"启动应用失败: {str(e)}"
            logger.exception(error_msg)

    def open_app(self):
        """置顶应用（如果已关闭则重新启动）"""
            # 新增进程状态检查
        is_running = self.bring_to_front()
        logger.info(f"running:{is_running}")
        if not is_running:
            logger.info("应用未运行，正在重新启动...")
            self.start_app()
        
    
    def find_related_python_processes(self):
        """查找所有相关的Python进程"""
        related_pids = [self.process.pid] if self.process else []
        
        try:
            # 使用tasklist查找所有Python进程
            result = subprocess.run(['tasklist', '/FO', 'CSV'], 
                                  capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            
            python_processes = []
            for line in result.stdout.split('\n'):
                if 'python' in line.lower():
                    parts = line.split(',')
                    if len(parts) >= 2:
                        try:
                            pid = int(parts[1].strip('"'))
                            process_name = parts[0].strip('"')
                            python_processes.append({'pid': pid, 'name': process_name})
                            logger.info(f"发现Python进程: {process_name} (PID: {pid})")
                        except:
                            continue
            
            # 如果找到多个Python进程，都加入搜索范围
            for proc in python_processes:
                if proc['pid'] not in related_pids:
                    related_pids.append(proc['pid'])
            
            logger.info(f"相关进程PIDs: {related_pids}")
            return related_pids
            
        except Exception as e:
            logger.warning(f"查找Python进程失败: {e}")
            return related_pids
    
    def _is_likely_main_window(self, window_text, class_name, is_visible):
        """判断窗口是否可能是主应用窗口"""
        
        # 排除明显的系统和内部窗口
        excluded_classes = [
            'ScreenChangeObserverWindow',  # Qt屏幕变化观察窗口
            'TrayIconMessageWindow',       # Qt托盘消息窗口
            'IME',                         # 输入法窗口
            'MSCTFIME',                    # 微软输入法
            'SoPY_',                       # 搜狗输入法
            'Sogou_',                      # 搜狗输入法
        ]
        
        # 检查是否是要排除的窗口类
        for excluded in excluded_classes:
            if excluded in class_name:
                logger.debug(f"排除系统窗口: class='{class_name}', title='{window_text}'")
                return False
        
        # 排除没有标题且不可见的窗口
        if not window_text.strip() and not is_visible:
            logger.debug(f"排除无标题且不可见的窗口: class='{class_name}'")
            return False
        
        # 优先选择有意义标题的可见窗口
        if is_visible and window_text.strip():
            # 检查标题是否包含程序相关信息
            meaningful_titles = ['python', 'main', '四象限', '任务', 'task']
            title_lower = window_text.lower()
            for keyword in meaningful_titles:
                if keyword in title_lower:
                    logger.info(f"识别为主窗口（有意义标题）: title='{window_text}', class='{class_name}', visible={is_visible}")
                    return True
        
        # 检查是否是Qt主窗口类
        main_window_patterns = [
            'QWindowToolSaveBits',    # Qt主窗口类型
            'QWidget',                # QWidget主窗口
            'QMainWindow',            # Qt主窗口
        ]
        
        for pattern in main_window_patterns:
            if pattern in class_name and is_visible:
                logger.info(f"识别为主窗口（Qt主窗口类）: title='{window_text}', class='{class_name}', visible={is_visible}")
                return True
        
        logger.debug(f"不是主窗口: title='{window_text}', class='{class_name}', visible={is_visible}")
        return False
    
    def bring_to_front(self):
        """将应用窗口置顶（只置顶一次，不保持）"""
        # 检查应用是否在运行
        if self.process is None or self.process.poll() is not None:
            logger.info("应用未运行，无法置顶")
            self.showMessage("操作失败", "应用未运行，请先打开应用", QSystemTrayIcon.MessageIcon.Warning)
            return
        
        try:
            # 检查是否有Windows API支持
            if not HAS_WIN32:
                logger.error("Windows API 不可用，无法执行置顶操作")
                self.showMessage("操作失败", "系统不支持此功能", QSystemTrayIcon.MessageIcon.Critical)
                return
            
            # 查找所有相关的Python进程
            related_pids = self.find_related_python_processes()
            logger.info(f"开始在进程 {related_pids} 中查找窗口...")
            
            # 收集所有相关窗口信息用于调试
            all_windows = []
            target_windows = []
            
            def debug_callback(hwnd, data):
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    window_text = win32gui.GetWindowText(hwnd)
                    class_name = win32gui.GetClassName(hwnd)
                    is_visible = win32gui.IsWindowVisible(hwnd)
                    
                    all_windows.append({
                        'hwnd': hwnd,
                        'pid': pid,
                        'title': window_text,
                        'class': class_name,
                        'visible': is_visible
                    })
                    
                    # 如果是相关进程的窗口
                    if pid in related_pids:
                        # logger.info(f"找到进程窗口: hwnd={hwnd}, title='{window_text}', class='{class_name}', visible={is_visible}")
                        
                        # 精确检查是否是主窗口，排除系统和内部窗口
                        is_main_window = self._is_likely_main_window(window_text, class_name, is_visible)
                        
                        if is_main_window:
                            target_windows.append(hwnd)
                            
                            # 先尝试显示窗口（如果被隐藏或最小化）
                            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
                            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                            
                            # 设置为前台窗口
                            try:
                                win32gui.SetForegroundWindow(hwnd)
                            except:
                                # 如果直接设置前台失败，尝试其他方法
                                win32gui.BringWindowToTop(hwnd)
                                win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, 0, 0, 0, 0, 
                                                    win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
                            
                            # 临时置顶显示窗口
                            win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, 
                                                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
                            import time
                            time.sleep(0.1)  # 短暂延迟
                            # 取消置顶，保持在正常层级
                            win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, 
                                                win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
                        
                except Exception as e:
                    logger.debug(f"处理窗口 {hwnd} 时出错: {e}")
                return True
            
            # 枚举所有窗口，包括子窗口和隐藏窗口
            win32gui.EnumWindows(debug_callback, None)
            
            # 输出调试信息
            related_windows = [w for w in all_windows if w['pid'] in related_pids]
            logger.info(f"总共找到 {len(all_windows)} 个窗口")
            logger.info(f"相关进程 {related_pids} 的窗口数量: {len(related_windows)}")
            logger.info(f"成功处理的窗口数量: {len(target_windows)}")
            
            if target_windows:
                logger.info(f"成功操作了 {len(target_windows)} 个窗口")
                self.showMessage("操作成功", "已将四象限任务管理工具窗口置顶", QSystemTrayIcon.MessageIcon.Information)
                return True
            else:
                # 如果没找到目标窗口，显示相关进程的所有窗口信息
                if related_windows:
                    logger.warning(f"相关进程 {related_pids} 有 {len(related_windows)} 个窗口，但都不是主窗口:")
                    for i, win in enumerate(related_windows):
                        logger.info(f"  窗口{i+1}: PID={win['pid']}, hwnd={win['hwnd']}, title='{win['title']}', class='{win['class']}', visible={win['visible']}")
                else:
                    logger.warning(f"相关进程 {related_pids} 没有找到任何窗口")
                
                self.showMessage("操作失败", "找不到可操作的应用窗口，可能应用窗口创建失败", QSystemTrayIcon.MessageIcon.Warning)
                
        except Exception as e:
            logger.error(f"置顶窗口失败: {str(e)}")
            self.showMessage("操作失败", f"置顶操作失败: {str(e)}", QSystemTrayIcon.MessageIcon.Critical)
    
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
    init_logging()
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