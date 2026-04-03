# MessageBox 通知统一设计

## 背景

当前项目中的消息提示与确认对话框存在混用情况：

- 一部分代码直接调用 `QMessageBox.warning(...)`
- 一部分代码直接调用 `QMessageBox.information(...)`
- 一部分代码直接调用 `QMessageBox.question(...)`
- `core/scheduler.py` 中已经有直接实例化 `MessageBox(...).exec()` 的写法

这种状态带来的问题是：

- 调用方式不统一，业务层需要知道不同弹窗 API 的细节
- 后续如果要统一按钮文案、父窗口绑定或视觉风格，需要逐个调用点处理
- `ui/notifications.py` 已经承担了一部分通知封装，但当前覆盖范围不完整

本次改动目标是在**不引入兼容回退**、**不扩大到更重通知架构**的前提下，把项目中的 `QMessageBox` 用法统一替换为 `MessageBox`，并收敛到 `ui/notifications.py`。

## 目标

- 将项目中的 `QMessageBox` 调用统一替换为 `ui/notifications.py` 中的封装函数
- 将普通提示和确认框都统一基于 `qfluentwidgets.MessageBox`
- 保持调用层尽量简单，业务代码不直接处理 `MessageBox` 的实例化和返回值细节
- 让确认框对业务层返回稳定的 `bool` 语义

## 非目标

- 不保留 `QMessageBox` 兼容回退逻辑
- 不改造成更复杂的 `NotificationService` 类或全局服务
- 不把现有成功/错误提示改造成 `InfoBar`
- 不顺带重构与本次替换无关的 UI 行为

## 设计概览

`ui/notifications.py` 继续采用函数式封装，扩展为一组最小但完整的接口：

- `show_success(widget, title, content)`
- `show_info(widget, title, content)`
- `show_warning(widget, title, content)`
- `show_error(widget, title, content)`
- `confirm(widget, title, content) -> bool`

设计原则如下：

- 普通提示和确认弹窗统一由 `ui/notifications.py` 创建
- 业务层只表达“显示什么”，不直接处理弹窗组件细节
- `confirm()` 内部负责执行 `MessageBox` 并把结果规范成 `True/False`
- 不再保留 `QMessageBox` 作为底层实现或兜底分支

## 具体行为

### 普通提示

`show_info()`、`show_warning()`、`show_error()`、`show_success()` 都直接创建并执行 `MessageBox`。

其中：

- `show_success()` 保持现有语义，用于成功提示
- `show_info()` 用于普通信息提示，替换原有 `QMessageBox.information(...)`
- `show_warning()` 用于警告提示，替换原有 `QMessageBox.warning(...)`
- `show_error()` 用于错误提示，替换原有错误弹窗调用

这些函数统一接收：

- `widget`：父窗口
- `title`：弹窗标题
- `content`：弹窗内容

调用方不关心底层是如何构造 `MessageBox` 的。

### 确认框

`confirm(widget, title, content) -> bool` 用于替换所有确认类弹窗。

行为约定：

- 内部创建 `MessageBox`
- 调用 `.exec()`
- 当用户点击确认时返回 `True`
- 当用户取消或关闭时返回 `False`

这样业务层可以统一写成：

- `if not confirm(...): return`

不再关心 `QMessageBox.StandardButton.Yes`、`No` 或 `MessageBox.exec()` 的具体返回值细节。

## 替换范围

本次替换覆盖项目中的以下调用类型：

- `QMessageBox.warning(...)`
- `QMessageBox.information(...)`
- `QMessageBox.question(...)`
- 零散直接写出的 `MessageBox(...).exec()`

预期涉及的业务文件包括：

- `core/quadrant_widget.py`
- `core/scheduler.py`
- `core/task_label.py`
- `core/export_summary_dialog.py`
- `core/complete_table.py`

如果测试文件中存在对旧 `QMessageBox` 调用的断言，也一并调整到新的封装接口或 `MessageBox` 行为。

## 文件修改计划

### 修改 `ui/notifications.py`

- 去掉 `QMessageBox` 依赖
- 引入并统一使用 `MessageBox`
- 新增 `show_info()`、`show_warning()`、`confirm()`
- 保留并按新实现整理 `show_success()`、`show_error()`

### 修改业务文件

- 替换各处 `QMessageBox.*` 调用为 `ui.notifications` 导出的函数
- 删除不再需要的 `QMessageBox` 或 `MessageBox` 直接导入
- 保持现有业务流程和提示文案不变

## 测试策略

采用最小测试补充策略，只验证抽象是否稳定：

- 更新 `tests/test_notifications.py`
- 增加一个普通提示测试，验证会创建并执行 `MessageBox`
- 增加一个确认框测试，验证确认与取消时的布尔返回语义

不为每个业务文件单独新增重复性弹窗测试，避免低价值覆盖。

## 风险与注意事项

- `MessageBox.exec()` 的返回值与 `QMessageBox.question(...)` 不同，实现时需要先确认现有项目里的返回语义，确保 `confirm()` 判断正确
- 业务文件可能对 `QMessageBox.StandardButton.Yes` 做显式比较，这类代码需要同步改写成布尔判断
- 现有 `show_success()` / `show_error()` 测试基于旧实现时，测试断言需要按新的 `MessageBox` 行为更新

## 成功标准

- 代码库中不再有运行时代码对 `QMessageBox` 的直接调用
- 业务层弹窗统一通过 `ui/notifications.py` 访问
- 提示文案与原有行为保持一致
- 确认框调用点能正常得到 `True/False` 结果
- 相关测试通过
