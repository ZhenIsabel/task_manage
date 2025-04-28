import sys
import os
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve

from config_manager import load_config
from quadrant_widget import QuadrantWidget

# 程序入口点
if __name__ == "__main__":
    print("程序启动中...")
    app = QApplication(sys.argv)
    print("QApplication初始化完成")
    
    # 加载配置
    config = load_config()
    print("配置加载完毕")
    
    # 创建主窗口
    window = QuadrantWidget(config)
    print("四象限窗口创建完毕")
    
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
    
    print("窗口显示完成，进入事件循环")
    
    sys.exit(app.exec())