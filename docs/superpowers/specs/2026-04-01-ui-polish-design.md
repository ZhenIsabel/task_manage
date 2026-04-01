# UI 视觉统一与交互打磨设计
日期：2026-04-01

## 背景

当前项目的 UI 已经具备可用性，但视觉和交互层面仍然呈现出明显的“局部优化”痕迹，而不是一套稳定的设计系统：

- 样式虽然部分集中在 [ui/styles.py](D:/repositories/task_manage/ui/styles.py)，但多个业务文件仍存在大量内联 `setStyleSheet(...)`，导致按钮、标题、表格、弹窗、提示文本在不同页面上的表现不一致。
- 设计语言缺少统一 token，圆角、边框、阴影、字号、间距存在多套并行取值，典型值包括 `6 / 8 / 10 / 12 / 15` 等。
- 动效能力目前主要停留在基础淡入淡出，缺少 hover、press、弹层进入、拖拽反馈等更符合桌面应用体验的轻量反馈。
- 字体策略在桌面端与 gantt web 页之间并不统一，Windows 下中文、英文、数字的呈现风格会产生割裂感。
- 主界面、弹窗、设置页、甘特图页目前还没有形成一致的视觉层级和品牌感。

本次设计目标不是重做业务流程，也不是引入复杂主题系统，而是在现有 PyQt + 嵌入式 web 页面基础上，建立一套轻量但稳定的 UI 规范，并逐步应用到主要界面。

## 目标

在不改变现有主要业务流程和信息架构的前提下，完成一轮面向前端体验的 UI 收敛与打磨，使项目在以下方面达到可持续维护的状态：

- 建立一套集中式设计 token，用于统一颜色、圆角、间距、边框、阴影、字号和动画参数。
- 消除主要界面之间的视觉断层，使主界面、弹窗、设置页、表格页、甘特图页拥有一致的组件语言。
- 为常用交互补齐轻量动效和反馈，提升桌面端的精致感与可感知性。
- 明确 Windows 下的中文字体回退策略，保证 100% / 125% / 150% 缩放下的可读性和稳定性。
- 为后续主题化、深浅色扩展和组件复用打下结构基础。

## 非目标

- 不在本次设计中处理“统一状态表达”这一项，包括完成、过期、危险、选中、禁用等状态的系统化重构。
- 不重写现有业务数据结构、数据库逻辑或远程同步逻辑。
- 不将整个项目重构为完整的组件库或主题引擎。
- 不在本次范围内引入深色模式、国际化字体切换或品牌重设计。
- 不对甘特图功能本身做交互能力增强，只处理其视觉对齐与样式统一。

## 方案比较

### 方案 A：只做样式查漏补缺

做法：继续沿用当前样式结构，只在发现问题的页面补局部样式。

优点：
- 开发成本最低。
- 不会触及太多现有代码。

缺点：
- 无法解决风格分裂问题。
- 后续页面继续新增时，重复劳动会持续累积。
- 很难形成统一规范。

### 方案 B：集中 token，但只改 `ui/styles.py`

做法：把颜色、圆角、阴影、字体收敛进样式管理器，但暂时不清理业务文件中的内联样式。

优点：
- 比方案 A 更有结构。
- 可以快速建立一版设计规范草案。

缺点：
- 实际界面仍然会存在局部例外。
- 设计 token 只能部分生效，维护成本依旧偏高。

### 方案 C：建立 token + 统一组件样式入口 + 覆盖主流程界面（推荐）

做法：
- 在 [ui/styles.py](D:/repositories/task_manage/ui/styles.py) 中建立轻量设计 token 和通用样式模板。
- 清理核心业务页面中的内联样式，使按钮、标题、表格、弹窗、表单、辅助文案改为复用统一样式入口。
- 同步补齐动效参数和 Windows 字体策略。
- 将 gantt web 页 [gantt/static/index.html](D:/repositories/task_manage/gantt/static/index.html) 的视觉规则对齐到桌面端。

优点：
- 可以从结构上解决样式分裂问题。
- 设计语言真正落地，而不仅是文档层统一。
- 后续继续迭代时可复用成本最低。

缺点：
- 需要同时修改样式文件与多个核心页面。
- 需要一次性梳理主界面的视觉层级。

## 采用方案

采用方案 C：建立轻量设计 token 与统一组件样式入口，并优先覆盖主界面、主要弹窗、设置页和 gantt 页。

## 设计概览

### 1. 设计 token 层

在 [ui/styles.py](D:/repositories/task_manage/ui/styles.py) 中补一层明确的 token 定义，至少包含以下类别：

- 颜色：背景、表面、边框、主色、主色 hover、危险色、辅助文字色。
- 圆角：`sm / md / lg` 三档。
- 间距：`xs / sm / md / lg / xl` 五档。
- 阴影：浮层阴影、悬浮工具条阴影、轻悬浮阴影三档。
- 字体：Windows 中文字体栈、字号层级、字重层级。
- 动效：快反馈、常规反馈、弹层进入三档时长与 easing。

