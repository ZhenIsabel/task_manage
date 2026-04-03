# MessageBox 通知统一 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将运行时代码中的 `QMessageBox` 调用统一替换为 `ui.notifications` 的 `MessageBox` 封装，并保持原有提示文案与确认流程语义不变。

**Architecture:** 保持 `ui/notifications.py` 为函数式通知入口，新增最小接口 `show_info()`、`show_warning()`、`confirm()`，并把现有 `show_success()`、`show_error()` 一并收敛到统一的 `MessageBox` 构造逻辑。业务文件只调用通知函数，不再直接实例化 `QMessageBox` 或 `MessageBox`。

**Tech Stack:** Python, PyQt6, qfluentwidgets, unittest, unittest.mock

---

## File Structure

### Modify

- `ui/notifications.py`：统一封装 `MessageBox` 提示与确认接口
- `tests/test_notifications.py`：新增 `MessageBox` 封装行为测试
- `core/scheduler.py`：替换必填校验警告与删除确认对话框
- `core/complete_table.py`：替换还原确认对话框
- `core/task_label.py`：替换必填校验警告
- `core/export_summary_dialog.py`：替换日期错误与无数据提示
- `core/quadrant_widget.py`：替换添加任务必填校验与导出信息提示

### No New Runtime Files

- 不新增通知服务类
- 不新增兼容回退层
- 不新增业务级包装器

### Test Scope

- 定向执行 `tests/test_notifications.py`
- 定向执行依赖弹窗替换的现有测试（如果存在与通知模块直接相关的失败再补）

### Task 1: 先写失败测试，锁定新通知接口

**Files:**
- Modify: `tests/test_notifications.py`
- Test: `tests/test_notifications.py`

- [ ] **Step 1: 写 `show_warning()` 和 `confirm()` 的失败测试**

```python
import os
import unittest
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QApplication, QWidget

from ui.notifications import (
    confirm,
    resolve_notification_host,
    show_error,
    show_success,
    show_warning,
)


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class NotificationHelpersTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_show_warning_uses_message_box_with_top_level_parent(self):
        main_window = QWidget()
        dialog = QWidget(main_window)
        child = QWidget(dialog)
        self.addCleanup(child.deleteLater)
        self.addCleanup(dialog.deleteLater)
        self.addCleanup(main_window.deleteLater)

        box = MagicMock()

        with patch("ui.notifications.MessageBox", return_value=box) as message_box_cls:
            show_warning(child, "提示", "任务内容 为必填项")

        message_box_cls.assert_called_once_with("提示", "任务内容 为必填项", main_window)
        box.exec.assert_called_once_with()

    def test_confirm_returns_true_when_user_accepts(self):
        parent = QWidget()
        self.addCleanup(parent.deleteLater)
        box = MagicMock()
        box.exec.return_value = True

        with patch("ui.notifications.MessageBox", return_value=box) as message_box_cls:
            result = confirm(parent, "确认删除", "确定删除吗？")

        self.assertTrue(result)
        message_box_cls.assert_called_once_with("确认删除", "确定删除吗？", parent)
        box.exec.assert_called_once_with()

    def test_confirm_returns_false_when_user_cancels(self):
        parent = QWidget()
        self.addCleanup(parent.deleteLater)
        box = MagicMock()
        box.exec.return_value = False

        with patch("ui.notifications.MessageBox", return_value=box):
            result = confirm(parent, "确认还原", "确定还原吗？")

        self.assertFalse(result)
```

- [ ] **Step 2: 运行测试，确认因缺少新接口或旧行为不符而失败**

Run: `python -m unittest tests.test_notifications -v`

Expected:
- `ImportError` 或 `AttributeError`，因为 `show_warning` / `confirm` 尚未存在
- 或断言失败，因为 `show_success` / `show_error` 仍在走 `InfoBar` / `QMessageBox`

- [ ] **Step 3: 补齐现有测试，使其也指向 `MessageBox` 行为**

