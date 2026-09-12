@echo off
setlocal

cd /d "%~dp0"

set "PYTHON=%~dp0.venv\Scripts\python.exe"
set "PORT=8510"

if not exist "%PYTHON%" (
    msg * "Kenya Financial Analytics: .venv Python was not found."
    exit /b 1
)

REM Stop only Streamlit processes belonging to this project
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"Get-CimInstance Win32_Process -Filter 'Name = ''python.exe''' | Where-Object { $_.CommandLine -like '*streamlit*' -and $_.CommandLine -like '*Kenya_Financial_Analytics*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"

REM Start the RESTORED dashboard, NOT app.py
start "" /min "%PYTHON%" -m streamlit run "%~dp0dashboard.py" --server.port %PORT% --server.headless true --browser.gatherUsageStats false

REM Give Streamlit time to start
timeout /t 5 /nobreak >nul

REM Open the new dashboard
start "" "http://localhost:%PORT%"

exit