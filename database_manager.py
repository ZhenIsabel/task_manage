import sqlite3
import json
import os
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
import threading
import time

# 获取logger并确保配置正确
logger = logging.getLogger(__name__)

# 如果logger没有处理器，添加一个默认的处理器
if not logger.handlers:
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    
    # 添加处理器到logger
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)

class DatabaseManager:
    """数据库管理器 - 支持本地缓存和远程同步，并支持定时同步"""
    
    def __init__(self, db_path: str = 'tasks.db', remote_config: Optional[Dict] = None, sync_interval: int = 0):
        """
        :param db_path: 数据库文件路径
        :param remote_config: 远程服务器配置
        :param sync_interval: 定时同步间隔（秒），为0表示不自动同步
        """
        self.db_path = db_path
        self.conn = None
        self.remote_config = remote_config or {}
        self.api_base_url = self.remote_config.get('api_base_url', '')
        self.api_token = self.remote_config.get('api_token', '')
        self._sync_interval = sync_interval
        self._sync_thread = None
        self._stop_sync_event = threading.Event()
        
        logger.info(f"初始化数据库管理器: {db_path}")
        if self.api_base_url:
            logger.info(f"配置远程服务器: {self.api_base_url}")
        else:
            logger.info("使用本地模式")
            
        self.init_database()
        if self._sync_interval and self.api_base_url:
            self.start_periodic_sync(self._sync_interval)
    
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
        self.stop_periodic_sync()
    
    def init_database(self):
        """初始化数据库表结构"""
        try:
            logger.info("开始初始化数据库表结构")
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
            logger.debug("配置表创建/检查完成")
            
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
                    create_date TEXT DEFAULT '',
                    sync_status TEXT DEFAULT ''
                )
            ''')
            logger.debug("任务表创建/检查完成")
            
            # 创建任务历史记录表
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
            logger.debug("任务历史记录表创建/检查完成")
            
            # 创建同步状态表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sync_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    last_sync_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sync_type TEXT,
                    status TEXT,
                    message TEXT
                )
            ''')
            logger.debug("同步状态表创建/检查完成")
            
            # 创建索引以提高查询性能
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_completed ON tasks(completed)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_deleted ON tasks(deleted)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_sync_status ON tasks(sync_status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_history_task_id ON task_history(task_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_history_timestamp ON task_history(timestamp)')
            logger.debug("数据库索引创建/检查完成")
            
            conn.commit()
            logger.info("数据库初始化完成")
        except Exception as e:
            logger.error(f"数据库初始化失败: {str(e)}")
            raise
    
    def _make_api_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """发送API请求到远程服务器"""
        if not self.api_base_url:
            logger.debug("未配置API服务器地址，跳过API请求")
            return None
        
        try:
            url = f"{self.api_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_token}'
            }
            
            logger.debug(f"发送API请求: {method} {url}")
            if data:
                logger.debug(f"请求数据: {json.dumps(data, ensure_ascii=False)[:200]}...")
            
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            logger.debug(f"API响应状态: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.debug(f"API请求成功: {endpoint}")
                return result
            elif response.status_code == 500:
                logger.error(f"API请求失败：服务器内部错误")
                logger.error(f"错误信息: {response.text}")
            else:
                logger.error(f"API请求失败: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"API请求超时: {endpoint}")
            return None
        except requests.exceptions.ConnectionError:
            logger.error(f"API连接错误: {endpoint}")
            return None
        except Exception as e:
            logger.error(f"API请求异常: {str(e)}")
            return None
    
    def sync_to_server(self) -> bool:
        """同步本地数据到服务器"""
        try:
            # 获取需要同步的任务
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM tasks WHERE sync_status != 'synced'
            ''')
            unsynced_tasks = cursor.fetchall()
            
            if not unsynced_tasks:
                logger.info("没有需要同步的数据")
                return True
            
            # 同步每个任务
            for task in unsynced_tasks:
                task_data = dict(task)
                task_data['position'] = {'x': task['position_x'], 'y': task['position_y']}
                
                # 发送到服务器
                result = self._make_api_request('POST', '/api/tasks', task_data)
                if result:
                    # 更新同步状态
                    cursor.execute('''
                        UPDATE tasks SET sync_status = 'synced' WHERE id = ?
                    ''', (task['id'],))
                else:
                    logger.error(f"同步任务 {task['id']} 失败")
            
            conn.commit()
            
            # 记录同步状态
            cursor.execute('''
                INSERT INTO sync_status (sync_type, status, message)
                VALUES (?, ?, ?)
            ''', ('upload', 'success', f'同步了 {len(unsynced_tasks)} 个任务'))
            
            conn.commit()
            logger.info(f"成功同步 {len(unsynced_tasks)} 个任务到服务器")
            return True
            
        except Exception as e:
            logger.error(f"同步到服务器失败: {str(e)}")
            return False
    
    def sync_from_server(self) -> bool:
        """从服务器同步数据到本地"""
        try:
            # 获取服务器数据
            result = self._make_api_request('GET', '/api/tasks')
            if not result:
                logger.error("无法从服务器获取数据")
                return False
            
            server_tasks = result.get('tasks', [])
            
            # 更新本地数据
            conn = self.get_connection()
            cursor = conn.cursor()
            
            for task_data in server_tasks:
                # 检查本地是否有更新版本
                cursor.execute('''
                    SELECT updated_at FROM tasks WHERE id = ?
                ''', (task_data['id'],))
                
                local_task = cursor.fetchone()
                
                if not local_task or task_data['updated_at'] > local_task['updated_at']:
                    # 服务器数据更新，覆盖本地数据
                    self._save_task_to_local(cursor, task_data, 'synced')
            
            conn.commit()
            
            # 记录同步状态
            cursor.execute('''
                INSERT INTO sync_status (sync_type, status, message)
                VALUES (?, ?, ?)
            ''', ('download', 'success', f'从服务器同步了 {len(server_tasks)} 个任务'))
            
            conn.commit()
            logger.info(f"成功从服务器同步 {len(server_tasks)} 个任务")
            return True
            
        except Exception as e:
            logger.error(f"从服务器同步失败: {str(e)}")
            return False
    
    def _save_task_to_local(self, cursor, task_data: Dict[str, Any], sync_status: str = 'modified'):
        """保存任务到本地数据库"""
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
        
        # 插入或更新任务信息
        cursor.execute('''
            INSERT OR REPLACE INTO tasks 
            (id, color, position_x, position_y, completed, completed_date, deleted, 
             text, notes, due_date, priority, directory, create_date, updated_at, sync_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (task_id, color, position['x'], position['y'], completed, 
              completed_date, deleted, field_values.get('text', ''),
              field_values.get('notes', ''), field_values.get('due_date', ''),
              field_values.get('priority', ''), field_values.get('directory', ''),
              field_values.get('create_date', ''), task_data.get('updated_at', datetime.now().isoformat()),
              sync_status))
    
    def save_task(self, task_data: Dict[str, Any]) -> bool:
        """保存任务到数据库"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 保存到本地数据库
            self._save_task_to_local(cursor, task_data, 'modified')
            
            # 如果是新任务，设置创建时间
            if not self._task_exists(task_data['id']):
                cursor.execute('''
                    UPDATE tasks SET created_at = ? WHERE id = ?
                ''', (datetime.now().isoformat(), task_data['id']))
            
            # 只有在没有迁移历史记录的情况下才保存字段历史记录
            if not task_data.get('_history_migrated', False):
                self._save_task_history(cursor, task_data['id'], task_data)
            
            conn.commit()
            logger.info(f"任务 {task_data['id']} 本地保存成功")
            threading.Thread(target=self.sync_to_server).start()
            return True
        except Exception as e:
            logger.error(f"保存任务失败: {str(e)}")
            return False
        # 远程保存任务
        
    
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
            
            # 查询任务信息
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
            threading.Thread(target=self.sync_from_server).start()
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
                SET deleted = TRUE, updated_at = ?, sync_status = 'modified'
                WHERE id = ?
            ''', (datetime.now().isoformat(), task_id))
            
            conn.commit()
            logger.info(f"任务 {task_id} 已逻辑删除")
            threading.Thread(target=self.sync_to_server).start()
            return True
        except Exception as e:
            logger.error(f"删除任务失败: {str(e)}")
            return False
    
    def get_sync_status(self) -> Dict[str, Any]:
        """获取同步状态"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 获取最近的同步记录
            cursor.execute('''
                SELECT * FROM sync_status 
                ORDER BY last_sync_at DESC 
                LIMIT 5
            ''')
            sync_records = cursor.fetchall()
            
            # 获取待同步的任务数量
            cursor.execute('''
                SELECT COUNT(*) FROM tasks WHERE sync_status != 'synced'
            ''')
            pending_sync_count = cursor.fetchone()[0]
            
            return {
                'last_sync_records': [dict(record) for record in sync_records],
                'pending_sync_count': pending_sync_count,
                'server_connected': bool(self.api_base_url)
            }
        except Exception as e:
            logger.error(f"获取同步状态失败: {str(e)}")
            return {}

    # ========== 定时同步相关 ==========
    def start_periodic_sync(self, interval_seconds: int):
        """
        启动定时同步线程，每隔 interval_seconds 秒自动同步到服务器并从服务器拉取数据。
        """
        if self._sync_thread and self._sync_thread.is_alive():
            logger.info("定时同步线程已在运行")
            return
        if interval_seconds <= 0:
            logger.info("定时同步间隔无效，不启动定时同步")
            return
        self._sync_interval = interval_seconds
        self._stop_sync_event.clear()
        self._sync_thread = threading.Thread(target=self._periodic_sync_worker, daemon=True)
        self._sync_thread.start()
        logger.info(f"定时同步线程已启动，间隔 {interval_seconds} 秒")

    def stop_periodic_sync(self):
        """
        停止定时同步线程。
        """
        if self._sync_thread and self._sync_thread.is_alive():
            self._stop_sync_event.set()
            self._sync_thread.join(timeout=5)
            logger.info("定时同步线程已停止")

    def _periodic_sync_worker(self):
        """
        定时同步线程的工作函数。
        """
        logger.info("定时同步线程工作函数启动")
        while not self._stop_sync_event.is_set():
            try:
                logger.info("定时同步：开始同步到服务器")
                self.sync_to_server()
                logger.info("定时同步：开始从服务器同步")
                self.sync_from_server()
            except Exception as e:
                logger.error(f"定时同步异常: {str(e)}")
            # 等待下一个周期或直到被停止
            self._stop_sync_event.wait(self._sync_interval)
        logger.info("定时同步线程退出")

# 全局数据库管理器实例
_db_manager = None

def get_db_manager(sync_interval: int =3000) -> DatabaseManager:
    """获取全局数据库管理器实例，可选定时同步间隔（秒）"""
    global _db_manager
    if _db_manager is None:
        # 从配置文件加载远程配置
        remote_config = {}
        if os.path.exists('remote_config.json'):
            try:
                with open('remote_config.json', 'r', encoding='utf-8') as f:
                    remote_config = json.load(f)
            except Exception as e:
                logger.error(f"加载远程配置失败: {str(e)}")
        
        _db_manager = DatabaseManager(remote_config=remote_config, sync_interval=sync_interval)
    return _db_manager 