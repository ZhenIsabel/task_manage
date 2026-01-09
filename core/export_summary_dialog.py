"""导出概要对话框 - 选择时间区间并生成任务概要报告"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from PyQt6.QtCore import Qt, QDate, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QDateEdit, QPushButton, QProgressBar,
    QMessageBox, QFileDialog, QTextEdit
)
from PyQt6.QtGui import QColor, QMouseEvent

from ui.styles import StyleManager
from ui.ui import apply_drop_shadow
from database.database_manager import get_db_manager
from core.LLMService import get_llm_service

logger = logging.getLogger(__name__)


class SummaryWorker(QThread):
    """后台线程：查询任务历史并生成概要"""
    progress = pyqtSignal(str)  # 进度信息
    finished = pyqtSignal(bool, str, object)  # (成功, 消息, 数据)
    
    def __init__(self, start_date: str, end_date: str):
        super().__init__()
        self.start_date = start_date
        self.end_date = end_date
        
    def run(self):
        """执行查询和生成概要"""
        try:
            self.progress.emit("正在查询任务历史...")
            db_manager = get_db_manager()
            
            # 确保缓存已刷新到数据库
            db_manager.flush_cache_to_db()
            
            # 查询时间区间内有更新的任务
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            
            # 查询该时间段内有历史记录的任务ID
            cursor.execute('''
                SELECT DISTINCT task_id 
                FROM task_history 
                WHERE timestamp BETWEEN ? AND ?
            ''', (self.start_date, self.end_date + ' 23:59:59'))
            
            task_ids = [row[0] for row in cursor.fetchall()]
            
            if not task_ids:
                self.finished.emit(False, "所选时间区间内没有任务更新记录", None)
                return
            
            self.progress.emit(f"找到 {len(task_ids)} 个任务，正在获取详细信息...")
            
            # 获取这些任务的详细信息
            tasks_data = []
            for task_id in task_ids:
                cursor.execute('''
                    SELECT id, text, priority, notes, due_date, completed, 
                           completed_date, created_at, updated_at, directory
                    FROM tasks 
                    WHERE id = ?
                ''', (task_id,))
                
                row = cursor.fetchone()
                if row:
                    task_dict = dict(row)
                    
                    # 获取该任务的历史记录
                    cursor.execute('''
                        SELECT field_name, field_value, action, timestamp
                        FROM task_history
                        WHERE task_id = ? AND timestamp BETWEEN ? AND ?
                        ORDER BY timestamp ASC
                    ''', (task_id, self.start_date, self.end_date + ' 23:59:59'))
                    
                    history = []
                    for hist_row in cursor.fetchall():
                        history.append({
                            'field': hist_row[0],
                            'value': hist_row[1],
                            'action': hist_row[2],
                            'timestamp': hist_row[3]
                        })
                    
                    task_dict['history'] = history
                    tasks_data.append(task_dict)
            
            self.progress.emit(f"数据获取完成，准备生成概要...")
            
            # 调用 LLM 生成概要
            try:
                llm_service = get_llm_service()
                
                if not llm_service.is_available():
                    logger.warning("LLM服务不可用")
                    # 即使LLM不可用，也返回基础数据
                    for task in tasks_data:
                        task['summary'] = '（LLM服务不可用，无法生成总结）'
                    self.finished.emit(True, "数据获取成功（未使用AI总结）", tasks_data)
                    return
                
                schema = {
                            "type": "object",
                            "title":"summary",
                            "properties": {
                                    "task_id": {"type": "string"},
                                    "summary": {"type": "string"}
                            },
                            "required": ["task_id", "summary"],
                        }

                # 并行生成任务总结
                total_tasks = len(tasks_data)
                success_count = 0
                completed_count = 0
                
                # 使用线程池并行处理
                max_workers = min(10, total_tasks)  # 最多10个并发线程
                
                # #region agent log
                import json as _json; _log_file = r"d:\solutions\task_manage\.cursor\debug.log"; _log_data = {"sessionId":"debug-session","runId":"initial","hypothesisId":"B","location":"export_summary_dialog.py:128","message":"thread pool starting","data":{"max_workers":max_workers,"total_tasks":total_tasks,"thread_id":__import__('threading').current_thread().ident},"timestamp":__import__('time').time()*1000}
                try:
                    with open(_log_file, "a", encoding="utf-8") as _f: _f.write(_json.dumps(_log_data, ensure_ascii=False) + "\n")
                except: pass
                # #endregion
                
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # 提交所有任务到线程池
                    future_to_task = {
                        executor.submit(self._generate_single_task_summary, task, llm_service, schema): task 
                        for task in tasks_data
                    }
                    
                    # 处理完成的任务
                    for future in as_completed(future_to_task):
                        task = future_to_task[future]
                        completed_count += 1
                        
                        try:
                            # 获取结果
                            summary, is_success = future.result()
                            task['summary'] = summary
                            
                            if is_success:
                                success_count += 1
                                logger.info(f"任务 {task['id']} 总结生成成功")
                            else:
                                logger.warning(f"任务 {task['id']} 总结生成失败")
                            
                            # 更新进度
                            self.progress.emit(f"正在使用AI生成任务总结... ({completed_count}/{total_tasks})")
                            
                        except Exception as e:
                            logger.error(f"任务 {task['id']} 处理结果时出错: {str(e)}", exc_info=True)
                            task['summary'] = '（生成总结时出错）'
                
                # 所有任务处理完成
                if success_count == total_tasks:
                    self.finished.emit(True, f"概要生成成功（{success_count}/{total_tasks}）", tasks_data)
                elif success_count > 0:
                    self.finished.emit(True, f"概要部分生成成功（{success_count}/{total_tasks}）", tasks_data)
                else:
                    self.finished.emit(True, "数据获取成功（AI总结生成失败）", tasks_data)
                    
            except Exception as e:
                logger.error(f"调用LLM服务失败: {str(e)}", exc_info=True)
                # 出错时也返回基础数据
                for task in tasks_data:
                    task['summary'] = '（生成总结时出错）'
                self.finished.emit(True, "数据获取成功（生成总结时出错）", tasks_data)
            
        except Exception as e:
            logger.error(f"生成概要失败: {str(e)}", exc_info=True)
            self.finished.emit(False, f"生成概要失败: {str(e)}", None)
    
    def _generate_single_task_summary(self, task: Dict[str, Any], llm_service, schema: Dict[str, Any]) -> tuple:
        """
        生成单个任务的总结（用于并行执行）
        
        Args:
            task: 任务数据
            llm_service: LLM服务实例
            schema: JSON schema
            
        Returns:
            tuple: (summary_text, is_success)
        """
        # #region agent log
        import json as _json; _log_file = r"d:\solutions\task_manage\.cursor\debug.log"; _log_data = {"sessionId":"debug-session","runId":"initial","hypothesisId":"B","location":"export_summary_dialog.py:190","message":"single task summary start","data":{"task_id":task.get('id'),"thread_id":__import__('threading').current_thread().ident},"timestamp":__import__('time').time()*1000}
        try:
            with open(_log_file, "a", encoding="utf-8") as _f: _f.write(_json.dumps(_log_data, ensure_ascii=False) + "\n")
        except: pass
        # #endregion
        
        try:
            # 构建提示词
            messages = self._build_single_task_summary_prompt(task)
            
            # 调用LLM服务
            response_text = llm_service.generate_response_sync(messages, schema)
            
            if response_text:
                # 解析响应
                summary_result = llm_service.parse_json_response(response_text)
                if summary_result and 'summary' in summary_result:
                    return (summary_result['summary'], True)
                else:
                    # 解析失败
                    logger.error(f"任务 {task['id']} LLM响应格式错误")
                    return ('（总结生成失败）', False)
            else:
                # LLM调用失败
                logger.error(f"任务 {task['id']} LLM调用返回空")
                return ('（总结生成失败）', False)
        
        except Exception as e:
            logger.error(f"任务 {task['id']} 生成总结时出错: {str(e)}", exc_info=True)
            return ('（生成总结时出错）', False)
    
    def _build_single_task_summary_prompt(self, task: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        构建单个任务总结的提示词
        
        Args:
            task: 单个任务数据
            
        Returns:
            消息列表 [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
        """
        system_content = """你是一个任务总结助手。你会收到一个任务的信息和它的变更历史记录。

            你的任务是：
            1. 分析任务的变更历史，理解任务的执行情况，无需关注截止时间的调整
            2. 生成简洁的工作概要（200-400字）
            3. 概要应突出关键进展、重要变更和最终状态。
            4. 用中文回答
            """
        
        # 构建用户内容
        user_content = "以下是需要总结的任务信息：\n\n"
        user_content += f"- ID: {task.get('id')}\n"
        user_content += f"- 内容: {task.get('text', '无')}\n"
        user_content += f"- 优先级: {task.get('priority', '无')}\n"
        user_content += f"- 状态: {'已完成' if task.get('completed') else '进行中'}\n"
        user_content += f"- 创建时间: {task.get('created_at', '无')}\n"
        user_content += f"- 完成时间: {task.get('completed_date', '未完成')}\n"
        
        # 添加历史记录
        history = task.get('history', [])
        if history:
            user_content += f"- 变更历史（{len(history)}条）:\n"
            for h in history:
                action_text = {
                    'created': '创建',
                    'updated': '更新',
                    'completed': '完成',
                    'deleted': '删除'
                }.get(h.get('action'), h.get('action'))
                
                user_content += f"  [{h.get('timestamp')}] {action_text} - "
                user_content += f"{h.get('field')}: {h.get('value')}\n"
        else:
            user_content += "- 变更历史: 无\n"
        
        user_content += "\n请为这个任务生成工作概要。"
        
        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]
    

