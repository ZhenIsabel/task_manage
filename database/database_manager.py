import sqlite3
import json
import os
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
import threading
import copy

# 获取logger并确保配置正确
logger = logging.getLogger(__name__)

if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = 'tasks.db', remote_config: Optional[Dict] = None, sync_interval: int = 0, flush_interval: int = 5):
        """
        :param db_path: 数据库文件路径
        :param remote_config: 远程服务器配置
        :param sync_interval: 定时同步间隔（秒），为0表示不自动同步
        :param flush_interval: 内存数据写入磁盘的间隔（秒）
        """
        # 规范化数据库路径：相对路径基于项目根目录
        self.db_path = db_path if os.path.isabs(db_path) else os.path.join(APP_ROOT,'database', db_path)
        self.conn = None
        self.remote_config = remote_config or {}
        self.api_base_url = self.remote_config.get('api_base_url', '')
        self.api_token = self.remote_config.get('api_token', '')
        self._sync_interval = sync_interval
        self._sync_thread = None
        self._stop_sync_event = threading.Event()

        # 内存缓存
        self._task_cache = {}  # id -> task_data
        self._task_history_cache = []  # [(task_id, field_name, field_value, action, timestamp)]
        self._deleted_task_ids = set()
        self._cache_lock = threading.Lock()
        self._cache_dirty = False

        # 定时flush相关
        self._flush_interval = flush_interval
        self._flush_thread = None
        self._stop_flush_event = threading.Event()

        logger.info(f"初始化数据库管理器: {db_path}")
        if self.api_base_url:
            logger.info(f"配置远程服务器: {self.api_base_url}")
        else:
            logger.info("使用本地模式")

        self.init_database()
        self._load_all_tasks_to_cache()
        self.start_periodic_flush(self._flush_interval)
        # 启用定时同步
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
        self.flush_cache_to_db()
        if self.conn:
            self.conn.close()
            self.conn = None
        self.stop_periodic_sync()
        self.stop_periodic_flush()

    def init_database(self):
        """初始化数据库表结构"""
        try:
            logger.info("开始初始化数据库表结构")
            conn = self.get_connection()
            cursor = conn.cursor()
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

    def _load_all_tasks_to_cache(self):
        """启动时加载所有任务到内存缓存"""
        try:
            with self._cache_lock:
                self._task_cache.clear()
                self._deleted_task_ids.clear()
                
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM tasks')
                
                for row in cursor.fetchall():
                    task = dict(row)
                    self._task_cache[task['id']] = task
                    if task.get('deleted'):
                        self._deleted_task_ids.add(task['id'])
                
                logger.info(f"从数据库加载了 {len(self._task_cache)} 个任务到缓存")
                self._cache_dirty = False
        except Exception as e:
            logger.error(f"加载任务到缓存失败: {str(e)}")
            # 如果数据库加载失败，创建空的缓存
            with self._cache_lock:
                self._task_cache.clear()
                self._deleted_task_ids.clear()
                self._cache_dirty = False

    def flush_cache_to_db(self):
        """将内存缓存中的更改批量写入数据库"""
        with self._cache_lock:
            if not self._cache_dirty:
                return
            conn = self.get_connection()
            cursor = conn.cursor()
            
            try:
                # 批量写入tasks
                for task_id, task in self._task_cache.items():
                    cursor.execute('''
                        INSERT OR REPLACE INTO tasks 
                        (id, color, position_x, position_y, completed, completed_date, deleted, 
                         text, notes, due_date, priority, directory, create_date, updated_at, sync_status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        task['id'],
                        task.get('color', '#4ECDC4'),
                        task.get('position_x', 100),
                        task.get('position_y', 100),
                        task.get('completed', False),
                        task.get('completed_date', ''),
                        task.get('deleted', False),
                        task.get('text', ''),
                        task.get('notes', ''),
                        task.get('due_date', ''),
                        task.get('priority', ''),
                        task.get('directory', ''),
                        task.get('create_date', ''),
                        task.get('updated_at', datetime.now().isoformat()),
                        task.get('sync_status', ''),
                        task.get('created_at', datetime.now().isoformat())
                    ))
                
                # 批量写入历史记录
                if self._task_history_cache:
                    for hist in self._task_history_cache:
                        cursor.execute('''
                            INSERT OR IGNORE INTO task_history 
                            (task_id, field_name, field_value, action, timestamp)
                            VALUES (?, ?, ?, ?, ?)
                        ''', hist)
                    # logger.info(f"写入 {len(self._task_history_cache)} 条历史记录到数据库")
                    self._task_history_cache.clear()
                
                conn.commit()
                self._cache_dirty = False
                # logger.info("内存缓存已写入数据库")
            except Exception as e:
                logger.error(f"写入数据库失败: {str(e)}")
                conn.rollback()
                raise

    def start_periodic_flush(self, interval_seconds: int):
        """启动定时flush线程，将内存缓存定期写入数据库"""
        if self._flush_thread and self._flush_thread.is_alive():
            return
        if interval_seconds <= 0:
            return
        self._flush_interval = interval_seconds
        self._stop_flush_event.clear()
        self._flush_thread = threading.Thread(target=self._periodic_flush_worker, daemon=True)
        self._flush_thread.start()
        logger.info(f"定时flush线程已启动，间隔 {interval_seconds} 秒")

    def stop_periodic_flush(self):
        """停止定时flush线程"""
        if self._flush_thread and self._flush_thread.is_alive():
            self._stop_flush_event.set()
            self._flush_thread.join(timeout=5)
            logger.info("定时flush线程已停止")

    def _periodic_flush_worker(self):
        """定时flush线程的工作函数"""
        logger.info("定时flush线程工作函数启动")
        while not self._stop_flush_event.is_set():
            try:
                self.flush_cache_to_db()
            except Exception as e:
                logger.error(f"定时flush异常: {str(e)}")
            self._stop_flush_event.wait(self._flush_interval)
        logger.info("定时flush线程退出")

    def sync_to_server(self) -> bool:
        """同步本地数据到服务器"""
        try:
            with self._cache_lock:
                unsynced_tasks = [copy.deepcopy(task) for task in self._task_cache.values() if task.get('sync_status') != 'synced']
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
                    with self._cache_lock:
                        self._task_cache[task['id']]['sync_status'] = 'synced'
                        self._cache_dirty = True
                else:
                    logger.error(f"同步任务 {task['id']} 失败")
            # 记录同步状态
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO sync_status (sync_type, status, message)
                VALUES (?, ?, ?)
            ''', ('upload', 'success', f'同步了 {len(unsynced_tasks)} 个任务'))
            conn.commit()
            # logger.info(f"成功同步 {len(unsynced_tasks)} 个任务到服务器")
            return True
        except Exception as e:
            logger.error(f"同步到服务器失败: {str(e)}")
            return False

    def sync_from_server(self) -> bool:
        """从服务器同步数据到本地"""
        try:
            result = self._make_api_request('GET', '/api/tasks')
            if not result:
                logger.error("无法从服务器获取数据")
                return False
            server_tasks = result.get('tasks', [])
            updated_count = 0
            with self._cache_lock:
                for task_data in server_tasks:
                    local_task = self._task_cache.get(task_data['id'])
                    if (not local_task) or (task_data['updated_at'] > local_task.get('updated_at', '')):
                        self._save_task_to_cache(task_data, 'synced')
                        updated_count += 1
                self._cache_dirty = True
            # 记录同步状态
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO sync_status (sync_type, status, message)
                VALUES (?, ?, ?)
            ''', ('download', 'success', f'从服务器同步了 {len(server_tasks)} 个任务'))
            conn.commit()
            # logger.info(f"成功从服务器同步 {len(server_tasks)} 个任务")
            return True
        except Exception as e:
            logger.error(f"从服务器同步失败: {str(e)}")
            return False

    def clear_server_and_upload(self) -> bool:
        """清空服务器任务后，用本地任务覆盖上传。
        步骤：
        1) 拉取服务器现有任务列表
        2) 逐个调用DELETE删除服务器任务
        3) 将本地缓存中的任务逐个POST到服务器
        """
        if not self.api_base_url:
            logger.error("未配置API服务器地址，无法执行清空并覆盖")
            return False

        try:
            # 1) 获取服务器任务
            server_result = self._make_api_request('GET', '/api/tasks')
            if server_result is None:
                logger.error("获取服务器任务失败")
                return False
            server_tasks = server_result.get('tasks', [])

            # 2) 删除服务器任务
            delete_failed = 0
            for task in server_tasks:
                task_id = task.get('id')
                if not task_id:
                    continue
                result = self._make_api_request('DELETE', f"/api/tasks/{task_id}")
                if result is None:
                    delete_failed += 1
                    logger.error(f"删除服务器任务失败: {task_id}")

            if delete_failed:
                logger.warning(f"有 {delete_failed} 条服务器任务删除失败，继续覆盖上传")

            # 3) 上传本地任务到服务器
            with self._cache_lock:
                local_tasks = [copy.deepcopy(task) for task in self._task_cache.values()]
            uploaded = 0
            for task in local_tasks:
                task_data = dict(task)
                task_data['position'] = {'x': task['position_x'], 'y': task['position_y']}
                result = self._make_api_request('POST', '/api/tasks', task_data)
                if result:
                    uploaded += 1
                else:
                    logger.error(f"上传任务失败: {task['id']}")

            # 记录同步状态
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO sync_status (sync_type, status, message)
                VALUES (?, ?, ?)
            ''', ('overwrite_server', 'success', f'删除 {len(server_tasks)} 条服务器任务，上传 {uploaded} 条本地任务'))
            conn.commit()

            logger.info(f"清空并覆盖完成：删除服务器 {len(server_tasks)}，上传本地 {uploaded}")
            return True
        except Exception as e:
            logger.error(f"清空服务器并覆盖失败: {str(e)}")
            return False

    def _save_task_to_cache(self, task_data: Dict[str, Any], sync_status: str = 'modified'):
        """保存任务到内存缓存"""
        task_id = task_data['id']
        color = task_data.get('color', '#4ECDC4')
        position = task_data.get('position', {'x': 100, 'y': 100})
        completed = task_data.get('completed', False)
        completed_date = task_data.get('completed_date', '')
        deleted = task_data.get('deleted', False)
        
        from config.config_manager import load_config
        config = load_config()
        field_names = [f['name'] for f in config.get('task_fields', [])]
        field_values = {}
        for field_name in field_names:
            if field_name in task_data:
                field_values[field_name] = str(task_data[field_name]) if task_data[field_name] is not None else ''
            else:
                field_values[field_name] = ''
        
        task = {
            'id': task_id,
            'color': color,
            'position_x': position['x'],
            'position_y': position['y'],
            'completed': completed,
            'completed_date': completed_date,
            'deleted': deleted,
            'text': field_values.get('text', ''),
            'notes': field_values.get('notes', ''),
            'due_date': field_values.get('due_date', ''),
            'priority': field_values.get('priority', ''),
            'directory': field_values.get('directory', ''),
            'create_date': field_values.get('create_date', ''),
            'updated_at': task_data.get('updated_at', datetime.now().isoformat()),
            'sync_status': sync_status,
            'created_at': task_data.get('created_at', datetime.now().isoformat())
        }
        
        self._task_cache[task_id] = task
        if deleted:
            self._deleted_task_ids.add(task_id)
        self._cache_dirty = True

    def save_task(self, task_data: Dict[str, Any]) -> bool:
        """保存任务到内存缓存，延迟写入数据库"""
        try:
            with self._cache_lock:
                is_new = not self._task_exists_in_cache(task_data['id'])
                
                # 先记录字段历史（排除位置字段，因为位置变化太频繁）
                # 在保存到缓存之前记录历史，这样能正确比较新旧值
                self._save_task_history_to_cache(task_data['id'], task_data)
                
                # 然后保存任务到缓存
                self._save_task_to_cache(task_data, 'modified')
                
                # 为新任务设置创建时间
                if is_new:
                    self._task_cache[task_data['id']]['created_at'] = datetime.now().isoformat()
                
                self._cache_dirty = True
            
            # logger.info(f"任务 {task_data['id']} 已写入内存缓存")
            return True
        except Exception as e:
            logger.error(f"保存任务失败: {str(e)}")
            return False

    def _task_exists_in_cache(self, task_id: str) -> bool:
        """检查任务是否在内存缓存中存在"""
        return task_id in self._task_cache

    def _save_task_history_to_cache(self, task_id: str, task_data: Dict[str, Any]):
        """保存任务字段历史记录到内存缓存"""
        from config.config_manager import load_config
        config = load_config()
        field_names = [f['name'] for f in config.get('task_fields', [])]
        current_timestamp = datetime.now().isoformat()
        
        logger.debug(f"开始保存任务 {task_id} 的历史记录")
        # logger.debug(f"字段名称: {field_names}")
        # logger.debug(f"任务数据: {task_data}")
        
        # 排除位置字段，因为位置变化太频繁
        excluded_fields = {'position_x', 'position_y'}
        
        for field_name in field_names:
            if field_name in task_data and field_name not in excluded_fields:
                current_value = str(task_data[field_name]) if task_data[field_name] is not None else ''
                prev_value = ''
                
                # 获取之前的字段值
                if task_id in self._task_cache:
                    prev_value = str(self._task_cache[task_id].get(field_name, '')) if self._task_cache[task_id].get(field_name) is not None else ''
                
                logger.debug(f"字段 {field_name}: 之前='{prev_value}', 现在='{current_value}'")
                
                # 只有当值真正发生变化时才记录历史
                if prev_value != current_value:
                    action = 'create' if not prev_value else 'update'
                    self._task_history_cache.append(
                        (task_id, field_name, current_value, action, current_timestamp)
                    )
                    logger.info(f"记录字段历史: {task_id}.{field_name} {action}: '{prev_value}' -> '{current_value}'")
                else:
                    logger.debug(f"字段 {field_name} 值未变化，跳过历史记录")
        
        # 如果没有历史记录，至少记录一个创建记录
        if not self._task_history_cache and task_id not in self._task_cache:
            logger.debug(f"任务 {task_id} 是新任务，记录初始字段值")
            for field_name in field_names:
                if field_name in task_data and field_name not in excluded_fields:
                    current_value = str(task_data[field_name]) if task_data[field_name] is not None else ''
                    if current_value:  # 只记录有值的字段
                        self._task_history_cache.append(
                            (task_id, field_name, current_value, 'create', current_timestamp)
                        )
                        logger.info(f"记录初始字段历史: {task_id}.{field_name} create: '{current_value}'")
        
        logger.debug(f"任务 {task_id} 历史记录缓存数量: {len(self._task_history_cache)}")
        self._cache_dirty = True

    def load_tasks(self, include_completed_today: bool = True,all_tasks=False) -> List[Dict[str, Any]]:
        """从内存缓存加载任务列表"""
        try:
            with self._cache_lock:
                tasks = list(self._task_cache.values())
                result = []
                today = datetime.now().strftime('%Y-%m-%d')
                for task in tasks:
                    if all_tasks:
                        task_dict = dict(task)
                        task_dict['position'] = {'x': task['position_x'], 'y': task['position_y']}
                        result.append(task_dict)
                    elif task.get('deleted'):
                        continue
                    elif include_completed_today:
                        if (not task.get('completed')) or (task.get('completed_date') == today):
                            task_dict = dict(task)
                            task_dict['position'] = {'x': task['position_x'], 'y': task['position_y']}
                            result.append(task_dict)
                    else:
                        if not task.get('completed'):
                            task_dict = dict(task)
                            task_dict['position'] = {'x': task['position_x'], 'y': task['position_y']}
                            result.append(task_dict)
                result.sort(key=lambda t: t.get('created_at', ''), reverse=True)
            # logger.info(f"成功加载 {len(result)} 个任务（来自内存缓存）")
            return result
        except Exception as e:
            logger.error(f"加载任务失败: {str(e)}")
            return []

    def get_task_history(self, task_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """从数据库获取任务的历史记录"""
        try:
            # 先确保缓存中的历史记录已写入数据库
            self.flush_cache_to_db()
            
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT field_name, field_value, action, timestamp
                FROM task_history 
                WHERE task_id = ?
                ORDER BY timestamp ASC
            ''', (task_id,))
            history_records = cursor.fetchall()
            
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
            
            # logger.debug(f"获取任务 {task_id} 的历史记录: {len(history_records)} 条")
            return field_history
        except Exception as e:
            logger.error(f"获取任务历史记录失败: {str(e)}")
            return {}

    def delete_task(self, task_id: str) -> bool:
        """逻辑删除任务（仅标记为deleted，延迟写入数据库）"""
        try:
            with self._cache_lock:
                if task_id in self._task_cache:
                    self._task_cache[task_id]['deleted'] = True
                    self._task_cache[task_id]['updated_at'] = datetime.now().isoformat()
                    self._task_cache[task_id]['sync_status'] = 'modified'
                    self._deleted_task_ids.add(task_id)
                    self._cache_dirty = True
                else:
                    logger.warning(f"任务 {task_id} 不存在于缓存，无法删除")
                    return False
            logger.info(f"任务 {task_id} 已逻辑删除（内存缓存）")
            threading.Thread(target=self.sync_to_server).start()
            return True
        except Exception as e:
            logger.error(f"删除任务失败: {str(e)}")
            return False

    def get_sync_status(self) -> Dict[str, Any]:
        """获取同步状态"""
        try:
            self.flush_cache_to_db()
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM sync_status 
                ORDER BY last_sync_at DESC 
                LIMIT 5
            ''')
            sync_records = cursor.fetchall()
            with self._cache_lock:
                pending_sync_count = sum(1 for t in self._task_cache.values() if t.get('sync_status') != 'synced')
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

def get_db_manager(sync_interval: int = 180, flush_interval: int = 5) -> DatabaseManager:
    """获取全局数据库管理器实例，可选定时同步间隔（秒）和flush间隔（秒）"""
    global _db_manager
    if _db_manager is None:
        # 从配置文件加载远程配置
        remote_config = {}
        # 同时兼容项目根和 config/remote_config.json 的位置
        try:
            candidates = [
                os.path.join(APP_ROOT, 'remote_config.json'),
                os.path.join(APP_ROOT, 'config', 'remote_config.json'),
            ]
            for cfg_path in candidates:
                if os.path.exists(cfg_path):
                    with open(cfg_path, 'r', encoding='utf-8') as f:
                        remote_config = json.load(f)
                    break
        except Exception as e:
            logger.error(f"加载远程配置失败: {str(e)}")
        _db_manager = DatabaseManager(remote_config=remote_config, sync_interval=sync_interval, flush_interval=flush_interval)
    return _db_manager