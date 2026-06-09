import logging

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from database.database_manager import get_db_manager
from ui.adaptive_table import AdaptiveTextTableWidget
from ui.notifications import show_error, show_success
from ui.styles import StyleManager, apply_button_role


logger = logging.getLogger(__name__)


class ArchiveRestoreConfirmDialog(QDialog):
    """使用项目统一面板样式的还原确认对话框。"""

    def __init__(self, parent=None, message=""):
        super().__init__(
            parent,
            flags=Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setModal(True)
        self.setWindowTitle("确认还原")

        border_radius = 15
        if parent and hasattr(parent, "config"):
            border_radius = parent.config.get("ui", {}).get("border_radius", 15)
        elif parent and hasattr(parent, "parent_widget"):
            host = parent.parent_widget
            if host and hasattr(host, "config"):
                border_radius = host.config.get("ui", {}).get("border_radius", 15)
        self.setStyleSheet(
            f"QDialog {{ background-color: white; border-radius: {border_radius}px; }}"
        )

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        panel = QWidget(self)
        panel.setObjectName("dialog_panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(24, 24, 24, 24)
        panel_layout.setSpacing(18)
        panel.setStyleSheet(StyleManager().get_stylesheet("dialog_panel_shell"))

        title_label = QLabel("确认还原", panel)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #333; padding: 4px 0;"
        )
        panel_layout.addWidget(title_label)

        message_label = QLabel(message, panel)
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(message_label)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_button = QPushButton("取消", panel)
        self.cancel_button.clicked.connect(self.reject)
        apply_button_role(self.cancel_button, "ghost")
        button_layout.addWidget(self.cancel_button)

        self.confirm_button = QPushButton("还原", panel)
        self.confirm_button.clicked.connect(self.accept)
        self.confirm_button.setDefault(True)
        apply_button_role(self.confirm_button, "primary")
        button_layout.addWidget(self.confirm_button)

        panel_layout.addLayout(button_layout)
        main_layout.addWidget(panel)

        panel.setMinimumWidth(400)
        panel_layout.activate()
        panel.adjustSize()
        self.resize(panel.size())

        if parent:
            parent_rect = parent.frameGeometry()
            self.move(
                parent_rect.center().x() - self.width() // 2,
                parent_rect.center().y() - self.height() // 2,
            )


class ArchiveTableDialog(QDialog):
    """已归档事项共享的分页、筛选、选择和还原对话框。"""

    window_title = ""
    search_object_name = "archive_task_search_input"
    search_placeholder = ""
    empty_message = ""
    no_results_message = ""
    date_column_title = ""
    date_field = ""
    restore_button_text = "还原选中事项"
    page_loader_name = ""
    count_loader_name = ""
    id_loader_name = ""
    restore_method_name = ""
    confirm_message_template = "确定要还原 {count} 个事项吗？"
    success_message_template = "成功还原 {count} 个事项"
    load_error_label = "归档事项"
    restore_error_label = "事项"

    def __init__(self, parent=None, db_manager=None):
        super().__init__(parent)
        self.parent_widget = parent
        self.db_manager = db_manager or get_db_manager()
        self.selected_tasks = set()
        self.archive_tasks = []
        self.page_size = 50
        self.loaded_count = 0
        self.total_count = 0
        self.selection_total_count_override = None
        self.current_search_query = ""
        self.search_debounce_timer = QTimer(self)
        self.search_debounce_timer.setSingleShot(True)
        self.search_debounce_timer.setInterval(500)
        self.search_debounce_timer.timeout.connect(self._apply_archive_task_filter)

        self._setup_ui()
        self._load_archive_tasks()

    def _setup_ui(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        border_radius = 15
        if self.parent_widget and hasattr(self.parent_widget, "config"):
            border_radius = self.parent_widget.config.get("ui", {}).get("border_radius", 15)
        self.setStyleSheet(
            f"QDialog {{ background-color: white; border-radius: {border_radius}px; }}"
        )
        self.setModal(True)
        self.setWindowTitle(self.window_title)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.panel = QWidget()
        self.panel.setObjectName("dialog_panel")
        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(20, 20, 20, 20)
        panel_layout.setSpacing(15)
        self.panel.setStyleSheet(StyleManager().get_stylesheet("add_task_dialog"))

        title_label = QLabel(self.window_title)
        title_label.setStyleSheet(
            """
            font-size: 18px;
            font-weight: bold;
            color: #333;
            padding: 10px 0;
            """
        )
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        panel_layout.addWidget(title_label)

        self.search_input = QLineEdit()
        self.search_input.setObjectName(self.search_object_name)
        self.search_input.setPlaceholderText(self.search_placeholder)
        self.search_input.textChanged.connect(self._schedule_archive_task_filter)
        panel_layout.addWidget(self.search_input)

        self.table = self._create_table([])
        panel_layout.addWidget(self.table)

        button_layout = QHBoxLayout()
        self.select_all_button = QPushButton("全选")
        self.select_all_button.clicked.connect(self.toggle_select_all)
        apply_button_role(self.select_all_button, "secondary")

        self.load_more_button = QPushButton("加载更多")
        self.load_more_button.clicked.connect(self._load_more_archive_tasks)
        apply_button_role(self.load_more_button, "secondary")

        self.restore_button = QPushButton(self.restore_button_text)
        self.restore_button.clicked.connect(self.restore_selected_tasks)
        self.restore_button.setEnabled(False)
        apply_button_role(self.restore_button, "primary")

        self.close_button = QPushButton("关闭")
        self.close_button.clicked.connect(self.accept)
        apply_button_role(self.close_button, "ghost")

        button_layout.addWidget(self.select_all_button)
        button_layout.addWidget(self.load_more_button)
        button_layout.addStretch()
        button_layout.addWidget(self.restore_button)
        button_layout.addWidget(self.close_button)
        panel_layout.addLayout(button_layout)
        main_layout.addWidget(self.panel)

        self.resize(800, 600)
        if self.parent_widget:
            parent_rect = self.parent_widget.geometry()
            self.move(
                parent_rect.x() + (parent_rect.width() - self.width()) // 2,
                parent_rect.y() + (parent_rect.height() - self.height()) // 2,
            )

    def _empty_state_message(self):
        if self.current_search_query.strip():
            return self.no_results_message
        return self.empty_message

    def _load_archive_tasks(self):
        try:
            self.current_search_query = (
                self.search_input.text() if hasattr(self, "search_input") else ""
            )
            count_loader = getattr(self.db_manager, self.count_loader_name)
            page_loader = getattr(self.db_manager, self.page_loader_name)
            self.total_count = count_loader(self.current_search_query)
            self.archive_tasks = page_loader(
                limit=self.page_size,
                offset=0,
                search_query=self.current_search_query,
            )
            self.loaded_count = len(self.archive_tasks)
            self._render_archive_tasks(
                self.archive_tasks,
                self._empty_state_message(),
                clear_selection=True,
            )
            self._update_load_more_button()
            logger.info(
                "加载了 %s/%s 个%s",
                self.loaded_count,
                self.total_count,
                self.load_error_label,
            )
        except Exception as e:
            logger.error("加载%s失败: %s", self.load_error_label, str(e))
            show_error(self, "错误", f"加载{self.load_error_label}失败: {str(e)}")

    def _load_more_archive_tasks(self):
        if self.loaded_count >= self.total_count:
            self._update_load_more_button()
            return

        try:
            page_loader = getattr(self.db_manager, self.page_loader_name)
            next_page = page_loader(
                limit=self.page_size,
                offset=self.loaded_count,
                search_query=self.current_search_query,
            )
            if not next_page:
                self.loaded_count = len(self.archive_tasks)
                self.total_count = self.loaded_count
                self._update_load_more_button()
                return

            self.archive_tasks.extend(next_page)
            self.loaded_count = len(self.archive_tasks)
            self._render_archive_tasks(
                self.archive_tasks,
                self._empty_state_message(),
                clear_selection=False,
            )
            self._update_load_more_button()
        except Exception as e:
            logger.error("加载更多%s失败: %s", self.load_error_label, str(e))
            show_error(self, "错误", f"加载更多{self.load_error_label}失败: {str(e)}")

    def _schedule_archive_task_filter(self):
        self.search_debounce_timer.start()

    def _apply_archive_task_filter(self):
        self._load_archive_tasks()

    def _normalize_task_id(self, task_id):
        return str(task_id) if task_id else None

    def _load_archive_task_ids_for_selection(self):
        id_loader = getattr(self.db_manager, self.id_loader_name, None)
        if id_loader:
            return {
                task_id
                for task_id in (
                    self._normalize_task_id(task_id)
                    for task_id in id_loader(self.current_search_query)
                )
                if task_id
            }
        return {
            task_id
            for task_id in (
                self._normalize_task_id(task.get("id"))
                for task in self.archive_tasks
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

    def _render_archive_tasks(self, tasks, empty_message, clear_selection=True):
        previous_selected = set() if clear_selection else set(self.selected_tasks)
        self.selected_tasks = set(previous_selected)
        if clear_selection:
            self.selection_total_count_override = None

        rows = [
            [
                "",
                task.get("text", ""),
                task.get(self.date_field, ""),
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
            task_id = self._normalize_task_id(task.get("id"))
            checkbox.setProperty("task_id", task_id)
            if task_id in previous_selected:
                checkbox.setChecked(True)
            self.table.setCellWidget(row, 0, checkbox)

        self.restore_button.setEnabled(bool(self.selected_tasks))
        self.on_selection_changed()

        if not tasks:
            self.table.item(0, 1).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setSpan(0, 1, 1, 3)

    def _update_load_more_button(self):
        if self.loaded_count < self.total_count:
            self.load_more_button.setEnabled(True)
            self.load_more_button.setText(
                f"加载更多 ({self.loaded_count}/{self.total_count})"
            )
        else:
            self.load_more_button.setEnabled(False)
            self.load_more_button.setText("已全部加载")

    def _create_table(self, rows):
        table = AdaptiveTextTableWidget(
            headers=["", "任务内容", self.date_column_title, "备注"],
            rows=rows,
            fixed_width_columns={0: 30, 3: 300},
            multiline_columns={3},
        )
        table.horizontalHeader().setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Stretch,
        )
        table.setSortingEnabled(False)
        return table

    def on_selection_changed(self):
        visible_task_ids = set()
        checked_visible_task_ids = set()
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if not checkbox:
                continue
            task_id = self._normalize_task_id(checkbox.property("task_id"))
            if not task_id:
                continue
            visible_task_ids.add(task_id)
            if checkbox.isChecked():
                checked_visible_task_ids.add(task_id)

        self.selected_tasks.difference_update(visible_task_ids)
        self.selected_tasks.update(checked_visible_task_ids)
        self.restore_button.setEnabled(bool(self.selected_tasks))

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
            self.select_all_button.setText(
                f"全选 ({checked_count}/{selection_total_count})"
            )

    def _set_visible_checkboxes_from_selection(self):
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox:
                task_id = self._normalize_task_id(checkbox.property("task_id"))
                checkbox.blockSignals(True)
                checkbox.setChecked(bool(task_id and task_id in self.selected_tasks))
                checkbox.blockSignals(False)

    def toggle_select_all(self):
        matching_task_ids = self._load_archive_task_ids_for_selection()
        all_selected = (
            bool(matching_task_ids)
            and matching_task_ids.issubset(self.selected_tasks)
        )
        if all_selected:
            self.selected_tasks.clear()
            self.selection_total_count_override = None
        else:
            self.selected_tasks = set(matching_task_ids)
            self.selection_total_count_override = len(matching_task_ids)

        self._set_visible_checkboxes_from_selection()
        self.on_selection_changed()

    def restore_selected_tasks(self):
        if not self.selected_tasks:
            return

        selected_task_ids = set(self.selected_tasks)
        confirm_dialog = ArchiveRestoreConfirmDialog(
            self,
            self.confirm_message_template.format(count=len(selected_task_ids)),
        )
        if confirm_dialog.exec() != QDialog.DialogCode.Accepted:
            return

        try:
            restore_task = getattr(self.db_manager, self.restore_method_name)
            restored_count = sum(
                1 for task_id in selected_task_ids if restore_task(task_id)
            )
            if restored_count == 0:
                show_error(self, "还原失败", f"没有找到要还原的{self.restore_error_label}")
                return

            self.db_manager.flush_cache_to_db()
            self._load_archive_tasks()
            if hasattr(self.parent_widget, "load_tasks"):
                self.parent_widget.load_tasks()
            show_success(
                self,
                "还原成功",
                self.success_message_template.format(count=restored_count),
            )
        except Exception as e:
            logger.error("还原%s失败: %s", self.restore_error_label, str(e))
            show_error(
                self,
                "还原失败",
                f"还原{self.restore_error_label}时发生错误: {str(e)}",
            )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if (
            event.buttons() == Qt.MouseButton.LeftButton
            and hasattr(self, "_drag_position")
        ):
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
