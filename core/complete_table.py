from datetime import datetime
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,QMessageBox,
                            QPushButton, QCheckBox, QHeaderView,
                            QLabel, QLineEdit)
from PyQt6.QtCore import Qt, QTimer
from ui.adaptive_table import AdaptiveTextTableWidget
from ui.notifications import show_error, show_success
from ui.styles import StyleManager, apply_button_role
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
        self.completed_tasks = []
        self.page_size = 50
        self.loaded_count = 0
        self.total_count = 0
        self.selection_total_count_override = None
        self.current_search_query = ""
        self.search_debounce_timer = QTimer(self)
        self.search_debounce_timer.setSingleShot(True)
        self.search_debounce_timer.setInterval(500)
        self.search_debounce_timer.timeout.connect(self._apply_completed_task_filter)
        
        self._setup_ui()
        self._load_completed_tasks()
        
    def _setup_ui(self):
        """设置UI界面"""
        # 设置对话框属性
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        # 不再使用透明背景，避免弹窗外侧出现可透底的透明区域
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        parent_widget = self.parent()
        border_radius = 15
        if parent_widget and hasattr(parent_widget, "config"):
            border_radius = parent_widget.config.get("ui", {}).get("border_radius", 15)
        self.setStyleSheet(f"QDialog {{ background-color: white; border-radius: {border_radius}px; }}")
        self.setModal(True)
        self.setWindowTitle("已完成任务")
        
        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建白色圆角面板
        from PyQt6.QtWidgets import QWidget
        self.panel = QWidget()
        self.panel.setObjectName("dialog_panel")
        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(20, 20, 20, 20)
        panel_layout.setSpacing(15)
        
        # 应用样式
        style_manager = StyleManager()
        self.panel.setStyleSheet(style_manager.get_stylesheet("add_task_dialog"))
        
        
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

        self.search_input = QLineEdit()
        self.search_input.setObjectName("completed_task_search_input")
        self.search_input.setPlaceholderText("搜索已完成任务标题，多个关键字用空格分隔")
        self.search_input.textChanged.connect(self._schedule_completed_task_filter)
        panel_layout.addWidget(self.search_input)
        
        # 创建表格
        self.table = self._create_table([])
        panel_layout.addWidget(self.table)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        # 全选/取消全选按钮
        self.select_all_button = QPushButton("全选")
        self.select_all_button.clicked.connect(self.toggle_select_all)
        apply_button_role(self.select_all_button, "secondary")

        # 加载更多按钮
        self.load_more_button = QPushButton("加载更多")
        self.load_more_button.clicked.connect(self._load_more_completed_tasks)
        apply_button_role(self.load_more_button, "secondary")
        
        # 还原按钮
        self.restore_button = QPushButton("还原选中任务")
        self.restore_button.clicked.connect(self.restore_selected_tasks)
        self.restore_button.setEnabled(False)
        apply_button_role(self.restore_button, "primary")
        
        # 关闭按钮
        self.close_button = QPushButton("关闭")
        self.close_button.clicked.connect(self.accept)
        apply_button_role(self.close_button, "ghost")
        
        button_layout.addWidget(self.select_all_button)
        button_layout.addWidget(self.load_more_button)
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
        """加载已完成任务第一页。"""
        try:
            self.current_search_query = self.search_input.text() if hasattr(self, 'search_input') else ""
            self.total_count = self.db_manager.count_completed_tasks(self.current_search_query)
            self.completed_tasks = self.db_manager.load_completed_tasks_page(
                limit=self.page_size,
                offset=0,
                search_query=self.current_search_query,
            )
            self.loaded_count = len(self.completed_tasks)

            empty_message = (
                "未找到匹配的已完成任务"
                if self.current_search_query.strip()
                else "暂无已完成任务"
            )
            self._render_completed_tasks(self.completed_tasks, empty_message, clear_selection=True)
            self._update_load_more_button()

            logger.info(f"加载了 {self.loaded_count}/{self.total_count} 个已完成任务")
                
        except Exception as e:
            logger.error(f"加载已完成任务失败: {str(e)}")
            show_error(self, "错误", f"加载已完成任务失败: {str(e)}")

    def _load_more_completed_tasks(self):
        """加载下一页已完成任务并追加到当前表格。"""
        if self.loaded_count >= self.total_count:
            self._update_load_more_button()
            return

        try:
            next_page = self.db_manager.load_completed_tasks_page(
                limit=self.page_size,
                offset=self.loaded_count,
                search_query=self.current_search_query,
            )
            if not next_page:
                self.loaded_count = len(self.completed_tasks)
                self.total_count = self.loaded_count
                self._update_load_more_button()
                return

            self.completed_tasks.extend(next_page)
            self.loaded_count = len(self.completed_tasks)
            empty_message = (
                "未找到匹配的已完成任务"
                if self.current_search_query.strip()
                else "暂无已完成任务"
            )
            self._render_completed_tasks(self.completed_tasks, empty_message, clear_selection=False)
            self._update_load_more_button()
        except Exception as e:
            logger.error(f"加载更多已完成任务失败: {str(e)}")
            show_error(self, "错误", f"加载更多已完成任务失败: {str(e)}")

    def _schedule_completed_task_filter(self):
        self.search_debounce_timer.start()

    def _apply_completed_task_filter(self):
        """根据搜索框内容重新加载匹配结果第一页。"""
        self._load_completed_tasks()

    def _parse_search_keywords(self, query):
        return [keyword.casefold() for keyword in str(query).split() if keyword]

    def _title_matches_keywords(self, title, keywords):
        normalized_title = str(title).casefold()
        return all(keyword in normalized_title for keyword in keywords)

    def _normalize_task_id(self, task_id):
        return str(task_id) if task_id else None

    def _load_completed_task_ids_for_selection(self):
        if hasattr(self.db_manager, "load_completed_task_ids"):
            return {
                task_id
                for task_id in (
                    self._normalize_task_id(task_id)
                    for task_id in self.db_manager.load_completed_task_ids(self.current_search_query)
                )
                if task_id
            }
        return {
            task_id
            for task_id in (
                self._normalize_task_id(task.get("id"))
                for task in self.completed_tasks
            )
            if task_id
        }

    def _selection_total_count(self, visible_checkbox_count=0):
        if self.selection_total_count_override is not None:
            return max(
                self.selection_total_count_override,
                visible_checkbox_count,
                len(self.selected_tasks),
            )
        return max(self.total_count, visible_checkbox_count, len(self.selected_tasks))

    def _render_completed_tasks(self, tasks, empty_message, clear_selection=True):
        previous_selected = set() if clear_selection else set(self.selected_tasks)
        self.selected_tasks = set(previous_selected)
        if clear_selection:
            self.selection_total_count_override = None
        rows = [
            [
                "",
                task.get("text", ""),
                task.get("completed_date", ""),
                task.get("notes", ""),
            ]
            for task in tasks
        ]
        if not tasks:
            rows = [["", empty_message, "", ""]]

        self.table.set_rows(rows)

        for row, task in enumerate(tasks):
            checkbox = QCheckBox()
            checkbox.stateChanged.connect(self.on_selection_changed)
            task_id = self._normalize_task_id(task.get('id'))
            checkbox.setProperty('task_id', task_id)
            if task_id in previous_selected:
                checkbox.setChecked(True)
            self.table.setCellWidget(row, 0, checkbox)

        self.restore_button.setEnabled(len(self.selected_tasks) > 0)
        self.on_selection_changed()

        if not tasks:
            self.table.item(0, 1).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setSpan(0, 1, 1, 3)  # 合并单元格

    def _update_load_more_button(self):
        if self.loaded_count < self.total_count:
            self.load_more_button.setEnabled(True)
            self.load_more_button.setText(f"加载更多 ({self.loaded_count}/{self.total_count})")
        else:
            self.load_more_button.setEnabled(False)
            self.load_more_button.setText("已全部加载")

    def _create_table(self, rows):
        table = AdaptiveTextTableWidget(
            headers=["", "任务内容", "完成日期",  "备注"],
            rows=rows,
            fixed_width_columns={0: 30, 3: 300},
            multiline_columns={3},
        )
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        table.setSortingEnabled(False)
        return table
    
    def on_selection_changed(self):
        """选择状态改变时的回调"""
        # 只用当前可见行更新可见任务，保留分页外的选中任务 ID。
        visible_task_ids = set()
        checked_visible_task_ids = set()
        
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if not checkbox:
                continue
            task_id = self._normalize_task_id(checkbox.property('task_id'))
            if not task_id:
                continue
            visible_task_ids.add(task_id)
            if checkbox.isChecked():
                checked_visible_task_ids.add(task_id)

        self.selected_tasks.difference_update(visible_task_ids)
        self.selected_tasks.update(checked_visible_task_ids)

        # 更新还原按钮状态
        self.restore_button.setEnabled(len(self.selected_tasks) > 0)

        # 更新全选按钮文本
        total_checkboxes = sum(
            1
            for row in range(self.table.rowCount())
            if self.table.cellWidget(row, 0)
        )
        selection_total_count = self._selection_total_count(total_checkboxes)
        checked_count = len(self.selected_tasks)

        if checked_count == 0:
            self.selection_total_count_override = None
            self.select_all_button.setText("全选")
        elif selection_total_count and checked_count >= selection_total_count:
            self.select_all_button.setText("取消全选")
        else:
            self.select_all_button.setText(f"全选 ({checked_count}/{selection_total_count})")

    def _set_visible_checkboxes_from_selection(self):
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                task_id = self._normalize_task_id(checkbox.property('task_id'))
                checkbox.blockSignals(True)
                checkbox.setChecked(bool(task_id and task_id in self.selected_tasks))
                checkbox.blockSignals(False)
    
    def toggle_select_all(self):
        """切换全选状态"""
        matching_task_ids = self._load_completed_task_ids_for_selection()
        all_selected = bool(matching_task_ids) and matching_task_ids.issubset(self.selected_tasks)

        if all_selected:
            self.selected_tasks.clear()
            self.selection_total_count_override = None
        else:
            self.selected_tasks = set(matching_task_ids)
            self.selection_total_count_override = len(matching_task_ids)

        self._set_visible_checkboxes_from_selection()
        self.on_selection_changed()
    
    def restore_selected_tasks(self):
        """还原选中的任务"""
        if not self.selected_tasks:
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self,
            "确认",
            f"确定要将 {len(self.selected_tasks)} 个任务还原为未完成状态吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
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
                
                show_success(self, "还原成功", f"成功还原 {restored_count} 个任务为未完成状态")
                
                # 刷新表格
                self._load_completed_tasks()
                
                # 通知父窗口刷新任务列表
                if hasattr(self.parent_widget, 'load_tasks'):
                    self.parent_widget.load_tasks()
                    
            else:
                show_error(self, "还原失败", "没有找到要还原的任务")
                
        except Exception as e:
            logger.error(f"还原任务失败: {str(e)}")
            show_error(self, "还原失败", f"还原任务时发生错误: {str(e)}")
    
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
