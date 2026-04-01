import sqlite3
import json
import os
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
import threading
import copy
import calendar

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
logger.propagate = False

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
        configured_api_base_url = self.remote_config.get('api_base_url', '')
        self.remote_enabled = self.remote_config.get('enabled', bool(configured_api_base_url))
        self.api_base_url = configured_api_base_url if self.remote_enabled else ''
        self.api_token = self.remote_config.get('api_token', '') if self.remote_enabled else ''
        self.username = self.remote_config.get('username', '') if self.remote_enabled else ''
        self._remote_user_registration_attempted = False
        self._remote_auth_paused = False
        self._sync_interval = sync_interval
        self._sync_thread = None
        self._stop_sync_event = threading.Event()

        # 内存缓存
        self._task_cache = {}  # id -> task_data
        self._task_history_cache = []  # [(task_id, field_name, field_value, action, timestamp)]
        self._deleted_task_ids = set()
        self._cache_lock = threading.Lock()
        self._cache_dirty = False
        self._task_sync_listeners = []
        self._listener_lock = threading.Lock()
        self._pending_remote_task_changes = {}

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
                    urgency TEXT DEFAULT '低',
                    importance TEXT DEFAULT '低',
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
            # 创建定时任务表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scheduled_tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    priority TEXT,
                    urgency TEXT DEFAULT '低',
                    importance TEXT DEFAULT '低',
                    notes TEXT,
                    due_date TEXT,
                    frequency TEXT NOT NULL,
                    week_day INTEGER,
                    month_day INTEGER,
                    quarter_day INTEGER,
                    year_month INTEGER,
                    year_day INTEGER,
                    next_run_at TIMESTAMP,
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建索引以提高查询性能
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_completed ON tasks(completed)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_deleted ON tasks(deleted)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_sync_status ON tasks(sync_status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_history_task_id ON task_history(task_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_history_timestamp ON task_history(timestamp)')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_scheduled_active ON scheduled_tasks(active)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_scheduled_next_run ON scheduled_tasks(next_run_at)')
            logger.debug("数据库索引创建/检查完成")
            
            conn.commit()
            logger.info("数据库初始化完成")
        except Exception as e:
            logger.error(f"数据库初始化失败: {str(e)}")
            raise

    def _is_public_endpoint(self, endpoint: str) -> bool:
        """判断接口是否为无需鉴权的公共接口。"""
        normalized_endpoint = f"/{endpoint.lstrip('/')}"
        return normalized_endpoint in {'/api/health', '/api/users'}

    def _build_api_headers(self, endpoint: str) -> Dict[str, str]:
        """构造接口请求头。"""
        headers = {'Content-Type': 'application/json'}
        if (not self._is_public_endpoint(endpoint)) and self.api_token:
            headers['Authorization'] = f'Bearer {self.api_token}'
        return headers

    def _reset_remote_auth_state(self) -> None:
        """重置远程鉴权降级状态，允许重新尝试自动注册。"""
        self._remote_user_registration_attempted = False
        self._remote_auth_paused = False

    def _pause_remote_auth(self) -> None:
        """在自动注册失败后暂停受保护远程请求，避免周期同步反复刷屏。"""
        self._remote_auth_paused = True

    def _register_remote_user(self) -> bool:
        """首次鉴权失败时，尝试按配置自动注册远程用户。"""
        if self._remote_user_registration_attempted:
            return False

        self._remote_user_registration_attempted = True
        if not self.api_base_url or not self.username or not self.api_token:
            logger.warning("缺少远程注册所需的 username 或 api_token，跳过自动注册")
            self._pause_remote_auth()
            return False

        try:
            response = requests.request(
                method='POST',
                url=f"{self.api_base_url.rstrip('/')}/api/users",
                headers=self._build_api_headers('/api/users'),
                json={'username': self.username, 'api_token': self.api_token},
                timeout=30
            )
        except requests.exceptions.Timeout:
            logger.error("自动注册远程用户超时")
            self._pause_remote_auth()
            return False
        except requests.exceptions.ConnectionError:
            logger.error("自动注册远程用户时连接失败")
            self._pause_remote_auth()
            return False
        except Exception as e:
            logger.error(f"自动注册远程用户异常: {str(e)}")
            self._pause_remote_auth()
            return False

        if response.status_code in (200, 201, 409):
            logger.info(f"自动注册远程用户结果: {response.status_code}")
            self._remote_auth_paused = False
            return True

        logger.error(f"自动注册远程用户失败: {response.status_code} - {response.text}")
        self._pause_remote_auth()
        return False

    def _make_api_request(self, method: str, endpoint: str, data: Optional[Dict] = None, retry_on_auth_failure: bool = True) -> Optional[Dict]:
        if not self.api_base_url:
            logger.debug("未配置API服务器地址，跳过API请求")
            return None
        if self._remote_auth_paused and (not self._is_public_endpoint(endpoint)):
            logger.debug(f"远程鉴权已暂停，跳过请求: {endpoint}")
            return None
        try:
            url = f"{self.api_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            headers = self._build_api_headers(endpoint)
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
            if response.status_code in (200, 201):
                logger.debug(f"API请求成功: {endpoint}")
                try:
                    return response.json()
                except ValueError:
                    return {}
            if response.status_code == 204:
                logger.debug(f"API请求成功且无响应体: {endpoint}")
                return {}
            if response.status_code == 401 and retry_on_auth_failure and (not self._is_public_endpoint(endpoint)):
                logger.warning(f"API鉴权失败，尝试自动注册用户后重试: {endpoint}")
                if self._register_remote_user():
                    return self._make_api_request(method, endpoint, data, retry_on_auth_failure=False)
                logger.error("自动注册远程用户失败，无法重试业务请求")
                return None
            if response.status_code == 500:
                logger.error("API请求失败：服务器内部错误")
                logger.error(f"错误信息: {response.text}")
                return None

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

    def bootstrap_remote_sync(self) -> bool:
        """在界面监听器就绪后，显式触发一次远程健康检查与拉取。"""
        if not self.api_base_url:
            logger.info("未配置远程服务器，跳过启动同步")
            return False

        self._reset_remote_auth_state()
        health = self._make_api_request('GET', '/api/health')
        if not health:
            logger.warning("远程服务健康检查失败，保留本地数据")
            return False

        tasks_ok = self.sync_from_server()
        scheduled_ok = self.sync_scheduled_tasks_from_server()
        if self._sync_interval and tasks_ok and scheduled_ok:
            self.start_periodic_sync(self._sync_interval)
        return tasks_ok and scheduled_ok

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
                         text, notes, due_date, priority, urgency, importance, directory, create_date, updated_at, sync_status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        task.get('urgency', '低'),
                        task.get('importance', '低'),
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
        if self._remote_auth_paused:
            return False
        try:
            with self._cache_lock:
                if self._pending_remote_task_changes:
                    logger.info("存在待确认的远程修改，暂不上传本地任务")
                    return False
                unsynced_tasks = [copy.deepcopy(task) for task in self._task_cache.values() if task.get('sync_status') != 'synced']
            if not unsynced_tasks:
                logger.info("没有需要同步的数据")
                return True

            for task in unsynced_tasks:
                task_data = dict(task)
                task_data['position'] = {'x': task['position_x'], 'y': task['position_y']}

                result = self._make_api_request('POST', '/api/tasks', task_data)
                if result:
                    with self._cache_lock:
                        self._task_cache[task['id']]['sync_status'] = 'synced'
                        self._cache_dirty = True
                else:
                    logger.error(f"同步任务 {task['id']} 失败")

            conn = self.get_connection()
            cursor = conn.cursor()
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
        """从服务器同步数据到本地缓存。"""
        if self._remote_auth_paused:
            return False
        try:
            with self._cache_lock:
                pending_summaries = self._build_pending_remote_change_summaries_locked()
            if pending_summaries:
                self._notify_task_sync_listeners(pending_summaries)
                return True

            result = self._make_api_request('GET', '/api/tasks')
            if not result:
                logger.error("无法从服务器获取数据")
                return False

            server_tasks = result.get('tasks', [])
            pending_changes = {}
            server_task_ids = {task_data['id'] for task_data in server_tasks}
            with self._cache_lock:
                for task_data in server_tasks:
                    local_task = self._task_cache.get(task_data['id'])
                    if (not local_task) or self._is_remote_task_newer_or_changed(local_task, task_data):
                        change = self._build_remote_change(local_task, task_data)
                        pending_changes[change['change_key']] = change

                for task_id, local_task in self._task_cache.items():
                    if task_id in server_task_ids:
                        continue
                    if local_task.get('sync_status') != 'synced':
                        continue
                    if local_task.get('deleted'):
                        continue
                    change = self._build_remote_delete_change(local_task)
                    pending_changes[change['change_key']] = change

            if not pending_changes:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO sync_status (sync_type, status, message)
                    VALUES (?, ?, ?)
                ''', ('download', 'success', f'从服务器检查了 {len(server_tasks)} 个任务'))
                conn.commit()
                return True

            if not self._has_task_sync_listeners():
                with self._cache_lock:
                    for change in pending_changes.values():
                        self._apply_remote_change_locked(change)
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO sync_status (sync_type, status, message)
                    VALUES (?, ?, ?)
                ''', ('download', 'success', f'从服务器同步了 {len(pending_changes)} 个任务'))
                conn.commit()
                return True

            with self._cache_lock:
                self._pending_remote_task_changes.update(pending_changes)
                pending_summaries = self._build_pending_remote_change_summaries_locked()

            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO sync_status (sync_type, status, message)
                VALUES (?, ?, ?)
            ''', ('download', 'pending', f'发现 {len(pending_changes)} 个待确认的远程修改'))
            conn.commit()

            self._notify_task_sync_listeners(pending_summaries)
            return True
        except Exception as e:
            logger.error(f"从服务器同步失败: {str(e)}")
            return False

    def add_task_sync_listener(self, listener) -> None:
        """注册任务下载同步后的回调。"""
        if listener is None:
            return
        with self._listener_lock:
            if listener not in self._task_sync_listeners:
                self._task_sync_listeners.append(listener)

    def remove_task_sync_listener(self, listener) -> None:
        """移除任务下载同步后的回调。"""
        with self._listener_lock:
            if listener in self._task_sync_listeners:
                self._task_sync_listeners.remove(listener)

    def _has_task_sync_listeners(self) -> bool:
        """是否存在任务同步监听器。"""
        with self._listener_lock:
            return bool(self._task_sync_listeners)

    def _notify_task_sync_listeners(self, change_summaries) -> None:
        """通知界面层：有新的服务端任务等待确认。"""
        with self._listener_lock:
            listeners = list(self._task_sync_listeners)

        for listener in listeners:
            try:
                listener(copy.deepcopy(change_summaries))
            except Exception as e:
                logger.error(f"任务同步回调执行失败: {str(e)}")

    def _cache_task_to_task_data(self, cache_task: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """将缓存中的任务记录转换成外部任务数据结构。"""
        if not cache_task:
            return None

        task_data = dict(cache_task)
        task_data['position'] = {
            'x': task_data.pop('position_x', 100),
            'y': task_data.pop('position_y', 100)
        }
        return task_data

    def _is_remote_task_newer_or_changed(self, local_task: Dict[str, Any], remote_task: Dict[str, Any]) -> bool:
        """判断远程任务是否比本地更新，或其完成/删除状态已变化。"""
        if remote_task.get('updated_at', '') > local_task.get('updated_at', ''):
            return True

        local_task_data = self._cache_task_to_task_data(local_task)
        return any([
            bool(remote_task.get('completed', False)) != bool(local_task_data.get('completed', False)),
            bool(remote_task.get('deleted', False)) != bool(local_task_data.get('deleted', False)),
            str(remote_task.get('completed_date', '') or '') != str(local_task_data.get('completed_date', '') or ''),
        ])

    def _build_remote_change(self, local_task: Optional[Dict[str, Any]], remote_task: Dict[str, Any]) -> Dict[str, Any]:
        """构造待确认的远程修改项。"""
        local_task_data = self._cache_task_to_task_data(local_task)
        entity_id = remote_task['id']
        title = remote_task.get('text') or (local_task_data.get('text') if local_task_data else '') or f"任务 {entity_id}"
        return {
            'change_key': f'task:{entity_id}',
            'entity_type': 'task',
            'entity_id': entity_id,
            'title': str(title),
            'change_type': 'create' if local_task_data is None else 'update',
            'local_record': copy.deepcopy(local_task_data),
            'remote_record': copy.deepcopy(remote_task),
        }

    def _build_remote_delete_change(self, local_task: Dict[str, Any]) -> Dict[str, Any]:
        """构造远程已删除任务的待确认项。"""
        local_task_data = self._cache_task_to_task_data(local_task)
        remote_task = copy.deepcopy(local_task_data)
        remote_task['deleted'] = True
        remote_task['completed'] = False
        remote_task['completed_date'] = ''
        remote_task['updated_at'] = datetime.now().isoformat()
        entity_id = local_task_data['id']
        return {
            'change_key': f'task:{entity_id}',
            'entity_type': 'task',
            'entity_id': entity_id,
            'title': str(local_task_data.get('text') or f"任务 {entity_id}"),
            'change_type': 'delete',
            'local_record': copy.deepcopy(local_task_data),
            'remote_record': remote_task,
        }

    def _build_scheduled_remote_change(self, local_task: Optional[Dict[str, Any]], remote_task: Dict[str, Any]) -> Dict[str, Any]:
        """构造待确认的远程定时任务修改项。"""
        entity_id = remote_task['id']
        title = remote_task.get('title') or (local_task.get('title') if local_task else '') or f"定时任务 {entity_id}"
        return {
            'change_key': f'scheduled:{entity_id}',
            'entity_type': 'scheduled_task',
            'entity_id': entity_id,
            'title': str(title),
            'change_type': 'create' if local_task is None else 'update',
            'local_record': copy.deepcopy(local_task),
            'remote_record': copy.deepcopy(remote_task),
        }

    def _build_pending_remote_change_summaries_locked(self) -> List[Dict[str, Any]]:
        """生成待确认远程修改的摘要。"""
        summaries = []
        for change in self._pending_remote_task_changes.values():
            summaries.append({
                'id': change.get('change_key', ''),
                'entity_type': change.get('entity_type', 'task'),
                'entity_id': change.get('entity_id', ''),
                'title': change.get('title', ''),
                'change_type': change.get('change_type', 'update'),
                'local_record': copy.deepcopy(change.get('local_record')),
                'remote_record': copy.deepcopy(change.get('remote_record')),
            })
        summaries.sort(key=lambda item: item.get('title', ''))
        return summaries

    def _apply_remote_change_locked(self, change: Dict[str, Any]) -> None:
        """接受远程修改并写入本地缓存/数据库。"""
        if change.get('entity_type') == 'scheduled_task':
            remote_record = change.get('remote_record')
            if remote_record is not None:
                self._upsert_scheduled_task_local(remote_record)
            return

        self._save_task_to_cache(change['remote_record'], 'synced')

    def _reject_remote_change_locked(self, change: Dict[str, Any]) -> None:
        """拒绝远程修改，保留本地版本并标记为待上传。"""
        if change.get('entity_type') == 'scheduled_task':
            local_record = change.get('local_record')
            if local_record is not None:
                self._upsert_scheduled_task_local(local_record)
            return

        local_task = change.get('local_record')
        if local_task is None:
            local_task = copy.deepcopy(change['remote_record'])
            local_task['deleted'] = True
            local_task['completed'] = False
            local_task['completed_date'] = ''
        else:
            local_task = copy.deepcopy(local_task)

        local_task['updated_at'] = datetime.now().isoformat()
        self._save_task_to_cache(local_task, 'modified')

    def resolve_pending_remote_task_changes(self, accepted_ids: List[str], rejected_ids: List[str]) -> bool:
        """处理待确认的远程修改。"""
        try:
            accepted_set = set(accepted_ids or [])
            rejected_set = set(rejected_ids or [])
            rejected_changes = []
            with self._cache_lock:
                pending_ids = set(self._pending_remote_task_changes.keys())
                for change_key in pending_ids & accepted_set:
                    self._apply_remote_change_locked(self._pending_remote_task_changes[change_key])
                for change_key in pending_ids & rejected_set:
                    change = self._pending_remote_task_changes[change_key]
                    self._reject_remote_change_locked(change)
                    rejected_changes.append(copy.deepcopy(change))
                for change_key in pending_ids & (accepted_set | rejected_set):
                    self._pending_remote_task_changes.pop(change_key, None)
                self._cache_dirty = True

            for change in rejected_changes:
                if change.get('entity_type') != 'scheduled_task' or (not self.api_base_url):
                    continue

                local_record = change.get('local_record')
                if local_record is not None:
                    self._make_api_request('POST', '/api/scheduled_tasks', self._serialize_scheduled_task_for_api(local_record))
                elif change.get('entity_id'):
                    self._make_api_request('DELETE', f"/api/scheduled_tasks/{change['entity_id']}")
            return True
        except Exception as e:
            logger.error(f"处理待确认远程修改失败: {str(e)}")
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
            'urgency': field_values.get('urgency', task_data.get('urgency', '低')),
            'importance': field_values.get('importance', task_data.get('importance', '低')),
            'directory': field_values.get('directory', ''),
            'create_date': field_values.get('create_date', ''),
            'updated_at': task_data.get('updated_at', datetime.now().isoformat()),
            'sync_status': sync_status,
            'created_at': task_data.get('created_at', datetime.now().isoformat())
        }
        
        self._task_cache[task_id] = task
        if deleted:
            self._deleted_task_ids.add(task_id)
        else:
            self._deleted_task_ids.discard(task_id)
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
        """优先从远程接口获取任务历史，失败时回退到本地数据库。"""
        try:
            if self.api_base_url:
                remote_result = self._make_api_request('GET', f'/api/tasks/{task_id}/history')
                if remote_result and isinstance(remote_result.get('history'), dict):
                    return remote_result.get('history', {})

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

    def _normalize_scheduled_task_data(self, schedule_data: Dict[str, Any], existing: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """补齐定时任务字段，统一本地落库数据结构。"""
        normalized = dict(existing or {})
        normalized.update(schedule_data)
        now = datetime.now().isoformat()
        normalized['priority'] = normalized.get('priority', '中')
        normalized['urgency'] = normalized.get('urgency', '低')
        normalized['importance'] = normalized.get('importance', '低')
        normalized['notes'] = normalized.get('notes', '')
        normalized['due_date'] = normalized.get('due_date', '')
        normalized['active'] = normalized.get('active', True)
        normalized['created_at'] = normalized.get('created_at') or (existing or {}).get('created_at') or now
        normalized['updated_at'] = schedule_data.get('updated_at') or now
        return normalized

    def _serialize_scheduled_task_for_api(self, schedule_data: Dict[str, Any]) -> Dict[str, Any]:
        """将定时任务记录转换为远端接口期望的 JSON 结构。"""
        payload = copy.deepcopy(schedule_data)
        active = payload.get('active', True)
        if isinstance(active, bool):
            payload['active'] = active
        elif isinstance(active, str):
            lowered = active.strip().lower()
            if lowered in {'1', 'true', 'yes', 'on'}:
                payload['active'] = True
            elif lowered in {'0', 'false', 'no', 'off', ''}:
                payload['active'] = False
            else:
                payload['active'] = bool(active)
        else:
            payload['active'] = bool(active)
        return payload

    def _upsert_scheduled_task_local(self, schedule_data: Dict[str, Any], commit: bool = True) -> bool:
        """在本地数据库中插入或更新定时任务。"""
        try:
            existing = self.get_scheduled_task(schedule_data['id'])
            normalized = self._normalize_scheduled_task_data(schedule_data, existing=existing)
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO scheduled_tasks 
                (id, title, priority, urgency, importance, notes, due_date, frequency,
                 week_day, month_day, quarter_day, year_month, year_day,
                 next_run_at, active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                normalized['id'],
                normalized['title'],
                normalized.get('priority', '中'),
                normalized.get('urgency', '低'),
                normalized.get('importance', '低'),
                normalized.get('notes', ''),
                normalized.get('due_date', ''),
                normalized['frequency'],
                normalized.get('week_day'),
                normalized.get('month_day'),
                normalized.get('quarter_day'),
                normalized.get('year_month'),
                normalized.get('year_day'),
                normalized.get('next_run_at'),
                normalized.get('active', True),
                normalized['created_at'],
                normalized['updated_at']
            ))
            if commit:
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"本地写入定时任务失败: {str(e)}")
            return False

    def create_scheduled_task(self, schedule_data: Dict[str, Any]) -> bool:
        """创建定时任务，并在成功写入本地后尽力回写远端。"""
        try:
            schedule_to_save = self._normalize_scheduled_task_data(schedule_data)
            if not self._upsert_scheduled_task_local(schedule_to_save):
                return False

            if self.api_base_url:
                result = self._make_api_request('POST', '/api/scheduled_tasks', self._serialize_scheduled_task_for_api(schedule_to_save))
                if result:
                    logger.info(f"创建定时任务已同步到服务器: {schedule_to_save['id']}")
                else:
                    logger.warning(f"创建定时任务未能同步到服务器，保留本地结果: {schedule_to_save['id']}")

            logger.info(f"创建定时任务成功: {schedule_to_save['id']}")
            return True
        except Exception as e:
            logger.error(f"创建定时任务失败: {str(e)}")
            return False

    def list_scheduled_tasks(
        self, 
        active_only: bool = False, 
        due_before: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """列出定时任务"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = 'SELECT * FROM scheduled_tasks WHERE 1=1'
            params = []
            
            if active_only:
                query += ' AND active = ?'
                params.append(True)
            
            if due_before:
                query += ' AND next_run_at <= ?'
                params.append(due_before.isoformat())
            
            query += ' ORDER BY next_run_at ASC'
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            schedules = [dict(row) for row in rows]
            return schedules
        except Exception as e:
            logger.error(f"查询定时任务失败: {str(e)}")
            return []
    
    def get_scheduled_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取单个定时任务"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM scheduled_tasks WHERE id = ?', (task_id,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
        except Exception as e:
            logger.error(f"获取定时任务失败: {str(e)}")
            return None
    
    def update_scheduled_task(self, task_id: str, updates: Dict[str, Any]) -> bool:
        """更新定时任务，并在本地成功后尽力回写远端。"""
        try:
            existing = self.get_scheduled_task(task_id)
            if not existing:
                logger.warning(f"定时任务 {task_id} 不存在，无法更新")
                return False

            merged = dict(existing)
            merged.update({key: value for key, value in updates.items() if key != 'id'})
            merged['id'] = task_id
            merged['updated_at'] = updates.get('updated_at') or datetime.now().isoformat()

            if not self._upsert_scheduled_task_local(merged):
                return False

            if self.api_base_url:
                result = self._make_api_request('POST', '/api/scheduled_tasks', self._serialize_scheduled_task_for_api(merged))
                if result:
                    logger.info(f"更新定时任务已同步到服务器: {task_id}")
                else:
                    logger.warning(f"更新定时任务未能同步到服务器，保留本地结果: {task_id}")

            logger.info(f"更新定时任务成功: {task_id}")
            return True
        except Exception as e:
            logger.error(f"更新定时任务失败: {str(e)}")
            return False

    def delete_scheduled_task(self, task_id: str) -> bool:
        """删除定时任务"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM scheduled_tasks WHERE id = ?', (task_id,))
            conn.commit()
            
            # 如果配置了远程服务器，同步删除到服务器
            if self.api_base_url:
                try:
                    result = self._make_api_request('DELETE', f'/api/scheduled_tasks/{task_id}')
                    if result:
                        logger.info(f"删除定时任务已同步到服务器: {task_id}")
                    else:
                        logger.warning(f"删除定时任务未能同步到服务器: {task_id}")
                except Exception as e:
                    logger.error(f"同步删除到服务器时出错: {str(e)}")
            
            logger.info(f"删除定时任务成功: {task_id}")
            return True
        except Exception as e:
            logger.error(f"删除定时任务失败: {str(e)}")
            return False

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

    def sync_scheduled_tasks_to_server(self) -> bool:
        """同步定时任务到服务器"""
        if not self.api_base_url:
            return True
        if self._remote_auth_paused:
            return False
        
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 获取所有定时任务
            cursor.execute('SELECT * FROM scheduled_tasks')
            scheduled_tasks = cursor.fetchall()
            
            synced_count = 0
            for row in scheduled_tasks:
                task = dict(row)
                # 发送到服务器
                result = self._make_api_request('POST', '/api/scheduled_tasks', self._serialize_scheduled_task_for_api(task))
                if result:
                    synced_count += 1
                else:
                    logger.error(f"同步定时任务 {task['id']} 失败")
            
            logger.info(f"成功同步 {synced_count} 个定时任务到服务器")
            return True
        except Exception as e:
            logger.error(f"同步定时任务到服务器失败: {str(e)}")
            return False

    def sync_scheduled_tasks_from_server(self) -> bool:
        """从服务器同步定时任务到本地，本地已有项遇到远端更新时转为待确认冲突。"""
        if not self.api_base_url:
            return True
        if self._remote_auth_paused:
            return False

        try:
            result = self._make_api_request('GET', '/api/scheduled_tasks')
            if not result:
                logger.error("无法从服务器获取定时任务")
                return False

            server_tasks = result.get('scheduled_tasks', [])
            pending_changes = {}
            inserted_count = 0

            for task_data in server_tasks:
                local_task = self.get_scheduled_task(task_data['id'])
                if not local_task:
                    if self._upsert_scheduled_task_local(task_data, commit=True):
                        inserted_count += 1
                    continue

                if task_data.get('updated_at', '') > local_task.get('updated_at', ''):
                    change = self._build_scheduled_remote_change(local_task, task_data)
                    pending_changes[change['change_key']] = change

            if pending_changes:
                with self._cache_lock:
                    self._pending_remote_task_changes.update(pending_changes)
                    pending_summaries = self._build_pending_remote_change_summaries_locked()

                if self._has_task_sync_listeners():
                    self._notify_task_sync_listeners(pending_summaries)

                logger.info(f"发现 {len(pending_changes)} 个待确认的远程定时任务修改")

            logger.info(f"成功从服务器同步 {inserted_count} 个定时任务，待确认 {len(pending_changes)} 个")
            return True
        except Exception as e:
            logger.error(f"从服务器同步定时任务失败: {str(e)}")
            return False

    def _periodic_sync_worker(self):
        """定时同步线程的工作函数。"""
        logger.info("定时同步线程工作函数启动")
        while not self._stop_sync_event.is_set():
            if self._remote_auth_paused:
                self._stop_sync_event.wait(self._sync_interval)
                continue
            try:
                logger.info("定时同步：开始从服务器同步普通任务")
                self.sync_from_server()
                logger.info("定时同步：开始同步普通任务到服务器")
                self.sync_to_server()

                logger.info("定时同步：开始从服务器同步定时任务")
                self.sync_scheduled_tasks_from_server()
                logger.info("定时同步：开始同步定时任务到服务器")
                self.sync_scheduled_tasks_to_server()
            except Exception as e:
                logger.error(f"定时同步异常: {str(e)}")

            # 等待下一个周期或直到被停止
            self._stop_sync_event.wait(self._sync_interval)

        logger.info("定时同步线程退出")

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