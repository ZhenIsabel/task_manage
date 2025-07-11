#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据迁移工具
将现有的tasks.json转换为支持历史记录的格式
"""

import json
import os
from datetime import datetime
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def migrate_tasks_data():
    """迁移任务数据到新的历史记录格式"""
    tasks_file = 'tasks.json'
    backup_file = 'tasks_backup.json'
    
    if not os.path.exists(tasks_file):
        logger.info("tasks.json文件不存在，无需迁移")
        return True
    
    try:
        # 读取现有数据
        logger.info("正在读取现有任务数据...")
        with open(tasks_file, 'r', encoding='utf-8') as f:
            old_tasks = json.load(f)
        
        if not old_tasks:
            logger.info("任务文件为空，无需迁移")
            return True
        
        # 创建备份
        logger.info("正在创建备份文件...")
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(old_tasks, f, indent=4, ensure_ascii=False)
        
        # 获取字段配置
        from config_manager import load_config
        config = load_config()
        field_names = [f['name'] for f in config.get('task_fields', [])]
        
        # 转换数据格式
        logger.info("正在转换数据格式...")
        new_tasks = []
        current_timestamp = datetime.now().isoformat()
        
        for task in old_tasks:
            # 创建新的任务数据结构
            new_task = {
                'id': task.get('id', f"migrated_task_{len(new_tasks)}"),
                'color': task.get('color', '#4ECDC4'),
                'position': task.get('position', {'x': 100, 'y': 100}),
                'completed': task.get('completed', False),
                'date': task.get('date', datetime.now().strftime('%Y-%m-%d')),
                'completed_date': task.get('completed_date', ''),
                'deleted': False,  # 逻辑删除标记
                'created_at': current_timestamp,
                'updated_at': current_timestamp
            }
            
            # 为每个字段创建历史记录
            for field_name in field_names:
                current_value = task.get(field_name, "")
                new_task[f'{field_name}_history'] = [{
                    'value': current_value,
                    'timestamp': current_timestamp,
                    'action': 'migrate'  # 标记为迁移操作
                }]
            
            new_tasks.append(new_task)
        
        # 保存新格式的数据
        logger.info("正在保存新格式的数据...")
        with open(tasks_file, 'w', encoding='utf-8') as f:
            json.dump(new_tasks, f, indent=4, ensure_ascii=False)
        
        logger.info(f"数据迁移完成！共迁移了 {len(new_tasks)} 个任务")
        logger.info(f"备份文件已保存为: {backup_file}")
        return True
        
    except Exception as e:
        logger.error(f"数据迁移失败: {str(e)}")
        return False

def verify_migration():
    """验证迁移结果"""
    tasks_file = 'tasks.json'
    
    if not os.path.exists(tasks_file):
        logger.error("tasks.json文件不存在")
        return False
    
    try:
        with open(tasks_file, 'r', encoding='utf-8') as f:
            tasks = json.load(f)
        
        if not tasks:
            logger.info("任务文件为空")
            return True
        
        # 检查第一个任务是否包含历史记录字段
        first_task = tasks[0]
        from config_manager import load_config
        config = load_config()
        field_names = [f['name'] for f in config.get('task_fields', [])]
        
        for field_name in field_names:
            history_key = f'{field_name}_history'
            if history_key not in first_task:
                logger.error(f"迁移验证失败：缺少字段 {history_key}")
                return False
        
        logger.info("迁移验证成功！")
        return True
        
    except Exception as e:
        logger.error(f"验证失败: {str(e)}")
        return False

if __name__ == "__main__":
    print("开始数据迁移...")
    if migrate_tasks_data():
        print("数据迁移成功！")
        if verify_migration():
            print("迁移验证通过！")
        else:
            print("迁移验证失败！")
    else:
        print("数据迁移失败！") 