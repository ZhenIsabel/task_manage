from PyQt6.QtWidgets import QColorDialog

class MyColorDialog(QColorDialog):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 自定义样式表
        self.setStyleSheet("""
            QColorDialog {
                background-color: #ECECEC;
            }
            QLabel {
                color: #333;
                font-family: '微软雅黑';
                font-size: 12px;
            }
            QPushButton {
                background-color: #ECECEC;
                border: 1px solid rgba(100, 100, 100, 0.5);
                border-radius: 6px;
                padding: 4px 8px;
                font-family: '微软雅黑';
                font-size: 12px;
                color: #333;
            }
            QPushButton:hover {
                background-color: #D6D6D6;
            }
            QFrame {
                background-color: #ECECEC;
            }
            QLineEdit {
                background-color: white;
                border: 1px solid rgba(100, 100, 100, 0.5);
                border-radius: 4px;
                padding: 2px 6px;
                font-family: '微软雅黑';
                font-size: 12px;
                color: #333;
            }
        """)