```python
    def test_show_success_uses_message_box(self):
        main_window = QWidget()
        dialog = QWidget(main_window)
        child = QWidget(dialog)
        self.addCleanup(child.deleteLater)
        self.addCleanup(dialog.deleteLater)
        self.addCleanup(main_window.deleteLater)
        box = MagicMock()

        with patch("ui.notifications.MessageBox", return_value=box) as message_box_cls:
            show_success(child, "成功", "操作完成")

        message_box_cls.assert_called_once_with("成功", "操作完成", main_window)
        box.exec.assert_called_once_with()

    def test_show_error_uses_message_box_when_host_exists(self):
        parent = QWidget()
        self.addCleanup(parent.deleteLater)
        box = MagicMock()

        with patch("ui.notifications.MessageBox", return_value=box) as message_box_cls:
            show_error(parent, "失败", "没有可用窗口")

        message_box_cls.assert_called_once_with("失败", "没有可用窗口", parent)
        box.exec.assert_called_once_with()
```

- [ ] **Step 4: 再次运行测试，确认仍然失败但失败原因只剩实现缺失**

Run: `python -m unittest tests.test_notifications -v`

Expected:
- 新增测试被发现
- 失败集中在 `ui.notifications` 尚未完成的实现，而不是测试语法或导入错误

- [ ] **Step 5: 提交前检查当前 diff，不提交**

Run: `git diff -- tests/test_notifications.py`

Expected:
- 只看到测试文件改动
- 暂不提交，等实现和调用点替换一起验证后再考虑提交

### Task 2: 用最小实现收敛 `ui.notifications`

**Files:**
- Modify: `ui/notifications.py`
- Test: `tests/test_notifications.py`

- [ ] **Step 1: 实现统一的 `MessageBox` 构造辅助函数**

```python
from __future__ import annotations

from typing import Optional

from PyQt6.QtWidgets import QApplication, QWidget
from qfluentwidgets import MessageBox


def resolve_notification_host(widget: Optional[QWidget]) -> Optional[QWidget]:
    host = widget or QApplication.activeWindow()
    while host is not None and host.parentWidget() is not None:
        host = host.parentWidget()
    return host


def _show_message_box(widget: Optional[QWidget], title: str, content: str) -> bool:
    host = resolve_notification_host(widget)
    box = MessageBox(title, content, host)
    return bool(box.exec())
```

- [ ] **Step 2: 基于该辅助函数补齐公开接口**

```python
def show_success(widget: Optional[QWidget], title: str, content: str):
    _show_message_box(widget, title, content)


def show_info(widget: Optional[QWidget], title: str, content: str):
    _show_message_box(widget, title, content)


def show_warning(widget: Optional[QWidget], title: str, content: str):
    _show_message_box(widget, title, content)


def show_error(widget: Optional[QWidget], title: str, content: str):
    _show_message_box(widget, title, content)


def confirm(widget: Optional[QWidget], title: str, content: str) -> bool:
    return _show_message_box(widget, title, content)
```

- [ ] **Step 3: 删除旧实现中与本次方案冲突的代码**

```python
# 删除这些旧依赖和旧常量
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QMessageBox, QWidget
from qfluentwidgets import InfoBar, InfoBarPosition

DEFAULT_SUCCESS_DURATION_MS = 1000
DEFAULT_ERROR_DURATION_MS = -1

# 删除整个旧辅助函数定义
def _show_info_bar(factory, fallback, widget, title, content, *, position, duration):
    host = resolve_notification_host(widget)
    if host is None:
        fallback(None, title, content)
        return None

    return factory(
        title=title,
        content=content,
        orient=Qt.Orientation.Horizontal,
        isClosable=True,
        position=position,
        duration=duration,
        parent=host,
    )
```

- [ ] **Step 4: 运行通知模块测试，确认全部转绿**

Run: `python -m unittest tests.test_notifications -v`

