# UIManager 使用指南

## 概述

`UIManager` 是一个强大的UI控件管理类，用于统一管理应用程序中各种控件的显示、隐藏、动画、状态和属性。它提供了集中化的控件管理，使代码更加清晰和易于维护。

## 主要功能

### 1. 控件注册和管理
- 注册控件到管理器
- 统一管理控件的显示/隐藏状态
- 支持控件的批量操作

### 2. 动画效果
- 淡入淡出动画
- 可自定义动画时长
- 动画完成回调

### 3. 状态管理
- 跟踪控件状态变化
- 状态变化信号通知
- 自动保存控件状态

### 4. 属性管理
- 为控件设置自定义属性
- 属性持久化
- 属性查询和修改

### 5. 事件处理
- 注册事件处理器
- 统一事件管理
- 事件回调机制

## 基本使用方法

### 1. 创建和初始化

```python
from ui import UIManager

# 创建UI管理器实例
ui_manager = UIManager()

# 在应用关闭时清理资源
def closeEvent(self, event):
    self.ui_manager.cleanup()
    event.accept()
```

### 2. 注册控件

```python
# 注册控件到管理器
ui_manager.register_widget("button1", self.button1, "visible")
ui_manager.register_widget("label1", self.label1, "visible")
ui_manager.register_widget("slider1", self.slider1, "hidden")

# 设置控件属性
ui_manager.set_widget_property("button1", "type", "push_button")
ui_manager.set_widget_property("button1", "color", "#FF6B6B")
```

### 3. 显示和隐藏控件

```python
# 显示控件（带动画）
ui_manager.show_widget("button1", animate=True, duration=300)

# 隐藏控件（带动画）
ui_manager.hide_widget("button1", animate=True, duration=300)

# 切换控件可见性
ui_manager.toggle_widget_visibility("button1", animate=True)

# 淡入淡出效果
ui_manager.fade_in_widget("button1", duration=500)
ui_manager.fade_out_widget("button1", duration=500)
```

### 4. 控件状态管理

```python
# 获取控件状态
state = ui_manager.get_widget_state("button1")

# 设置控件启用状态
ui_manager.set_widget_enabled("button1", True)

# 检查控件是否启用
is_enabled = ui_manager.is_widget_enabled("button1")
```

### 5. 控件位置和大小

```python
# 设置控件位置
ui_manager.set_widget_position("button1", 100, 200)

# 获取控件位置
position = ui_manager.get_widget_position("button1")

# 设置控件大小
ui_manager.set_widget_size("button1", 150, 50)

# 获取控件大小
size = ui_manager.get_widget_size("button1")
```

### 6. 信号连接

```python
# 连接状态变化信号
ui_manager.widget_state_changed.connect(self.on_widget_state_changed)

# 连接动画完成信号
ui_manager.animation_finished.connect(self.on_animation_finished)

def on_widget_state_changed(self, widget_name, new_state):
    print(f"控件 {widget_name} 状态改变为: {new_state}")

def on_animation_finished(self, widget_name):
    print(f"控件 {widget_name} 动画完成")
```

### 7. 事件处理器注册

```python
# 注册事件处理器
ui_manager.register_event_handler("button1", "click", self.on_button1_click)
ui_manager.register_event_handler("button1", "hover", self.on_button1_hover)

def on_button1_click(self):
    print("按钮1被点击")

def on_button1_hover(self):
    print("鼠标悬停在按钮1上")
```

## 高级用法

### 1. 批量操作

```python
# 显示所有控件
widgets = ["button1", "label1", "slider1"]
for widget_name in widgets:
    ui_manager.show_widget(widget_name, animate=True)

# 隐藏所有控件
for widget_name in widgets:
    ui_manager.hide_widget(widget_name, animate=True)
```

### 2. 序列动画

```python
from PyQt6.QtCore import QTimer

# 创建序列动画效果
ui_manager.fade_out_widget("widget1", duration=300)
QTimer.singleShot(300, lambda: ui_manager.fade_in_widget("widget1", duration=300))
QTimer.singleShot(600, lambda: ui_manager.fade_out_widget("widget2", duration=300))
QTimer.singleShot(900, lambda: ui_manager.fade_in_widget("widget2", duration=300))
```

### 3. 获取所有控件信息

```python
# 获取所有控件的详细信息
info = ui_manager.get_all_widgets_info()
for name, data in info.items():
    print(f"控件: {name}")
    print(f"  状态: {data['state']}")
    print(f"  可见: {data['visible']}")
    print(f"  启用: {data['enabled']}")
    print(f"  位置: {data['position']}")
    print(f"  大小: {data['size']}")
    print(f"  属性: {data['properties']}")
```

