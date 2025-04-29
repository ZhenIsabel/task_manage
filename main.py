import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve

from config_manager import load_config
from quadrant_widget import QuadrantWidget

import logging

# 添加日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('main.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("Main")

if __name__ == "__main__":
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
        print("任务加载完毕")
        
        # 添加淡入动画效果
        window.setWindowOpacity(0.0)
        window.show()
        
        # 创建淡入动画
        fade_in = QPropertyAnimation(window, b"windowOpacity")
        fade_in.setDuration(1000)  # 1秒淡入
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.InOutQuad)
        fade_in.start()
        
        logger.info("窗口显示完成，进入事件循环")
        sys.exit(app.exec())
        
    except Exception as e:
        logger.exception("程序崩溃！错误信息：")
        QMessageBox.critical(None, "致命错误", f"程序崩溃：{str(e)}")