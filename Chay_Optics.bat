@echo off
cd /d "%~dp0"
set "DIP_UI_PYTHON=%~dp0.venv-ui\Scripts\python.exe"
if not exist "%DIP_UI_PYTHON%" set "DIP_UI_PYTHON=%~dp0.venv-research\Scripts\python.exe"
if not exist "%DIP_UI_PYTHON%" set "DIP_UI_PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%DIP_UI_PYTHON%" (
    echo Moi truong Python chua san sang. Vui long kiem tra .venv.
    pause
    exit /b 1
)
"%DIP_UI_PYTHON%" run_optics.py
if errorlevel 1 pause

