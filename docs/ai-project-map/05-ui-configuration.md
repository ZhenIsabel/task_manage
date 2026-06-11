# UI 基础设施与配置

> [返回 AI 项目地图总目录](../AI_PROJECT_MAP.md)
>
> **阅读范围：** 用于修改样式、通知、Fluent 控件、滚动条、自适应表格、徽标、设置对话框和 JSON 配置契约。
>
> **相关分卷：** 主窗口交互见 [02](02-desktop-task-flow.md)；测试映射见 [07](07-dependencies-tests.md)。
## `config/` 文件职责

| 文件 | 职责 | 重要事实 |
|---|---|---|
| `config/config_manager.py` | 读写 `config/config.json`；提供默认配置；把所有可见 `TaskLabel` 转成任务数据并写入 DB；数据库失败时兼容读取旧 `database/tasks.json` | `save_tasks()` 负责按坐标重算 urgency/importance，并移除旧 `priority`；配置合并仅为顶层浅合并 |
| `config/remote_config.py` | 远程配置文件定位、读写、测试连接、清除配置和交互式 CLI | 优先根目录 `remote_config.json`，否则 `config/remote_config.json`；CLI 的“查看配置”会显示令牌前缀，不应在自动化日志中运行 |
| `config/__init__.py` | 包标识 | 无运行逻辑 |

## `ui/` 文件职责

| 文件 | 职责 | 复用原则 |
|---|---|---|
| `ui/styles.py` | 按钮主题 token、尺寸 token、角色样式、表单 QSS、任务卡/详情/菜单/控制面板/设置样式 | 新 UI 优先扩展此处，避免散落平行样式 |
| `ui/fluent.py` | 统一导出 Fluent 控件，缺包时回退原生 Qt；修补日历弹层外壳、动画和断开警告 | 依赖 qfluentwidgets 私有内部类，升级时重点回归 |
| `ui/scrollbar.py` | 全局为 Qt 滚动区安装 `SmoothScrollDelegate`；提供 `FluentScrollArea` fallback | `main.py` 启动时全局安装 |
| `ui/adaptive_table.py` | `AdaptiveTextTableWidget`；固定列、多行文本 size hint、自适应高度、原地换行 | 历史、归档、定时任务共同使用 |
| `ui/degree_badges.py` | urgency/importance 的中英文展示与冷暖配色；完成状态元数据 | “高”映射为暖色，其他值按“低”处理 |
| `ui/notifications.py` | 把 InfoBar 绑定到活动顶层窗口；无宿主时回退 QMessageBox | 所有业务提示应复用 |
| `ui/ui.py` | `UIManager` 注册/显隐/动画/批量切换/边界控制；`MyColorDialog` | 30 秒状态自动保存目前只写日志，不持久化 |
| `ui/__init__.py` | 导出表格、滚动区、UIManager、StyleManager | 公共 UI 入口 |

## 配置契约

### 应用配置主要键

| 键 | 用途 |
|---|---|
| `quadrants.q1..q4.color/opacity` | 四象限背景与新任务基础色 |
| `color_ranges.q1..q4.hue_range/saturation_range/value_range` | 新任务随机色扰动 |
| `size.width/height` | 主窗口尺寸 |
| `position.x/y` | 主窗口位置 |
| `control_panel.x/y` | 控制面板位置 |
| `edit_mode` | 编辑/查看模式 |
| `ui.border_radius` | 面板圆角 |
| `ui.shadow_effect` | 配置键存在；当前主窗口实际使用有限 |
| `ui.font_family` | 字体配置；部分样式仍使用代码常量 |
| `ui.animation_enabled` | 配置键存在；并非所有动画都读取它 |
| `ui.desktop_mode` | 桌面窗口模式 |
| `ui.control_panel_opacity` | 控制面板透明度 |
| `task_fields` | 普通任务动态表单及历史字段列表 |
| `schedule_task_fields` | 定时任务动态表单 |
| `auto_refresh.enabled/refresh_time` | 每日刷新和定时任务检查 |
| `LLM_CONFIG.api_key/model/base_url` | LLM |

`DEFAULT_CONFIG` 中的 `task_fields` 仍是旧的 text/due_date/priority/notes 集合；当前工作配置包含 urgency/importance 等更多字段。由于 `load_config()` 只做顶层浅合并，工作配置缺失嵌套键时不会深度补齐。