class ExportSummaryDialog(QDialog):
    """导出概要对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.worker = None
        self.summary_data = None
        
        # 创建UI
        self.setup_ui()
        
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("生成概要")
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
        
        # 说明
        desc_label = QLabel("选择时间区间，系统将导出该期间内所有更新过的任务概要。")
        desc_label.setStyleSheet("font-size: 12px; color: #666;")
        desc_label.setWordWrap(True)
        panel_layout.addWidget(desc_label)
        
        # 日期选择区域
        date_layout = QHBoxLayout()
        
        # 开始日期
        start_label = QLabel("开始日期:")
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.start_date_edit.setDate(QDate.currentDate().addDays(-30))  # 默认30天前
        
        # 结束日期
        end_label = QLabel("结束日期:")
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.end_date_edit.setDate(QDate.currentDate())
        
        date_layout.addWidget(start_label)
        date_layout.addWidget(self.start_date_edit)
        date_layout.addSpacing(20)
        date_layout.addWidget(end_label)
        date_layout.addWidget(self.end_date_edit)
        
        panel_layout.addLayout(date_layout)
        
        # 快捷选择按钮
        quick_layout = QHBoxLayout()
        quick_label = QLabel("快捷选择:")
        quick_layout.addWidget(quick_label)
        
        btn_7days = QPushButton("近7天")
        btn_7days.clicked.connect(lambda: self._set_date_range(7))
        quick_layout.addWidget(btn_7days)
        
        btn_30days = QPushButton("近30天")
        btn_30days.clicked.connect(lambda: self._set_date_range(30))
        quick_layout.addWidget(btn_30days)
        
        btn_90days = QPushButton("近90天")
        btn_90days.clicked.connect(lambda: self._set_date_range(90))
        quick_layout.addWidget(btn_90days)
        
        quick_layout.addStretch()
        panel_layout.addLayout(quick_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 0)  # 不确定进度
        panel_layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 12px; color: #666;")
        self.status_label.setVisible(False)
        panel_layout.addWidget(self.status_label)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.generate_button = QPushButton("生成概要")
        self.generate_button.clicked.connect(self._generate_summary)
        button_layout.addWidget(self.generate_button)
        
        self.export_button = QPushButton("导出Excel")
        self.export_button.clicked.connect(self._export_to_excel)
        self.export_button.setEnabled(False)
        button_layout.addWidget(self.export_button)
        
        cancel_button = QPushButton("关闭")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        panel_layout.addLayout(button_layout)
        
        main_layout.addWidget(panel)
        
        # 居中显示
        self.adjustSize()
        self.center_on_parent()
        # 添加阴影
        apply_drop_shadow(panel, blur_radius=10, color=QColor(0, 0, 0, 60), offset_x=0, offset_y=0)
        
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

    
    def _set_date_range(self, days: int):
        """设置日期范围"""
        self.end_date_edit.setDate(QDate.currentDate())
        self.start_date_edit.setDate(QDate.currentDate().addDays(-days))
    
    def _generate_summary(self):
        """生成概要"""
        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_date_edit.date().toString("yyyy-MM-dd")
        
        # 验证日期
        if start_date > end_date:
            QMessageBox.warning(self, "日期错误", "开始日期不能晚于结束日期")
            return
        
        # 禁用按钮
        self.generate_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setVisible(True)
        self.status_label.setText("正在生成概要...")
        
        # 启动后台线程
        self.worker = SummaryWorker(start_date, end_date)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.start()
    
    def _on_progress(self, message: str):
        """更新进度"""
        self.status_label.setText(message)
    
    def _on_finished(self, success: bool, message: str, data):
        """生成完成"""
        self.progress_bar.setVisible(False)
        self.generate_button.setEnabled(True)
        
        if success:
            self.summary_data = data
            self.export_button.setEnabled(True)
            self.status_label.setText(f"✓ {message}，共 {len(data)} 个任务")
            self.status_label.setStyleSheet("font-size: 12px; color: #4ECDC4;")
        else:
            self.status_label.setText(f"✗ {message}")
            self.status_label.setStyleSheet("font-size: 12px; color: #ff4757;")
    
    def _export_to_excel(self):
        """导出到Excel"""
        if not self.summary_data:
            QMessageBox.warning(self, "提示", "没有可导出的数据")
            return
        
        try:
            import pandas as pd
        except ImportError:
            QMessageBox.critical(self, "导出失败", "未安装pandas库，无法导出为Excel。\n\n请先安装: pip install pandas")
            return
        
        try:
            import openpyxl
        except ImportError:
            QMessageBox.critical(self, "导出失败", "未安装openpyxl库，无法导出为Excel。\n\n请先安装: pip install openpyxl")
            return
        
        # 选择保存位置
        desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
        default_filename = os.path.join(
            desktop_path,
            f"任务概要_{self.start_date_edit.date().toString('yyyyMMdd')}-{self.end_date_edit.date().toString('yyyyMMdd')}.xlsx"
        )
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "保存任务概要",
            default_filename,
            "Excel文件 (*.xlsx);;所有文件 (*)"
        )
        
        if not filename:
            return
        
        try:
            # 转换为DataFrame
            df = pd.DataFrame(self.summary_data)
            
            # 重新排列列的顺序
            column_order = [
                'id', 'text', 'priority', 'completed',
                'created_at', 'updated_at', 'completed_date', 'due_date',
                'directory', 'summary', 'notes'
            ]
            
            # 只保留存在的列
            existing_columns = [col for col in column_order if col in df.columns]
            df = df[existing_columns]
            
            # 重命名列
            column_names = {
                'id': '任务ID',
                'text': '任务内容',
                'priority': '优先级',
                'completed': '完成状态',
                'created_at': '创建时间',
                'updated_at': '最后更新',
                'completed_date': '完成时间',
                'due_date': '截止日期',
                'directory': '目录',
                'summary': '工作概要',
                'notes': '备注'
            }
            df = df.rename(columns=column_names)
            
            # 导出到Excel
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='任务概要')
                
                # 调整列宽
                worksheet = writer.sheets['任务概要']
                for i, col in enumerate(df.columns):
                    # 计算列宽（基于列名和内容的最大长度）
                    max_length = max(
                        len(str(col)),
                        df[col].astype(str).str.len().max() if len(df) > 0 else 0
                    )
                    worksheet.column_dimensions[chr(65 + i)].width = min(max_length + 2, 50)
            
            QMessageBox.information(self, "导出成功", f"任务概要已导出到:\n{filename}")
            logger.info(f"成功导出 {len(df)} 个任务概要到: {filename}")
            
            # 导出成功后关闭对话框
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出任务概要时发生错误:\n{str(e)}")
            logger.error(f"导出任务概要失败: {str(e)}", exc_info=True)
    
    # 拖动实现
    def mousePressEvent(self, e: QMouseEvent):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.pos()
    
    def mouseMoveEvent(self, e: QMouseEvent):
        if self._drag_pos and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)
    
    def mouseReleaseEvent(self, e: QMouseEvent):
        self._drag_pos = None
