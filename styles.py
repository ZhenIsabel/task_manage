from PyQt6.QtWidgets import QColorDialog, QDialog, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt


class StyleManager:
    """负责样式管理的类"""
    def __init__(self):
        self.stylesheets = {
            # 任务标签样式
            "task_label": """
            QWidget {{
                background: transparent;  /* 透明背景 */
                border-radius: 10px;      /* 圆角 */
                border: none;             /* 无边框 */
            }}
            QLabel {{
                background-color: rgba({bg_color_red}, {bg_color_green}, {bg_color_blue}, 217);  /* 标签背景色，带透明度 */
                color: rgb({text_color_red}, {text_color_green}, {text_color_blue});             /* 文字颜色 */
                font-weight: bold;        /* 加粗 */
                font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;  /* 字体 */
                padding: 2px 8px;         /* 上下 2px、左右 8px 内边距 */
            }}
            QCheckBox {{
                spacing: 5px;             /* 复选框与文字间距 */
                background-color: transparent;  /* 透明背景 */
            }}
            QCheckBox::indicator {{
                width: {indicator_size}px;     /* 指示器宽度 */
                height: {indicator_size}px;    /* 指示器高度 */
                border-radius: 9px;            /* 圆角 */
                border: 2px solid gray;        /* 灰色边框 */
                background-color: rgba({bg_color_red}, {bg_color_green}, {bg_color_blue}, 0.85); /* 背景色 */
            }}
            QCheckBox::indicator:checked {{
                background-color: rgba({bg_color_red}, {bg_color_green}, {bg_color_blue}, 0.85); /* 选中时背景色 */
                border: 2px solid #4ECDC4;    /* 选中时边框色 */
                image:  url(./icons/check.png); /* 选中时显示对勾图片 */
            }}
            QMenu {{
                background-color: white;   /* 菜单背景色 */
                border-radius: 8px;        /* 圆角 */
                padding: 5px;              /* 内边距 */
            }}
            QMenu::item {{
                padding: 5px 20px;         /* 菜单项内边距 */
                border-radius: 4px;        /* 菜单项圆角 */
            }}
            QMenu::item:selected {{
                background-color: #4ECDC4; /* 选中项背景色 */
                color: white;              /* 选中项文字色 */
            }}
        """,
        # 详情弹窗样式
        "detail_popup": """
            QFrame {{
                background-color: #ECECEC;  /* 浅灰背景 */
                border-radius: 10px;        /* 圆角 */
                border: 1px solid rgba(100, 100, 100, 0.5); /* 半透明边框 */
            }}
            QLabel {{
                color: black;               /* 文字黑色 */
                font-family: '微软雅黑';      /* 字体 */
                padding: 4px;               /* 内边距 */
            }}
            QScrollArea {{
                border: none;               /* 无边框 */
                background-color: transparent; /* 透明背景 */
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 4px 2px 4px 0;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: #D6D6D6;
                min-height: 30px;
                border-radius: 4px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
            QScrollBar:horizontal {{
                background: transparent;
                height: 8px;
                margin: 0 4px 0 4px;
                border-radius: 4px;
            }}
            QScrollBar::handle:horizontal {{
                background: #D6D6D6;
                min-width: 30px;
                border-radius: 4px;
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: none;
            }}
        """,
        # 任务标签上的按钮样式
        "task_label_button": """  
            QPushButton {{
                background-color: #ECECEC;  /* 按钮背景色 */
                border: 1px solid rgba(100, 100, 100, 0.5); /* 半透明边框 */
                border-radius: 6px;         /* 圆角 */
                padding: 4px 8px;           /* 内边距 */
                font-family: '微软雅黑';      /* 字体 */
                font-size: 12px;            /* 字号 */
                color: #333;                /* 文字颜色 */
            }}
            QPushButton:hover {{
                background-color: #D6D6D6;  /* 悬停时背景色 */
            }}""",

        # 添加任务对话框样式
        "add_task_dialog": """
            QWidget#panel {{
            background-color: white;        /* 面板背景色 */
            border-radius: 15px;            /* 圆角 */
        }}
        QLabel {{
            color: #333333;                 /* 文字颜色 */
            font-family: '微软雅黑';          /* 字体 */
            font-weight: bold;              /* 加粗 */
            font-size: 14px;                /* 字号 */
        }}
        QLineEdit, QTextEdit {{
            background-color: #f5f5f5;      /* 输入框背景色 */
            color: #333333;                 /* 文字颜色 */
            border: 1px solid #dddddd;      /* 边框 */
            border-radius: 8px;             /* 圆角 */
            padding: 12px;                  /* 内边距 */
            font-family: '微软雅黑';          /* 字体 */
            font-size: 13px;                /* 字号 */
        }}
        QDateEdit {{
            background-color: #f5f5f5;      /* 日期编辑背景色 */
            color: #333333;                 /* 文字颜色 */
            border: 1px solid #dddddd;      /* 边框 */
            border-radius: 8px;             /* 圆角 */
            padding: 12px;                  /* 内边距 */
            font-family: '微软雅黑';          /* 字体 */
            font-size: 13px;                /* 字号 */
            min-height: 20px;               /* 最小高度 */
        }}
        QPushButton {{
            background-color: #4ECDC4;      /* 按钮背景色 */
            color: white;                   /* 文字颜色 */
            border: none;                   /* 无边框 */
            border-radius: 8px;             /* 圆角 */
            padding: 10px 20px;             /* 内边距 */
            font-family: '微软雅黑';          /* 字体 */
            font-weight: bold;              /* 加粗 */
        }}
        QPushButton:hover {{background-color: #45B8B0; }} /* 悬停时按钮色 */
        QComboBox {{
            background-color: #f5f5f5;      /* 下拉框背景色 */
            color: #333333;                 /* 文字颜色 */
            border: 1px solid #dddddd;      /* 边框 */
            border-radius: 8px;             /* 圆角 */
            padding: 10px;                  /* 内边距 */
            font-family: '微软雅黑';          /* 字体 */
            font-size: 13px;                /* 字号 */
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;     /* 下拉按钮位置 */
            subcontrol-position: top right;
            width: 30px;                    /* 下拉按钮宽度 */
            border-left: 1px solid #dddddd; /* 左边框 */
            background-color: #f5f5f5;      /* 下拉按钮背景色 */
        }}
        QComboBox::down-arrow {{
            image: url(./icons/down_arrow.png); /* 下拉箭头图片 */
            width: 20px;
            height: 20px;
        }}
        QComboBox QAbstractItemView {{
            background-color: #f5f5f5;      /* 下拉列表背景色 */
            border: 1px solid #dddddd;      /* 边框 */
            selection-background-color: #4ECDC4; /* 选中时的背景色 */
            selection-color: white;              /* 选中时文字白色 */
            padding: 5px;                   /* 内边距 */
            outline: 0px;                   /* 无外边框 */
            font-family: '微软雅黑';          /* 字体 */
            font-size: 13px;                /* 字号 */
            border-radius: 8px;             /* 下拉列表本身也有圆角 */
        }}
            """,
        # 四象限主窗口样式
        "quadrant_widget": """
            QWidget {{
                background-color: #F8F9FA;      /* 主窗口背景色 */
                border: 1px solid #E0E0E0;      /* 边框 */
                border-radius: 8px;             /* 圆角 */
            }}
            QLabel {{
                background-color: #FFFFFF;       /* 标签背景色 */
                border: 1px solid #E0E0E0;      /* 边框 */
                border-radius: 6px;             /* 圆角 */
                padding: 6px 10px;              /* 内边距 */
                margin: 2px;                    /* 外边距 */
                font-family: '微软雅黑';          /* 字体 */
                font-size: 11px;                /* 字号 */
                color: #333333;                 /* 文字颜色 */
            }}
        """,
        # 控制面板样式
        "control_panel": """
            QWidget {{
                background-color: rgba(40, 40, 40, 0.7);   /* 控制面板背景色，带透明度 */
                border-radius: 15px;                       /* 圆角 */
                padding: 5px;                              /* 内边距 */
            }}
            QPushButton {{
                background-color: rgba(60, 60, 60, 0.8);   /* 按钮背景色 */
                color: white;                              /* 文字颜色 */
                border: none;                              /* 无边框 */
                border-radius: 8px;                        /* 圆角 */
                padding: 8px 15px;                         /* 内边距 */
                font-family: '微软雅黑';                    /* 字体 */
                font-weight: bold;                         /* 加粗 */
            }}
            QPushButton:hover {{
                background-color: rgba(80, 80, 80, 0.9);   /* 悬停时按钮色 */
            }}
            QPushButton:pressed {{
                background-color: rgba(100, 100, 100, 1.0);/* 按下时按钮色 */
            }}
            """,
        # 设置面板样式
        "settings_panel": """
            QDialog {{
                background-color: white;
                border-radius: 15px;
                border: 1px solid #e0e0e0;
            }}
            QTabWidget::pane {{
                border: 1px solid #e0e0e0;
                background-color: white;
                border-radius: 8px;
            }}
            QTabBar::tab {{
                background-color: #f5f5f5;
                color: #505050;
                border: 1px solid #e0e0e0;
                border-bottom: none;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-family: '微软雅黑';
            }}
            QTabBar::tab:selected {{
                background-color: white;
                color: #4ECDC4;
                font-weight: bold;
            }}
            QLabel {{
                color: #505050;
                font-family: '微软雅黑';
                font-size: 13px;
            }}
            QSpinBox {{
                background-color: #f5f5f5;
                color: #505050;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                padding: 8px;
                min-height: 24px;
            }}
            QSlider::groove:horizontal {{
                height: 8px;
                background: #e0e0e0;
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: #4ECDC4;
                width: 16px;
                height: 16px;
                margin: -4px 0;
                border-radius: 8px;
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
            QPushButton:hover {{
                background-color: #45B8B0;
            }}
            QCheckBox {{
                color: #505050;
                font-family: '微软雅黑';
                padding: 5px;
            }}
        """,
        # 历史记录表格美化样式
        "history_table": """
            QTableWidget {
                background: transparent;
                border: none;
                border-radius: 10px;
                font-family: '微软雅黑', 'Microsoft YaHei', sans-serif;
                font-size: 13px;
                color: #333;
                gridline-color: #F0F0F0;
            }
            QTableWidget::item {
                border: none;
                padding: 8px 6px;
                background: transparent;
            }
            QHeaderView::section {
                background: transparent;
                color: #666;
                border: none;
                font-weight: bold;
                font-size: 13px;
                padding: 8px 0;
            }
            QTableCornerButton::section {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                margin: 4px 2px 4px 0;
                border-radius: 4px;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: #D6D6D6;
                min-height: 30px;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
            QScrollBar:horizontal {
                background: transparent;
                height: 8px;
                margin: 0 4px 0 4px;
                border-radius: 4px;
            }
            QScrollBar::handle:horizontal {
                background: #D6D6D6;
                min-width: 30px;
                border-radius: 4px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
            QScrollArea, QFrame, QWidget {
                border: none;
                background: transparent;
            }
        """
        }

    def get_stylesheet(self, component_name):
        """获取指定组件的样式表"""
        return self.stylesheets.get(component_name, "")
    
    def set_stylesheet(self, component_name, stylesheet):
        """设置指定组件的样式表"""
        self.stylesheets[component_name] = stylesheet
    
    def add_component_style(self, component_name, stylesheet):
        """添加新组件的样式"""
        self.stylesheets[component_name] = stylesheet
    
    def remove_component_style(self, component_name):
        """移除组件的样式"""
        if component_name in self.stylesheets:
            del self.stylesheets[component_name]


class MyColorDialog(QColorDialog):
    """自定义颜色对话框"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_custom_style()
    
    def _apply_custom_style(self):
        """应用自定义样式"""
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
    """警告弹窗"""
    def __init__(self, parent=None, message=""):
        super().__init__(parent)
        self._setup_ui(message)
        self._apply_style()
    
    def _setup_ui(self, message):
        """设置UI"""
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
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
    
    def _apply_style(self):
        """应用样式"""
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