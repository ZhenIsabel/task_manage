from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QTableWidget, QTableWidgetItem, QPushButton, 
                            QHeaderView, QAbstractItemView, QWidget,
                            QAbstractScrollArea)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QFont
from datetime import datetime

from ui.styles import StyleManager
from ui.ui import apply_drop_shadow
from database.database_manager import get_db_manager
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
        panel.setMaximumWidth(600)
        
        # 样式表
        panel.setStyleSheet(style_manager.get_stylesheet("add_task_dialog").format())
        
        # 任务基本信息
        if self.task_data.get('text'):
            text_label = QLabel(f" {self.task_data.get('text', '没有详细内容喵~')}修改记录")
            text_label.setStyleSheet(style_manager.get_stylesheet("label_small_muted"))
            text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            panel_layout.addWidget(text_label)
        
        # 加载历史记录
        self.load_history_records(panel_layout)
        
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
        # 添加阴影
        apply_drop_shadow(panel, blur_radius=10, color=QColor(0, 0, 0, 60), offset_x=0, offset_y=0)
        
    def load_history_records(self, layout):
        """从数据库加载历史记录并合并显示到一个表格"""
        try:
            # 从数据库获取历史记录
            task_id = self.task_data.get('id')
            if not task_id:
                layout.addWidget(QLabel("未找到任务ID"))
                return
            
            db_manager = get_db_manager()
            field_history = db_manager.get_task_history(task_id)
            
            if not field_history:
                layout.addWidget(QLabel("未找到该任务的历史记录"))
                return

            # 字段名称映射
            field_name_map = {
                'text': '任务内容',
                'notes': '备注',
                'due_date': '到期日期',
                'priority': '优先级',
                'directory': '目录',
                'create_date': '创建日期'
            }

            # 合并所有字段的历史记录
            merged_history = []
            for field_name, history_list in field_history.items():
                # 使用友好的字段名称
                display_name = field_name_map.get(field_name, field_name)
                for record in history_list:
                    merged_history.append({
                        'field': display_name,
                        'timestamp': record.get('timestamp', ''),
                        'action': record.get('action', 'update'),
                        'value': record.get('value', '')
                    })

            # 按时间排序
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

        # 按内容自动调整列宽
        header = table.horizontalHeader()
        for i in range(table.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

        # 不拉伸最后一列
        header.setStretchLastSection(False)
        # 启用自动换行
        table.setWordWrap(True)
        # 按内容调整行高
        table.resizeRowsToContents()
        # 关闭省略策略：
        table.setTextElideMode(Qt.TextElideMode.ElideNone)
        table.horizontalHeader().setTextElideMode(Qt.TextElideMode.ElideNone)
        # 允许滚动
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        # 按行选择
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        table.setMaximumHeight(400)
        # 应用美化样式
        style_manager = StyleManager()
        table.setStyleSheet(style_manager.get_stylesheet("history_table").format())
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
        import os
        
        # 从数据库获取历史记录
        task_id = self.task_data.get('id')
        if not task_id:
            QMessageBox.critical(self, "导出失败", "未找到任务ID")
            return
        
        try:
            db_manager = get_db_manager()
            field_history = db_manager.get_task_history(task_id)
            
            if not field_history:
                QMessageBox.information(self, "导出历史记录", "没有历史记录可导出")
                return
            
            # 合并所有字段的历史记录
            merged_history = []
            
            # 字段名称映射
            field_name_map = {
                'text': '任务内容',
                'notes': '备注',
                'due_date': '到期日期',
                'priority': '优先级',
                'directory': '目录',
                'create_date': '创建日期'
            }
            
            for field_name, history_list in field_history.items():
                # 使用友好的字段名称
                display_name = field_name_map.get(field_name, field_name)
                for record in history_list:
                    merged_history.append({
                        '时间': record.get('timestamp', ''),
                        '字段': display_name,
                        '操作': '创建' if record.get('action', 'update') == 'create' else '更新',
                        '值': record.get('value', '')
                    })
            
            if not merged_history:
                QMessageBox.information(self, "导出历史记录", "没有历史记录可导出")
                return
            
            # 按时间排序
            merged_history.sort(key=lambda x: x['时间'])
            
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
                
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"获取历史记录时发生错误:\n{str(e)}") 