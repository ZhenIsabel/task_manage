"""
定时任务调度器模块
负责定时任务的业务逻辑、下次运行时间计算、任务生成等
"""

from datetime import datetime, timedelta
from typing import Optional
from calendar import monthrange

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QMessageBox,
                            QPushButton, QWidget,QAbstractScrollArea,QCheckBox,
                            QComboBox,QTextEdit,QLineEdit)
from PyQt6.QtCore import Qt, QDate

from ui.adaptive_table import AdaptiveTextTableWidget
from ui.fluent import ComboBox, create_calendar_picker, get_date_string_from_picker, is_date_picker
from ui.notifications import show_error, show_success,show_warning,resolve_notification_host
from ui.styles import StyleManager
from ui.degree_badges import create_degree_table_cell, is_degree_field
from database.database_manager import get_db_manager
from config.config_manager import load_config
import logging
logger = logging.getLogger(__name__)


class TaskScheduler:
    """定时任务调度器"""
    
    def __init__(self):
        """
        初始化调度器
        
        :param db_manager: 数据库管理器实例
        """
        self.db_manager = get_db_manager()
    
    @staticmethod
    def calculate_next_run_time(
        frequency: str,
        base_time: datetime,
        week_day: Optional[int] = None,
        month_day: Optional[int] = None,
        quarter_day: Optional[int] = None,
        year_month: Optional[int] = None,
        year_day: Optional[int] = None,
        created_time: Optional[datetime] = None
    ) -> datetime:
        """
        计算下次运行时间
        
        :param frequency: 频率 (daily, weekly, monthly, quarterly, yearly)
        :param base_time: 基准时间（通常是start_time或上次运行时间）
        :param week_day: 周几 (1=周一, 7=周日)，weekly 时使用（保留用于兼容性，但不影响周期计算）
        :param month_day: 每月第几天 (1-31)，monthly 时使用（保留用于兼容性，但不影响周期计算）
        :param quarter_day: 每季度第几天，quarterly 时使用（保留用于兼容性，但不影响周期计算）
        :param year_month: 每年第几月 (1-12)，yearly 时使用（保留用于兼容性，但不影响周期计算）
        :param year_day: 每年该月第几天，yearly 时使用（保留用于兼容性，但不影响周期计算）
        :return: 下次运行时间（保持base_time的时分秒）
        """
        # 如果没有提供创建时间，使用base_time作为参考
        reference_time = created_time if created_time is not None else base_time
        
        if frequency == 'daily':
            # 每天：直接加1天，保持原有时分秒
            next_run = base_time + timedelta(days=1)
            return next_run.replace(hour=0, minute=2, second=0, microsecond=0)
        
        elif frequency == 'weekly':
            # 每周：直接加7天，保持原有时分秒
            next_run = base_time + timedelta(days=7)
            return next_run
        
        elif frequency == 'monthly':
            # 每月：从base_time加1个月，保持相同的日期和时间
            year = base_time.year
            month = base_time.month + 1
            if month > 12:
                month = 1
                year += 1
            
            # 处理月末溢出（如1月31日+1个月，2月没有31日）
            day = base_time.day
            max_day = monthrange(year, month)[1]
            actual_day = min(day, max_day)
            
            next_run = datetime(year, month, actual_day, base_time.hour, base_time.minute, base_time.second, base_time.microsecond)
            return next_run
        
        elif frequency == 'quarterly':
            # 每季度：从base_time加3个月
            year = base_time.year
            month = base_time.month + 3
            while month > 12:
                month -= 12
                year += 1
            
            # 处理日期溢出
            day = base_time.day
            max_day = monthrange(year, month)[1]
            actual_day = min(day, max_day)
            
            next_run = datetime(year, month, actual_day, base_time.hour, base_time.minute, base_time.second, base_time.microsecond)
            return next_run
        
        elif frequency == 'yearly':
            # 每年：从base_time加1年，保持相同的月日时间
            year = base_time.year + 1
            month = base_time.month
            day = base_time.day
            
            # 处理闰年问题（如2月29日在非闰年）
            max_day = monthrange(year, month)[1]
            actual_day = min(day, max_day)
            
            next_run = datetime(year, month, actual_day, base_time.hour, base_time.minute, base_time.second, base_time.microsecond)
            return next_run
        
        else:
            # 默认1天后
            return base_time + timedelta(days=1)
    
    def check_and_spawn_scheduled_tasks(self, now: Optional[datetime] = None) -> int:
        """
        检查并生成到期的定时任务
        
        :param now: 当前时间，默认为系统当前时间
        :return: 生成的任务数量
        """
        if now is None:
            now = datetime.now()
        
        try:
            # 获取所有到期的激活定时任务
            due_schedules = self.db_manager.list_scheduled_tasks(
                active_only=True,
                due_before=now
            )
            
            spawned_count = 0
            
            for schedule in due_schedules:
                try:
                    # 生成新任务
                    task_id = f"scheduled_{schedule['id']}_{now.strftime('%Y%m%d%H%M%S')}"
                    
                    task_data = {
                        'id': task_id,
                        'text': schedule['title'],
                        'urgency': schedule.get('urgency', '低'),
                        'importance': schedule.get('importance', '低'),
                        'notes': schedule.get('notes', ''),
                        'due_date': schedule.get('due_date', ''),
                        'completed': False,
                        'deleted': False,
                        'color': '#4ECDC4',
                        'position': {'x': 100, 'y': 100},
                        'created_at': now.isoformat(),
                        'updated_at': now.isoformat()
                    }
                    
                    # 保存任务到数据库（通过缓存）
                    success = self.db_manager.save_task(task_data)
                    
                    if success:
                        # 获取创建时间，如果不存在则使用当前时间（向后兼容）
                        created_time_str = schedule.get('created_at')
                        if created_time_str:
                            try:
                                created_time = datetime.fromisoformat(created_time_str)
                            except (ValueError, TypeError):
                                created_time = None
                        else:
                            created_time = None
                        
                        # 计算下次运行时间
                        next_run = self.calculate_next_run_time(
                            frequency=schedule['frequency'],
                            base_time=now,
                            week_day=schedule.get('week_day'),
                            month_day=schedule.get('month_day'),
                            quarter_day=schedule.get('quarter_day'),
                            year_month=schedule.get('year_month'),
                            year_day=schedule.get('year_day'),
                            created_time=created_time  # 传入创建时间作为参考
                        )
                        
                        # 更新定时任务的下次运行时间
                        self.db_manager.update_scheduled_task(
                            schedule['id'],
                            {'next_run_at': next_run.isoformat()}
                        )
                        
                        spawned_count += 1
                        logger.info(f"定时任务已生成: {task_id}, 标题: {schedule['title']}, 下次运行: {next_run}")
                    else:
                        logger.error(f"保存定时任务失败: {schedule['id']}")
                
                except Exception as e:
                    logger.error(f"处理定时任务 {schedule['id']} 时出错: {str(e)}")
                    continue
            
            if spawned_count > 0:
                # 立即将生成的任务写入数据库
                self.db_manager.flush_cache_to_db()
                logger.info(f"成功生成 {spawned_count} 个定时任务")
            
            return spawned_count
        
        except Exception as e:
            logger.error(f"检查定时任务失败: {str(e)}")
            return 0
    
    def create_scheduled_task(
        self,
        title: str,
        frequency: str,
        urgency: str = '低',
        importance: str = '低',
        notes: str = '',
        due_date: str = '',
        week_day: Optional[int] = None,
        month_day: Optional[int] = None,
        quarter_day: Optional[int] = None,
        year_month: Optional[int] = None,
        year_day: Optional[int] = None,
        start_time: str = ''
    ) -> Optional[str]:
        """
        创建新的定时任务
        
        :param title: 任务标题
        :param frequency: 频率 (daily, weekly, monthly, quarterly, yearly)
        :param urgency: 紧急程度
        :param importance: 重要程度
        :param notes: 备注
        :param due_date: 到期日期
        :param week_day: 周几 (weekly)
        :param month_day: 每月第几天 (monthly)
        :param quarter_day: 每季度第几天 (quarterly)
        :param year_month: 每年第几月 (yearly)
        :param year_day: 每年第几天 (yearly)
        :param start_time: 开始时间，默认为当前时间
        :return: 创建的任务ID，失败返回None
        """
        # 处理 start_time 参数：可能是字符串、None 或 datetime 对象
        if start_time is None or start_time == '':
            start_time = datetime.now()
        elif isinstance(start_time, str):
            # 尝试解析字符串日期
            try:
                start_time = datetime.strptime(start_time, '%Y-%m-%d')
            except ValueError:
                # 如果解析失败，使用当前时间
                start_time = datetime.now()
        
        # 生成任务ID
        base_task_id = f"sched_{start_time.strftime('%Y%m%d%H%M%S%f')}"
        task_id = base_task_id
        
        # 检查ID是否重复，如果重复则添加区别符
        counter = 1
        while self.db_manager.get_scheduled_task(task_id) is not None:
            task_id = f"{base_task_id}_{counter}"
            counter += 1
            # 为防止无限循环，设置最大尝试次数
            if counter > 100:
                logger.error(f"生成唯一任务ID失败: 尝试次数超过100次")
                return None
        
        # 计算首次运行时间
        next_run = self.calculate_next_run_time(
            frequency=frequency,
            base_time=start_time,
            week_day=week_day,
            month_day=month_day,
            quarter_day=quarter_day,
            year_month=year_month,
            year_day=year_day,
            created_time=start_time  # 传入创建时间作为参考
        )
        
        schedule_data = {
            'id': task_id,
            'title': title,
            'urgency': urgency,
            'importance': importance,
            'notes': notes,
            'due_date': due_date,
            'frequency': frequency,
            'week_day': week_day,
            'month_day': month_day,
            'quarter_day': quarter_day,
            'year_month': year_month,
            'year_day': year_day,
            'next_run_at': next_run.isoformat(),
            'created_at': start_time.isoformat(),  # 保存创建时间
            'active': True
        }
        
        success = self.db_manager.create_scheduled_task(schedule_data)
        
        if success:
            logger.info(f"创建定时任务成功: {task_id}, 首次运行: {next_run}")
            return task_id
        else:
            logger.error(f"创建定时任务失败: {title}")
            return None


