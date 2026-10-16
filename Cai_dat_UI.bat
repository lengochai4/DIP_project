@echo off
setlocal
cd /d "%~dp0"
python -c "import sys,struct; sys.exit(0 if sys.version_info[:2] >= (3,11) and struct.calcsize('P') == 8 else 1)" >nul 2>&1
if not errorlevel 1 (
    python -X utf8 -m submission.setup_ui
) else (
    py -3 -X utf8 -m submission.setup_ui
)
if errorlevel 1 (
    echo Setup failed. See HUONG_DAN_CHAY.md. Requires Python 3.11+ x64 and compatible dependency wheels.
    pause
    exit /b 1
)
pause
