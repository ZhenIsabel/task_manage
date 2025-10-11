# 样式集中管理：不包含任何 UI 控件类


# ===== 基础样式模板 =====
BASE_SCROLLBAR_STYLE = """
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 2px 1px 2px 0;
    border-radius: 3px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: #D6D6D6;
    min-height: 20px;
    border-radius: 3px;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
    margin: 0 2px 0 2px;
    border-radius: 3px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: #D6D6D6;
    min-width: 20px;
    border-radius: 3px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}
"""


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
        """,
            # 到期任务标签样式（带橙色描边）
            "task_label_overdue": """
            QWidget {{
                background: transparent;  /* 透明背景 */
                border-radius: 10px;      /* 圆角 */
                
            }}
            QLabel {{
                background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba({bg_color_red}, {bg_color_green}, {bg_color_blue}, 217),
        stop:0.5 rgba({bg_color_red}, {bg_color_green}, {bg_color_blue}, 217),
        stop:0.51 rgba(255, 165, 0, 0.8),
        stop:1 rgba(255, 165, 0, 0.8)
    );
    color: rgb({text_color_red}, {text_color_green}, {text_color_blue});
    font-weight: bold;
    font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
    padding: 2px 8px;
    border-radius: 10px;
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
            color: #333;
            font-family: '微软雅黑';
            font-size: 13px;
            font-weight: normal;
            background: transparent;
            padding: 2px 0 2px 2px;
            margin: 0;
            border: none;
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
            color: #333;                 /* 文字颜色 */
            border: 1.5px solid #dddddd;      /* 边框 */
            padding: 8px 12px;                  /* 内边距 */
            font-family: '微软雅黑';          /* 字体 */
            font-size: 14px;                /* 字号 */
            min-height: 28px;               /* 最小高度 */
            selection-background-color: #dddddd;
            selection-color: white;
            outline: none;
        }}
        QDateEdit::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 28px;
            border-left: 1px solid #dddddd;
            background: #f5f5f5;
        }}
        QDateEdit::down-arrow {{
            image: url(./icons/down_arrow.png);
            width: 18px;
            height: 18px;
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
        QCalendarWidget {{
            background: #f8f8f8;
            border: 1.5px solid #4ECDC4;
            font-family: '微软雅黑';
            font-size: 14px;
            color: #333;
        }}
        QCalendarWidget QWidget#qt_calendar_navigationbar {{
            background: #f8f8f8;
        }}
        QCalendarWidget QToolButton {{
            background: transparent;
            color: #4ECDC4;
            font-weight: bold;
            font-size: 15px;
            border: none;
            padding: 2px 8px;
        }}
        QCalendarWidget QToolButton::menu-indicator {{
            image: none;
        }}
        QCalendarWidget QToolButton:hover {{
            color: #45B8B0;
        }}
        QCalendarWidget QMenu {{
            background: #fff;
            border: 1px solid #4ECDC4;
        }}
        QCalendarWidget QSpinBox {{
            background: #f5f5f5;
            border: 1px solid #4ECDC4;
            font-size: 13px;
            padding: 2px 6px;
        }}
        QCalendarWidget QSpinBox::up-button, QCalendarWidget QSpinBox::down-button {{
            width: 12px;
            height: 12px;
        }}
        QCalendarWidget QAbstractItemView {{
            outline: none;
            selection-background-color: #4ECDC4;
            selection-color: white;
            font-size: 14px;
            background: #fff;
        }}
        QCalendarWidget QHeaderView {{
            background: #f8f8f8;
        }}
        QCalendarWidget QHeaderView::section {{
            background: #f8f8f8;
            color: #4ECDC4;
            font-weight: bold;
            border: none;
            font-size: 13px;
            padding: 2px 0;
        }}
        """ + BASE_SCROLLBAR_STYLE,
        # 通用菜单样式
        "menu": """
            QMenu {{
                background-color: #ffffff;
                border-radius: 10px;
                padding: 6px 0;
                min-width: 60px;
                font-family: "微软雅黑";
                font-size: 14px;
                color: #333333;
            }}
            QMenu::item {{
                background: transparent;
                padding: 8px 8px 8px 8px;
                border-radius: 6px;
                margin: 2px 8px;
                color: #333333;
            }}
            QMenu::item:selected {{
                background-color: #4ECDC4;
                color: #fff;
            }}
            QMenu::separator {{
                height: 1px;
                background: #e0e0e0;
                margin: 4px 0;
            }}
        """ + BASE_SCROLLBAR_STYLE,
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
        """ + BASE_SCROLLBAR_STYLE,
        # 控制面板样式
        "control_panel": """
            #control_panel {
                background-color: rgba(40, 40, 40, 0.7);   /* 控制面板背景色，带透明度 */
                border-radius: 15px;                       /* 圆角 */
                padding: 5px;                              /* 内边距 */
            }
            #control_panel QPushButton {
                background-color: rgba(60, 60, 60, 0.8);   /* 按钮背景色 */
                color: white;                              /* 文字颜色 */
                border: none;                              /* 无边框 */
                border-radius: 8px;                        /* 圆角 */
                padding: 8px 15px;                         /* 内边距 */
                font-family: '微软雅黑';                    /* 字体 */
                font-weight: bold;                         /* 加粗 */
            }
            #control_panel QPushButton:hover {
                background-color: rgba(80, 80, 80, 0.9);   /* 悬停时按钮色 */
            }
            #control_panel QPushButton:pressed {
                background-color: rgba(100, 100, 100, 1.0);/* 按下时按钮色 */
            }
            #control_panel QMenu {
                background-color: #ffffff;
                border-radius: 10px;
                padding: 6px 0;
                min-width: 60px;
                font-family: "微软雅黑";
                font-size: 14px;
                color: #333333;
            }
            #control_panel QMenu::item {
                background: transparent;
                padding: 8px 8px 8px 8px;
                border-radius: 6px;
                margin: 2px 8px;
                color: #333333;
            }
            #control_panel QMenu::item:selected {
                background-color: #4ECDC4;
                color: #fff;
            }
            #control_panel QMenu::separator {
                height: 1px;
                background: #e0e0e0;
                margin: 4px 0;
            }
            """ + BASE_SCROLLBAR_STYLE,
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
        """ + BASE_SCROLLBAR_STYLE,
        # 历史记录表格美化样式
        "history_table": """
            QTableWidget {{
                border: 1px solid #ddd;
                border-radius: 8px;
                background-color: white;
                gridline-color: #eee;
            }}
            QTableWidget::item {{
                border: none;
                padding: 8px;
            }}
            QTableWidget::item:selected {{
                background-color: #4ECDC4;
            }}
            QHeaderView::section {{
                background-color: white;
                padding: 5px;
                border: none;
                border-right: 1px solid #ddd;
                font-weight: bold;
                color: #333;
                gridline-color: #eee;
            }}
            """ + BASE_SCROLLBAR_STYLE,
        # 通用：小号灰色标签
        "label_small_muted": """
            QLabel {{
                font-size: 12px;
                color: #666;
                border: none;
                background: transparent;
            }}
        """,
        # 通用：透明滚动区域
        "scroll_area_transparent": """
            QScrollArea {{ border: none; background: transparent; }}
        """,
        # 通用：浅灰圆角容器
        "scroll_content_panel": """
            QWidget {{background: #F0F0F0; border-radius: 12px; }}
        """,
        # 详情标题标签
        "detail_title_label": """
            QLabel {{ font-size: 14px; font-weight: bold; color: black; }}
        """,
        # 到期日期标签
        "due_date_label": """
            QLabel {{ font-size: 10px; }}
        """,
        # 颜色按钮（详细弹窗内）
        "color_button": """
            QPushButton {{
                background-color: {button_color};
                border: 2px solid #bbb;
                border-radius: 6px;
                margin: 0 2px;
            }}
            QPushButton:hover {{
                border: 2px solid #4ECDC4;
            }}
        """,
        # 颜色色块（设置页）
        "color_chip": """
            QPushButton {{
                background-color: {button_color};
                border-radius: 15px;
                border: 1px solid #ddd;
            }}
        """,
        # 删除确认对话框样式
        "delete_confirm_dialog": """
            QWidget#panel {
                background-color: white;        /* 面板背景色 */
                border-radius: 15px;            /* 圆角 */
            }
            QDialog {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #e0e0e0;
            }
            QLabel#title_label {
                background-color: transparent;
                color: #333333;
                font-family: '微软雅黑';
                font-size: 16px;
                font-weight: bold;
                margin-bottom: 10px;
            }
            QLabel#message_label {
                background-color: transparent;
                color: #666666;
                font-family: '微软雅黑';
                font-size: 14px;
                line-height: 1.4;
                margin: 10px 0;
            }
            QPushButton#cancel_button {
                background-color: #f5f5f5;
                color: #666666;
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                font-family: '微软雅黑';
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#cancel_button:hover {
                background-color: #e8e8e8;
                border-color: #c0c0c0;
            }
            QPushButton#cancel_button:pressed {
                background-color: #d8d8d8;
            }
            QPushButton#delete_button {
                background-color: #ff4757;
                color: white;
                border: 1px solid #ff3742;
                border-radius: 8px;
                font-family: '微软雅黑';
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#delete_button:hover {
                background-color: #ff3742;
                border-color: #ff2f3a;
            }
            QPushButton#delete_button:pressed {
                background-color: #e63946;
                border-color: #d63031;
            }
        """,
        # 警告弹窗样式
        "warning_popup": """
            QWidget#panel {
                background-color: white;        /* 面板背景色 */
                border-radius: 15px;            /* 圆角 */
            }
            QDialog {
                background-color: #ECECEC;
                border-radius: 10px;
            }
            QLabel {
                background-color: transparent;
                color: #333;
                font-family: '微软雅黑';
                font-size: 14px;
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
        """,
        # 颜色对话框样式
        "color_dialog": """
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
        