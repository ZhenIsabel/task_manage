from datetime import datetime
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                            QTableWidgetItem, QPushButton, QCheckBox, QHeaderView,
                            QLabel, QMessageBox, QAbstractItemView)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from ui.styles import StyleManager
from ui.ui import apply_drop_shadow
from database.database_manager import get_db_manager
import logging

logger = logging.getLogger(__name__)

class CompleteTableDialog(QDialog):
    """已完成任务表格对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.db_manager = get_db_manager()
        self.selected_tasks = set()  # 存储选中的任务ID
        
        self._setup_ui()
        self._load_completed_tasks()
        
    def _setup_ui(self):
        """设置UI界面"""
        # 设置对话框属性
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setWindowTitle("已完成任务")
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建白色圆角面板
        from PyQt6.QtWidgets import QWidget
        self.panel = QWidget()
        self.panel.setObjectName("panel")
        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(20, 20, 20, 20)
        panel_layout.setSpacing(15)
        
        # 应用样式
        style_manager = StyleManager()
        self.panel.setStyleSheet(style_manager.get_stylesheet("add_task_dialog").format())
        
        # 添加阴影效果
        apply_drop_shadow(self.panel, blur_radius=8, color=QColor(0, 0, 0, 60))
        
        # 标题
        title_label = QLabel("已完成任务")
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #333;
            padding: 10px 0;
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(title_label)
        
        # 创建表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["选择", "任务内容", "完成日期", "优先级", "备注"])
        
        # 设置表格属性
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        # 设置列宽
        self.table.setColumnWidth(0, 60)  # 选择列
        
        # 设置表格样式
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 8px;
                background-color: white;
                gridline-color: #eee;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 10px;
                border: none;
                border-right: 1px solid #ddd;
                font-weight: bold;
                color: #333;
            }
            QHeaderView::section:first {
                border-top-left-radius: 8px;
            }
            QHeaderView::section:last {
                border-top-right-radius: 8px;
                border-right: none;
            }
        """)
        
        panel_layout.addWidget(self.table)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        # 全选/取消全选按钮
        self.select_all_button = QPushButton("全选")
        self.select_all_button.clicked.connect(self.toggle_select_all)
        self.select_all_button.setStyleSheet("""
            QPushButton {
                background-color: #4ECDC4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45b7b8;
            }
        """)
        
        # 还原按钮
        self.restore_button = QPushButton("还原选中任务")
        self.restore_button.clicked.connect(self.restore_selected_tasks)
        self.restore_button.setEnabled(False)
        self.restore_button.setStyleSheet("""
            QPushButton {
                background-color: #FF6B6B;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff5252;
            }
            QPushButton:disabled {
                background-color: #ccc;
                color: #666;
            }
        """)
        
        # 关闭按钮
        self.close_button = QPushButton("关闭")
        self.close_button.clicked.connect(self.accept)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: #95a5a6;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7f8c8d;
            }
        """)
        
        button_layout.addWidget(self.select_all_button)
        button_layout.addStretch()
        button_layout.addWidget(self.restore_button)
        button_layout.addWidget(self.close_button)
        
        panel_layout.addLayout(button_layout)
        
        # 将面板添加到主布局
        main_layout.addWidget(self.panel)
        
        # 设置对话框大小和位置
        self.resize(800, 600)
        if self.parent_widget:
            # 在父窗口中央显示
            parent_rect = self.parent_widget.geometry()
            x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
            y = parent_rect.y() + (parent_rect.height() - self.height()) // 2
            self.move(x, y)
    
    def _load_completed_tasks(self):
        """加载已完成的任务"""
        try:
            # 从数据库获取所有任务
            all_tasks = self.db_manager.load_tasks(all_tasks=True)
            
            # 筛选出已完成的任务
            completed_tasks = [task for task in all_tasks if task.get('completed', False)]
            
            # 按完成日期倒序排列
            completed_tasks.sort(key=lambda t: t.get('completed_date', ''), reverse=True)
            
            # 设置表格行数
            self.table.setRowCount(len(completed_tasks))
            
            # 填充表格数据
            for row, task in enumerate(completed_tasks):
                # 选择复选框
                checkbox = QCheckBox()
                checkbox.stateChanged.connect(self.on_selection_changed)
                checkbox.setProperty('task_id', task['id'])
                self.table.setCellWidget(row, 0, checkbox)
                
                # 任务内容
                text_item = QTableWidgetItem(task.get('text', ''))
                text_item.setFlags(text_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 1, text_item)
                
                # 完成日期
                completed_date = task.get('completed_date', '')
                date_item = QTableWidgetItem(completed_date)
                date_item.setFlags(date_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 2, date_item)
                
                # 优先级
                priority = task.get('priority', '')
                priority_item = QTableWidgetItem(priority)
                priority_item.setFlags(priority_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 3, priority_item)
                
                # 备注
                notes = task.get('notes', '')
                notes_item = QTableWidgetItem(notes)
                notes_item.setFlags(notes_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 4, notes_item)
            
            logger.info(f"加载了 {len(completed_tasks)} 个已完成任务")
            
            # 如果没有已完成任务，显示提示
            if not completed_tasks:
                self.table.setRowCount(1)
                no_data_item = QTableWidgetItem("暂无已完成任务")
                no_data_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                no_data_item.setFlags(no_data_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(0, 1, no_data_item)
                self.table.setSpan(0, 1, 1, 4)  # 合并单元格
                
        except Exception as e:
            logger.error(f"加载已完成任务失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"加载已完成任务失败: {str(e)}")
    
    def on_selection_changed(self):
        """选择状态改变时的回调"""
        # 重新计算选中的任务
        self.selected_tasks.clear()
        
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                task_id = checkbox.property('task_id')
                if task_id:
                    self.selected_tasks.add(task_id)
        
        # 更新还原按钮状态
        self.restore_button.setEnabled(len(self.selected_tasks) > 0)
        
        # 更新全选按钮文本
        total_checkboxes = self.table.rowCount()
        checked_count = len(self.selected_tasks)
        
        if checked_count == 0:
            self.select_all_button.setText("全选")
        elif checked_count == total_checkboxes:
            self.select_all_button.setText("取消全选")
        else:
            self.select_all_button.setText(f"全选 ({checked_count}/{total_checkboxes})")
    
    def toggle_select_all(self):
        """切换全选状态"""
        # 检查是否所有项都已选中
        all_selected = len(self.selected_tasks) == self.table.rowCount()
        
        # 设置所有复选框状态
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(not all_selected)
    
    def restore_selected_tasks(self):
        """还原选中的任务"""
        if not self.selected_tasks:
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self, 
            "确认还原", 
            f"确定要将 {len(self.selected_tasks)} 个任务还原为未完成状态吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            restored_count = 0
            
            # 遍历选中的任务进行还原
            for task_id in self.selected_tasks:
                # 从数据库缓存中找到任务
                with self.db_manager._cache_lock:
                    if task_id in self.db_manager._task_cache:
                        task = self.db_manager._task_cache[task_id]
                        # 更新任务状态
                        task['completed'] = False
                        task['completed_date'] = ''
                        task['updated_at'] = datetime.now().isoformat()
                        task['sync_status'] = 'modified'
                        
                        self.db_manager._cache_dirty = True
                        restored_count += 1
                        logger.info(f"还原任务: {task_id}")
            
            if restored_count > 0:
                # 强制写入数据库
                self.db_manager.flush_cache_to_db()
                
                QMessageBox.information(
                    self, 
                    "还原成功", 
                    f"成功还原 {restored_count} 个任务为未完成状态"
                )
                
                # 刷新表格
                self._load_completed_tasks()
                self.selected_tasks.clear()
                self.restore_button.setEnabled(False)
                self.select_all_button.setText("全选")
                
                # 通知父窗口刷新任务列表
                if hasattr(self.parent_widget, 'load_tasks'):
                    self.parent_widget.load_tasks()
                    
            else:
                QMessageBox.warning(self, "还原失败", "没有找到要还原的任务")
                
        except Exception as e:
            logger.error(f"还原任务失败: {str(e)}")
            QMessageBox.critical(self, "还原失败", f"还原任务时发生错误: {str(e)}")
    
    def mousePressEvent(self, event):
        """鼠标按下事件，用于拖动窗口"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件，用于拖动窗口"""
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, '_drag_position'):
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
