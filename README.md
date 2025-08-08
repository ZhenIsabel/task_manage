# 四象限任务管理器

一个基于PyQt6的桌面任务管理应用，支持四象限工作法，具有任务历史记录、数据同步等功能。

## 功能特性

- 🎯 **四象限工作法**：按重要性和紧急性分类任务
- 📝 **任务管理**：创建、编辑、删除、完成任务
- 📊 **历史记录**：完整记录任务字段的变更历史
- 💾 **数据持久化**：支持本地SQLite数据库存储
- 🔄 **数据同步**：支持客户端-服务器架构，多设备同步
- 🎨 **自定义界面**：支持主题切换和界面定制

## 架构设计

### 客户端-服务器架构

项目支持两种运行模式：

1. **本地模式**：数据存储在本地SQLite数据库
2. **同步模式**：数据存储在服务器，本地作为缓存

#### 客户端特性
- 本地SQLite缓存，支持离线使用
- 自动同步机制，定期与服务器同步
- 冲突检测和解决
- 数据备份和恢复

#### 服务器特性
- RESTful API接口
- 用户认证和权限管理
- 多用户数据隔离
- 数据备份和监控

## 目录结构

```
task_manage/
├── main.py                 # 主程序入口
├── ui.py                   # 主界面
├── quadrant_widget.py      # 四象限组件
├── task_label.py           # 任务标签组件
├── add_task_dialog.py      # 添加任务对话框
├── history_viewer.py       # 历史记录查看器
├── config_manager.py       # 配置管理
├── database_manager.py     # 数据库管理（支持本地和远程）
├── remote_config.py        # 远程配置管理
├── sync_manager.py         # 同步管理
├── server_example.py       # 服务器API示例
├── styles.py               # 样式定义
├── tray_launcher.py        # 系统托盘启动器
├── utils.py                # 工具函数
├── requirements.txt        # 客户端依赖
├── server_requirements.txt # 服务器依赖
├── config.json             # 配置文件
├── tasks.json              # 任务数据（已迁移到数据库）
├── tasks.db                # 本地SQLite数据库
├── remote_config.json      # 远程服务器配置
└── icons/                  # 图标资源
```

## 安装和配置

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd task_manage

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 本地模式运行

```bash
# 直接运行（首次运行会自动初始化数据库）
python tray_launcher.py
```

### 3. 同步模式配置

#### 3.1 配置服务器连接

```bash
# 运行配置工具
python remote_config.py

# 选择"设置服务器配置"
# 输入API服务器地址和访问令牌
```

#### 3.2 启动服务器（可选）

在服务器端
```bash
# 安装服务器依赖
pip install -r server_requirements.txt

# 启动示例服务器
python server_example.py
```

#### 3.3 数据同步

```bash
# 运行同步管理工具
python sync_manager.py

# 选择同步操作
```

## 数据库系统

### 本地数据库
- **类型**：SQLite
- **文件**：`tasks.db`
- **表结构**：
  - `tasks`：任务数据（包含所有字段）
  - `task_history`：任务历史记录
  - `sync_status`：同步状态记录

### 服务器数据库
- **类型**：SQLite
- **文件**：`server_tasks.db`
- **表结构**：
  - `users`：用户信息
  - `tasks`：任务数据（多用户）
  - `task_history`：任务历史记录

## API接口

### 认证
所有API请求需要在Header中包含Bearer Token：
```
Authorization: Bearer <your-api-token>
```

### 主要接口

#### 健康检查
```
GET /api/health
```

#### 获取任务列表
```
GET /api/tasks
```

#### 创建/更新任务
```
POST /api/tasks
Content-Type: application/json

{
  "id": "task_123",
  "text": "任务内容",
  "notes": "备注",
  "due_date": "2025-08-15",
  "priority": "高",
  "completed": false
}
```

#### 删除任务
```
DELETE /api/tasks/{task_id}
```

#### 获取任务历史
```
GET /api/tasks/{task_id}/history
```

## 配置系统

### 应用配置
存储在数据库中，包含：
- 任务字段定义
- 界面主题设置
- 同步配置

### 远程配置
存储在`remote_config.json`中：
```json
{
  "api_base_url": "https://api.example.com",
  "api_token": "your-api-token"
}
```

## 同步机制

### 同步策略
1. **增量同步**：只同步变更的数据
2. **冲突解决**：基于时间戳的自动冲突解决
3. **离线支持**：网络断开时使用本地缓存
4. **自动同步**：定期自动同步数据

### 同步状态
- `synced`：已同步
- `modified`：本地已修改，待同步
- `conflict`：存在冲突

## 使用指南

### 基本操作

1. **创建任务**：双击空白区域或使用快捷键
2. **编辑任务**：双击任务标签
3. **移动任务**：拖拽到不同象限
4. **完成任务**：点击任务前的复选框
5. **删除任务**：右键选择删除
6. **查看历史**：右键选择查看历史

### 四象限分类

- **第一象限**：重要且紧急
- **第二象限**：重要不紧急
- **第三象限**：紧急不重要
- **第四象限**：不重要不紧急

### 日志查看

应用程序日志保存在`logs/`目录下。

## 许可证

本项目采用MIT许可证。