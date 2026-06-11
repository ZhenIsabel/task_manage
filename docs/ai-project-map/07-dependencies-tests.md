# 依赖与测试地图

> [返回 AI 项目地图总目录](../AI_PROJECT_MAP.md)
>
> **阅读范围：** 用于确定第三方库使用点、选择聚焦测试、了解当前测试基线和覆盖缺口。
>
> **相关分卷：** 改动影响和风险优先级见 [08](08-change-guide-risks.md)。
## 第三方依赖到使用点映射

| 依赖 | 使用点 | 用途/备注 |
|---|---|---|
| `PyQt6` | `main.py`、`core/*`、`ui/*`、托盘 | GUI、线程、信号、绘制、表格、对话框 |
| `PyQt6-Fluent-Widgets` / `qfluentwidgets` | `ui/fluent.py`、`ui/scrollbar.py`、`ui/adaptive_table.py`、通知、设置 | Fluent 控件、InfoBar、TableWidget、平滑滚动 |
| `requests` | `database/database_manager.py` | 远程 REST |
| `pywin32` | `windows/tray_launcher.py` | 枚举/恢复/置前 Win32 窗口；缺包时托盘仍可启动但不能置前 |
| `pandas` | `quadrant_widget.py`、`history_viewer.py`、`export_summary_dialog.py` | 文本数据表和 Excel/CSV 导出 |
| `openpyxl` | 同上 | pandas Excel writer 与列宽设置 |
| `Flask` | `gantt/app.py` | 本地甘特服务 |
| `Flask-CORS` | `gantt/app.py` | `/tasks` 跨域 |
| `volcengine-python-sdk[ark]` | `core/LLMService.py` | `AsyncArk` LLM 调用 |
| `frappe-gantt` npm 包 | `package.json` | 当前源码未直接引用；实际 HTML 使用 CDN |
| 可选 `PyQt6.QtWebEngineWidgets` | `QuadrantWidget.show_gantt_dialog()` 动态导入 | 内嵌甘特页，失败时系统浏览器回退 |
| `sqlite3` 标准库 | DB 管理器、甘特、维护脚本 | 本地持久化 |
| `threading` / `QThread` / `ThreadPoolExecutor` | DB、远程 bootstrap、Flask、概要导出 | 多种并发模型并存 |

## 测试覆盖地图

全套测试使用 `unittest` 风格；部分 UI 测试设置 offscreen 平台并用 Win32 stub。首选完整命令：

```powershell
& '.\venv\Scripts\python.exe' -m unittest discover -s tests -v
```

### 当前测试基线（2026-06-10）

- 本地图验收时运行完整测试命令，进程退出码为 1；失败集中在 `tests/test_database_manager_remote.py` 的设置对话框相关测试。
- 单独运行该模块得到：`Ran 52 tests`，`FAILED (errors=8)`。
- 其中 7 个 error 是测试文件缺少 `deepcopy` 或 `MagicMock` 导入导致的 `NameError`；另 1 个 error 是测试仍 patch `core.quadrant_widget.QMessageBox.warning`，但该模块当前没有 `QMessageBox` 属性。
- 本次地图工作只新增 Markdown 文件，没有修改业务代码或测试。后续 AI 不应把这 8 个既有 error 自动归因于自己的改动，也不应声称当前全套测试为绿色；修复它们时应作为独立任务重新验证。

| 测试文件 | 主要覆盖 |
|---|---|
| `test_database_manager_remote.py` | 启动不抢跑同步、401 自动注册、鉴权暂停、普通/定时任务缓存先写、远程时间比较、5 分钟本地优先、冲突接受/拒绝、远程设置提交/回滚、后台 bootstrap、任务列表批量重建 |
| `test_database_manager_history_sync.py` | 完成/删除分页排序、关键字与转义、ID 全选查询、完成/删除还原语义、历史分页、仅本地历史、远程历史合并、上传携带历史 |
| `test_archive_task_panels.py` | 完成/删除共享基类、删除列表文案、跨页选择、批量还原、主窗口“完成/更多”菜单路由 |
| `test_history_viewer_table_layout.py` | 自适应表格、历史行渲染、完成列表原地刷新、搜索防抖、加载更多、跨页全选、过期计数、完整历史导出 |
| `test_settings_dialog.py` | 实时预览、颜色范围、配置结果结构、tab 布局、SwitchButton、远程四字段、数值归一化、无边框拖动、颜色对话框 |
| `test_urgency_importance_ui.py` | 徽标文案/配色、普通/定时表单两字段同排、输入高度/阴影、目录选择布局 |
| `test_task_label_shadow.py` | 标签轻阴影、notes 换行、详情字段、重复打开详情后删除、状态切换保存 |
| `test_fluent_date_picker_migration.py` | 日期读写、日历弹层去壳和禁动画、ComboBox 弹层补丁、核心对话框统一 helper |
| `test_notifications.py` | 顶层宿主解析、活动窗口 InfoBar、无宿主 QMessageBox 回退 |
| `test_panel_form_styles.py` | 共享表单 QSS、按钮 token/角色/尺寸、作用域、设置/详情样式、无旧绿色硬编码 |
| `test_remove_drop_shadow.py` | 旧公共 `apply_drop_shadow` 已移除，UI 模块不依赖旧 API |
| `test_ui_dialog_transparency.py` | 核心弹窗不再使用 `WA_TranslucentBackground` |

### 明显测试缺口

- `TaskScheduler.calculate_next_run_time()` 和每日自动刷新没有专门行为测试。
- 坐标中心线/标签左上角偏移没有契约测试。
- `SummaryWorker` 的历史键映射、线程池和 LLM 多事件循环没有测试。
- Gantt Flask 路由、日期解析、CDN/离线行为没有测试。
- 托盘进程识别、正常关闭与强杀数据安全没有自动化测试。
- 维护脚本没有测试。
- 配置 JSON 深度合并和损坏恢复没有测试。