class ScheduledTaskDialog(QDialog):
    def __init__(self,  parent=None):
        logger.info("初始化定时任务面板")
        super().__init__(parent)
        
        # 先初始化必需的属性，再调用 setup_ui
        self.selected_tasks = set()  # 存储选中的任务ID
        self.db_manager = get_db_manager()
        self.task_scheduler = TaskScheduler()  # 初始化任务调度器
        self.setup_ui()
        pass
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("定时任务")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        # 不再使用透明背景，避免弹窗外侧出现可透底的透明区域
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("QDialog { background-color: white; border-radius: 15px; }")
        self.adjustSize()
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(0)
        
        # 样式管理器
        style_manager = StyleManager()
        
        # 创建主面板
        panel = QWidget(self)
        panel.setObjectName("dialog_panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(20,20,20,20)
        panel_layout.setSpacing(15)
        panel.setMaximumWidth(600)
        
        # 样式表
        panel.setStyleSheet(style_manager.get_stylesheet("add_task_dialog"))
        
        # 加载
        self.load_scheduled_tasks(panel_layout)


        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 添加按钮
        add_button=QPushButton("添加")
        add_button.clicked.connect(self.add)
        add_button.setStyleSheet(style_manager.get_stylesheet("task_label_button"))
        add_button.setFixedHeight(35)
        button_layout.addWidget(add_button)

        # 删除按钮
        delete_button=QPushButton("删除")
        delete_button.clicked.connect(self.delete_task)
        delete_button.setStyleSheet("""
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
        delete_button.setFixedHeight(35)
        button_layout.addWidget(delete_button)

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
        
    def load_scheduled_tasks(self,layout):
        """加载定时任务"""
        try:
            scheduled_tasks = self.db_manager.list_scheduled_tasks()
            if not scheduled_tasks:
                layout.addWidget(QLabel("没有定时任务"))
                logger.info("没有定时任务")
                return
            # 创建表格
            self.create_table(layout, scheduled_tasks)
        except Exception as e:
            logger.error(f"加载定时任务失败: {str(e)}")
            layout.addWidget(QLabel(f"加载定时任务失败: {str(e)}"))

    def create_table(self, layout, scheduled_tasks):
        """创建表格"""
        logger.info(f"加载定时任务表条数{len(scheduled_tasks)}")
        rows = [
            [
                "",
                scheduled_task["title"],
                scheduled_task["frequency"],
                scheduled_task["next_run_at"],
                "",
                "",
                scheduled_task.get("notes", ""),
            ]
            for scheduled_task in scheduled_tasks
        ]
        self.table = AdaptiveTextTableWidget(
            headers=["选择", "任务内容", "频率", "下次运行", "紧急程度", "重要程度", "备注"],
            rows=rows,
            fixed_width_columns={6: 300},
            multiline_columns={6},
        )
        header = self.table.verticalHeader()
        header.setMinimumSectionSize(35)
        self.table.setSortingEnabled(False)
        for row, scheduled_task in enumerate(scheduled_tasks):
            # 复选框
            checkbox = QCheckBox()
            checkbox.stateChanged.connect(self.on_selection_changed)
            checkbox.setProperty('id', scheduled_task['id'])
            self.table.setCellWidget(row, 0, checkbox)
            self.table.setCellWidget(row, 4, create_degree_table_cell('urgency', scheduled_task.get('urgency', '低'), self.table))
            self.table.setCellWidget(row, 5, create_degree_table_cell('importance', scheduled_task.get('importance', '低'), self.table))
        self.table.resizeRowsToContents()
        self.table.setSortingEnabled(True)
        
        # 允许滚动
        self.table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)

        self.table.setMaximumHeight(400)
        layout.addWidget(self.table)

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

    def delete_task(self):
        """删除选中的任务"""
        if not self.selected_tasks:
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self,
            "确认",
            "确定要删除吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            deleted_count=0
            for task_id in self.selected_tasks:
                result=self.db_manager.delete_scheduled_task(task_id)
                if result:
                    deleted_count+=1
            
            # 显示成功消息
            show_success(self, "删除成功", f"成功删除 {deleted_count} 个定时任务")
            
            # 刷新任务列表 - 关闭对话框以触发父窗口刷新
            self.close()

        except Exception as e:
            logger.error(f"删除任务失败: {str(e)}")
            show_error(self, "删除失败", f"删除任务时发生错误: {str(e)}")
        
        
    
    def add(self):
        # 获取当前字段配置
        task_fields = []
        for meta in self.get_editable_fields():
            value = getattr(self, meta["name"], "") or ""  # 双重空值保护
            task_fields.append(dict(meta, default=value))
        dialog=AddScheduleDialog(self,task_fields)
        result=dialog.exec()
        # 如果点击确定就取回数据
        if result != QDialog.DialogCode.Accepted:
            return
        # 从对话框中获取字段值
        task_data = dialog.get_data()
        # 检查必填
        for f in task_fields:
            if f.get("required") and not task_data.get(f["name"]):
                show_warning(self,"提示",f"{f['label']} 为必填项")
                return
        # 创建任务
        try:
            # 字段映射：配置中使用 'text'，但 create_scheduled_task 期望 'title'
            title = task_data.get('title') or task_data.get('text', '')
            result_id = self.task_scheduler.create_scheduled_task(
                title=title,
                frequency=task_data['frequency'],
                urgency=task_data.get('urgency', '低'),
                importance=task_data.get('importance', '低'),
                notes=task_data.get('notes', ''),
                due_date=task_data.get('due_date', ''),
                start_time=task_data.get('start_time')
            )
            if result_id:
                show_success(self, "成功", "定时任务创建成功")
                # 刷新任务列表
                self.close()
            else:
                show_error(self, "失败", "定时任务创建失败，请查看日志")
        except Exception as e:
            show_error(self, "错误", f"创建定时任务时发生错误: {str(e)}")
            logger.error(f"创建定时任务异常: {str(e)}", exc_info=True)


    def on_selection_changed(self):
        """选择状态改变时的回调"""
        # 重新计算选中的任务
        self.selected_tasks.clear()
        
        for row in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                task_id = checkbox.property('id')
                if task_id:
                    self.selected_tasks.add(task_id)
        
    def get_editable_fields(self):
        """从配置中获取可编辑字段"""
        config = load_config()
        fields = config.get('schedule_task_fields', [])
        logger.info(f"获取到字段了{fields}")
        return fields
    

class AddScheduleDialog(QDialog):
    def __init__(self,  parent=None,task_fields=None):
        logger.info("添加定时任务")
        self.task_fields=task_fields
        super().__init__(parent)
        self.setup_ui()
        

    def setup_ui(self):
        """设置UI"""
        logger.info("进入添加定时任务的setup_ui咯")
        self.setWindowTitle("添加定时任务")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        # 不再使用透明背景，避免弹窗外侧出现可透底的透明区域
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("QDialog { background-color: white; border-radius: 15px; }")
        self.adjustSize()
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(0)
        
        # 样式管理器
        style_manager = StyleManager()
        
        # 创建主面板
        panel = QWidget(self)
        panel.setObjectName("dialog_panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(30, 30, 30, 30)
        panel_layout.setSpacing(5)
        
        # 样式表
        panel.setStyleSheet(style_manager.get_stylesheet("add_task_dialog"))

        # 输入字段
        self.inputs = {}

        index = 0
        while index < len(self.task_fields):
            field = self.task_fields[index]
            next_field = self.task_fields[index + 1] if index + 1 < len(self.task_fields) else None

            if self._should_group_degree_fields(field, next_field):
                self._add_degree_field_row(panel, panel_layout, field, next_field)
                index += 2
                continue

            self._add_single_field(panel, panel_layout, field)
            index += 1

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 添加按钮
        add_button=QPushButton("添加")
        add_button.clicked.connect(self.accept)
        add_button.setStyleSheet(style_manager.get_stylesheet("task_label_button"))
        add_button.setFixedHeight(35)
        button_layout.addWidget(add_button)

        # 关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.reject)
        close_button.setStyleSheet(style_manager.get_stylesheet("task_label_button"))
        close_button.setFixedHeight(35)
        button_layout.addWidget(close_button)
        
        panel_layout.addLayout(button_layout)
        
        main_layout.addWidget(panel)
        
        # ❹ 自动根据内容调大小，再把“壳”和“面板”都居中放
        # 外圈透明壳/留白去掉：把“壳”尺寸与真实面板对齐
        shadow_margin = 0
        # 让 panel 先自适应内容
        panel.setMinimumWidth(400)
        panel_layout.activate()
        panel.adjustSize()
        # 让壳与面板对齐
        self.resize(panel.width() + shadow_margin * 2, panel.height() + shadow_margin * 2)
        # 把面板放回壳左上角
        panel.move(shadow_margin, shadow_margin)

    def _should_group_degree_fields(self, current_field, next_field):
        return (
            current_field
            and next_field
            and current_field.get('name') == 'urgency'
            and next_field.get('name') == 'importance'
            and is_degree_field(current_field.get('name'))
            and is_degree_field(next_field.get('name'))
        )

    def _create_field_input(self, parent, field):
        default_value = field.get('default', '')
        if field['type'] == 'date':
            initial_date = QDate.fromString(default_value, "yyyy-MM-dd") if default_value else QDate.currentDate()
            return create_calendar_picker(parent, initial_date)
        if field['type'] == 'select':
            widget = ComboBox()
            for option in field.get('options', []):
                widget.addItem(option)
            if default_value and default_value in field.get('options', []):
                widget.setCurrentText(default_value)
            return widget
        if field['type'] == 'multiline':
            widget = QTextEdit()
            widget.setPlaceholderText("请输入备注...")
            widget.setMinimumHeight(100)
            if default_value:
                widget.setText(str(default_value))
            return widget
        return QLineEdit(str(default_value))

    def _add_single_field(self, panel, parent_layout, field):
        parent_layout.addWidget(QLabel(f"{field['label']}{' *' if field.get('required') else ''}"))
        widget = self._create_field_input(panel, field)
        parent_layout.addWidget(widget)
        self.inputs[field['name']] = widget

    def _add_degree_field_row(self, panel, parent_layout, first_field, second_field):
        row = QHBoxLayout()
        row.setSpacing(12)

        for field in (first_field, second_field):
            column_widget = QWidget(panel)
            column_layout = QVBoxLayout(column_widget)
            column_layout.setContentsMargins(0, 0, 0, 0)
            column_layout.setSpacing(5)
            column_layout.addWidget(QLabel(f"{field['label']}{' *' if field.get('required') else ''}"))
            widget = self._create_field_input(panel, field)
            column_layout.addWidget(widget)
            row.addWidget(column_widget, 1)
            self.inputs[field['name']] = widget

        parent_layout.addLayout(row)

    def get_data(self):
        """把表单内容打包成 dict 返回"""
        data = {}
        for name, w in self.inputs.items():
            if is_date_picker(w):
                data[name] = get_date_string_from_picker(w)
            elif isinstance(w, (QComboBox, ComboBox)):
                data[name] = w.currentText()
            elif isinstance(w, QTextEdit):
                data[name] = w.toPlainText()
            else:
                data[name] = w.text()
        return data


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
