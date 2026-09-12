@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo ERROR: .venv not found.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" -m pip install pywebview >nul 2>&1
".venv\Scripts\python.exe" desktop_app_new.py
