from PyQt6.QtWidgets import QColorDialog
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

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



class WarningPopup(QDialog):
    def __init__(self, parent=None, message=""):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("""
            QDialog {
                background-color: #ECECEC;
                border-radius: 10px;
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
        """)

        self.setFixedSize(280, 140)
        layout = QVBoxLayout(self)
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