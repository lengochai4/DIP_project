@echo off
cd /d "%~dp0"
set "DIP_UI_PYTHON=%~dp0.venv-research\Scripts\python.exe"
if not exist "%DIP_UI_PYTHON%" set "DIP_UI_PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%DIP_UI_PYTHON%" (
    echo Python environment missing. See submission\stem_ui\README.md.
    pause
    exit /b 1
)
"%DIP_UI_PYTHON%" -X utf8 -m submission.stem_ui.app
if errorlevel 1 pause
