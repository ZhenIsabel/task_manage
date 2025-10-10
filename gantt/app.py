from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
from datetime import datetime, timedelta
import os

DB_PATH = os.environ.get("DB_PATH", "./database/tasks.db")  # 改成你的 SQLite 文件路径

gantt_app = Flask(__name__, static_url_path="", static_folder="static")
CORS(gantt_app)

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def parse_date(s):
    """把表里的日期字符串转成 YYYY-MM-DD。允许空值。"""
    if not s:
        return None
    # 你表里像 due_date/create_date 用 TEXT，可能是 '2025-10-01' 或 '2025/10/01 12:00:00'
    # 尝试多种格式
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except:
            pass
    return None

@gantt_app.route("/tasks")
def tasks():
    """
    把你 tasks 表的数据映射为 frappe-gantt 的任务结构：
      id: str
      name: str
      start: 'YYYY-MM-DD'
      end: 'YYYY-MM-DD'
      progress: 0-100
      (可选) custom_class / dependencies / etc.
    这里约定：
      start 取 create_date（没有则用今天）
      end   取 due_date（没有则 start+3 天）
      progress: completed==TRUE -> 100，否则 0
      name 用 text 字段（为空则用 id）
      deleted==FALSE 的才返回
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, text, notes, create_date, due_date, completed, deleted, color
        FROM tasks
        WHERE COALESCE(deleted, 0) = 0
        ORDER BY COALESCE(due_date, create_date)
    """)
    rows = cur.fetchall()
    conn.close()

    today = datetime.today().strftime("%Y-%m-%d")
    results = []
    for r in rows:
        if r["completed"] in (1, True, "1", "true", "TRUE") :
            continue
        start = parse_date(r["create_date"]) or today
        end = parse_date(r["due_date"])
        if not end:
            # 默认给 3 天周期
            end = (datetime.strptime(start, "%Y-%m-%d") + timedelta(days=3)).strftime("%Y-%m-%d")
        name = r["text"] if r["text"] else r["id"]
        progress = 100 if (r["completed"] in (1, True, "1", "true", "TRUE")) else 0

        task = {
            "id": r["id"],
            "name": name,
            "start": start,
            "end": end,
            "progress": progress,
            # 可选：自定义样式 class，或直接把 color 放到 popup 用
            "custom_class": "",
            "notes": r["notes"] or "",
            "color": r["color"] or "#4ECDC4",
        }
        results.append(task)

    return jsonify(results)

@gantt_app.route("/")
def index():
    return send_from_directory("static", "index.html")

if __name__ == "__main__":
    # 运行：  DB_PATH=/path/to/your.db  python app.py
    gantt_app.run(host="127.0.0.1", port=5000, debug=True)
