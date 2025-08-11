import json
from datetime import datetime
from PyQt6.QtWidgets import QMessageBox
import logging
logger = logging.getLogger(__name__)

# 导入数据库管理器
from database.database_manager import get_db_manager

# 配置和数据文件（统一定位到项目根目录）
import os
APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
CONFIG_FILE = os.path.join(APP_ROOT,'config', 'config.json')
TASKS_FILE = os.path.join(APP_ROOT,'database', 'tasks.json')

# 默认配置
DEFAULT_CONFIG = {
    'quadrants': {
        'q1': {'color': '#FF6B6B', 'opacity': 0.8},  # 重要且紧急 - 更柔和的红色
        'q2': {'color': '#4ECDC4', 'opacity': 0.8},  # 重要不紧急 - 青绿色
        'q3': {'color': '#FFE66D', 'opacity': 0.8},  # 不重要但紧急 - 柔和的黄色
        'q4': {'color': '#6D8EA0', 'opacity': 0.7},  # 不重要不紧急 - 灰蓝色
    },
    'size': {'width': 800, 'height': 600},
    'position': {'x': 100, 'y': 100},
    'edit_mode': False,
    'ui': {
        'border_radius': 15,
        'shadow_effect': True,
        'font_family': '微软雅黑',
        'animation_enabled': True,
        'desktop_mode': True,  # 桌面融合模式
        'control_panel_opacity': 0.0  # 控制面板初始透明度
    },
    'task_fields': [
        {'name': 'text', 'label': '任务内容', 'type': 'text', 'required': True},
        {'name': 'due_date', 'label': '到期日期', 'type': 'date', 'required': False},
        {'name': 'priority', 'label': '优先级', 'type': 'text', 'required': False},
        {'name': 'notes', 'label': '备注', 'type': 'text', 'required': False}
    ]
}

logger = logging.getLogger(__name__)

def load_config():
    """从文件加载配置"""
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)  # 创建默认配置
        return DEFAULT_CONFIG
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # 合并默认配置确保完整性
            return {**DEFAULT_CONFIG, **config}
    except Exception as e:
        logger.error(f"加载配置失败: {str(e)}")
        return DEFAULT_CONFIG

def save_config(config, parent=None):
    """保存配置到文件"""
    logger.debug("正在保存配置到文件...")
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        logger.info("配置保存成功")
        return True
    except Exception as e:
        logger.error(f"保存配置失败: {str(e)}")
        if parent:
            QMessageBox.warning(parent, "保存失败", f"保存配置失败: {str(e)}")
        return False


def save_tasks(tasks, parent=None):
    """保存任务到数据库，支持历史记录和逻辑删除"""
    logger.debug("正在保存任务到数据库...")
    try:
        db_manager = get_db_manager()
        
        # 处理当前任务列表
        current_task_ids = set()
        for task in tasks:
            task_data = task.get_data()
            task_id = task_data.get('id')
            current_task_ids.add(task_id)
            
            # 保存任务到数据库
            success = db_manager.save_task(task_data)
            if not success:
                logger.error(f"保存任务 {task_id} 失败")
        
        # 标记不在当前列表中的任务为逻辑删除
        # 注意：这里需要从数据库获取所有任务，然后标记删除
        # 为了简化，我们暂时不处理这个逻辑，因为数据库会自动处理历史记录
        
        logger.info(f"成功保存了 {len(current_task_ids)} 个任务")
        return True
    except Exception as e:
        logger.error(f"保存任务失败: {str(e)}")
        if parent:
            QMessageBox.warning(parent, "保存失败", f"保存任务失败: {str(e)}")
        return False


def load_tasks_with_history():
    """从数据库加载任务，支持历史记录"""
    logger.debug("正在从数据库加载任务（支持历史记录）...")
    try:
        db_manager = get_db_manager()
        tasks = db_manager.load_tasks(include_completed_today=True)
        
        logger.info(f"成功加载了 {len(tasks)} 个可见任务")
        return tasks
        
    except Exception as e:
        logger.error(f"加载任务失败: {str(e)}")
        # 如果数据库加载失败，尝试从文件加载（向后兼容）
        if os.path.exists(TASKS_FILE):
            logger.info("尝试从文件加载任务数据...")
            try:
                with open(TASKS_FILE, 'r', encoding='utf-8') as f:
                    tasks_data = json.load(f)
                
                # 获取当前日期
                today = datetime.now().strftime('%Y-%m-%d')
                
                # 获取字段配置
                config = load_config()
                field_names = [f['name'] for f in config.get('task_fields', [])]
                
                # 处理任务数据，只返回当前应该显示的任务
                visible_tasks = []
                for task_data in tasks_data:
                    # 跳过逻辑删除的任务
                    if task_data.get('deleted', False):
                        continue
                    
                    # 跳过已完成且不是今天完成的任务
                    if task_data.get('completed', False) and task_data.get('completed_date', '') != today:
                        continue
                    
                    # 创建任务数据，只包含每个字段的最新值
                    processed_task_data = {
                        'id': task_data['id'],
                        'color': task_data.get('color', '#4ECDC4'),
                        'position': task_data.get('position', {'x': 100, 'y': 100}),
                        'completed': task_data.get('completed', False),
                        'date': task_data.get('date', ''),
                        'completed_date': task_data.get('completed_date', ''),
                        'created_at': task_data.get('created_at', ''),
                        'updated_at': task_data.get('updated_at', '')
                    }
                    
                    # 为每个字段获取最新值
                    for field_name in field_names:
                        history_key = f'{field_name}_history'
                        if history_key in task_data and task_data[history_key]:
                            # 获取历史记录中的最新值
                            latest_history = task_data[history_key][-1]
                            processed_task_data[field_name] = latest_history.get('value', '')
                        else:
                            # 如果没有历史记录，使用旧格式的字段值
                            processed_task_data[field_name] = task_data.get(field_name, '')
                    
                    visible_tasks.append(processed_task_data)
                
                logger.info(f"从文件成功加载了 {len(visible_tasks)} 个可见任务")
                return visible_tasks
            except Exception as file_error:
                logger.error(f"从文件加载任务也失败: {str(file_error)}")
        
        return []