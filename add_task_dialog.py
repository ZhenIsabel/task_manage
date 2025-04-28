from PyQt6.QtCore import Qt,QDate               # PySide6 也是 QtCore.Qt
from PyQt6.QtWidgets import (QDialog, QWidget, QVBoxLayout,
                             QGraphicsDropShadowEffect, QLabel, QLineEdit,
                             QDateEdit, QPushButton, QHBoxLayout)
from PyQt6.QtGui import QColor, QMouseEvent

class AddTaskDialog(QDialog):
    def __init__(self, parent=None, task_fields=None):
        # ❶ 直接把 QDialog 设为「无边框」窗口
        super().__init__(parent, flags=Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        # ❷ 允许窗口背景透明（才能配合圆角 + 阴影）
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # ------- 外层透明壳，什么都不画 ------- #

        # ❸ 真正的白色圆角面板
        panel = QWidget(self)
        panel.setObjectName("panel")
        panel.setStyleSheet("""
            QWidget#panel {
                background: white;
                border-radius: 15px;
            }
        """)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(30, 30, 30, 30)
        panel_layout.setSpacing(15)

        # 样式
        panel.setStyleSheet("""
        QWidget#panel {
            background-color: white;
            border-radius: 15px;
        }
        /* 把你之前放在 QDialog 上的整段 QSS 原封不动贴进来 */
        QLabel {
            color: #333333;
            font-family: '微软雅黑';
            font-weight: bold;
            font-size: 14px;
        }
        QLineEdit, QTextEdit {
            background-color: #f5f5f5;
            color: #333333;
            border: 1px solid #dddddd;
            border-radius: 8px;
            padding: 12px;
            font-family: '微软雅黑';
            font-size: 13px;
        }
        QDateEdit {
            background-color: #f5f5f5;
            color: #333333;
            border: 1px solid #dddddd;
            border-radius: 8px;
            padding: 12px;
            font-family: '微软雅黑';
            font-size: 13px;
            min-height: 20px;
        }
        QPushButton {
            background-color: #4ECDC4;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 20px;
            font-family: '微软雅黑';
            font-weight: bold;
        }
        QPushButton:hover { background-color: #45B8B0; }
        """)

        # 阴影
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 0)
        shadow.setColor(QColor(0, 0, 0, 150))
        panel.setGraphicsEffect(shadow)

        # ------- 下面放你的字段、按钮 ------- #
        if task_fields is None:
            task_fields = [
                {'name': 'text', 'label': '任务内容', 'type': 'text', 'required': True},
                {'name': 'due_date', 'label': '到期日期', 'type': 'date', 'required': False}
            ]

        self.inputs = {}
        for f in task_fields:
            lab = QLabel(f"{f['label']}{' *' if f.get('required') else ''}")
            panel_layout.addWidget(lab)

            # 创建控件时设置默认值
            default_value = f.get('default', '')
            if f['type'] == 'date':
                w = QDateEdit()
                w.setCalendarPopup(True)
                w.setDisplayFormat("yyyy-MM-dd")
                # 如果有默认值则设置日期，否则保持原逻辑
                if default_value:
                    w.setDate(QDate.fromString(default_value, "yyyy-MM-dd"))
                else:
                    w.setDate(QDate.currentDate().addDays(1))
            else:
                w = QLineEdit(str(default_value))  # 设置文本默认值
                
            panel_layout.addWidget(w)
            self.inputs[f['name']] = w

        # 按钮
        btn_row = QHBoxLayout()
        ok = QPushButton("确定"); ok.clicked.connect(self.accept)
        cancel = QPushButton("取消"); cancel.clicked.connect(self.reject)
        btn_row.addWidget(ok); btn_row.addWidget(cancel)
        panel_layout.addLayout(btn_row)

        # ❹ 自动根据内容调大小，再把“壳”和“面板”都居中放
        panel.setMinimumWidth(400)          # 或 panel.setFixedWidth(400)

        panel_layout.activate()             # 让布局重新计算
        panel.adjustSize()                  # 先让 panel 把高度伸展开

        self.resize(panel.size())           # 再把外壳调到同样大小
        panel.move(0, 0)                    # 面板贴壳左上
        self.setFixedWidth(self.width())    # 如需锁宽度，可留下这句

        # ❺ 可选：实现拖动窗口（因为没了系统标题栏）
        self._drag_pos = None

    # ---------- 拖动实现 ----------
    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, e: QMouseEvent):
        if self._drag_pos and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e: QMouseEvent):
        self._drag_pos = None

    def get_data(self):
        """把表单内容打包成 dict 返回"""
        data = {}
        for name, w in self.inputs.items():
            if isinstance(w, QDateEdit):
                data[name] = w.date().toString("yyyy-MM-dd")
            else:
                data[name] = w.text()
        return data