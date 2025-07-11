class FunctionManager:
    """负责功能逻辑的类"""
    def __init__(self):
        self.functions = {}
        self.active_functions = set()
    
    def register_function(self, function_name, function):
        """注册功能函数"""
        self.functions[function_name] = function
    
    def execute_function(self, function_name, *args, **kwargs):
        """执行功能函数"""
        if function_name in self.functions:
            try:
                result = self.functions[function_name](*args, **kwargs)
                self.active_functions.add(function_name)
                return result
            except Exception as e:
                print(f"执行功能 {function_name} 时出错: {e}")
                return None
        else:
            print(f"功能 {function_name} 未注册")
            return None
    
    def deactivate_function(self, function_name):
        """停用功能"""
        if function_name in self.active_functions:
            self.active_functions.remove(function_name)
    
    def is_function_active(self, function_name):
        """检查功能是否激活"""
        return function_name in self.active_functions
    
    def get_all_functions(self):
        """获取所有注册的功能"""
        return list(self.functions.keys())
    
    def get_active_functions(self):
        """获取所有激活的功能"""
        return list(self.active_functions)


class StorageManager:
    """负责数据存储的类"""
    def __init__(self):
        self.data = {}
        self.file_path = None
    
    def set_file_path(self, file_path):
        """设置存储文件路径"""
        self.file_path = file_path
    
    def save_data(self, key, value):
        """保存数据"""
        self.data[key] = value
    
    def load_data(self, key, default=None):
        """加载数据"""
        return self.data.get(key, default)
    
    def delete_data(self, key):
        """删除数据"""
        if key in self.data:
            del self.data[key]
    
    def clear_all_data(self):
        """清空所有数据"""
        self.data.clear()
    
    def get_all_data(self):
        """获取所有数据"""
        return self.data.copy()
    
    def save_to_file(self, file_path=None):
        """保存数据到文件"""
        import json
        target_path = file_path or self.file_path
        if target_path:
            try:
                with open(target_path, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=2)
                return True
            except Exception as e:
                print(f"保存文件时出错: {e}")
                return False
        return False
    
    def load_from_file(self, file_path=None):
        """从文件加载数据"""
        import json
        import os
        target_path = file_path or self.file_path
        if target_path and os.path.exists(target_path):
            try:
                with open(target_path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                return True
            except Exception as e:
                print(f"加载文件时出错: {e}")
                return False
        return False

