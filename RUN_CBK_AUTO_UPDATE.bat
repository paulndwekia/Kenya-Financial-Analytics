@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" exit /b 1

".venv\Scripts\python.exe" "cbk_auto_update.py"
