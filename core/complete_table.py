from database.database_manager import get_db_manager

from .archive_table import ArchiveTableDialog


class CompleteTableDialog(ArchiveTableDialog):
    """已完成任务对话框。"""

    window_title = "已完成任务"
    search_object_name = "completed_task_search_input"
    search_placeholder = "搜索已完成任务标题，多个关键字用空格分隔"
    empty_message = "暂无已完成任务"
    no_results_message = "未找到匹配的已完成任务"
    date_column_title = "完成日期"
    date_field = "completed_date"
    restore_button_text = "还原选中任务"
    page_loader_name = "load_completed_tasks_page"
    count_loader_name = "count_completed_tasks"
    id_loader_name = "load_completed_task_ids"
    restore_method_name = "restore_completed_task"
    confirm_message_template = "确定要将 {count} 个任务还原为未完成状态吗？"
    success_message_template = "成功还原 {count} 个任务为未完成状态"
    load_error_label = "已完成任务"
    restore_error_label = "任务"

    def __init__(self, parent=None):
        super().__init__(parent, db_manager=get_db_manager())

    @property
    def completed_tasks(self):
        return self.archive_tasks

    @completed_tasks.setter
    def completed_tasks(self, tasks):
        self.archive_tasks = tasks

    def _load_completed_tasks(self):
        self._load_archive_tasks()

    def _load_more_completed_tasks(self):
        self._load_more_archive_tasks()

    def _schedule_completed_task_filter(self):
        self._schedule_archive_task_filter()

    def _apply_completed_task_filter(self):
        self._apply_archive_task_filter()

    def _load_completed_task_ids_for_selection(self):
        return self._load_archive_task_ids_for_selection()

    def _render_completed_tasks(self, tasks, empty_message, clear_selection=True):
        self._render_archive_tasks(tasks, empty_message, clear_selection)