要求：
- 业务样式不得再直接散落硬编码主色和圆角值。
- token 命名应以用途为主，而不是具体颜色值为主。
- 后续业务文件中的样式必须优先通过 `StyleManager` 复用。

### 2. 组件样式收敛

将当前散落在业务文件中的重复样式收敛成一组可复用的样式模板，至少包括：

- `button_primary`
- `button_secondary`
- `button_ghost`
- `button_danger`
- `dialog_panel`
- `section_title`
- `helper_text`
- `table_base`
- `form_input`
- `tab_base`
- `floating_toolbar`

要求：
- [core/complete_table.py](D:/repositories/task_manage/core/complete_table.py)、[core/history_viewer.py](D:/repositories/task_manage/core/history_viewer.py)、[core/export_summary_dialog.py](D:/repositories/task_manage/core/export_summary_dialog.py)、[core/scheduler.py](D:/repositories/task_manage/core/scheduler.py)、[core/quadrant_widget.py](D:/repositories/task_manage/core/quadrant_widget.py) 内的重复按钮和标题样式应改为复用模板。
- 保留少量业务特例，但特例应建立在通用模板之上，而不是完全独立。
- `add_task_dialog` 等现有样式若继续使用，需内部改造为引用 token，而不是维持独立参数体系。

### 3. 视觉语言统一

#### 圆角

统一收敛为三档：

- 小控件：6px
- 常规控件/输入框/表格单元：10px
- 弹窗与大面板：14px

#### 阴影

只在真正的浮层和悬浮面板上使用阴影：

- 主弹窗与详情浮层：中等柔和阴影
- 悬浮控制条：轻阴影
- 普通任务卡片：默认不加重阴影，必要时只在 hover 或拖拽中增强

#### 边框

默认通过浅边框建立结构，不再对所有元素同时叠加强阴影和显性边框。

#### 颜色

保留当前薄荷青为主品牌色方向，但重新定义用途：

- 主色：用于主按钮、重点交互和选中态的基础高亮
- 主色 hover：用于按钮和可点击项悬停
- 危险色：仅用于删除、不可逆操作
- 中性色：负责背景、表面、边框、辅助文字

#### 背景层级

- 主窗口背景保持低饱和浅色。
- 四象限色块进一步降低饱和度，让任务卡内容而不是背景成为视觉中心。
- 浮层统一使用高亮度白色或浅表面色，与主背景形成清晰层级差。

### 4. 动效策略

本次动效不追求复杂，而是补齐必要反馈。

#### 基础交互反馈

- 按钮 hover：轻微提亮或背景色过渡。
- 按钮 press：轻微压暗。
- 可点击卡片 hover：轻微强调边框或阴影。

#### 弹层进入/退出

在现有透明度动画基础上，逐步加入以下效果：

- 弹窗进入：`opacity + 轻微位移`
- 弹窗退出：`opacity` 为主，避免拖泥带水
- 时长统一走 token，不再每个页面各自定义

#### 拖拽反馈

对于任务拖拽：

- 拖拽中的任务卡允许出现轻微抬升感。
- 目标象限在拖拽经过时允许有弱高亮反馈。

#### 动效参数

统一建议：

- 快速反馈：120ms
- 常规切换：180ms
- 浮层进入：220ms
- easing 以 ease-out 或等效曲线为主

### 5. Windows 字体适配

建立统一字体策略，桌面端和 gantt web 页使用一致的 Windows 优先字体栈：

- 中文优先：`"Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", sans-serif`
- 英文与数字优先跟随 `Segoe UI` 的系统观感

要求：
- 清理 [ui/styles.py](D:/repositories/task_manage/ui/styles.py) 中 `微软雅黑`、`Microsoft YaHei`、`PingFang SC`、`system-ui` 的混用情况。
- 配置项 [config/config_manager.py](D:/repositories/task_manage/config/config_manager.py) 中的默认字体应改为统一字体栈入口，而不是单独写死 `微软雅黑`。
- 保证桌面端正文字号不低于 13px，辅助信息不低于 12px。
- 明确校验 Windows 缩放 100% / 125% / 150% 下的控件高度、文字截断和弹窗排版。

### 6. 布局与信息密度优化

在不改变业务流程的前提下优化布局节奏：

- 统一主界面、弹窗、设置页、表格页的外边距和区块间距。
- 减少“控件直接堆叠”的观感，让标题、说明、操作区、内容区之间有清晰间隔。
- 控制面板从“抢视觉注意力”的深色悬浮块，调整为更轻量、与整体配色一致的浅色悬浮工具条方向。
- 表格页按钮区和说明文应对齐新的排版节奏。

### 7. Gantt 页样式对齐

[gantt/static/index.html](D:/repositories/task_manage/gantt/static/index.html) 需要与桌面端建立一致性：

