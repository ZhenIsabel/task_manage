# Quadrant Table And Color Grid Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make history/completed-task tables grow only up to the quadrant panel height and then scroll internally, while reorganizing the settings color tab into a 2x2 quadrant grid with full per-quadrant controls.

**Architecture:** Extend the existing `AdaptiveTextTableWidget` with reusable max-visible-height behavior instead of adding a wrapper container. Then wire `HistoryViewer` and `CompleteTableDialog` to pass a recommended height derived from the parent quadrant panel, and refactor `SettingsDialog` color controls into four card widgets laid out by `QGridLayout` while preserving preview and save payloads.

**Tech Stack:** Python 3.12, PyQt6, qfluentwidgets-compatible table wrapper, unittest, pytest

---

## File Structure

- Modify: `ui/adaptive_table.py`
  Adds reusable table height constraint APIs and content-height recalculation.
- Modify: `core/history_viewer.py`
  Applies the table height limit to the history table using the parent quadrant height.
- Modify: `core/complete_table.py`
  Applies the same table height limit to the completed-task table without replacing the existing table instance.
- Modify: `core/settings_dialog.py`
  Rebuilds the color tab into a 2x2 grid of quadrant cards while keeping object names, preview wiring, and result structure stable.
- Modify: `ui/styles.py`
  Adds scoped settings-card styles for the new color-grid layout without affecting other settings tabs.
- Modify: `tests/test_history_viewer_table_layout.py`
  Covers the reusable constrained-height table behavior and dialog integration.
- Modify: `tests/test_settings_dialog.py`
  Verifies the color tab becomes a 2x2 grid while preserving preview and existing slider object names.
- Modify: `tests/test_panel_form_styles.py`
  Verifies the new card styling remains scoped under `settings_panel`.

### Task 1: Create The Dedicated Worktree And Verify Baseline

**Files:**
- Modify: none
- Test: `tests/test_history_viewer_table_layout.py`
- Test: `tests/test_settings_dialog.py`
- Test: `tests/test_panel_form_styles.py`

- [ ] **Step 1: Create the feature worktree**

Run:

```powershell
git worktree add .worktrees/codex-quadrant-table-grid -b codex/quadrant-table-grid
```

Expected: Git reports a new worktree at `.worktrees/codex-quadrant-table-grid` on branch `codex/quadrant-table-grid`.

- [ ] **Step 2: Switch all subsequent work into the new worktree**

Run:

```powershell
Set-Location 'C:\Users\liang\Documents\solutions\task_manage\.worktrees\codex-quadrant-table-grid'
git status --short
```

Expected: no modified files are shown in the new worktree.

- [ ] **Step 3: Run the current targeted baseline tests**

Run:

```powershell
python -m pytest tests/test_history_viewer_table_layout.py tests/test_settings_dialog.py tests/test_panel_form_styles.py -v
```

Expected: PASS for the current baseline before adding the new behavior.

- [ ] **Step 4: Commit the clean worktree checkpoint**

Run:

```powershell
git commit --allow-empty -m "chore: start quadrant table and settings grid worktree"
```

Expected: one empty checkpoint commit on `codex/quadrant-table-grid`.

### Task 2: Add Reusable Constrained-Height Support To The Adaptive Table

**Files:**
- Modify: `ui/adaptive_table.py`
- Test: `tests/test_history_viewer_table_layout.py`

- [ ] **Step 1: Write the failing table-height tests**

Add these tests to `tests/test_history_viewer_table_layout.py`:

