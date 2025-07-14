@echo off
cd /d %~dp0

REM 检查虚拟环境是否存在
if not exist "venv\Scripts\activate.bat" (
    echo 错误：虚拟环境不存在，请先运行 setup_venv.bat 创建虚拟环境
    echo.
    echo 正在尝试自动创建虚拟环境...
    call setup_venv.bat
    if errorlevel 1 (
        echo 虚拟环境创建失败，请手动运行 setup_venv.bat
        pause
        exit /b 1
    )
)

REM 激活虚拟环境并启动程序
echo 正在启动四象限任务管理工具...
call venv\Scripts\activate.bat && start pythonw.exe tray_launcher.py

REM 如果启动失败，尝试使用python.exe
if errorlevel 1 (
    echo 使用pythonw.exe启动失败，尝试使用python.exe...
    call venv\Scripts\activate.bat && start python.exe tray_launcher.py
)