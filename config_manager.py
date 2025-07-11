import json
import os
from datetime import datetime
from PyQt6.QtWidgets import QMessageBox
import logging
logger = logging.getLogger(__name__)

# 配置文件路径
CONFIG_FILE = 'config.json'
TASKS_FILE = 'tasks.json'

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
    """保存任务到文件，支持历史记录和逻辑删除"""
    logger.debug("正在保存任务到文件...")
    try:
        # 获取所有任务字段定义
        config = load_config()
        editable_fields = config.get('task_fields', [])
        field_names = [f['name'] for f in editable_fields]

        # 读取现有的任务数据（保留所有任务，包括已完成的）
        existing_tasks = []
        if os.path.exists(TASKS_FILE):
            try:
                with open(TASKS_FILE, 'r', encoding='utf-8') as f:
                    existing_tasks = json.load(f)
            except Exception as e:
                logger.warning(f"读取现有任务文件失败: {str(e)}")
                existing_tasks = []

        # 创建现有任务的映射，用于更新
        existing_task_map = {task.get('id'): task for task in existing_tasks}
        
        # 处理当前任务列表
        current_task_ids = set()
        for task in tasks:
            task_data = task.get_data()
            task_id = task_data.get('id')
            current_task_ids.add(task_id)
            
            # 获取当前时间戳
            current_timestamp = datetime.now().isoformat()
            
            
            # 如果是新任务，创建历史记录结构
            if task_id not in existing_task_map:
                # 新任务：为每个字段创建历史记录
                history_task_data = {
                    'id': task_id,
                    'color': task_data.get('color', '#4ECDC4'),
                    'position': task_data.get('position', {'x': 100, 'y': 100}),
                    'completed': task_data.get('completed', False),
                    'date': task_data.get('date', datetime.now().strftime('%Y-%m-%d')),
                    'completed_date': task_data.get('completed_date', ''),
                    'deleted': False,  # 逻辑删除标记
                    'created_at': current_timestamp,
                    'updated_at': current_timestamp
                }
                
                # 为每个字段创建历史记录
                for field_name in field_names:
                    current_value = task_data.get(field_name, "")
                    history_task_data[f'{field_name}_history'] = [{
                        'value': current_value,
                        'timestamp': current_timestamp,
                        'action': 'create'
                    }]
                
                existing_task_map[task_id] = history_task_data
            else:
                # 现有任务：更新历史记录
                existing_task = existing_task_map[task_id]
                old_completed = existing_task.get('completed', False)  # 先取旧值
                existing_task['updated_at'] = current_timestamp
                existing_task['completed'] = task_data.get('completed', False)
                existing_task['position'] = task_data.get('position', existing_task.get('position', {'x': 100, 'y': 100}))
                
                # 如果任务状态从未完成变为已完成，记录完成时间
                if task_data.get('completed', False) and not old_completed:
                    existing_task['completed_date'] = datetime.now().strftime('%Y-%m-%d')
                
                # 更新每个字段的历史记录
                for field_name in field_names:
                    current_value = task_data.get(field_name, "")
                    
                    # 确保历史记录字段存在
                    if f'{field_name}_history' not in existing_task:
                        existing_task[f'{field_name}_history'] = []
                    
                    # 检查值是否发生变化
                    last_history = existing_task[f'{field_name}_history'][-1] if existing_task[f'{field_name}_history'] else None
                    if not last_history or last_history.get('value') != current_value:
                        # 值发生变化，添加新的历史记录
                        existing_task[f'{field_name}_history'].append({
                            'value': current_value,
                            'timestamp': current_timestamp,
                            'action': 'update'
                        })
        
        # 保留所有任务（包括已完成的），但标记当前不显示的任务为逻辑删除
        for task_id, task_data in existing_task_map.items():
            if task_id not in current_task_ids:
                # 任务不在当前列表中，标记为逻辑删除（但不物理删除）
                task_data['deleted'] = True
                task_data['updated_at'] = datetime.now().isoformat()
        
        # 保存到文件
        with open(TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(existing_task_map.values()), f, indent=4, ensure_ascii=False)
        
        logger.info(f"成功保存了 {len(existing_task_map)} 个任务（包括历史记录）")
        return True
    except Exception as e:
        logger.error(f"保存任务失败: {str(e)}")
        if parent:
            QMessageBox.warning(parent, "保存失败", f"保存任务失败: {str(e)}")
        return False


def load_tasks_with_history():
    """从文件加载任务，支持历史记录"""
    logger.debug("正在从文件加载任务（支持历史记录）...")
    if not os.path.exists(TASKS_FILE):
        logger.info("任务文件不存在，返回空列表")
        return []
    
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
        
        logger.info(f"成功加载了 {len(visible_tasks)} 个可见任务")
        return visible_tasks
        
    except Exception as e:
        logger.error(f"加载任务失败: {str(e)}")
        return []