### 4. 条件显示

```python
# 根据条件显示/隐藏控件
if some_condition:
    ui_manager.show_widget("advanced_panel", animate=True)
else:
    ui_manager.hide_widget("advanced_panel", animate=True)
```

## 在四象限任务管理工具中的应用

### 1. 主窗口集成

```python
# 在 main.py 中
class TaskManagerApp:
    def __init__(self):
        self.ui_manager = UIManager()
        
    def initialize(self):
        # 创建主窗口并传入UI管理器
        self.main_window = QuadrantWidget(self.config, ui_manager=self.ui_manager)
        
        # 注册各种控件
        self.ui_manager.register_widget("main_window", self.main_window, "visible")
        self.ui_manager.register_widget("control_panel", self.main_window.control_widget, "visible")
        self.ui_manager.register_widget("edit_button", self.main_window.edit_button, "visible")
        # ... 更多控件
```

### 2. 编辑模式切换

```python
# 在 QuadrantWidget 中
def toggle_edit_mode(self):
    self.edit_mode = not self.edit_mode
    
    # 使用UI管理器管理按钮显示/隐藏
    if self.ui_manager:
        if self.edit_mode:
            self.ui_manager.show_widget("add_task_button", animate=True)
            self.ui_manager.show_widget("export_tasks_button", animate=True)
        else:
            self.ui_manager.hide_widget("add_task_button", animate=True)
            self.ui_manager.hide_widget("export_tasks_button", animate=True)
```

### 3. 任务标签管理

```python
# 创建任务时注册到UI管理器
def create_task(self, task_data):
    task = TaskLabel(task_id, color, parent=self, **task_data)
    
    # 注册任务到UI管理器
    task_name = f"task_{task.task_id}"
    self.ui_manager.register_widget(task_name, task, "visible")
    
    # 设置任务属性
    self.ui_manager.set_widget_property(task_name, "quadrant", quadrant)
    self.ui_manager.set_widget_property(task_name, "priority", priority)
```

## 最佳实践

### 1. 命名规范
- 使用有意义的控件名称
- 保持命名一致性
- 避免使用特殊字符

```python
# 好的命名
ui_manager.register_widget("main_window", self.main_window)
ui_manager.register_widget("control_panel", self.control_widget)
ui_manager.register_widget("add_task_button", self.add_button)

# 避免的命名
ui_manager.register_widget("w1", self.widget1)
ui_manager.register_widget("btn", self.button)
```

### 2. 状态管理
- 及时更新控件状态
- 使用状态变化信号
- 保持状态一致性

```python
# 监听状态变化
ui_manager.widget_state_changed.connect(self.update_ui_state)

def update_ui_state(self, widget_name, new_state):
    # 根据状态变化更新其他相关控件
    if widget_name == "edit_mode" and new_state == "active":
        self.enable_edit_controls()
```

### 3. 动画使用
- 合理使用动画效果
- 避免过度动画
- 考虑用户体验

```python
# 快速切换使用短动画
ui_manager.show_widget("tooltip", animate=True, duration=200)

# 重要操作使用较长动画
ui_manager.fade_in_widget("main_panel", animate=True, duration=500)
```

### 4. 资源管理
- 及时清理资源
- 避免内存泄漏
- 正确处理关闭事件

```python
def closeEvent(self, event):
    # 清理UI管理器资源
    if hasattr(self, 'ui_manager'):
        self.ui_manager.cleanup()
    event.accept()
```

## 故障排除

### 1. 控件未找到
```python
# 检查控件是否已注册
if "widget_name" in ui_manager.visible_widgets:
    ui_manager.show_widget("widget_name")
else:
    print("控件未注册")
```

### 2. 动画不工作
```python
# 确保控件支持透明度动画
if hasattr(widget, 'setWindowOpacity'):
    ui_manager.show_widget("widget_name", animate=True)
else:
    ui_manager.show_widget("widget_name", animate=False)
```

### 3. 状态不同步
```python
# 手动同步状态
widget_state = ui_manager.get_widget_state("widget_name")
if widget_state != "expected_state":
    ui_manager.widget_states["widget_name"] = "expected_state"
```

## 总结

`UIManager` 提供了一个强大而灵活的UI控件管理解决方案。通过合理使用其功能，可以：

1. **提高代码可维护性** - 集中管理所有UI控件
2. **增强用户体验** - 统一的动画和交互效果
3. **简化开发流程** - 减少重复代码
4. **提升应用性能** - 优化的状态管理和资源清理

通过遵循本指南的最佳实践，你可以充分利用 `UIManager` 的功能，创建更加专业和用户友好的应用程序。 