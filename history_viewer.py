from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QTableWidget, QTableWidgetItem, QPushButton, 
                            QHeaderView, QFrame, QScrollArea, QWidget,
                            QAbstractScrollArea)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QFont
from datetime import datetime
import json
import os

from styles import StyleManager
import logging
logger = logging.getLogger(__name__)

class HistoryViewer(QDialog):
    """历史记录查看器"""
    def __init__(self, task_data, parent=None):
        super().__init__(parent)
        self.task_data = task_data
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("任务历史记录")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.adjustSize()
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(0)
        
        # 样式管理器
        style_manager = StyleManager()
        
        # 创建主面板
        panel = QWidget(self)
        panel.setObjectName("panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(20,20,20,20)
        panel_layout.setSpacing(15)
        
        # 样式表
        panel.setStyleSheet(style_manager.get_stylesheet("add_task_dialog").format())
        
        # 任务基本信息
        if self.task_data.get('text'):
            text_label = QLabel(f" {self.task_data.get('text', '没有详细内容喵~')}修改记录")
            text_label.setStyleSheet("font-size: 12px; color: #666; border: none; background: transparent;")
            text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            panel_layout.addWidget(text_label)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("""
            background: #F0F0F0;
            border-radius: 12px;
        """)
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(5)
        
        # 加载历史记录
        self.load_history_records(scroll_layout)
        
        scroll_area.setWidget(scroll_content)
        panel_layout.addWidget(scroll_area)
        
        # 关闭和导出按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 导出按钮
        export_button = QPushButton("导出")
        export_button.setStyleSheet(style_manager.get_stylesheet("task_label_button"))
        export_button.setFixedHeight(35)
        export_button.clicked.connect(self.export_history)
        button_layout.addWidget(export_button)
        
        # 关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.close)
        close_button.setStyleSheet(style_manager.get_stylesheet("task_label_button"))
        close_button.setFixedHeight(35)
        button_layout.addWidget(close_button)
        
        panel_layout.addLayout(button_layout)
        
        main_layout.addWidget(panel)
        
        # 居中显示
        self.adjustSize()
        self.center_on_parent()
        
    def load_history_records(self, layout):
        """加载历史记录并合并显示到一个表格"""
        tasks_file = 'tasks.json'
        if not os.path.exists(tasks_file):
            layout.addWidget(QLabel("未找到历史记录数据"))
            return

        try:
            with open(tasks_file, 'r', encoding='utf-8') as f:
                all_tasks = json.load(f)

            # 找到对应的任务
            task_id = self.task_data.get('id')
            target_task = None
            for task in all_tasks:
                if task.get('id') == task_id:
                    target_task = task
                    break

            if not target_task:
                layout.addWidget(QLabel("未找到该任务的历史记录"))
                return

            # 合并所有字段的历史记录
            from config_manager import load_config
            config = load_config()
            field_names = [f['name'] for f in config.get('task_fields', [])]

            merged_history = []
            for field_name in field_names:
                history_key = f'{field_name}_history'
                if history_key in target_task and target_task[history_key]:
                    for record in target_task[history_key]:
                        merged_history.append({
                            'field': field_name,
                            'timestamp': record.get('timestamp', ''),
                            'action': record.get('action', 'update'),
                            'value': record.get('value', '')
                        })

            # 按时间排序（可选）
            merged_history.sort(key=lambda x: x['timestamp'])

            # 创建合并表格
            self.create_merged_history_table(layout, merged_history)

        except Exception as e:
            logger.error(f"加载历史记录失败: {str(e)}")
            layout.addWidget(QLabel(f"加载历史记录失败: {str(e)}"))

    def create_merged_history_table(self, layout, merged_history):
        """创建合并后的历史记录表格"""
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["时间", "字段", "操作", "值"])
        table.setRowCount(len(merged_history))

        for row, record in enumerate(merged_history):
            # 时间
            timestamp = record['timestamp']
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    time_str = timestamp
            else:
                time_str = 'N/A'
            time_item = QTableWidgetItem(time_str)
            time_item.setFlags(time_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 0, time_item)

            # 字段
            field_item = QTableWidgetItem(record['field'])
            field_item.setFlags(field_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 1, field_item)

            # 操作
            action = record['action']
            action_text = "创建" if action == 'create' else "更新"
            action_item = QTableWidgetItem(action_text)
            action_item.setFlags(action_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 2, action_item)

            # 值
            value_item = QTableWidgetItem(str(record['value']))
            value_item.setFlags(value_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 3, value_item)

        # 调整列宽
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # 关键：不要用 Stretch

        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)

        table.setMaximumHeight(400)
        # 应用美化样式
        style_manager = StyleManager()
        table.setStyleSheet(style_manager.get_stylesheet("history_table"))
        layout.addWidget(table)
    
    def center_on_parent(self):
        """居中显示窗口"""
        if self.parent():
            parent_rect = self.parent().geometry()
            x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
            y = parent_rect.y() + (parent_rect.height() - self.height()) // 2
            self.move(x, y)
        else:
            # 如果没有父窗口，居中到屏幕
            from PyQt6.QtWidgets import QApplication
            screen = QApplication.primaryScreen()
            screen_geometry = screen.availableGeometry()
            x = screen_geometry.center().x() - self.width() // 2
            y = screen_geometry.center().y() - self.height() // 2
            self.move(x, y) 

    def export_history(self):
        """导出历史记录为Excel或CSV文件"""
        try:
            import pandas as pd
        except ImportError:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "导出失败", "未安装pandas库，无法导出为Excel/CSV。请先安装pandas。\n\n安装命令：pip install pandas openpyxl")
            return
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        # 重新生成 merged_history
        from config_manager import load_config
        config = load_config()
        field_names = [f['name'] for f in config.get('task_fields', [])]
        merged_history = []
        # 读取 tasks.json
        import os, json
        tasks_file = 'tasks.json'
        if not os.path.exists(tasks_file):
            QMessageBox.critical(self, "导出失败", "未找到历史记录数据")
            return
        with open(tasks_file, 'r', encoding='utf-8') as f:
            all_tasks = json.load(f)
        task_id = self.task_data.get('id')
        target_task = None
        for task in all_tasks:
            if task.get('id') == task_id:
                target_task = task
                break
        if not target_task:
            QMessageBox.critical(self, "导出失败", "未找到该任务的历史记录")
            return
        for field_name in field_names:
            history_key = f'{field_name}_history'
            if history_key in target_task and target_task[history_key]:
                for record in target_task[history_key]:
                    merged_history.append({
                        '时间': record.get('timestamp', ''),
                        '字段': field_name,
                        '操作': '创建' if record.get('action', 'update') == 'create' else '更新',
                        '值': record.get('value', '')
                    })
        if not merged_history:
            QMessageBox.information(self, "导出历史记录", "没有历史记录可导出")
            return
        # 选择文件保存路径
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        default_filename = os.path.join(desktop_path, "任务历史记录.xlsx")
        filename, filetype = QFileDialog.getSaveFileName(
            self,
            "导出历史记录",
            default_filename,
            "Excel文件 (*.xlsx);;CSV文件 (*.csv);;所有文件 (*)"
        )
        if not filename:
            return
        try:
            df = pd.DataFrame(merged_history)
            if filetype.startswith("Excel") or filename.endswith(".xlsx"):
                df.to_excel(filename, index=False)
            elif filetype.startswith("CSV") or filename.endswith(".csv"):
                df.to_csv(filename, index=False, encoding='utf-8-sig')
            else:
                # 默认Excel
                df.to_excel(filename, index=False)
            QMessageBox.information(self, "导出成功", f"成功导出历史记录到:\n{filename}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出历史记录时发生错误:\n{str(e)}") 