```python
    def test_adaptive_table_widget_should_cap_visible_height_when_maximum_is_set(self):
        table = AdaptiveTextTableWidget(
            headers=["值"],
            rows=[[f"第 {i} 行\n额外内容"] for i in range(12)],
            fixed_width_columns={0: 280},
            multiline_columns={0},
        )

        table.set_max_visible_height(180)

        self.assertEqual(table.maximumHeight(), 180)
        self.assertEqual(table.minimumHeight(), 180)

    def test_adaptive_table_widget_should_shrink_after_rows_are_reduced(self):
        table = AdaptiveTextTableWidget(
            headers=["值"],
            rows=[[f"第 {i} 行\n额外内容"] for i in range(12)],
            fixed_width_columns={0: 280},
            multiline_columns={0},
        )

        table.set_max_visible_height(220)
        capped_height = table.maximumHeight()

        table.set_rows([["只剩一行"]])

        self.assertLess(table.maximumHeight(), capped_height)
        self.assertEqual(table.minimumHeight(), table.maximumHeight())
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run:

```powershell
python -m pytest tests/test_history_viewer_table_layout.py -k "cap_visible_height or shrink_after_rows_are_reduced" -v
```

Expected: FAIL because `AdaptiveTextTableWidget` does not yet expose `set_max_visible_height()` or recompute a constrained visible height.

- [ ] **Step 3: Implement the reusable max-visible-height API**

Update `ui/adaptive_table.py` by adding these concrete members and calls:

```python
    def __init__(
        self,
        headers,
        rows,
        fixed_width_columns=None,
        multiline_columns=None,
        parent=None,
    ):
        super().__init__(parent)
        self._headers = list(headers)
        self._rows = list(rows)
        self._fixed_width_columns = dict(fixed_width_columns or {})
        self._multiline_columns = set(multiline_columns or set())
        self._max_visible_height = None

        self.setBorderVisible(True)
        self.setBorderRadius(8)
        self.setColumnCount(len(self._headers))
        self.setHorizontalHeaderLabels(self._headers)
        self.setRowCount(len(self._rows))
        self.setWordWrap(True)
        self.setTextElideMode(Qt.TextElideMode.ElideNone)
        self.horizontalHeader().setTextElideMode(Qt.TextElideMode.ElideNone)
        self.horizontalHeader().setStretchLastSection(False)

        for column in range(self.columnCount()):
            if column in self._fixed_width_columns:
                self.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
                self.setColumnWidth(column, self._fixed_width_columns[column])
            else:
                self.horizontalHeader().setSectionResizeMode(
                    column, QHeaderView.ResizeMode.ResizeToContents
                )

        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.setSortingEnabled(True)
        self.set_rows(self._rows)

    def set_max_visible_height(self, max_height):
        if max_height is None:
            self._max_visible_height = None
        else:
            self._max_visible_height = max(1, int(max_height))
        self._update_visible_height()

    def _content_height(self):
        header_height = self.horizontalHeader().height() if self.horizontalHeader().isVisible() else 0
        frame_height = self.frameWidth() * 2
        row_heights = sum(self.rowHeight(row) for row in range(self.rowCount()))
        scrollbar_height = (
            self.horizontalScrollBar().sizeHint().height()
            if self.horizontalScrollBar().isVisible()
            else 0
        )
        return header_height + frame_height + row_heights + scrollbar_height + 4

    def _update_visible_height(self):
        target_height = self._content_height()
        if self._max_visible_height is not None:
            target_height = min(target_height, self._max_visible_height)
        self.setMinimumHeight(target_height)
        self.setMaximumHeight(target_height)

    def set_rows(self, rows):
        self._rows = list(rows)
        sorting_enabled = self.isSortingEnabled()
        self.setSortingEnabled(False)
        self.clearSpans()
        self.clearContents()
        self.setRowCount(len(self._rows))

        for row_index, row_values in enumerate(self._rows):
            for column_index, value in enumerate(row_values):
                item_text = "" if value is None else str(value)
                item = QTableWidgetItem(item_text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if column_index in self._multiline_columns:
                    width = self._fixed_width_columns.get(column_index, self.columnWidth(column_index))
                    item.setSizeHint(
                        compute_multiline_item_size_hint(self.fontMetrics(), item_text, width)
                    )
                self.setItem(row_index, column_index, item)

        self.resizeRowsToContents()
        self._update_visible_height()
        self.setSortingEnabled(sorting_enabled)
```

Keep the existing imports and add the scrollbar-aware height logic without changing the public constructor signature.

- [ ] **Step 4: Run the table-height tests to verify they pass**

Run:

```powershell
python -m pytest tests/test_history_viewer_table_layout.py -k "cap_visible_height or shrink_after_rows_are_reduced" -v
```

Expected: PASS for both new constrained-height tests.

- [ ] **Step 5: Commit the reusable table behavior**

Run:

```powershell
git add ui/adaptive_table.py tests/test_history_viewer_table_layout.py
git commit -m "feat: constrain adaptive table visible height"
```

### Task 3: Apply The Height Limit In History And Completed-Task Dialogs

**Files:**
- Modify: `core/history_viewer.py`
- Modify: `core/complete_table.py`
- Test: `tests/test_history_viewer_table_layout.py`

- [ ] **Step 1: Write the failing dialog integration tests**

Add these tests to `tests/test_history_viewer_table_layout.py`:

```python
    def test_history_viewer_table_should_apply_a_parent_based_maximum_height(self):
        parent = QWidget()
        parent.resize(1000, 800)

        viewer = HistoryViewer.__new__(HistoryViewer)
        viewer.setParent(parent)
        host = QWidget()
        layout = QVBoxLayout(host)

        viewer.create_merged_history_table(
            layout,
            [
                {
                    "field": "备注",
                    "timestamp": "2026-04-04T01:37:41",
                    "action": "update",
                    "value": "\n".join(f"第 {i} 行" for i in range(12)),
                }
            ],
        )

        table = layout.itemAt(0).widget()
        self.assertLessEqual(table.maximumHeight(), parent.height())
        self.assertGreater(table.maximumHeight(), 0)

    def test_complete_table_should_apply_a_parent_based_maximum_height(self):
        class FakeDbManager:
            def load_tasks(self, all_tasks=False):
                return [
                    {
                        "id": "task-1",
                        "text": "任务A",
                        "completed": True,
                        "completed_date": "2026-04-04",
                        "priority": "高",
                        "notes": "\n".join(f"第 {i} 行" for i in range(20)),
                    }
                ]

        parent = QWidget()
        parent.resize(1000, 800)

        with patch("core.complete_table.get_db_manager", return_value=FakeDbManager()):
            dialog = CompleteTableDialog(parent)

        self.assertLessEqual(dialog.table.maximumHeight(), parent.height())
        self.assertGreater(dialog.table.maximumHeight(), 0)
```

- [ ] **Step 2: Run the dialog integration tests to verify they fail**

Run:

```powershell
python -m pytest tests/test_history_viewer_table_layout.py -k "parent_based_maximum_height" -v
```

Expected: FAIL because neither dialog currently configures a maximum visible height on the table.

- [ ] **Step 3: Implement parent-derived max-height helpers in both dialogs**

Update `core/history_viewer.py`:

```python
    def _recommended_table_max_height(self):
        parent_widget = self.parentWidget()
        if parent_widget is not None and hasattr(parent_widget, "height"):
            return max(220, parent_widget.height() - 260)
        return 420

    def create_merged_history_table(self, layout, merged_history):
        rows = []
        for record in merged_history:
            timestamp = record["timestamp"]
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    time_str = timestamp
            else:
                time_str = "N/A"

            action_text = "创建" if record["action"] == "create" else "更新"
            rows.append([time_str, record["field"], action_text, str(record["value"])])

        table = AdaptiveTextTableWidget(
            headers=["时间", "字段", "操作", "值"],
            rows=rows,
            fixed_width_columns={3: 300},
            multiline_columns={3},
        )
        table.set_max_visible_height(self._recommended_table_max_height())
        layout.addWidget(table)
```

Update `core/complete_table.py`:

```python
    def _recommended_table_max_height(self):
        parent_widget = self.parentWidget()
        if parent_widget is not None and hasattr(parent_widget, "height"):
            return max(260, parent_widget.height() - 240)
        return 460

    def _create_table(self, rows):
        table = AdaptiveTextTableWidget(
            headers=["", "任务内容", "完成日期", "备注"],
            rows=rows,
            fixed_width_columns={0: 30, 3: 300},
            multiline_columns={3},
        )
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        table.set_max_visible_height(self._recommended_table_max_height())
        return table
```

If `_load_completed_tasks()` can materially change the total row heights after reload, reapply the same limit once rows are reset:

```python
            self.table.set_rows(rows)
            self.table.set_max_visible_height(self._recommended_table_max_height())
```

- [ ] **Step 4: Run the dialog integration tests and the existing table tests**

Run:

```powershell
python -m pytest tests/test_history_viewer_table_layout.py -v
```

Expected: PASS, including the existing “reuse same table instance” test and the new height-limit integration coverage.

- [ ] **Step 5: Commit the dialog wiring**

Run:

```powershell
git add core/history_viewer.py core/complete_table.py tests/test_history_viewer_table_layout.py
git commit -m "feat: cap history and completed table heights"
```

### Task 4: Refactor The Settings Color Tab Into A 2x2 Grid Of Quadrant Cards

**Files:**
- Modify: `core/settings_dialog.py`
- Modify: `ui/styles.py`
- Test: `tests/test_settings_dialog.py`
- Test: `tests/test_panel_form_styles.py`

- [ ] **Step 1: Write the failing color-grid tests**

Add these tests to `tests/test_settings_dialog.py`:

```python
from PyQt6.QtWidgets import QGridLayout, QWidget

    def test_color_tab_should_use_a_two_by_two_grid_layout(self):
        dlg = SettingsDialog(None, initial=_sample_initial())
        color_tab = dlg._tab_widget.widget(0)

        self.assertIsInstance(color_tab.layout(), QGridLayout)
        self.assertIsNotNone(dlg.findChild(QWidget, "settings_q1_color_card"))
        self.assertIsNotNone(dlg.findChild(QWidget, "settings_q2_color_card"))
        self.assertIsNotNone(dlg.findChild(QWidget, "settings_q3_color_card"))
        self.assertIsNotNone(dlg.findChild(QWidget, "settings_q4_color_card"))

    def test_color_tab_should_keep_existing_slider_object_names_inside_cards(self):
        dlg = SettingsDialog(None, initial=_sample_initial())

        self.assertIsNotNone(dlg.findChild(QSlider, "settings_q1_hue_range_slider"))
        self.assertIsNotNone(dlg.findChild(QSlider, "settings_q2_saturation_range_slider"))
        self.assertIsNotNone(dlg.findChild(QSlider, "settings_q3_value_range_slider"))
        self.assertIsNotNone(dlg.findChild(QSlider, "settings_q4_hue_range_slider"))
```

Add this scope/style assertion to `tests/test_panel_form_styles.py`:

```python
    def test_settings_panel_styles_should_include_color_card_rules(self):
        styles_py = self._read('ui/styles.py')
        self.assertIn('settingsColorCard', styles_py)
        self.assertIn('settingsColorCardTitle', styles_py)
```

- [ ] **Step 2: Run the new settings tests to verify they fail**

Run:

```powershell
python -m pytest tests/test_settings_dialog.py tests/test_panel_form_styles.py -k "two_by_two_grid_layout or slider_object_names_inside_cards or color_card_rules" -v
```

Expected: FAIL because the color tab still uses a `QFormLayout` and no settings color-card styles exist yet.

- [ ] **Step 3: Implement a reusable quadrant color-card builder**

Refactor `core/settings_dialog.py` to add a helper:

```python
from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

    def _build_quadrant_color_card(self, q_id: str, q_name: str) -> QWidget:
        qdata = self._working_quadrants[q_id]
        cr = self._working_color_ranges[q_id]

        card = QWidget()
        card.setObjectName(f"settings_{q_id}_color_card")
        card.setProperty("settingsColorCard", True)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)

        title = QLabel(q_name)
        title.setProperty("settingsColorCardTitle", True)
        title.setWordWrap(True)
        card_layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(12)
        form.setContentsMargins(0, 0, 0, 0)

        color_btn = QPushButton()
        color_btn.setStyleSheet(f"background-color: {qdata['color']}; border-radius: 15px;")
        color_btn.setFixedSize(30, 30)
        color_btn.clicked.connect(lambda _checked, qid=q_id: self._choose_color(qid))
        self._color_buttons[q_id] = color_btn

        opacity_slider = QSlider(Qt.Orientation.Horizontal)
        opacity_slider.setRange(1, 100)
        opacity_slider.setValue(int(qdata["opacity"] * 100))
        opacity_slider.valueChanged.connect(lambda value, qid=q_id: self._set_opacity(qid, value))
        self._opacity_sliders[q_id] = opacity_slider

        hue_s = QSlider(Qt.Orientation.Horizontal)
        hue_s.setObjectName(f"settings_{q_id}_hue_range_slider")
        hue_s.setRange(0, 180)
        hue_s.setValue(cr["hue_range"])
        hue_s.valueChanged.connect(lambda value, qid=q_id: self._set_color_range(qid, "hue_range", value))

        sat_s = QSlider(Qt.Orientation.Horizontal)
        sat_s.setObjectName(f"settings_{q_id}_saturation_range_slider")
        sat_s.setRange(0, 255)
        sat_s.setValue(cr["saturation_range"])
        sat_s.valueChanged.connect(lambda value, qid=q_id: self._set_color_range(qid, "saturation_range", value))

        val_s = QSlider(Qt.Orientation.Horizontal)
        val_s.setObjectName(f"settings_{q_id}_value_range_slider")
        val_s.setRange(0, 255)
        val_s.setValue(cr["value_range"])
        val_s.valueChanged.connect(lambda value, qid=q_id: self._set_color_range(qid, "value_range", value))

        self._color_range_sliders[q_id] = {
            "hue_range": hue_s,
            "saturation_range": sat_s,
            "value_range": val_s,
        }

        form.addRow("颜色:", color_btn)
        form.addRow("透明度:", opacity_slider)
        form.addRow("色相范围:", hue_s)
        form.addRow("饱和度范围:", sat_s)
        form.addRow("明度范围:", val_s)
        card_layout.addLayout(form)
        return card
