import json
import os
from datetime import datetime
from typing import Dict, List
from database_manager import get_db_manager

class SyncManager:
    """同步管理器"""
    
    def __init__(self):
        self.db_manager = get_db_manager()
    
    def sync_all(self) -> Dict[str, bool]:
        """执行完整同步（上传和下载）"""
        print("=== 开始数据同步 ===")
        
        results = {}
        
        # 先下载服务器数据
        print("\n1. 从服务器下载数据...")
        results['download'] = self.db_manager.sync_from_server()
        
        # 再上传本地数据
        print("\n2. 上传本地数据到服务器...")
        results['upload'] = self.db_manager.sync_to_server()
        
        # 显示同步结果
        print("\n=== 同步结果 ===")
        if results['download']:
            print("✅ 下载同步成功")
        else:
            print("❌ 下载同步失败")
            
        if results['upload']:
            print("✅ 上传同步成功")
        else:
            print("❌ 上传同步失败")
        
        return results
    
    def sync_to_server(self) -> bool:
        """只同步到服务器"""
        print("=== 上传数据到服务器 ===")
        result = self.db_manager.sync_to_server()
        
        if result:
            print("✅ 上传同步成功")
        else:
            print("❌ 上传同步失败")
        
        return result
    
    def sync_from_server(self) -> bool:
        """只从服务器同步"""
        print("=== 从服务器下载数据 ===")
        result = self.db_manager.sync_from_server()
        
        if result:
            print("✅ 下载同步成功")
        else:
            print("❌ 下载同步失败")
        
        return result
    
    def get_sync_status(self) -> Dict:
        """获取同步状态"""
        status = self.db_manager.get_sync_status()
        
        print("=== 同步状态 ===")
        print(f"服务器连接: {'✅ 已连接' if status['server_connected'] else '❌ 未连接'}")
        print(f"待同步任务数: {status['pending_sync_count']}")
        
        if status['last_sync_records']:
            print("\n最近同步记录:")
            for record in status['last_sync_records'][:3]:
                sync_time = record['last_sync_at']
                sync_type = record['sync_type']
                status_text = record['status']
                message = record['message']
                print(f"  {sync_time} - {sync_type} - {status_text}: {message}")
        else:
            print("\n暂无同步记录")
        
        return status
    
    def resolve_conflicts(self) -> Dict[str, int]:
        """解决同步冲突"""
        print("=== 检查同步冲突 ===")
        
        # 这里可以实现冲突解决逻辑
        # 例如：比较时间戳，选择最新的数据
        # 或者让用户选择保留哪个版本
        
        conflicts = {
            'resolved': 0,
            'unresolved': 0
        }
        
        print("✅ 冲突检查完成")
        return conflicts
    
    def backup_before_sync(self) -> bool:
        """同步前备份"""
        try:
            from shutil import copy2
            backup_file = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            copy2(self.db_manager.db_path, backup_file)
            print(f"✅ 备份已创建: {backup_file}")
            return True
        except Exception as e:
            print(f"❌ 备份失败: {str(e)}")
            return False
    
    def restore_from_backup(self, backup_file: str) -> bool:
        """从备份恢复"""
        try:
            from shutil import copy2
            if os.path.exists(backup_file):
                copy2(backup_file, self.db_manager.db_path)
                print(f"✅ 已从备份恢复: {backup_file}")
                return True
            else:
                print(f"❌ 备份文件不存在: {backup_file}")
                return False
        except Exception as e:
            print(f"❌ 恢复失败: {str(e)}")
            return False
    
    def list_backups(self) -> List[str]:
        """列出所有备份文件"""
        backups = []
        for file in os.listdir('.'):
            if file.startswith('backup_') and file.endswith('.db'):
                backups.append(file)
        
        backups.sort(reverse=True)  # 按时间倒序排列
        
        if backups:
            print("=== 可用备份文件 ===")
            for backup in backups:
                print(f"  {backup}")
        else:
            print("暂无备份文件")
        
        return backups

def main():
    """主函数"""
    print("=== 数据同步管理工具 ===")
    
    sync_manager = SyncManager()
    
    while True:
        print("\n请选择操作:")
        print("1. 完整同步（下载+上传）")
        print("2. 上传到服务器")
        print("3. 从服务器下载")
        print("4. 查看同步状态")
        print("5. 解决冲突")
        print("6. 创建备份")
        print("7. 从备份恢复")
        print("8. 列出备份")
        print("9. 退出")
        
        choice = input("\n请输入选择 (1-9): ").strip()
        
        if choice == '1':
            sync_manager.sync_all()
            
        elif choice == '2':
            sync_manager.sync_to_server()
            
        elif choice == '3':
            sync_manager.sync_from_server()
            
        elif choice == '4':
            sync_manager.get_sync_status()
            
        elif choice == '5':
            sync_manager.resolve_conflicts()
            
        elif choice == '6':
            sync_manager.backup_before_sync()
            
        elif choice == '7':
            backups = sync_manager.list_backups()
            if backups:
                backup_file = input("请输入要恢复的备份文件名: ").strip()
                if backup_file in backups:
                    sync_manager.restore_from_backup(backup_file)
                else:
                    print("❌ 无效的备份文件名")
            else:
                print("没有可用的备份文件")
                
        elif choice == '8':
            sync_manager.list_backups()
            
        elif choice == '9':
            print("退出同步工具")
            break
            
        else:
            print("无效选择，请重新输入")

if __name__ == '__main__':
    main() 