Expected:
- `ok` 覆盖 `resolve_notification_host`
- `ok` 覆盖 `show_success`
- `ok` 覆盖 `show_warning`
- `ok` 覆盖 `show_error`
- `ok` 覆盖 `confirm` 的确认/取消分支

- [ ] **Step 5: 检查 `ui.notifications` 对外接口是否与计划一致**

Run: `python -c "from ui.notifications import confirm, show_error, show_info, show_success, show_warning; print(all([confirm, show_error, show_info, show_success, show_warning]))"`

Expected:
- 输出 `True`

### Task 3: 替换运行时代码中的 `QMessageBox` / 直接 `MessageBox` 调用

**Files:**
- Modify: `core/scheduler.py`
- Modify: `core/complete_table.py`
- Modify: `core/task_label.py`
- Modify: `core/export_summary_dialog.py`
- Modify: `core/quadrant_widget.py`
- Test: `tests/test_notifications.py`

- [ ] **Step 1: 在业务文件中切换导入**

```python
# scheduler.py
from ui.notifications import confirm, show_error, show_success, show_warning

# complete_table.py
from ui.notifications import confirm, show_error, show_success

# task_label.py
from ui.notifications import show_error, show_warning

# export_summary_dialog.py
from ui.notifications import show_error, show_success, show_warning

# quadrant_widget.py
from ui.notifications import show_error, show_info, show_success, show_warning
```

- [ ] **Step 2: 用通知函数替换提示类弹窗**

```python
# scheduler.py
for f in task_fields:
    if f.get("required") and not task_data.get(f["name"]):
        show_warning(self, "提示", f"{f['label']} 为必填项")
        return

# task_label.py
for f in task_fields:
    if f.get("required") and not task_data.get(f["name"]):
        show_warning(self, "提示", f"{f['label']} 为必填项")
        return

# export_summary_dialog.py
if start_date > end_date:
    show_warning(self, "日期错误", "开始日期不能晚于结束日期")
    return

if not self.summary_data:
    show_warning(self, "提示", "没有可导出的数据")
    return

# quadrant_widget.py
if not unfinished_tasks:
    show_info(self, "导出任务", "没有未完成的任务可导出")
    return
```

- [ ] **Step 3: 用 `confirm()` 替换确认弹窗**

```python
# scheduler.py
if not confirm(self, "确认删除", f"确定要将 {len(self.selected_tasks)} 个定时任务删除吗？"):
    return

# complete_table.py
if not confirm(self, "确认还原", f"确定要将 {len(self.selected_tasks)} 个任务还原为未完成状态吗？"):
    return
```

- [ ] **Step 4: 清理不再需要的 Qt / Fluent 直接导入**

```python
# 删除类似这些旧导入
from PyQt6.QtWidgets import QMessageBox
from qfluentwidgets import MessageBox
```

- [ ] **Step 5: 搜索确认运行时代码已无 `QMessageBox` 剩余调用**

Run: `rg QMessageBox core ui`

Expected:
- 运行时代码目录 `core` / `ui` 中不再出现 `QMessageBox`
- 如果只剩文档或测试引用，继续保留

- [ ] **Step 6: 运行定向测试验证**

Run: `python -m unittest tests.test_notifications -v`

Expected:
- 全部通过

- [ ] **Step 7: 读取静态诊断，确认没有引入新的导入或名称错误**

Run: 使用 IDE lint 读取 `ui/notifications.py`、`core/scheduler.py`、`core/complete_table.py`、`core/task_label.py`、`core/export_summary_dialog.py`、`core/quadrant_widget.py`

Expected:
- 无新增未使用导入
- 无未定义名称
- 无拼写型接口错误

- [ ] **Step 8: 查看最终 diff，确认范围与计划一致**

Run: `git diff -- ui/notifications.py tests/test_notifications.py core/scheduler.py core/complete_table.py core/task_label.py core/export_summary_dialog.py core/quadrant_widget.py`

Expected:
- 只包含通知封装和调用点替换
- 不包含无关格式化或顺手重构
