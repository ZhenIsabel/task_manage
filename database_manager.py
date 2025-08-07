import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = 'tasks.db'):
        self.db_path = db_path
        self.conn = None
        self.init_database()
    
    def get_connection(self):
        """获取数据库连接"""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row  # 使查询结果可以通过列名访问
        return self.conn
    
    def close_connection(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def init_database(self):
        """初始化数据库表结构"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 创建配置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建任务表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                color TEXT DEFAULT '#4ECDC4',
                position_x INTEGER DEFAULT 100,
                position_y INTEGER DEFAULT 100,
                completed BOOLEAN DEFAULT FALSE,
                completed_date TEXT,
                deleted BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                text TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                due_date TEXT DEFAULT '',
                priority TEXT DEFAULT '',
                directory TEXT DEFAULT '',
                create_date TEXT DEFAULT ''
            )
        ''')
        
        # 创建任务字段值表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_history (
                task_id TEXT,
                field_name TEXT,
                field_value TEXT,
                action TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (task_id, field_name, timestamp),
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
        ''')
        
        # 创建索引以提高查询性能
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_completed ON tasks(completed)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_deleted ON tasks(deleted)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_history_task_id ON task_history(task_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_history_timestamp ON task_history(timestamp)')
        
        conn.commit()
        logger.info("数据库初始化完成")
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """保存配置到数据库"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 将配置转换为JSON字符串
            config_json = json.dumps(config, ensure_ascii=False)
            
            cursor.execute('''
                INSERT OR REPLACE INTO config (key, value, updated_at)
                VALUES (?, ?, ?)
            ''', ('app_config', config_json, datetime.now().isoformat()))
            
            conn.commit()
            logger.info("配置保存成功")
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {str(e)}")
            return False
    
    def load_config(self) -> Dict[str, Any]:
        """从数据库加载配置"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT value FROM config WHERE key = ?', ('app_config',))
            result = cursor.fetchone()
            
            if result:
                config = json.loads(result['value'])
                logger.info("配置加载成功")
                return config
            else:
                logger.info("配置不存在，返回默认配置")
                return {}
        except Exception as e:
            logger.error(f"加载配置失败: {str(e)}")
            return {}
    
    def save_task(self, task_data: Dict[str, Any]) -> bool:
        """保存任务到数据库"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 获取任务基本信息
            task_id = task_data['id']
            color = task_data.get('color', '#4ECDC4')
            position = task_data.get('position', {'x': 100, 'y': 100})
            completed = task_data.get('completed', False)
            completed_date = task_data.get('completed_date', '')
            deleted = task_data.get('deleted', False)
            
            # 获取配置中的字段定义
            from config_manager import load_config
            config = load_config()
            field_names = [f['name'] for f in config.get('task_fields', [])]
            
            # 构建字段值字典
            field_values = {}
            for field_name in field_names:
                if field_name in task_data:
                    field_values[field_name] = str(task_data[field_name])
                else:
                    field_values[field_name] = ''
            
            # 插入或更新任务信息（包含所有字段）
            cursor.execute('''
                INSERT OR REPLACE INTO tasks 
                (id, color, position_x, position_y, completed, completed_date, deleted, 
                 text, notes, due_date, priority, directory, create_date, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (task_id, color, position['x'], position['y'], completed, 
                  completed_date, deleted, field_values.get('text', ''),
                  field_values.get('notes', ''), field_values.get('due_date', ''),
                  field_values.get('priority', ''), field_values.get('directory', ''),
                  field_values.get('create_date', ''), datetime.now().isoformat()))
            
            # 如果是新任务，设置创建时间
            if not self._task_exists(task_id):
                cursor.execute('''
                    UPDATE tasks SET created_at = ? WHERE id = ?
                ''', (datetime.now().isoformat(), task_id))
            
            # 只有在没有迁移历史记录的情况下才保存字段历史记录
            if not task_data.get('_history_migrated', False):
                self._save_task_history(cursor, task_id, task_data)
            
            conn.commit()
            logger.info(f"任务 {task_id} 保存成功")
            return True
        except Exception as e:
            logger.error(f"保存任务失败: {str(e)}")
            return False
    
    def _task_exists(self, task_id: str) -> bool:
        """检查任务是否存在"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM tasks WHERE id = ?', (task_id,))
        return cursor.fetchone() is not None
    
    def _save_task_history(self, cursor, task_id: str, task_data: Dict[str, Any]):
        """保存任务字段历史记录"""
        # 获取配置中的字段定义
        from config_manager import load_config
        config = load_config()
        field_names = [f['name'] for f in config.get('task_fields', [])]
        
        current_timestamp = datetime.now().isoformat()
        
        for field_name in field_names:
            if field_name in task_data:
                current_value = str(task_data[field_name])
                
                # 检查是否需要添加历史记录 - 从tasks表中获取当前值
                cursor.execute('''
                    SELECT {} FROM tasks WHERE id = ?
                '''.format(field_name), (task_id,))
                
                result = cursor.fetchone()
                if not result or str(result[0]) != current_value:
                    # 值发生变化，添加历史记录
                    action = 'create' if not result else 'update'
                    cursor.execute('''
                        INSERT INTO task_history 
                        (task_id, field_name, field_value, action, timestamp)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (task_id, field_name, current_value, action, current_timestamp))
    
    def load_tasks(self, include_completed_today: bool = True) -> List[Dict[str, Any]]:
        """加载任务列表"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 构建查询条件
            conditions = ['deleted = FALSE']
            params = []
            
            if include_completed_today:
                # 包含未完成的任务和今天完成的任务
                today = datetime.now().strftime('%Y-%m-%d')
                conditions.append('(completed = FALSE OR completed_date = ?)')
                params.append(today)
            else:
                # 只包含未完成的任务
                conditions.append('completed = FALSE')
            
            # 查询任务基本信息
            query = f'''
                SELECT * FROM tasks 
                WHERE {' AND '.join(conditions)}
                ORDER BY created_at DESC
            '''
            cursor.execute(query, params)
            tasks = cursor.fetchall()
            
            # 转换为字典格式
            result = []
            for task in tasks:
                task_dict = dict(task)
                task_dict['position'] = {'x': task['position_x'], 'y': task['position_y']}
                result.append(task_dict)
            
            logger.info(f"成功加载 {len(result)} 个任务")
            return result
        except Exception as e:
            logger.error(f"加载任务失败: {str(e)}")
            return []
    
    def get_task_history(self, task_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """获取任务的历史记录"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT field_name, field_value, action, timestamp
                FROM task_history 
                WHERE task_id = ?
                ORDER BY timestamp ASC
            ''', (task_id,))
            
            history_records = cursor.fetchall()
            
            # 按字段分组历史记录
            field_history = {}
            for record in history_records:
                field_name = record['field_name']
                if field_name not in field_history:
                    field_history[field_name] = []
                
                field_history[field_name].append({
                    'value': record['field_value'],
                    'timestamp': record['timestamp'],
                    'action': record['action']
                })
            
            return field_history
        except Exception as e:
            logger.error(f"获取任务历史记录失败: {str(e)}")
            return {}
    
    def delete_task(self, task_id: str) -> bool:
        """逻辑删除任务"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE tasks 
                SET deleted = TRUE, updated_at = ?
                WHERE id = ?
            ''', (datetime.now().isoformat(), task_id))
            
            conn.commit()
            logger.info(f"任务 {task_id} 已逻辑删除")
            return True
        except Exception as e:
            logger.error(f"删除任务失败: {str(e)}")
            return False
    
    def migrate_from_json(self, config_file: str = 'config.json', tasks_file: str = 'tasks.json') -> bool:
        """从JSON文件迁移数据到数据库"""
        try:
            # 迁移配置
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self.save_config(config)
                logger.info("配置迁移完成")
            
            # 迁移任务数据
            if os.path.exists(tasks_file):
                with open(tasks_file, 'r', encoding='utf-8') as f:
                    tasks_data = json.load(f)
                
                for task_data in tasks_data:
                    # 处理历史记录格式的数据
                    if 'text_history' in task_data:
                        # 新格式：包含历史记录
                        processed_task = self._process_history_format_task(task_data)
                        # 标记为已迁移历史记录，避免重复处理
                        processed_task['_history_migrated'] = True
                    else:
                        # 旧格式：直接字段值
                        processed_task = self._process_old_format_task(task_data)
                    
                    self.save_task(processed_task)
                
                logger.info(f"任务数据迁移完成，共迁移 {len(tasks_data)} 个任务")
            
            return True
        except Exception as e:
            logger.error(f"数据迁移失败: {str(e)}")
            return False
    
    def _process_history_format_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理包含历史记录格式的任务数据"""
        # 获取最新值
        processed_task = {
            'id': task_data['id'],
            'color': task_data.get('color', '#4ECDC4'),
            'position': task_data.get('position', {'x': 100, 'y': 100}),
            'completed': task_data.get('completed', False),
            'completed_date': task_data.get('completed_date', ''),
            'deleted': task_data.get('deleted', False),
            'created_at': task_data.get('created_at', ''),
            'updated_at': task_data.get('updated_at', '')
        }
        
        # 从历史记录中获取最新值，并保存历史记录
        from config_manager import load_config
        config = load_config()
        field_names = [f['name'] for f in config.get('task_fields', [])]
        
        # 保存历史记录到数据库
        self._migrate_task_history(task_data)
        
        for field_name in field_names:
            history_key = f'{field_name}_history'
            if history_key in task_data and task_data[history_key]:
                latest_history = task_data[history_key][-1]
                processed_task[field_name] = latest_history.get('value', '')
            else:
                processed_task[field_name] = task_data.get(field_name, '')
        
        return processed_task
    
    def _migrate_task_history(self, task_data: Dict[str, Any]):
        """迁移任务的历史记录到数据库"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            from config_manager import load_config
            config = load_config()
            field_names = [f['name'] for f in config.get('task_fields', [])]
            
            task_id = task_data['id']
            
            for field_name in field_names:
                history_key = f'{field_name}_history'
                if history_key in task_data and task_data[history_key]:
                    history_list = task_data[history_key]
                    
                    for history_item in history_list:
                        value = history_item.get('value', '')
                        timestamp = history_item.get('timestamp', '')
                        action = history_item.get('action', 'update')
                        
                        # 插入历史记录
                        cursor.execute('''
                            INSERT OR IGNORE INTO task_history 
                            (task_id, field_name, field_value, action, timestamp)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (task_id, field_name, value, action, timestamp))
            
            conn.commit()
            logger.info(f"任务 {task_id} 的历史记录迁移完成")
            
        except Exception as e:
            logger.error(f"迁移任务历史记录失败: {str(e)}")
    
    def _process_old_format_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理旧格式的任务数据"""
        return {
            'id': task_data['id'],
            'color': task_data.get('color', '#4ECDC4'),
            'position': task_data.get('position', {'x': 100, 'y': 100}),
            'completed': task_data.get('completed', False),
            'completed_date': task_data.get('completed_date', ''),
            'deleted': False,
            'text': task_data.get('text', ''),
            'notes': task_data.get('notes', ''),
            'due_date': task_data.get('due_date', ''),
            'priority': task_data.get('priority', ''),
            'directory': task_data.get('directory', ''),
            'create_date': task_data.get('create_date', '')
        }

# 全局数据库管理器实例
_db_manager = None

def get_db_manager() -> DatabaseManager:
    """获取全局数据库管理器实例"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager 