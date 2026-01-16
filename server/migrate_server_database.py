"""
服务器端数据迁移脚本：将优先级字段迁移到紧急程度和重要程度

使用说明：
1. 在启动服务器之前执行此脚本
2. 脚本会自动检查是否需要迁移
3. 备份数据库后再执行迁移

迁移规则：
- 高优先级 → 紧急程度=高, 重要程度=高
- 中优先级 → 紧急程度=低, 重要程度=高  
- 低优先级 → 紧急程度=低, 重要程度=低
- default或空 → 紧急程度=低, 重要程度=低
"""

import sqlite3
import os
import sys
import shutil
from datetime import datetime

# 数据库路径
DB_PATH = 'server_tasks.db'
BACKUP_DIR = 'backups'


def backup_database():
    """备份数据库"""
    if not os.path.exists(DB_PATH):
        print(f"数据库文件不存在: {DB_PATH}")
        return None
    
    # 创建备份目录
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    # 生成备份文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = os.path.join(BACKUP_DIR, f'server_tasks_backup_{timestamp}.db')
    
    # 复制数据库文件
    shutil.copy2(DB_PATH, backup_path)
    print(f"服务器数据库已备份到: {backup_path}")
    return backup_path


def check_migration_needed(cursor):
    """检查是否需要迁移"""
    # 检查tasks表
    cursor.execute("PRAGMA table_info(tasks)")
    columns = [col[1] for col in cursor.fetchall()]
    
    tasks_needs_migration = 'priority' in columns and 'urgency' not in columns
    
    # 检查scheduled_tasks表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scheduled_tasks'")
    scheduled_exists = cursor.fetchone() is not None
    
    scheduled_needs_migration = False
    if scheduled_exists:
        cursor.execute("PRAGMA table_info(scheduled_tasks)")
        sched_columns = [col[1] for col in cursor.fetchall()]
        scheduled_needs_migration = 'priority' in sched_columns and 'urgency' not in sched_columns
    
    return tasks_needs_migration, scheduled_needs_migration, scheduled_exists


def migrate_tasks_table(cursor):
    """迁移tasks表"""
    print("\n开始迁移tasks表...")
    
    # 添加新字段
    print("  添加urgency字段...")
    cursor.execute('ALTER TABLE tasks ADD COLUMN urgency TEXT DEFAULT "低"')
    
    print("  添加importance字段...")
    cursor.execute('ALTER TABLE tasks ADD COLUMN importance TEXT DEFAULT "低"')
    
    # 迁移数据
    print("  迁移现有数据...")
    
    cursor.execute('UPDATE tasks SET urgency="高", importance="高" WHERE priority="高"')
    high_count = cursor.rowcount
    print(f"    已迁移 {high_count} 个高优先级任务")
    
    cursor.execute('UPDATE tasks SET urgency="低", importance="高" WHERE priority="中"')
    mid_count = cursor.rowcount
    print(f"    已迁移 {mid_count} 个中优先级任务")
    
    cursor.execute('UPDATE tasks SET urgency="低", importance="低" WHERE priority="低"')
    low_count = cursor.rowcount
    print(f"    已迁移 {low_count} 个低优先级任务")
    
    cursor.execute('UPDATE tasks SET urgency="低", importance="低" WHERE priority="default" OR priority="" OR priority IS NULL')
    default_count = cursor.rowcount
    print(f"    已迁移 {default_count} 个默认优先级任务")
    
    total_count = high_count + mid_count + low_count + default_count
    print(f"  tasks表迁移完成，共迁移 {total_count} 条记录")
    
    return total_count


