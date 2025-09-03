#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Tuple


def backup_database():
	"""备份数据库"""
	import shutil
	backup_file = f"database/tasks_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
	shutil.copy2('database/tasks.db', backup_file)
	print(f"✅ 数据库已备份到: {backup_file}")
	return backup_file


def _enable_foreign_keys(conn: sqlite3.Connection) -> None:
	# 确保删除 tasks 时联级删除 task_history
	conn.execute('PRAGMA foreign_keys = ON')


def _fetch_history_counts(cursor: sqlite3.Cursor, ids: List[str]) -> Dict[str, int]:
	"""返回每个 task_id 的历史记录数量"""
	if not ids:
		return {}
	placeholders = ','.join(['?' for _ in ids])
	cursor.execute(
		f"SELECT task_id, COUNT(*) AS c FROM task_history WHERE task_id IN ({placeholders}) GROUP BY task_id",
		ids,
	)
	rows = cursor.fetchall()
	return {row[0]: int(row[1]) for row in rows}


def analyze_duplicates() -> List[Dict[str, Any]]:
	"""分析重复记录 - 基于 completed、deleted、text、notes 字段分组"""
	conn = sqlite3.connect('database/tasks.db')
	conn.row_factory = sqlite3.Row
	_enable_foreign_keys(conn)
	cursor = conn.cursor()

	print("=== 重复记录分析 ===")

	cursor.execute('''
		SELECT completed, deleted, text, notes, COUNT(*) as count, GROUP_CONCAT(id) as ids
		FROM tasks
		GROUP BY completed, deleted, text, notes
		HAVING COUNT(*) > 1
		ORDER BY count DESC
	''')
	groups = cursor.fetchall()
	print(f"发现 {len(groups)} 组重复记录（按 completed、deleted、text、notes 分组）:")

	duplicate_groups: List[Dict[str, Any]] = []
	for row in groups:
		completed = row['completed']
		deleted = row['deleted']
		text = row['text']
		notes = row['notes']
		count = int(row['count'])
		ids = (row['ids'] or '').split(',') if row['ids'] else []

		print(f"\n重复组: completed={completed}, deleted={deleted}, text='{text}', notes='{notes}'")
		print(f"重复次数: {count}")
		print(f"ID列表: {','.join(ids)}")

		if not ids:
			continue

		# 取该组内记录详情
		placeholders = ','.join(['?' for _ in ids])
		cursor.execute(
			f'''
				SELECT id, completed, deleted, text, notes, created_at, updated_at
				FROM tasks
				WHERE id IN ({placeholders})
			''',
			ids,
		)
		record_rows = cursor.fetchall()
		records = [dict(r) for r in record_rows]

		# 获取 task_history 数量并决定保留项
		hist_counts = _fetch_history_counts(cursor, ids)
		for r in records:
			r['history_count'] = hist_counts.get(r['id'], 0)

		# 选择保留：优先 history_count 最大，若并列则按 updated_at 最新
		def sort_key(rec: Dict[str, Any]) -> Tuple[int, str]:
			return (int(rec.get('history_count', 0)), str(rec.get('updated_at') or ''))

		records_sorted = sorted(records, key=sort_key, reverse=True)
		keep_record = records_sorted[0]
		remove_records = records_sorted[1:]

		for rr in records_sorted:
			print(
				f"  ID: {rr['id']}, hist={rr['history_count']}, 更新: {rr.get('updated_at')}"
			)
		print(f"  预留: {keep_record['id']} (hist={keep_record['history_count']})")

		duplicate_groups.append({
			'completed': completed,
			'deleted': deleted,
			'text': text,
			'notes': notes,
			'count': count,
			'keep_id': keep_record['id'],
			'remove_ids': [r['id'] for r in remove_records],
		})

	conn.close()
	return duplicate_groups


def deduplicate_tasks(duplicate_groups: List[Dict[str, Any]]) -> int:
	"""去重：保留历史记录最多的一条，物理删除其余项（联级删除历史）"""
	conn = sqlite3.connect('database/tasks.db')
	_enable_foreign_keys(conn)
	cursor = conn.cursor()

	print("\n=== 开始去重操作（保留历史最多） ===")
	removed = 0

	for group in duplicate_groups:
		keep_id = group['keep_id']
		remove_ids = [rid for rid in group['remove_ids'] if rid != keep_id]
		if not remove_ids:
			continue
		print(f"处理分组: text='{group['text']}'，删除 {len(remove_ids)} 条，保留 {keep_id}")
		placeholders = ','.join(['?' for _ in remove_ids])
		cursor.execute(f"DELETE FROM tasks WHERE id IN ({placeholders})", remove_ids)
		removed += cursor.rowcount if cursor.rowcount is not None else len(remove_ids)

	conn.commit()
	conn.close()
	print(f"\n✅ 去重完成，物理删除 {removed} 条记录")
	return removed


def verify_deduplication() -> None:
	"""验证去重结果：是否仍有重复分组"""
	conn = sqlite3.connect('database/tasks.db')
	cursor = conn.cursor()
	cursor.execute('''
		SELECT completed, deleted, text, notes, COUNT(*)
		FROM tasks
		GROUP BY completed, deleted, text, notes
		HAVING COUNT(*) > 1
	''')
	dup = cursor.fetchall()
	if dup:
		print(f"⚠️  仍有 {len(dup)} 组重复记录")
	else:
		print("✅ 未发现重复记录")
	conn.close()


def main():
	"""主函数"""
	print("=== 任务去重工具 ===")
	print("去重规则: completed、deleted、text、notes 一致视为重复；保留历史最多")

	backup_file = backup_database()
	groups = analyze_duplicates()
	if not groups:
		print("✅ 没有发现重复记录，无需去重")
		return

	print(f"\n将对 {len(groups)} 组进行去重，保留历史最多的记录并物理删除其余")
	confirm = input("确认执行？(y/N): ").strip().lower()
	if confirm != 'y':
		print("操作已取消")
		return

	removed = deduplicate_tasks(groups)
	verify_deduplication()
	print("\n✅ 去重操作完成！")
	print(f"备份文件: {backup_file}")
	print(f"删除记录数: {removed}")


if __name__ == "__main__":
	main()
