@echo off
echo 正在为四象限任务管理工具创建虚拟环境...

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误：未找到Python，请先安装Python 3.8或更高版本
    pause
    exit /b 1
)

REM 创建虚拟环境
echo 创建虚拟环境...
python -m venv venv
if errorlevel 1 (
    echo 错误：创建虚拟环境失败
    pause
    exit /b 1
)

REM 激活虚拟环境
echo 激活虚拟环境...
call venv\Scripts\activate.bat

REM 升级pip
echo 升级pip...
python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple/

REM 安装依赖
echo 安装项目依赖...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

if errorlevel 1 (
    echo 错误：安装依赖失败
    pause
    exit /b 1
)

echo.
echo 虚拟环境设置完成！
echo.
echo 使用方法：
echo 1. 激活虚拟环境：venv\Scripts\activate.bat
echo 2. 运行程序：python main.py
echo 3. 退出虚拟环境：deactivate
echo.
pause 