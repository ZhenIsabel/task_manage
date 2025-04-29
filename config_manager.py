import json
import os
from PyQt6.QtWidgets import QMessageBox

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


def load_tasks(self):
    """从文件加载任务"""
    print("正在从文件加载任务...")
    if not os.path.exists(TASKS_FILE):
        print("任务文件不存在，跳过加载")
        return
    
    try:
        print("正在读取任务文件...")
        with open(TASKS_FILE, 'r', encoding='utf-8') as f:
            tasks_data = json.load(f)
        
        # 获取当前日期
        today = datetime.now().strftime('%Y-%m-%d')
        
        # 清除当前所有任务
        for task in self.tasks:
            task.deleteLater()
        self.tasks.clear()
        
        # 加载未完成的任务或当天完成的任务
        for task_data in tasks_data:
            # 跳过已完成且不是今天完成的任务
            if task_data.get('completed', False) and task_data.get('date', '') != today:
                continue
            
            # 获取所有可能的字段
            field_values = {}
            for meta in TaskLabel.get_editable_fields():
                field_name = meta['name']
                # 如果任务数据中有该字段，则使用；否则使用默认值或空字符串
                field_values[field_name] = task_data.get(field_name, "")
            
            # 创建任务标签 - 支持所有自定义字段
            task = TaskLabel(
                task_id=task_data.get('id', f"task_{len(self.tasks)}_{datetime.now().strftime('%Y%m%d%H%M%S')}"),
                color=task_data.get('color', "#4ECDC4"),
                parent=self,
                completed=task_data.get('completed', False),
                **field_values  # 使用字典解包传递所有字段
            )
            
            # 设置位置
            if 'position' in task_data:
                task.move(task_data['position']['x'], task_data['position']['y'])
            
            # 连接信号
            task.deleteRequested.connect(self.delete_task)
            task.statusChanged.connect(self.save_tasks)
            
            # 显示任务并添加到列表
            task.show()
            self.tasks.append(task)
        print(f"成功加载了 {len(self.tasks)} 个任务")
    except Exception as e:
        print(f"加载任务失败: {str(e)}")
        QMessageBox.warning(self, "加载失败", f"加载任务失败: {str(e)}")


def save_config(config, parent=None):
    """保存配置到文件"""
    print("正在保存配置到文件...")
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        print("配置保存成功")
        return True
    except Exception as e:
        print(f"保存配置失败: {str(e)}")
        if parent:
            QMessageBox.warning(parent, "保存失败", f"保存配置失败: {str(e)}")
        return False


def save_tasks(tasks, parent=None):
    """保存任务到文件"""
    print("正在保存任务到文件...")
    try:
        # 获取所有任务数据
        tasks_data = [task.get_data() for task in tasks]
        
        # 保存到文件，使用UTF-8编码并确保中文直接保存
        with open(TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(tasks_data, f, indent=4, ensure_ascii=False)
        print(f"成功保存了 {len(tasks_data)} 个任务")
        return True
    except Exception as e:
        print(f"保存任务失败: {str(e)}")
        if parent:
            QMessageBox.warning(parent, "保存失败", f"保存任务失败: {str(e)}")
        return False