```

- [ ] **Step 4: Replace the old single-column color tab with a 2x2 grid**

Update `_build_color_tab()` in `core/settings_dialog.py`:

```python
    def _build_color_tab(self) -> QWidget:
        widget = QWidget()
        layout = QGridLayout(widget)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        self._color_buttons = {}
        self._opacity_sliders = {}
        self._color_range_sliders = {}

        quadrant_order = ["q1", "q2", "q3", "q4"]
        for index, q_id in enumerate(quadrant_order):
            row = index // 2
            column = index % 2
            card = self._build_quadrant_color_card(q_id, QUADRANT_NAMES[q_id])
            layout.addWidget(card, row, column)

        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        return widget
```

- [ ] **Step 5: Add scoped styles for the new color cards**

Append these rules inside the existing `"settings_panel"` stylesheet in `ui/styles.py`:

```python
            QWidget#settings_panel QWidget[settingsColorCard="true"] {{
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
            }}
            QWidget#settings_panel QLabel[settingsColorCardTitle="true"] {{
                color: #1f2937;
                font-size: 13px;
                font-weight: 600;
                padding: 0 0 4px 0;
            }}
```

- [ ] **Step 6: Run the settings and style tests to verify they pass**

Run:

```powershell
python -m pytest tests/test_settings_dialog.py tests/test_panel_form_styles.py -v
```

Expected: PASS, including the existing preview/get-result tests and the new 2x2 grid coverage.

- [ ] **Step 7: Commit the settings grid refactor**

Run:

```powershell
git add core/settings_dialog.py ui/styles.py tests/test_settings_dialog.py tests/test_panel_form_styles.py
git commit -m "feat: organize settings colors in a quadrant grid"
```

### Task 5: Final Verification And Handoff

**Files:**
- Modify: none
- Test: `tests/test_history_viewer_table_layout.py`
- Test: `tests/test_settings_dialog.py`
- Test: `tests/test_panel_form_styles.py`

- [ ] **Step 1: Run the focused regression suite**

Run:

```powershell
python -m pytest tests/test_history_viewer_table_layout.py tests/test_settings_dialog.py tests/test_panel_form_styles.py -v
```

Expected: all targeted tests PASS.

- [ ] **Step 2: Run a broader smoke suite for nearby UI regressions**

Run:

```powershell
python -m pytest tests/test_ui_dialog_transparency.py tests/test_fluent_date_picker_migration.py tests/test_notifications.py -v
```

Expected: PASS, proving the dialog and shared UI helpers still behave correctly.

- [ ] **Step 3: Perform the manual UI check**

Open the app from the worktree and verify:

```powershell
python main.py
```

Expected manual results:

```text
1. 历史记录较少时，弹窗表格保持紧凑高度。
2. 历史记录较多时，表格高度停止增长，滚动条只出现在表格内部。
3. 已完成任务较多时，按钮区保持固定可见，全选/还原仍可用。
4. 设置 > 颜色设置页展示为 2x2 象限卡片，每个卡片都包含颜色、透明度、色相、饱和度、明度控件。
5. 调整任一颜色按钮或滑杆时，四象限主面板实时预览仍然更新。
```

- [ ] **Step 4: Commit the final verified implementation**

Run:

```powershell
git status --short
git add ui/adaptive_table.py core/history_viewer.py core/complete_table.py core/settings_dialog.py ui/styles.py tests/test_history_viewer_table_layout.py tests/test_settings_dialog.py tests/test_panel_form_styles.py
git commit -m "feat: constrain quadrant tables and grid color controls"
```

Expected: a clean commit containing the verified implementation.