- 字体栈与主应用统一。
- 按钮圆角、边框、背景层级与桌面端保持一致。
- 容器背景、边框和内边距与桌面端表面容器语言对齐。
- Tooltip/详情块的卡片语言与桌面端详情浮层接近。

### 8. 可维护性要求

- 新增或修改样式时，优先更新 `StyleManager`，其次才是在业务文件引用。
- 单个业务文件中允许保留少量临时样式，但不得再出现大段重复内联样式块。
- 核心视觉规则必须在 spec 对应的实现中有明确命名和复用路径。

## 涉及文件职责

### [ui/styles.py](D:/repositories/task_manage/ui/styles.py)

职责：
- 定义设计 token。
- 输出统一组件样式模板。
- 承担 PyQt 侧主要视觉规范入口。

### [ui/ui.py](D:/repositories/task_manage/ui/ui.py)

职责：
- 统一管理动效参数与阴影应用策略。
- 为弹窗进入/退出等动画提供复用能力。

### [core/quadrant_widget.py](D:/repositories/task_manage/core/quadrant_widget.py)

职责：
- 主界面、控制工具条、设置弹窗的样式消费方。
- 需要消除局部 tab、提示文字、按钮、色块等内联样式。

### [core/task_label.py](D:/repositories/task_manage/core/task_label.py)

职责：
- 任务卡片与详情浮层的视觉消费方。
- 需要收敛阴影、细节面板、按钮样式和文本层级。

### [core/add_task_dialog.py](D:/repositories/task_manage/core/add_task_dialog.py)

职责：
- 表单与弹窗规范的主要参考实现。
- 需要改造为真正基于 token 的表单样式。

### [core/complete_table.py](D:/repositories/task_manage/core/complete_table.py)

职责：
- 表格页和按钮区样式消费方。
- 需要去除重复的标题和按钮内联样式。

### [core/history_viewer.py](D:/repositories/task_manage/core/history_viewer.py)

职责：
- 表格与工具按钮样式消费方。
- 需要对齐标题层级、说明文字和按钮类型。

### [core/export_summary_dialog.py](D:/repositories/task_manage/core/export_summary_dialog.py)

职责：
- 弹窗、表单、状态提示的样式消费方。
- 需要对齐按钮、说明文字、快捷筛选区和状态文本的层级。

### [core/scheduler.py](D:/repositories/task_manage/core/scheduler.py)

职责：
- 定时任务列表和新增弹窗的样式消费方。
- 需要对齐表格、按钮、标题与输入样式。

### [config/config_manager.py](D:/repositories/task_manage/config/config_manager.py)

职责：
- 持有 UI 默认配置。
- 需要同步字体默认项和可能的圆角/动效开关默认值。

### [gantt/static/index.html](D:/repositories/task_manage/gantt/static/index.html)

职责：
- 承担嵌入式 web 页视觉对齐。
- 需要改造为共享同一套桌面端风格方向。

## 风险与缓解

### 风险 1：样式集中化过程中影响现有页面布局

缓解：
- 先改 token 和通用组件，再逐页替换，不一次性全量推翻。
- 优先覆盖主路径页面，避免边改边扩散。

### 风险 2：PyQt 样式表能力有限，过度追求复杂视觉会增加维护成本

缓解：
- 本次只做轻量设计语言，不引入复杂渐变、重装饰或过度动画。
- 以边框、表面色、轻阴影和节奏统一为主。

### 风险 3：桌面端和 web 端字体、尺寸表现不完全一致

缓解：
- 统一字体栈和字号目标，而不是要求逐像素一致。
- 手动校验关键场景，允许在 web 页做少量局部修正。

### 风险 4：业务文件残留内联样式导致规范被重新打散

缓解：
- 在实施计划中明确逐文件清理范围。
- 将新的组件样式命名清晰化，让复用路径比复制粘贴更容易。

## 验收标准

满足以下条件视为完成：

1. [ui/styles.py](D:/repositories/task_manage/ui/styles.py) 中存在清晰的设计 token 与通用组件样式入口。
2. 主界面、设置页、添加任务弹窗、历史/完成/定时任务表格页、导出概要弹窗都已改为复用统一样式模板，而不是继续使用大段重复内联样式。
3. 圆角、阴影、按钮和表单控件在主要页面中的视觉语言已明显统一。
4. [ui/ui.py](D:/repositories/task_manage/ui/ui.py) 中的动效参数具备统一入口，关键弹层与基础交互具备轻量动效反馈。
5. Windows 字体策略完成统一，桌面端和 gantt 页不再混用多套中文字体方案。
6. 在 Windows 100% / 125% / 150% 缩放下，主要界面的文字、按钮、输入框和弹窗布局无明显截断或拥挤。
7. gantt 页在按钮、容器、字体和细节块上与桌面主应用风格一致。
8. 本次改动不包含“统一状态表达”相关系统化重构，且不会误伤现有业务状态逻辑。
