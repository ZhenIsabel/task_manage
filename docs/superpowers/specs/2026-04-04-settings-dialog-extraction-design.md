# 设置对话框拆分设计

## 背景

当前 `core/quadrant_widget.py` 中的 `show_settings()` 同时承担了以下职责：

- 创建并布局整个设置对话框 UI
- 管理颜色、尺寸、UI、远程配置四个标签页
- 直接处理颜色/尺寸/圆角等界面实时变更
- 直接保存本地配置和远程配置
- 在远程配置不完整时跳转到远程设置页

这导致 `QuadrantWidget` 既是主界面窗口，又是设置页构建器和设置流程控制器。文件过大、职责混杂，也让后续新增设置项时只能继续往 `quadrant_widget.py` 塞代码。

本次改动目标是在**不改变用户现有使用体验**的前提下，把设置窗口抽离为独立文件和独立 `QDialog` 页面，并保留颜色相关与视觉相关设置的实时预览行为。

## 目标

- 将设置窗口 UI 和大部分设置流程从 `core/quadrant_widget.py` 移出
- 新增独立的 `QDialog` 类承载设置页面
- 保留以下设置项的实时预览能力：
  - 象限颜色
  - 象限透明度
  - 色相/饱和度/明度范围
  - 主窗口宽高
  - UI 圆角半径
- 保证“取消”会回滚预览中的视觉变更
- 保持远程配置仍能从设置入口访问，并支持初始打开远程页签
- 将持久化保存集中到“确定”阶段，避免拖动滑块时频繁写盘

## 非目标

- 不重做设置页视觉风格
- 不引入新的全局设置服务层或复杂 controller 分层
- 不调整远程同步启动流程的业务语义
- 不重构与设置无关的 `QuadrantWidget` 逻辑

## 设计概览

新增 `core/settings_dialog.py`，定义独立 `SettingsDialog(QDialog)`。

职责重新划分如下：

### `SettingsDialog`

- 负责设置页 UI 构建与布局
- 负责管理一份“编辑中的工作配置副本”
- 负责发出实时预览信号
- 负责收集用户最终确认的结果
- 负责读写远程配置表单值
- 负责支持初始页签切换，例如 `remote`

### `QuadrantWidget`

- 负责打开 `SettingsDialog`
- 负责向对话框传入当前配置快照和远程配置快照
- 负责接收实时预览并将结果应用到当前窗口实例
- 负责在确认时将工作配置提交到 `self.config`
- 负责在取消时恢复打开设置前的原始视觉状态
- 负责最终 `save_config()` 与 `_apply_remote_config_to_db_manager()`

这次拆分遵循“编辑设置”和“应用到运行中的主窗口”分离的原则。对话框负责采集和组织设置；主窗口负责把设置真正作用到当前界面实例。

## 文件结构

### 新增文件

- `core/settings_dialog.py`

### 修改文件

- `core/quadrant_widget.py`

### 非默认修改

- `ui/styles.py`

默认不修改 `ui/styles.py`。实现时优先复用现有 `dialog_panel_shell` 和 `settings_panel`；只有在拆分后发现样式无法被 `SettingsDialog` 直接复用时，才允许补一个最小的新样式键，且不得顺带重整样式体系。

## `SettingsDialog` 设计

### 初始化参数

`SettingsDialog` 初始化时接收：

- `config_snapshot`
- `remote_config_snapshot`
- `initial_tab`
- `parent`

其中：

- `config_snapshot` 是 `QuadrantWidget` 当前配置的深拷贝
- `remote_config_snapshot` 是 `RemoteConfigManager().get_server_config()` 的结果拷贝
- `initial_tab` 用于在远程配置不完整时直接打开远程设置页

### 内部状态

对话框内部维护两份核心状态：

- `working_config`
- `working_remote_config`

它们都只代表用户当前编辑中的值，不应直接写回主窗口，也不应在拖动滑块时立即持久化到磁盘。

### 信号与结果

建议在 `SettingsDialog` 中定义以下信号：

- `previewChanged(dict)`：用于发送实时预览载荷

建议在 `accept()` 前通过方法返回最终结果：

- `get_result() -> dict`

