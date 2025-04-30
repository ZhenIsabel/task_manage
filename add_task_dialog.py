from PyQt6.QtCore import Qt,QDate
from PyQt6.QtWidgets import (QDialog, QWidget, QVBoxLayout,
                             QGraphicsDropShadowEffect, QLabel, QLineEdit,
                             QDateEdit, QPushButton, QHBoxLayout, QComboBox, QTextEdit,QFileDialog)
from PyQt6.QtGui import QColor, QMouseEvent

from utils import ICON_PATH
import logging
logger = logging.getLogger(__name__)  # 自动获取模块名

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
        panel.setStyleSheet(f"""
        QWidget#panel {{
            background-color: white;
            border-radius: 15px;
        }}
        /* 把你之前放在 QDialog 上的整段 QSS 原封不动贴进来 */
        QLabel {{
            color: #333333;
            font-family: '微软雅黑';
            font-weight: bold;
            font-size: 14px;
        }}
        QLineEdit, QTextEdit {{
            background-color: #f5f5f5;
            color: #333333;
            border: 1px solid #dddddd;
            border-radius: 8px;
            padding: 12px;
            font-family: '微软雅黑';
            font-size: 13px;
        }}
        QDateEdit {{
            background-color: #f5f5f5;
            color: #333333;
            border: 1px solid #dddddd;
            border-radius: 8px;
            padding: 12px;
            font-family: '微软雅黑';
            font-size: 13px;
            min-height: 20px;
        }}
        QPushButton {{
            background-color: #4ECDC4;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 20px;
            font-family: '微软雅黑';
            font-weight: bold;
        }}
        QPushButton:hover {{background-color: #45B8B0; }}
        QComboBox {{
            background-color: #f5f5f5;
            color: #333333;
            border: 1px solid #dddddd;
            border-radius: 8px;
            padding: 10px;
            font-family: '微软雅黑';
            font-size: 13px;
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 30px;
            border-left: 1px solid #dddddd;
            background-color: #f5f5f5;
        }}
        QComboBox::down-arrow {{
            image: url({ICON_PATH}/down_arrow.png); /* 这里可以放一个小箭头图片，或者不加 */
            width: 20px;
            height: 20px;
        }}
        QComboBox QAbstractItemView {{
            background-color: #f5f5f5;
            border: 1px solid #dddddd;
            selection-background-color: #4ECDC4; /* 选中时的背景色 */
            selection-color: white;              /* 选中时文字白色 */
            padding: 5px;
            outline: 0px;
            font-family: '微软雅黑';
            font-size: 13px;
            border-radius: 8px; /* 下拉列表本身也有圆角 */
        }}
        """)

        # 阴影
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 0)
        shadow.setColor(QColor(0, 0, 0, 150))
        panel.setGraphicsEffect(shadow)

        # ------- 下面放你的字段、按钮 ------- #
        self.inputs = {}
        for f in task_fields:
            lab = QLabel(f"{f['label']}{' *' if f.get('required') else ''}")
            panel_layout.addWidget(lab)

            # 创建控件时设置默认值
            default_value = f.get('default', '')
            # 根据字段类型创建不同的控件
            if f['type'] == 'date':
                w = QDateEdit()
                w.setCalendarPopup(True)
                w.setDisplayFormat("yyyy-MM-dd")
                # 如果有默认值则设置日期，否则保持原逻辑
                if default_value:
                    w.setDate(QDate.fromString(default_value, "yyyy-MM-dd"))
                else:
                    w.setDate(QDate.currentDate().addDays(1))
            elif f['type'] == 'select':
                # 创建下拉选择框
                w = QComboBox()
                # 添加选项
                for option in f.get('options', []):
                    w.addItem(option)
                # 设置默认值
                if default_value and default_value in f.get('options', []):
                    w.setCurrentText(default_value)
            elif f['type'] == 'multiline':
                # 创建多行文本输入框
                w = QTextEdit()
                w.setPlaceholderText("请输入备注...")
                w.setMinimumHeight(100)  # 设置最小高度
                if default_value:
                    w.setText(str(default_value))
            elif f['type'] == 'file':
                dir_layout = QHBoxLayout()
                path_edit = QLineEdit()
                path_edit.setPlaceholderText("请选择文件夹路径...")
                path_edit.setReadOnly(True)
                if default_value:
                    path_edit.setText(str(default_value))
                btn = QPushButton("选择")
                # 使用lambda绑定当前path_edit实例
                btn.clicked.connect(lambda _, we=path_edit: self.choose_dir(we))
                dir_layout.addWidget(path_edit)
                dir_layout.addWidget(btn)
                panel_layout.addLayout(dir_layout)
                self.inputs[f['name']] = path_edit  # 存储正确的控件引用
                continue
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

    def choose_dir(self, widget):
        """Handle directory selection for file fields"""
        path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if path:
            widget.setText(path)


    def get_data(self):
        """把表单内容打包成 dict 返回"""
        data = {}
        for name, w in self.inputs.items():
            if isinstance(w, QDateEdit):
                data[name] = w.date().toString("yyyy-MM-dd")
            elif isinstance(w, QComboBox):
                data[name] = w.currentText()
            elif isinstance(w, QTextEdit):
                data[name] = w.toPlainText()
            else:
                data[name] = w.text()
        return data