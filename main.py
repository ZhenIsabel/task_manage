import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve

from config_manager import load_config
from quadrant_widget import QuadrantWidget


from utils import init_logging
import logging
logger = logging.getLogger(__name__)  # 自动获取模块名

if __name__ == "__main__":
    # 初始化日志
    init_logging()
    try:
        logger.info("程序启动中...")
        app = QApplication(sys.argv)
        logger.info("QApplication初始化完成")

        # 加载配置
        config = load_config()
        logger.info("配置加载完毕")

        # 创建主窗口
        window = QuadrantWidget(config)
        logger.info("四象限窗口创建完毕")

        # 加载任务
        window.load_tasks()
        logger.info("任务加载完毕")
        
        # 添加淡入动画效果
        window.setWindowOpacity(0.0)
        window.show()
        
        # 创建淡入动画
        fade_in = QPropertyAnimation(window, b"windowOpacity")
        fade_in.setDuration(500)  # 1秒淡入
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.InOutQuad)
        fade_in.start()
        
        logger.info("窗口显示完成，进入事件循环")
        sys.exit(app.exec())
        
    except Exception as e:
        logger.error("程序崩溃！错误信息：")
        QMessageBox.critical(None, "致命错误", f"程序崩溃：{str(e)}")