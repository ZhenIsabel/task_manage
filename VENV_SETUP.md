# 四象限任务管理工具 - 虚拟环境设置指南

## 项目依赖说明

本项目使用了以下主要依赖：

### 核心依赖
- **PyQt6** (>=6.4.0) - GUI框架，用于创建桌面应用程序界面
- **pywin32** (>=306) - Windows API支持，用于系统托盘和窗口管理功能
- **pandas** (>=1.5.0) - 数据处理库，用于Excel导出功能
- **openpyxl** (>=3.0.0) - Excel文件处理库，用于读写Excel文件

### 标准库依赖（无需额外安装）
- json, os, datetime, logging, statistics, subprocess等

## 启动脚本说明

项目提供了多个启动脚本，方便不同场景使用：

- **start.bat** - 智能启动脚本，自动检查虚拟环境并启动托盘程序
- **start.ps1** - PowerShell版本启动脚本，功能更丰富
- **run.bat** - 简单启动脚本，直接启动主程序（有控制台窗口）

## 快速设置
1. 双击运行 `setup_venv.bat`
2. 脚本会自动创建虚拟环境并安装所有依赖
3. 按照提示完成设置


### 方法三：手动设置
1. 打开命令提示符或PowerShell
2. 进入项目目录
3. 执行以下命令：
   ```bash
   # 创建虚拟环境
   python -m venv venv
   
   # 激活虚拟环境
   venv\Scripts\activate.bat  # Windows CMD
   # 或
   venv\Scripts\Activate.ps1  # PowerShell
   
   # 升级pip
   python -m pip install --upgrade pip
   
   # 安装依赖
   pip install -r requirements.txt
   ```

## 使用虚拟环境

### 激活虚拟环境
```bash
# Windows CMD
venv\Scripts\activate.bat

# PowerShell
venv\Scripts\Activate.ps1
```

### 运行程序

#### 方法一：使用启动脚本（推荐）
```bash
# 启动托盘程序（后台运行）
start.bat

# 或使用PowerShell启动
.\start.ps1

```

#### 方法二：手动启动
```bash
# 激活虚拟环境
venv\Scripts\activate.bat

# 启动主程序
python main.py

# 或启动托盘程序
python tray_launcher.py
```

### 退出虚拟环境
```bash
deactivate
```

## 常见问题

### 1. Python版本要求
- 需要Python 3.8或更高版本
- 建议使用Python 3.9或3.10

### 2. 依赖安装失败
- 确保网络连接正常
- 尝试使用国内镜像源：
  ```bash
  pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
  ```

### 3. PyQt6安装问题
- 如果PyQt6安装失败，可以尝试：
  ```bash
  pip install PyQt6 --force-reinstall
  ```

### 4. pywin32安装问题
- 如果pywin32安装失败，可以尝试：
  ```bash
  pip install pywin32 --force-reinstall
  ```

### 5. pandas/openpyxl安装问题
- 如果pandas或openpyxl安装失败，可以尝试：
  ```bash
  pip install pandas openpyxl --force-reinstall
  ```

## 开发环境设置

如果需要开发或调试，可以安装额外的开发工具：

```bash
# 取消注释requirements.txt中的开发工具部分
pip install pytest black flake8
```

## 注意事项

1. **虚拟环境隔离**：使用虚拟环境可以避免与系统Python环境的冲突
2. **依赖管理**：所有依赖都在requirements.txt中管理，便于部署和维护
3. **平台兼容性**：pywin32仅在Windows平台需要，其他平台会自动跳过
4. **版本控制**：建议将venv目录添加到.gitignore中，不要提交到版本控制

## 更新依赖

如果需要更新依赖版本：

1. 激活虚拟环境
2. 更新requirements.txt中的版本号
3. 重新安装依赖：
   ```bash
   pip install -r requirements.txt --upgrade
   ``` 