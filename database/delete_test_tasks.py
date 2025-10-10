#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
import sqlite3
from datetime import datetime

DB_PATH = os.path.join('database', 'tasks.db')


def backup_database() -> str:
	"""为当前数据库创建时间戳备份并返回备份文件路径。"""
	if not os.path.exists(DB_PATH):
		raise FileNotFoundError(f"未找到数据库文件: {DB_PATH}")
	backup_file = os.path.join('database', f"tasks_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
	shutil.copy2(DB_PATH, backup_file)
	print(f"[OK] 数据库已备份到: {backup_file}")
	return backup_file


def enable_foreign_keys(conn: sqlite3.Connection) -> None:
	"""开启外键以确保删除 tasks 时联级删除 task_history。"""
	conn.execute('PRAGMA foreign_keys = ON')


def count_target(conn: sqlite3.Connection) -> int:
	"""统计命中删除条件的记录数。"""
	cursor = conn.cursor()
	cursor.execute("SELECT COUNT(*) FROM tasks WHERE text LIKE '%test%' COLLATE NOCASE")
	(row_count,) = cursor.fetchone()
	return int(row_count)


def delete_test_tasks() -> int:
	"""物理删除标题包含 'test'（大小写不敏感）的任务，返回删除数量。"""
	conn = sqlite3.connect(DB_PATH)
	enable_foreign_keys(conn)
	cursor = conn.cursor()

	# 先统计
	to_delete = count_target(conn)
	if to_delete == 0:
		print("[INFO] 未找到标题包含 'test' 的任务，无需删除。")
		conn.close()
		return 0

	# 执行删除（联级删除 task_history）
	cursor.execute("DELETE FROM tasks WHERE text LIKE '%test%' COLLATE NOCASE")
	deleted = cursor.rowcount if cursor.rowcount is not None else to_delete
	conn.commit()
	conn.close()
	return int(deleted)


def main():
	print("=== 删除标题包含 'test' 的任务（物理删除） ===")
	print("说明: 将直接从 tasks 表删除匹配记录，外键联级清理 task_history。")
	backup_file = backup_database()
	deleted = delete_test_tasks()
	if deleted:
		print(f"[OK] 删除完成，共删除 {deleted} 条记录。")
	else:
		print("[OK] 无需删除。")
	print(f"备份文件: {backup_file}")


if __name__ == '__main__':
	main()