def migrate_scheduled_tasks_table(cursor):
    """迁移scheduled_tasks表"""
    print("\n开始迁移scheduled_tasks表...")
    
    # 添加新字段
    print("  添加urgency字段...")
    cursor.execute('ALTER TABLE scheduled_tasks ADD COLUMN urgency TEXT DEFAULT "低"')
    
    print("  添加importance字段...")
    cursor.execute('ALTER TABLE scheduled_tasks ADD COLUMN importance TEXT DEFAULT "低"')
    
    # 迁移数据
    print("  迁移现有数据...")
    
    cursor.execute('UPDATE scheduled_tasks SET urgency="高", importance="高" WHERE priority="高"')
    high_count = cursor.rowcount
    print(f"    已迁移 {high_count} 个高优先级定时任务")
    
    cursor.execute('UPDATE scheduled_tasks SET urgency="低", importance="高" WHERE priority="中"')
    mid_count = cursor.rowcount
    print(f"    已迁移 {mid_count} 个中优先级定时任务")
    
    cursor.execute('UPDATE scheduled_tasks SET urgency="低", importance="低" WHERE priority="低"')
    low_count = cursor.rowcount
    print(f"    已迁移 {low_count} 个低优先级定时任务")
    
    cursor.execute('UPDATE scheduled_tasks SET urgency="低", importance="低" WHERE priority="default" OR priority="" OR priority IS NULL')
    default_count = cursor.rowcount
    print(f"    已迁移 {default_count} 个默认优先级定时任务")
    
    total_count = high_count + mid_count + low_count + default_count
    print(f"  scheduled_tasks表迁移完成，共迁移 {total_count} 条记录")
    
    return total_count


def main():
    """主函数"""
    print("=" * 60)
    print("服务器数据库迁移脚本：优先级 → 紧急程度/重要程度")
    print("=" * 60)
    
    # 检查数据库是否存在
    if not os.path.exists(DB_PATH):
        print(f"\n错误：数据库文件不存在: {DB_PATH}")
        print("请先运行服务器以创建数据库")
        return 1
    
    # 备份数据库
    print("\n步骤 1: 备份数据库")
    backup_path = backup_database()
    if not backup_path:
        print("备份失败，终止迁移")
        return 1
    
    # 连接数据库
    print("\n步骤 2: 连接数据库")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    print(f"已连接到: {DB_PATH}")
    
    try:
        # 检查是否需要迁移
        print("\n步骤 3: 检查迁移需求")
        tasks_needs, scheduled_needs, scheduled_exists = check_migration_needed(cursor)
        
        if not tasks_needs and not scheduled_needs:
            print("  ✓ 数据库已经包含新字段，无需迁移")
            return 0
        
        if tasks_needs:
            print("  → tasks表需要迁移")
        else:
            print("  ✓ tasks表已迁移")
            
        if scheduled_exists:
            if scheduled_needs:
                print("  → scheduled_tasks表需要迁移")
            else:
                print("  ✓ scheduled_tasks表已迁移")
        else:
            print("  ℹ scheduled_tasks表不存在，跳过")
        
        # 执行迁移
        print("\n步骤 4: 执行迁移")
        total_migrated = 0
        
        if tasks_needs:
            count = migrate_tasks_table(cursor)
            total_migrated += count
        
        if scheduled_needs:
            count = migrate_scheduled_tasks_table(cursor)
            total_migrated += count
        
        # 提交更改
        print("\n步骤 5: 提交更改")
        conn.commit()
        print("  ✓ 所有更改已提交")
        
        # 验证迁移结果
        print("\n步骤 6: 验证迁移结果")
        cursor.execute("PRAGMA table_info(tasks)")
        tasks_columns = [col[1] for col in cursor.fetchall()]
        
        if 'urgency' in tasks_columns and 'importance' in tasks_columns:
            print("  ✓ tasks表字段验证通过")
        else:
            print("  ✗ tasks表字段验证失败")
            return 1
        
        if scheduled_exists:
            cursor.execute("PRAGMA table_info(scheduled_tasks)")
            scheduled_columns = [col[1] for col in cursor.fetchall()]
            
            if 'urgency' in scheduled_columns and 'importance' in scheduled_columns:
                print("  ✓ scheduled_tasks表字段验证通过")
            else:
                print("  ✗ scheduled_tasks表字段验证失败")
                return 1
        
        print("\n" + "=" * 60)
        print(f"迁移成功完成！共迁移 {total_migrated} 条记录")
        print(f"备份文件位于: {backup_path}")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\n错误：迁移过程中发生异常: {str(e)}")
        print("正在回滚更改...")
        conn.rollback()
        print("已回滚，数据库未被修改")
        print(f"如需恢复，可使用备份文件: {backup_path}")
        return 1
        
    finally:
        conn.close()
        print("\n数据库连接已关闭")


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
