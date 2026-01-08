"""
定时任务调度器模块
负责定时任务的业务逻辑、下次运行时间计算、任务生成等
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from calendar import monthrange

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QTableWidget, QTableWidgetItem, QPushButton, 
                            QHeaderView, QAbstractItemView, QWidget,
                            QAbstractScrollArea,QCheckBox,QMessageBox,
                            QDateEdit,QComboBox,QTextEdit,QLineEdit)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QFont

from ui.styles import StyleManager
from ui.ui import apply_drop_shadow
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
        start_time: str = ''
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
        # 添加阴影
        apply_drop_shadow(panel, blur_radius=10, color=QColor(0, 0, 0, 60), offset_x=0, offset_y=0)
        
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
        logger.info(f"加载定时任务表条数{0}",len(scheduled_tasks))
        self.table = QTableWidget()
        self.table.setRowCount(len(scheduled_tasks))
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["选择", "任务内容", "频率", "下次运行","优先级", "备注"])
        header = self.table.verticalHeader()
        header.setMinimumSectionSize(35) 
        for row, scheduled_task in enumerate(scheduled_tasks):
            # 复选框
            checkbox = QCheckBox()
            checkbox.stateChanged.connect(self.on_selection_changed)
            checkbox.setProperty('id', scheduled_task['id'])
            self.table.setCellWidget(row, 0, checkbox)
            self.table.setItem(row, 1, QTableWidgetItem(scheduled_task['title']))
            self.table.setItem(row, 2, QTableWidgetItem(scheduled_task['frequency']))
            self.table.setItem(row, 3, QTableWidgetItem(scheduled_task['next_run_at']))
            self.table.setItem(row, 4, QTableWidgetItem(scheduled_task['priority']))
            self.table.setItem(row, 5, QTableWidgetItem(scheduled_task['notes']))
        layout.addWidget(self.table)
        # 按内容自动调整列宽
        header = self.table.horizontalHeader()
        for i in range(self.table.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

        # 不拉伸最后一列
        header.setStretchLastSection(False)
        # 启用自动换行
        self.table.setWordWrap(True)
        # 按内容调整行高
        self.table.resizeRowsToContents()
        
        # 关闭省略策略：
        self.table.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.table.horizontalHeader().setTextElideMode(Qt.TextElideMode.ElideNone)
        # 允许滚动
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        # 按行选择
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.table.setMaximumHeight(400)
        # 应用美化样式
        style_manager = StyleManager()
        self.table.setStyleSheet(style_manager.get_stylesheet("history_table").format())
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
            "确认删除", 
            f"确定要将 {len(self.selected_tasks)} 个定时任务删除吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            deleted_count=0
            for task_id in self.selected_tasks:
                result=self.db_manager.delete_scheduled_task(task_id)
                if result:
                    deleted_count+=1
                
                QMessageBox.information(
                    self, 
                    "删除成功", 
                    f"成功删除 {deleted_count} 个定时任务"
                )

        except Exception as e:
            logger.error(f"删除任务失败: {str(e)}")
            QMessageBox.critical(self, "删除失败", f"删除任务时发生错误: {str(e)}")
        
        
    
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
                QMessageBox.warning(self, "提示", f"{f['label']} 为必填项")
                return
        # 创建任务
        try:
            result_id = self.task_scheduler.create_scheduled_task(
                title=task_data['title'],
                frequency=task_data['frequency'],
                priority=task_data['priority'],
                notes=task_data['notes'],
                due_date=task_data['due_date'],
                start_time=task_data.get('start_time')
            )
            if result_id:
                QMessageBox.information(self, "成功", f"定时任务创建成功")
                # 刷新任务列表
                self.close()
            else:
                QMessageBox.warning(self, "失败", "定时任务创建失败，请查看日志")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建定时任务时发生错误: {str(e)}")
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
    
    def get_editable_fields(self):
        """从配置中获取可编辑字段"""
        config = load_config()
        fields = config.get('schedule_task_fields', [])
        logger.info(f"获取到字段了{0}",fields)
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
        panel_layout.setContentsMargins(30, 30, 30, 30)
        panel_layout.setSpacing(5)
        
        # 样式表
        panel.setStyleSheet(style_manager.get_stylesheet("add_task_dialog").format())
        # 阴影
        apply_drop_shadow(panel, blur_radius=8, color=QColor(0, 0, 0, 60), offset_x=0, offset_y=0)

        # 输入字段
        self.inputs = {}
        
        for f in self.task_fields:
            lab = QLabel(f"{f['label']}{' *' if f.get('required') else ''}")
            panel_layout.addWidget(lab)
            # 创建控件时设置默认值
            default_value = f.get('default', '')
            # 根据字段类型创建不同的控件
            if f['type'] == 'date':
                w = QDateEdit()
                w.setStyleSheet(style_manager.get_stylesheet("calender"))
                w.setCalendarPopup(True)
                w.setDisplayFormat("yyyy-MM-dd")
                # 如果有默认值则设置日期，否则保持原逻辑
                if default_value:
                    w.setDate(QDate.fromString(default_value, "yyyy-MM-dd"))
                else:
                    w.setDate(QDate.currentDate().addDays(0))
            elif f['type'] == 'select':
                # 创建下拉选择框
                w = QComboBox()
                # 添加选项
                for option in f.get('options', []):
                    w.addItem(option)
                # 设置默认值
                if default_value and default_value in f.get('options', []):
                    w.setCurrentText(default_value)
            elif f['type'] == 'multiline':
                # 创建多行文本输入框
                w = QTextEdit()
                w.setPlaceholderText("请输入备注...")
                w.setMinimumHeight(100)  # 设置最小高度
                if default_value:
                    w.setText(str(default_value))
            else:
                w = QLineEdit(str(default_value))  # 设置文本默认值
            panel_layout.addWidget(w)
            self.inputs[f['name']] = w

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
        shadow_margin = 60  # 阴影空间
        # 让 panel 先自适应内容
        panel.setMinimumWidth(400)
        panel_layout.activate()
        panel.adjustSize()
        # 让壳比面板大一圈
        self.resize(panel.width() + shadow_margin * 2, panel.height() + shadow_margin * 2)
        # 把面板居中放到壳里
        panel.move(shadow_margin, shadow_margin)

    def get_data(self):
        """把表单内容打包成 dict 返回"""
        data = {}
        for name, w in self.inputs.items():
            if isinstance(w, QDateEdit):
                data[name] = w.date().toString("yyyy-MM-dd")
            elif isinstance(w, QComboBox):
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