结果中至少包含：

- `config`
- `remote_config`

如果实现上更顺手，也可以让 `SettingsDialog` 只暴露 `working_config` / `working_remote_config` 读取接口，但统一的 `get_result()` 更易读。

### 页面组成

设置页仍保留现有四个页签：

- 颜色设置
- 大小设置
- 界面设置
- 远程设置

其中内容迁移规则如下：

#### 颜色设置

迁移以下控件和逻辑：

- 每个象限的颜色按钮
- 透明度滑块
- 色相范围滑块
- 饱和度范围滑块
- 明度范围滑块

颜色按钮点击后仍弹出 `QColorDialog`，但行为变为：

1. 更新 `working_config`
2. 更新按钮色块显示
3. 发出 `previewChanged`

不在对话框内直接写入 `QuadrantWidget.config`，也不直接 `save_config()`。

#### 大小设置

迁移以下控件和逻辑：

- 宽度 `QSpinBox`
- 高度 `QSpinBox`

值变化时：

1. 更新 `working_config['size']`
2. 发出 `previewChanged`

#### 界面设置

迁移以下控件和逻辑：

- 圆角半径
- 自动刷新开关
- 刷新时间

其中：

- 圆角半径为实时预览项
- 自动刷新与刷新时间为确认保存项

这意味着圆角半径变化会发出 `previewChanged`，而自动刷新与刷新时间仅更新 `working_config`，不触发主界面即时副作用。

#### 远程设置

迁移以下控件和逻辑：

- 启用远程同步
- 服务器地址
- 用户名
- 访问令牌
- 说明文案

远程设置不参与实时预览，只在“确定”时保存。

## `QuadrantWidget` 改造设计

### 保留的入口

保留 `show_settings(initial_tab: str = '')` 作为外部入口，避免影响当前调用点，例如：

- 设置按钮点击
- `_bootstrap_remote_sync()` 中因配置不完整而打开远程设置页

但 `show_settings()` 的内容将缩减为设置流程编排，而不再包含设置页 UI 细节。

### 新增流程

`show_settings()` 的新流程如下：

1. 创建 `original_config_snapshot = deepcopy(self.config)`
2. 读取 `remote_config_snapshot`
3. 创建 `SettingsDialog`
4. 连接 `previewChanged` 到 `self.apply_settings_preview`
5. 执行对话框
6. 若接受：
   - 读取 dialog 最终结果
   - 调用 `apply_settings_commit(...)`
7. 若取消：
   - 调用 `restore_settings_snapshot(original_config_snapshot)`

### 新增方法

建议在 `QuadrantWidget` 中新增以下方法：

- `apply_settings_preview(payload: dict)`
- `apply_settings_commit(result: dict)`
- `restore_settings_snapshot(snapshot: dict)`
- `apply_visual_settings(config: dict)`

推荐职责如下：

#### `apply_settings_preview(payload)`

只负责把预览项作用到当前运行中的窗口实例，包括：

- 象限颜色
- 透明度
- 色域范围
- 窗口尺寸
- 圆角半径

应用后触发必要的：

- `resize(...)`
- `update()`
- `control_widget.adjustSize()`
- `center_control_panel()` 或等价的控制面板位置修正

但**不调用** `save_config()`。

#### `apply_settings_commit(result)`

负责最终提交：

- 用结果覆盖 `self.config`
- 保存本地配置
- 保存远程配置
- 调用 `_apply_remote_config_to_db_manager(...)`
- 补齐预览后仍需要的界面刷新

#### `restore_settings_snapshot(snapshot)`

负责取消时回滚：

- 恢复 `self.config`
- 把恢复后的视觉设置重新应用到当前窗口
- 不保存远程配置
- 不写盘

#### `apply_visual_settings(config)`

作为一个内部复用方法，统一处理视觉项应用，避免预览、提交、回滚重复拼装逻辑。

它至少应覆盖：

- `self.config['quadrants']`
- `self.config['color_ranges']`
- `self.config['size']`
- `self.config['ui']['border_radius']`

## 预览、提交、回滚的数据流

### 实时预览

