@echo off
cd /d %~dp0

REM ������⻷���Ƿ����
if not exist "venv\Scripts\activate.bat" (
    echo �������⻷�������ڣ��������� setup_venv.bat �������⻷��
    echo.
    echo ���ڳ����Զ��������⻷��...
    call setup_venv.bat
    if errorlevel 1 (
        echo ���⻷������ʧ�ܣ����ֶ����� setup_venv.bat
        pause
        exit /b 1
    )
)

REM �������⻷������������
echo �����������������������...
call venv\Scripts\activate.bat && start pythonw.exe tray_launcher.py

REM �������ʧ�ܣ�����ʹ��python.exe
if errorlevel 1 (
    echo ʹ��pythonw.exe����ʧ�ܣ�����ʹ��python.exe...
    call venv\Scripts\activate.bat && start python.exe tray_launcher.py
)