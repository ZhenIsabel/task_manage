from database.database_manager import get_db_manager

from .archive_table import ArchiveTableDialog


class DeletedTableDialog(ArchiveTableDialog):
    """已删除事项对话框。"""

    window_title = "已删除事项"
    search_object_name = "deleted_task_search_input"
    search_placeholder = "搜索已删除事项标题，多个关键字用空格分隔"
    empty_message = "暂无已删除事项"
    no_results_message = "未找到匹配的已删除事项"
    date_column_title = "删除日期"
    date_field = "updated_at"
    restore_button_text = "还原选中事项"
    page_loader_name = "load_deleted_tasks_page"
    count_loader_name = "count_deleted_tasks"
    id_loader_name = "load_deleted_task_ids"
    restore_method_name = "restore_deleted_task"
    confirm_message_template = "确定要还原 {count} 个已删除事项吗？"
    success_message_template = "成功还原 {count} 个已删除事项"
    load_error_label = "已删除事项"
    restore_error_label = "已删除事项"

    def __init__(self, parent=None):
        super().__init__(parent, db_manager=get_db_manager())