1. 用户在 `SettingsDialog` 中拖动滑块或修改实时项
2. 对话框更新 `working_config`
3. 对话框发送 `previewChanged(payload)`
4. `QuadrantWidget.apply_settings_preview(payload)` 立即更新界面

### 确认提交

1. 用户点击“确定”
2. 对话框完成表单整理与必要校验
3. 对话框返回最终结果
4. `QuadrantWidget.apply_settings_commit(result)` 将工作配置写回正式配置
5. `QuadrantWidget.save_config()` 持久化
6. 远程配置通过 `RemoteConfigManager` 持久化，并同步到当前数据库管理器

### 取消回滚

1. 用户点击“取消”或关闭窗口
2. `QuadrantWidget.restore_settings_snapshot(original_config_snapshot)`
3. 主界面恢复到打开设置前的外观和尺寸

## 持久化策略

### 本地配置

本地配置改为：

- 预览时仅修改内存中的工作态或主窗口运行态
- 确认时统一 `save_config()`

不再保留当前“每次滑块变化都立即写盘”的行为。

### 远程配置

远程配置保持“仅在确定时保存”：

- 点击确定时调用 `RemoteConfigManager.save_config(...)`
- 若保存失败，则提示用户并阻止关闭对话框
- 保存成功后调用 `_apply_remote_config_to_db_manager(...)`

## 错误处理

### 远程配置保存失败

行为保持与现有逻辑一致：

- 弹出 `QMessageBox.warning(...)`
- 不关闭对话框
- 保留用户输入内容，允许修正后再次提交

### 无效刷新时间

保留当前兜底逻辑：

- 如果配置中的时间解析失败，回退到 `00:02:00`

### 对话框取消

无论是点击取消按钮、关闭按钮还是 Esc 触发关闭，只要未确认提交，都应走统一回滚逻辑。

## 兼容性要求

- `self.show_settings('remote')` 仍然可用
- 启动远程同步时，如果远程配置不完整，仍然能够打开远程设置页
- 原有设置按钮入口不变
- 设置页视觉风格保持与 `AddTaskDialog` 和现有样式体系一致

## 测试策略

本次改动重点验证交互行为，不追求大规模补测试，但至少应覆盖关键回归路径。

### 建议新增或补充的验证点

#### 手动验证

- 打开设置页后拖动颜色相关滑块，主界面即时响应
- 修改颜色选择按钮后的颜色，主界面即时响应
- 修改宽高后主窗口即时变更
- 修改圆角半径后界面即时更新
- 点击取消后，颜色/尺寸/圆角全部恢复
- 点击确定后，颜色/尺寸/圆角保持并写入配置
- 修改自动刷新设置后点击确定，配置成功持久化
- 修改远程配置后点击确定，配置成功保存并同步到数据库管理器
- 远程配置不完整时，启动流程仍能跳到远程设置页

#### 自动化测试候选

如果当前测试基础允许，可优先补一到两个 focused 测试：

- 打开对话框后取消，回滚逻辑会恢复原始视觉配置
- 接收 `previewChanged` 后，`QuadrantWidget` 会更新运行态但不写盘

若现有 PyQt 测试基建不足，则本次以手动验证为主，不强行引入低价值 UI 自动化测试。

## 实施顺序

1. 新建 `core/settings_dialog.py`，迁移设置页 UI 和工作态逻辑
2. 为 `SettingsDialog` 建立 `previewChanged` 和结果读取接口
3. 缩减 `QuadrantWidget.show_settings()` 为流程编排入口
4. 新增 `apply_settings_preview`、`apply_settings_commit`、`restore_settings_snapshot`
5. 将视觉类设置应用逻辑收敛为复用方法
6. 接通远程配置保存与远程页签跳转
7. 验证预览、确认、取消三条核心路径

## 验收标准

- `quadrant_widget.py` 中不再包含整段设置页 UI 构建代码
- 设置页实现位于独立文件中，且仍为独立 `QDialog`
- 颜色、尺寸、圆角设置具备实时预览能力
- 点击取消会回滚实时预览改动
- 点击确定才会持久化本地配置和远程配置
- `show_settings('remote')` 行为不变
- 主界面现有设置入口与远程同步启动提示行为不回归
