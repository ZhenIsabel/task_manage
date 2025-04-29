# 四象限任务管理工具

基于PyQt6开发的桌面效率工具，帮助用户通过艾森豪威尔矩阵管理任务。支持桌面融合模式、任务拖拽管理、自定义样式配置等功能。

## 功能特性

### 用户功能
- 🖱️ 桌面融合模式（默认启用，可穿透鼠标操作）
- 📌 四象限任务管理：重要/紧急维度分类
- 🎨 深度自定义：支持配置颜色、透明度、圆角等样式
- 🔄 撤销操作
- 📅 任务到期日期管理
- 🖌️ 拖拽式任务管理
- 💾 自动保存配置和任务状态

### 开发功能
- 📦 可扩展字段系统（见`task_label.EDITABLE_FIELDS`）
- 🛠️ 配置热更新机制（修改立即生效）
- 🎭 完善的动画系统（淡入淡出、拖拽反馈）
- 📄 详尽的日志系统（操作轨迹可追溯）

## 快速开始

### 安装依赖
```bash
pip install -r requirements.txt
```

### 启动程序
```bash
python main.py
```

## 开发指南
### 目录结构
```plaintext
task_manage/
├── quadrant_widget.py    # 主界面逻辑 <mcsymbol name="QuadrantWidget" filename="quadrant_widget.py" path="d:\solutions\task_manage\quadrant_widget.py" startline="16" type="class"></mcsymbol>
├── task_label.py          # 任务标签组件 <mcsymbol name="TaskLabel" filename="task_label.py" path="d:\solutions\task_manage\task_label.py" startline="11" type="class"></mcsymbol>
├── config_manager.py      # 配置持久化管理 <mcsymbol name="load_config" filename="config_manager.py" path="d:\solutions\task_manage\config_manager.py" startline="37" type="function"></mcsymbol>
├── add_task_dialog.py     # 任务添加对话框
└── main.py                # 程序入口
```

### 配置系统
- 配置文件路径： `config.json`
- 热更新机制：通过 `save_config` 实现配置即时保存
- 扩展配置项：修改 `DEFAULT_CONFIG` 字典后自动合并到现有配置
### 任务系统
- 数据结构：通过 `get_data` 序列化任务状态
- 持久化存储：自动保存到 `tasks.json`
- 字段扩展：修改 `TaskLabel.EDITABLE_FIELDS` 添加新字段