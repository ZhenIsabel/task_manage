"""
任务管理服务器API示例
使用Flask框架实现RESTful API
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Any
import os

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 数据库配置
DB_PATH = 'server_tasks.db'

def init_server_database():
    """初始化服务器数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 创建用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            api_token TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建任务表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
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
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
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
    
    # 创建索引
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tasks_updated_at ON tasks(updated_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_history_task_id ON task_history(task_id)')
    
    conn.commit()
    conn.close()

def get_user_id_from_token(token: str) -> int:
    """从API令牌获取用户ID"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM users WHERE api_token = ?', (token,))
    result = cursor.fetchone()
    
    conn.close()
    return result[0] if result else None

def authenticate_request():
    """验证API请求"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header.split(' ')[1]
    user_id = get_user_id_from_token(token)
    
    if not user_id:
        return None
    
    return user_id

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """获取用户的任务列表"""
    user_id = authenticate_request()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 获取用户的任务
        cursor.execute('''
            SELECT * FROM tasks 
            WHERE user_id = ? AND deleted = FALSE
            ORDER BY updated_at DESC
        ''', (user_id,))
        
        tasks = cursor.fetchall()
        
        # 转换为字典格式
        result = []
        for task in tasks:
            task_dict = dict(zip([col[0] for col in cursor.description], task))
            task_dict['position'] = {'x': task['position_x'], 'y': task['position_y']}
            result.append(task_dict)
        
        conn.close()
        
        return jsonify({
            'tasks': result,
            'count': len(result)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks', methods=['POST'])
def create_or_update_task():
    """创建或更新任务"""
    user_id = authenticate_request()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        task_data = request.json
        task_id = task_data.get('id')
        
        if not task_id:
            return jsonify({'error': 'Task ID is required'}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 检查任务是否存在
        cursor.execute('SELECT id FROM tasks WHERE id = ? AND user_id = ?', (task_id, user_id))
        existing_task = cursor.fetchone()
        
        # 准备任务数据
        position = task_data.get('position', {'x': 100, 'y': 100})
        
        if existing_task:
            # 更新现有任务
            cursor.execute('''
                UPDATE tasks SET
                    color = ?, position_x = ?, position_y = ?, completed = ?,
                    completed_date = ?, deleted = ?, text = ?, notes = ?,
                    due_date = ?, priority = ?, directory = ?, create_date = ?,
                    updated_at = ?
                WHERE id = ? AND user_id = ?
            ''', (
                task_data.get('color', '#4ECDC4'),
                position['x'], position['y'],
                task_data.get('completed', False),
                task_data.get('completed_date', ''),
                task_data.get('deleted', False),
                task_data.get('text', ''),
                task_data.get('notes', ''),
                task_data.get('due_date', ''),
                task_data.get('priority', ''),
                task_data.get('directory', ''),
                task_data.get('create_date', ''),
                datetime.now().isoformat(),
                task_id, user_id
            ))
            action = 'updated'
        else:
            # 创建新任务
            cursor.execute('''
                INSERT INTO tasks (
                    id, user_id, color, position_x, position_y, completed,
                    completed_date, deleted, text, notes, due_date, priority,
                    directory, create_date, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task_id, user_id,
                task_data.get('color', '#4ECDC4'),
                position['x'], position['y'],
                task_data.get('completed', False),
                task_data.get('completed_date', ''),
                task_data.get('deleted', False),
                task_data.get('text', ''),
                task_data.get('notes', ''),
                task_data.get('due_date', ''),
                task_data.get('priority', ''),
                task_data.get('directory', ''),
                task_data.get('create_date', ''),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            action = 'created'
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'action': action,
            'task_id': task_id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """删除任务"""
    user_id = authenticate_request()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 逻辑删除任务
        cursor.execute('''
            UPDATE tasks 
            SET deleted = TRUE, updated_at = ?
            WHERE id = ? AND user_id = ?
        ''', (datetime.now().isoformat(), task_id, user_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': 'Task not found'}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Task deleted successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<task_id>/history', methods=['GET'])
def get_task_history(task_id):
    """获取任务历史记录"""
    user_id = authenticate_request()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 验证任务属于当前用户
        cursor.execute('SELECT id FROM tasks WHERE id = ? AND user_id = ?', (task_id, user_id))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Task not found'}), 404
        
        # 获取历史记录
        cursor.execute('''
            SELECT field_name, field_value, action, timestamp
            FROM task_history 
            WHERE task_id = ?
            ORDER BY timestamp ASC
        ''', (task_id,))
        
        history_records = cursor.fetchall()
        
        # 按字段分组
        field_history = {}
        for record in history_records:
            field_name = record[0]
            if field_name not in field_history:
                field_history[field_name] = []
            
            field_history[field_name].append({
                'value': record[1],
                'action': record[2],
                'timestamp': record[3]
            })
        
        conn.close()
        
        return jsonify({
            'task_id': task_id,
            'history': field_history
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/users', methods=['POST'])
def create_user():
    """创建新用户"""
    try:
        data = request.json
        username = data.get('username')
        api_token = data.get('api_token')
        
        if not username or not api_token:
            return jsonify({'error': 'Username and API token are required'}), 400
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO users (username, api_token)
            VALUES (?, ?)
        ''', (username, api_token))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'username': username
        })
        
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Username or API token already exists'}), 409
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # 初始化数据库
    init_server_database()
    
    print("=== 任务管理服务器启动 ===")
    print("API服务器地址: http://localhost:5000")
    print("健康检查: http://localhost:5000/api/health")
    print("按 Ctrl+C 停止服务器")
    
    # 启动Flask开发服务器
    app.run(host='0.0.0.0', port=5000, debug=True) 