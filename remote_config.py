import json
import os
from typing import Dict, Optional

class RemoteConfigManager:
    """远程配置管理器"""
    
    def __init__(self, config_file: str = 'remote_config.json'):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self) -> Dict:
        """加载远程配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载远程配置失败: {str(e)}")
        return {}
    
    def save_config(self, config: Dict) -> bool:
        """保存远程配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            print("远程配置保存成功")
            return True
        except Exception as e:
            print(f"保存远程配置失败: {str(e)}")
            return False
    
    def set_server_config(self, api_base_url: str, api_token: str) -> bool:
        """设置服务器配置"""
        config = {
            'api_base_url': api_base_url,
            'api_token': api_token
        }
        return self.save_config(config)
    
    def get_server_config(self) -> Dict:
        """获取服务器配置"""
        return {
            'api_base_url': self.config.get('api_base_url', ''),
            'api_token': self.config.get('api_token', '')
        }
    
    def test_connection(self) -> bool:
        """测试服务器连接"""
        from database_manager import DatabaseManager
        
        if not self.config.get('api_base_url'):
            print("未配置服务器地址")
            return False
        
        try:
            db_manager = DatabaseManager(remote_config=self.config)
            
            # 测试API连接
            result = db_manager._make_api_request('GET', '/api/health')
            if result:
                print("✅ 服务器连接成功")
                return True
            else:
                print("❌ 服务器连接失败")
                return False
                
        except Exception as e:
            print(f"❌ 连接测试失败: {str(e)}")
            return False
    
    def clear_config(self) -> bool:
        """清除远程配置"""
        try:
            if os.path.exists(self.config_file):
                os.remove(self.config_file)
            self.config = {}
            print("远程配置已清除")
            return True
        except Exception as e:
            print(f"清除配置失败: {str(e)}")
            return False

def main():
    """主函数"""
    print("=== 远程服务器配置工具 ===")
    
    config_manager = RemoteConfigManager()
    
    while True:
        print("\n请选择操作:")
        print("1. 设置服务器配置")
        print("2. 查看当前配置")
        print("3. 测试服务器连接")
        print("4. 清除配置")
        print("5. 退出")
        
        choice = input("\n请输入选择 (1-5): ").strip()
        
        if choice == '1':
            print("\n=== 设置服务器配置 ===")
            api_base_url = input("请输入API服务器地址 (例如: https://api.example.com): ").strip()
            api_token = input("请输入API访问令牌: ").strip()
            
            if api_base_url and api_token:
                if config_manager.set_server_config(api_base_url, api_token):
                    print("✅ 服务器配置设置成功")
                else:
                    print("❌ 服务器配置设置失败")
            else:
                print("❌ 请填写完整的配置信息")
                
        elif choice == '2':
            print("\n=== 当前配置 ===")
            config = config_manager.get_server_config()
            if config['api_base_url']:
                print(f"服务器地址: {config['api_base_url']}")
                print(f"访问令牌: {config['api_token'][:10]}..." if config['api_token'] else "未设置")
            else:
                print("未配置服务器信息")
                
        elif choice == '3':
            print("\n=== 测试服务器连接 ===")
            config_manager.test_connection()
            
        elif choice == '4':
            confirm = input("确定要清除远程配置吗？(y/N): ").strip().lower()
            if confirm == 'y':
                config_manager.clear_config()
            else:
                print("取消清除操作")
                
        elif choice == '5':
            print("退出配置工具")
            break
            
        else:
            print("无效选择，请重新输入")

if __name__ == '__main__':
    main() 