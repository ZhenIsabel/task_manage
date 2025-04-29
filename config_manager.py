import json
import os
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
    """保存任务到文件"""
    logger.debug("正在保存任务到文件...")
    try:
        # 获取所有任务字段定义
        config = load_config()
        editable_fields = config.get('task_fields', [])
        field_names = [f['name'] for f in editable_fields]

        tasks_data = []
        for task in tasks:
            data = task.get_data()
            # 补全缺失字段
            for name in field_names:
                if name not in data:
                    data[name] = ""
            tasks_data.append(data)
        
        # 保存到文件，使用UTF-8编码并确保中文直接保存
        with open(TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(tasks_data, f, indent=4, ensure_ascii=False)
        logger.info(f"成功保存了 {len(tasks_data)} 个任务")
        return True
    except Exception as e:
        logger.error(f"保存任务失败: {str(e)}")
        if parent:
            QMessageBox.warning(parent, "保存失败", f"保存任务失败: {str(e)}")
        return False