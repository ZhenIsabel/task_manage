@echo off
echo ����Ϊ��������������ߴ������⻷��...

REM ���Python�Ƿ�װ
python --version >nul 2>&1
if errorlevel 1 (
    echo ����δ�ҵ�Python�����Ȱ�װPython 3.8����߰汾
    pause
    exit /b 1
)

REM �������⻷��
echo �������⻷��...
python -m venv venv
if errorlevel 1 (
    echo ���󣺴������⻷��ʧ��
    pause
    exit /b 1
)

REM �������⻷��
echo �������⻷��...
call venv\Scripts\activate.bat

REM ����pip
echo ����pip...
python -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple/

REM ��װ����
echo ��װ��Ŀ����...
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/

if errorlevel 1 (
    echo ���󣺰�װ����ʧ��
    pause
    exit /b 1
)

echo.
echo ���⻷��������ɣ�
echo.
echo ʹ�÷�����
echo 1. �������⻷����venv\Scripts\activate.bat
echo 2. ���г���python main.py
echo 3. �˳����⻷����deactivate
echo.
pause 