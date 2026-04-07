# Task Detail Popup Win11 Restyle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the task detail popup to a compact Win11-like mica panel with layered info cards while preserving its current size class and behavior.

**Architecture:** Keep the change local to the detail popup by adding named child containers in `core/task_label.py` and binding new scoped styles in `ui/styles.py`. Cover the new structure with a regression test that fails until those named containers and style hooks exist.

**Tech Stack:** Python, PyQt6, unittest/pytest, scoped QSS in `ui/styles.py`

---

### Task 1: Add failing regression test for detail popup structure

**Files:**
- Modify: `D:/repositories/task_manage/tests/test_panel_form_styles.py`
- Test: `D:/repositories/task_manage/tests/test_panel_form_styles.py`

- [ ] **Step 1: Write the failing test**

```python
    def test_detail_popup_should_define_scoped_win11_card_styles(self):
        styles_py = self._read('ui/styles.py')
        task_label_py = self._read('core/task_label.py')

        self.assertIn('QFrame#task_detail_popup QWidget#detail_section_card', styles_py)
        self.assertIn('QWidget#detail_header_section', task_label_py)
        self.assertIn('QWidget#detail_meta_section', task_label_py)
        self.assertIn('QWidget#detail_notes_section', task_label_py)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_panel_form_styles.py -k detail_popup_should_define_scoped_win11_card_styles -v`
Expected: FAIL because the new selectors and object names do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
# Add named child sections in core/task_label.py and matching scoped selectors in ui/styles.py.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_panel_form_styles.py -k detail_popup_should_define_scoped_win11_card_styles -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_panel_form_styles.py core/task_label.py ui/styles.py
git commit -m "feat: restyle task detail popup"
```

### Task 2: Implement compact Win11-style detail popup restyle

**Files:**
- Modify: `D:/repositories/task_manage/core/task_label.py`
- Modify: `D:/repositories/task_manage/ui/styles.py`
- Test: `D:/repositories/task_manage/tests/test_panel_form_styles.py`

- [ ] **Step 1: Write the failing test**

```python
# Re-use the Task 1 regression test as the red state for the structural style hooks.
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_panel_form_styles.py -k detail_popup_should_define_scoped_win11_card_styles -v`
Expected: FAIL until both structure and styles are present.

- [ ] **Step 3: Write minimal implementation**

```python
# In core/task_label.py:
# - wrap title row in detail_header_section
# - wrap due date, meta row, notes area, and created date in named detail_section_card containers
# - keep popup width unchanged

# In ui/styles.py:
# - replace dark detail popup shell with light Win11-like shell
# - add scoped card/button/header/notes selectors under QFrame#task_detail_popup
# - keep styling isolated to task_detail_popup
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_panel_form_styles.py -k detail_popup_should_define_scoped_win11_card_styles -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_panel_form_styles.py core/task_label.py ui/styles.py
git commit -m "feat: restyle task detail popup"
```

### Task 3: Verify no regressions in related style tests

**Files:**
- Test: `D:/repositories/task_manage/tests/test_panel_form_styles.py`
- Test: `D:/repositories/task_manage/tests/test_ui_dialog_transparency.py`

- [ ] **Step 1: Run focused tests**

```bash
pytest tests/test_panel_form_styles.py tests/test_ui_dialog_transparency.py -v
```

- [ ] **Step 2: Confirm expected result**

Expected: PASS with no new failures from style scoping or dialog shell changes.

- [ ] **Step 3: Commit**

```bash
git add tests/test_panel_form_styles.py core/task_label.py ui/styles.py
git commit -m "test: verify detail popup style restyle"
```
