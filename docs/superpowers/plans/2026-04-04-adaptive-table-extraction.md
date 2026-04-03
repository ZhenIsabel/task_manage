# Adaptive Table Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把历史记录弹窗里“多行文本自适应高度”的表格抽到 `ui` 层作为可复用组件，并让 `history_viewer` 依赖该组件。

**Architecture:** 在 `ui/adaptive_table.py` 中新增一个继承 `qfluentwidgets.TableWidget` 的轻量组件，统一封装表头、行数据、固定列宽和多行列的 `sizeHint` 逻辑。`core/history_viewer.py` 只负责组装历史记录数据，不再持有通用表格布局代码。

**Tech Stack:** Python, PyQt6, qfluentwidgets, unittest

---

### Task 1: 先用测试锁定新抽象接口

**Files:**
- Modify: `tests/test_history_viewer_table_layout.py`
- Test: `tests/test_history_viewer_table_layout.py`

- [ ] **Step 1: Write the failing test**

```python
from ui.adaptive_table import AdaptiveTextTableWidget, compute_multiline_item_size_hint

def test_history_viewer_should_use_adaptive_table_widget(self):
    source = self._read("core/history_viewer.py")
    self.assertIn("AdaptiveTextTableWidget", source)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m unittest tests.test_history_viewer_table_layout`
Expected: FAIL with import error or assertion failure because `ui.adaptive_table` and `AdaptiveTextTableWidget` 还不存在

- [ ] **Step 3: Write minimal implementation**

```python
class AdaptiveTextTableWidget(TableWidget):
    pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m unittest tests.test_history_viewer_table_layout`
Expected: PASS for the new import/usage assertions

### Task 2: 提取通用自适应表格组件

**Files:**
- Create: `ui/adaptive_table.py`
- Modify: `ui/__init__.py`
- Test: `tests/test_history_viewer_table_layout.py`

- [ ] **Step 1: Write the failing test**

```python
def test_adaptive_table_widget_should_expand_multiline_columns(self):
    table = AdaptiveTextTableWidget(
        headers=["值"],
        rows=[["第一行\n第二行\n第三行\n第四行"]],
        fixed_width_columns={0: 300},
        multiline_columns={0},
    )
    self.assertGreater(table.item(0, 0).sizeHint().height(), 30)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m unittest tests.test_history_viewer_table_layout`
Expected: FAIL because组件还未真正实现多行 size hint

- [ ] **Step 3: Write minimal implementation**

```python
def compute_multiline_item_size_hint(font_metrics, text, width):
    ...

class AdaptiveTextTableWidget(TableWidget):
    def __init__(self, headers, rows, fixed_width_columns=None, multiline_columns=None, parent=None):
        ...
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m unittest tests.test_history_viewer_table_layout`
Expected: PASS

### Task 3: 让历史记录弹窗改用新组件

**Files:**
- Modify: `core/history_viewer.py`
- Test: `tests/test_history_viewer_table_layout.py`

- [ ] **Step 1: Write the failing test**

```python
def test_history_viewer_should_build_history_table_through_adaptive_widget(self):
    source = self._read("core/history_viewer.py")
    self.assertIn("AdaptiveTextTableWidget(", source)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m unittest tests.test_history_viewer_table_layout`
Expected: FAIL because `history_viewer` 仍直接操作 `TableWidget`

- [ ] **Step 3: Write minimal implementation**

```python
table = AdaptiveTextTableWidget(
    headers=["时间", "字段", "操作", "值"],
    rows=rows,
    fixed_width_columns={3: 300},
    multiline_columns={3},
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `venv\Scripts\python.exe -m unittest tests.test_history_viewer_table_layout`
Expected: PASS

### Task 4: 全量回归验证

**Files:**
- Test: `tests/test_history_viewer_table_layout.py`
- Test: `tests/test_ui_dialog_transparency.py`

- [ ] **Step 1: Run focused regression suite**

Run: `venv\Scripts\python.exe -m unittest tests.test_history_viewer_table_layout tests.test_ui_dialog_transparency`
Expected: `OK`

- [ ] **Step 2: Check diagnostics**

Run: lints for `ui/adaptive_table.py`, `ui/__init__.py`, `core/history_viewer.py`, `tests/test_history_viewer_table_layout.py`
Expected: no new errors
