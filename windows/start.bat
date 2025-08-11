@echo off
cd /d %~dp0

REM ������⻷���Ƿ����
if not exist "..\venv\Scripts\activate.bat" (
    echo �������⻷�������ڣ��������� setup_first.bat �������⻷��
    echo.
    echo ���ڳ����Զ��������⻷��...
    call setup_first.bat
    if errorlevel 1 (
        echo ���⻷������ʧ�ܣ����ֶ����� setup_first.bat
        pause
        exit /b 1
    )
)

REM �������⻷������������
echo �������������������������...
call ..\venv\Scripts\activate.bat && start pythonw.exe tray_launcher.py

REM �������ʧ�ܣ�����ʹ��python.exe
if errorlevel 1 (
    echo ʹ��pythonw.exe����ʧ�ܣ�����ʹ��python.exe...
    call ..\venv\Scripts\activate.bat && start python.exe tray_launcher.py
)