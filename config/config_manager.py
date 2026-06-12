import json
from datetime import datetime
import logging
from font_families import APP_FONT_FAMILY
logger = logging.getLogger(__name__)

# 导入数据库管理器
from database.database_manager import get_db_manager
from ui.notifications import show_error

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
    'color_ranges': {
        'q1': {'hue_range': 30, 'saturation_range': 20, 'value_range': 20},
        'q2': {'hue_range': 30, 'saturation_range': 20, 'value_range': 20},
        'q3': {'hue_range': 30, 'saturation_range': 20, 'value_range': 20},
        'q4': {'hue_range': 30, 'saturation_range': 20, 'value_range': 20},
    },
    'size': {'width': 800, 'height': 600},
    'position': {'x': 100, 'y': 100},
    'edit_mode': False,
    'ui': {
        'border_radius': 15,
        'shadow_effect': True,
        'font_family': APP_FONT_FAMILY,
        'animation_enabled': True,
        'desktop_mode': True,  # 桌面融合模式
        'control_panel_opacity': 0.0  # 控制面板初始透明度
    },
    'task_fields': [
        {'name': 'text', 'label': '任务内容', 'type': 'text', 'required': True},
        {'name': 'due_date', 'label': '到期日期', 'type': 'date', 'required': False},
        {'name': 'priority', 'label': '优先级', 'type': 'text', 'required': False},
        {'name': 'notes', 'label': '备注', 'type': 'text', 'required': False}
    ],
    'schedule_task_fields': [
        {'name': 'title', 'label': '任务标题', 'type': 'text', 'required': True},
        {'name': 'frequency', 'label': '频率', 'type': 'select',
         'options': ['daily', 'weekly', 'monthly', 'quarterly', 'yearly'],
         'default': 'monthly', 'required': True},
        {'name': 'urgency', 'label': '紧急程度', 'type': 'select',
         'options': ['高', '低'], 'default': '低', 'required': False},
        {'name': 'importance', 'label': '重要程度', 'type': 'select',
         'options': ['高', '低'], 'default': '低', 'required': False},
        {'name': 'notes', 'label': '备注', 'type': 'multiline', 'required': False},
        {'name': 'due_offset_days', 'label': '到期天数（触发后）', 'type': 'number',
         'min': 0, 'max': 3650, 'suffix': ' 天',
         'empty_text': '不设置（沿用固定到期日期）', 'required': False},
        {'name': 'start_time', 'label': '开始时间', 'type': 'date', 'required': False}
    ]
}

def _merge_defaults(defaults, config):
    """递归用默认值补齐配置中缺失的键；用户已有的值保持不变。"""
    merged = dict(config)
    for key, default_value in defaults.items():
        if key not in merged:
            merged[key] = default_value
        elif isinstance(default_value, dict) and isinstance(merged[key], dict):
            merged[key] = _merge_defaults(default_value, merged[key])
    return merged


def _merge_field_list(default_fields, user_fields):
    """按字段名补齐用户字段列表中缺失的默认字段。

    旧版本配置中已存在的字段列表会整体覆盖默认值，导致升级新增的字段
    （如 due_offset_days）不会出现在表单中。这里保留用户已有字段及其顺序，
    并把缺失的默认字段插入到接近其默认位置处。
    """
    if not isinstance(user_fields, list):
        return [dict(field) for field in default_fields]
    merged = list(user_fields)
    existing_names = {
        field.get('name') for field in merged if isinstance(field, dict)
    }
    for index, field in enumerate(default_fields):
        if field.get('name') not in existing_names:
            merged.insert(min(index, len(merged)), dict(field))
    return merged


def load_config():
    """从文件加载配置"""
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)  # 创建默认配置
        return DEFAULT_CONFIG

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # 合并默认配置确保完整性（含嵌套键）
            merged = _merge_defaults(DEFAULT_CONFIG, config)
            # 仅对定时任务字段列表按字段名合并，补齐升级新增的字段（如 due_offset_days）
            # 注意：不要合并 task_fields——它是用户可自定义的表单，
            # 合并会把用户已删除的默认字段（如已废弃的 priority）重新插回。
            merged['schedule_task_fields'] = _merge_field_list(
                DEFAULT_CONFIG['schedule_task_fields'],
                merged.get('schedule_task_fields'),
            )
            return merged
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
            show_error(parent, "保存失败", f"保存配置失败: {str(e)}")
        return False


def save_tasks(tasks, parent=None):
    """保存任务到数据库，支持历史记录和逻辑删除"""
    logger.debug("正在保存任务到数据库...")
    try:
        db_manager = get_db_manager()
        
        # 获取父窗口的中心坐标用于判断象限
        center_x = parent.width() // 2 if parent else 500
        center_y = parent.height() // 2 if parent else 400
        
        # 处理当前任务列表
        current_task_ids = set()
        for task in tasks:
            task_data = task.get_data()
            task_id = task_data.get('id')
            current_task_ids.add(task_id)
            
            # 根据坐标自动判断并更新紧急程度和重要程度
            position = task_data.get('position', {'x': 100, 'y': 100})
            position_x = position['x']
            position_y = position['y']
            
            # x轴判断紧急程度：右侧=高，左侧=低
            urgency = "高" if position_x > center_x else "低"
            
            # y轴判断重要程度：上方=高，下方=低
            importance = "高" if position_y < center_y else "低"
            
            task_data['urgency'] = urgency
            task_data['importance'] = importance
            
            # 同时更新任务对象本身的属性
            task.urgency = urgency
            task.importance = importance
            
            # 移除旧的priority字段（向后兼容）
            task_data.pop('priority', None)
            
            # 保存任务到数据库
            success = db_manager.save_task(task_data)
            if not success:
                logger.error(f"保存任务 {task_id} 失败")
        
        logger.info(f"成功保存了 {len(current_task_ids)} 个任务")
        return True
    except Exception as e:
        logger.error(f"保存任务失败: {str(e)}")
        if parent:
            show_error(parent, "保存失败", f"保存任务失败: {str(e)}")
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
