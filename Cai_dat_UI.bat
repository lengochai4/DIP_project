@echo off
setlocal
cd /d "%~dp0"
py -3.12 -X utf8 -m submission.setup_ui
if errorlevel 1 (
    echo Setup failed. See HUONG_DAN_CHAY.md. Requires Python 3.12 x64.
    pause
    exit /b 1
)
pause
