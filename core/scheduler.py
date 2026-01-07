"""
定时任务调度器模块
负责定时任务的业务逻辑、下次运行时间计算、任务生成等
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from calendar import monthrange

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


class TaskScheduler:
    """定时任务调度器"""
    
    def __init__(self, db_manager):
        """
        初始化调度器
        
        :param db_manager: 数据库管理器实例
        """
        self.db_manager = db_manager
    
    @staticmethod
    def calculate_next_run_time(
        frequency: str,
        base_time: datetime,
        week_day: Optional[int] = None,
        month_day: Optional[int] = None,
        quarter_day: Optional[int] = None,
        year_month: Optional[int] = None,
        year_day: Optional[int] = None
    ) -> datetime:
        """
        计算下次运行时间
        
        :param frequency: 频率 (daily, weekly, monthly, quarterly, yearly)
        :param base_time: 基准时间（通常是当前时间或上次运行时间）
        :param week_day: 周几 (1=周一, 7=周日)，weekly 时使用
        :param month_day: 每月第几天 (1-31)，monthly 时使用
        :param quarter_day: 每季度第几天，quarterly 时使用（简化为每季度第一个月的第几天）
        :param year_month: 每年第几月 (1-12)，yearly 时使用
        :param year_day: 每年该月第几天，yearly 时使用
        :return: 下次运行时间
        """
        if frequency == 'daily':
            # 每天：直接加1天
            next_run = base_time + timedelta(days=1)
            return next_run.replace(hour=0, minute=2, second=0, microsecond=0)
        
        elif frequency == 'weekly':
            # 每周：找到下一个指定的周几
            if week_day is None:
                week_day = 1  # 默认周一
            
            # 当前是周几 (0=周一, 6=周日)
            current_weekday = base_time.weekday()
            target_weekday = week_day - 1  # 转换为 0-6
            
            # 计算到目标周几还有几天
            days_ahead = target_weekday - current_weekday
            if days_ahead <= 0:  # 如果已经过了或是今天，跳到下周
                days_ahead += 7
            
            next_run = base_time + timedelta(days=days_ahead)
            return next_run.replace(hour=0, minute=2, second=0, microsecond=0)
        
        elif frequency == 'monthly':
            # 每月：指定每月的第几天
            if month_day is None:
                month_day = 1  # 默认每月1号
            
            # 尝试下个月的同一天
            year = base_time.year
            month = base_time.month + 1
            if month > 12:
                month = 1
                year += 1
            
            # 处理月末溢出（如2月30日）
            max_day = monthrange(year, month)[1]
            actual_day = min(month_day, max_day)
            
            next_run = datetime(year, month, actual_day, 0, 2, 0)
            return next_run
        
        elif frequency == 'quarterly':
            # 每季度：以1/4/7/10月为季度起点
            if quarter_day is None:
                quarter_day = 1  # 默认季度第1天
            
            # 季度起始月份
            quarter_months = [1, 4, 7, 10]
            
            # 找到下一个季度月份
            current_month = base_time.month
            next_quarter_month = None
            for qm in quarter_months:
                if qm > current_month:
                    next_quarter_month = qm
                    break
            
            if next_quarter_month is None:
                # 跳到明年第一季度
                next_quarter_month = 1
                year = base_time.year + 1
            else:
                year = base_time.year
            
            # 处理日期溢出
            max_day = monthrange(year, next_quarter_month)[1]
            actual_day = min(quarter_day, max_day)
            
            next_run = datetime(year, next_quarter_month, actual_day, 0, 2, 0)
            return next_run
        
        elif frequency == 'yearly':
            # 每年：指定月份和日期
            if year_month is None:
                year_month = 1  # 默认1月
            if year_day is None:
                year_day = 1  # 默认1号
            
            # 尝试今年的指定日期
            year = base_time.year
            if base_time.month >= year_month and base_time.day >= year_day:
                # 已经过了，跳到明年
                year += 1
            
            # 处理闰年问题（2月29日）
            max_day = monthrange(year, year_month)[1]
            actual_day = min(year_day, max_day)
            
            next_run = datetime(year, year_month, actual_day, 0, 2, 0)
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
                        'priority': schedule.get('priority', '中'),
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
                        # 计算下次运行时间
                        next_run = self.calculate_next_run_time(
                            frequency=schedule['frequency'],
                            base_time=now,
                            week_day=schedule.get('week_day'),
                            month_day=schedule.get('month_day'),
                            quarter_day=schedule.get('quarter_day'),
                            year_month=schedule.get('year_month'),
                            year_day=schedule.get('year_day')
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
        priority: str = '中',
        notes: str = '',
        due_date: str = '',
        week_day: Optional[int] = None,
        month_day: Optional[int] = None,
        quarter_day: Optional[int] = None,
        year_month: Optional[int] = None,
        year_day: Optional[int] = None,
        start_time: Optional[datetime] = None
    ) -> Optional[str]:
        """
        创建新的定时任务
        
        :param title: 任务标题
        :param frequency: 频率 (daily, weekly, monthly, quarterly, yearly)
        :param priority: 优先级
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
        if start_time is None:
            start_time = datetime.now()
        
        # 生成任务ID
        task_id = f"sched_{start_time.strftime('%Y%m%d%H%M%S%f')}"
        
        # 计算首次运行时间
        next_run = self.calculate_next_run_time(
            frequency=frequency,
            base_time=start_time,
            week_day=week_day,
            month_day=month_day,
            quarter_day=quarter_day,
            year_month=year_month,
            year_day=year_day
        )
        
        schedule_data = {
            'id': task_id,
            'title': title,
            'priority': priority,
            'notes': notes,
            'due_date': due_date,
            'frequency': frequency,
            'week_day': week_day,
            'month_day': month_day,
            'quarter_day': quarter_day,
            'year_month': year_month,
            'year_day': year_day,
            'next_run_at': next_run.isoformat(),
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
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("定时任务")
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
        
    def load_scheduled_tasks(self,layout):
        """加载定时任务"""
        try:
            db_manager = get_db_manager()
            scheduled_tasks = db_manager.list_scheduled_tasks()
            
            if not scheduled_tasks:
                layout.addWidget(QLabel("没有定时任务"))
                return
            # 创建表格
            self.create_table(layout, scheduled_tasks)
        except Exception as e:
            logger.error(f"加载定时任务失败: {str(e)}")
            layout.addWidget(QLabel(f"加载定时任务失败: {str(e)}"))

    def create_table(self, layout, scheduled_tasks):
        """创建表格"""
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["标题", "频率", "下次运行时间", "优先级", "备注"])
        table.setRowCount(len(scheduled_tasks))
        for row, scheduled_task in enumerate(scheduled_tasks):
            table.setItem(row, 0, QTableWidgetItem(scheduled_task['title']))
            table.setItem(row, 1, QTableWidgetItem(scheduled_task['frequency']))
            table.setItem(row, 2, QTableWidgetItem(scheduled_task['next_run_at']))
            table.setItem(row, 3, QTableWidgetItem(scheduled_task['priority']))
            table.setItem(row, 4, QTableWidgetItem(scheduled_task['notes']))
        layout.addWidget(table)
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


# 全局调度器实例
_scheduler = None


def get_scheduler(db_manager=None):
    """获取全局调度器实例"""
    global _scheduler
    if _scheduler is None:
        if db_manager is None:
            from database.database_manager import get_db_manager
            db_manager = get_db_manager()
        _scheduler = TaskScheduler(db_manager)
    return _scheduler
