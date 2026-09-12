@echo off
setlocal EnableExtensions EnableDelayedExpansion

title KENYA FINANCIAL ANALYTICS - RESTORE

cd /d "%~dp0"

echo.
echo ============================================================
echo       KENYA FINANCIAL ANALYTICS
echo       CLEAN JARVIS + RESTORE FINANCIAL APPLICATION
echo ============================================================
echo.
echo Project:
echo %CD%
echo.

REM ============================================================
REM 1. VERIFY PROJECT
REM ============================================================

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] .venv Python was not found.
    echo.
    echo Expected:
    echo %CD%\.venv\Scripts\python.exe
    echo.
    pause
    exit /b 1
)

set "PYTHON=%CD%\.venv\Scripts\python.exe"

echo [OK] Python environment found.
echo.

REM ============================================================
REM 2. CREATE BACKUP
REM ============================================================

set "BACKUP=%CD%\JARVIS_REMOVED_BACKUP"

if not exist "%BACKUP%" (
    mkdir "%BACKUP%"
)

echo ============================================================
echo [1/6] BACKUP FOLDER READY
echo ============================================================
echo.
echo %BACKUP%
echo.

REM ============================================================
REM 3. STOP OLD STREAMLIT / JARVIS PROCESSES
REM ============================================================

echo ============================================================
echo [2/6] STOPPING OLD APPLICATION PROCESSES
echo ============================================================
echo.

taskkill /F /IM streamlit.exe >nul 2>&1

REM Do NOT kill every Python process.
REM We only attempt to close processes that have these titles.

taskkill /F /FI "WINDOWTITLE eq JARVIS*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq JARVIS SPEECH*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq JARVIS COMMAND CENTER*" >nul 2>&1

echo [OK] Old application processes checked.
echo.

REM ============================================================
REM 4. MOVE JARVIS FILES TO BACKUP
REM ============================================================

echo ============================================================
echo [3/6] REMOVING JARVIS FROM ACTIVE PROJECT
echo ============================================================
echo.

call :MOVE_IF_EXISTS "jarvis_speech.py"
call :MOVE_IF_EXISTS "jarvis_tts.py"
call :MOVE_IF_EXISTS "jarvis_voice.py"
call :MOVE_IF_EXISTS "jarvis_speech_bridge.py"
call :MOVE_IF_EXISTS "jarvis_command_center.py"
call :MOVE_IF_EXISTS "jarvis_finance_bridge.py"
call :MOVE_IF_EXISTS "jarvis_financial_integration.py"
call :MOVE_IF_EXISTS "jarvis_financial_voice.py"
call :MOVE_IF_EXISTS "jarvis_interface.py"
call :MOVE_IF_EXISTS "jarvis_state.json"

call :MOVE_IF_EXISTS "integrate_jarvis_dashboard.py"

call :MOVE_IF_EXISTS "create_jarvis_financial_integration.py"
call :MOVE_IF_EXISTS "create_jarvis_financial_voice.py"
call :MOVE_IF_EXISTS "create_jarvis_interface.py"
call :MOVE_IF_EXISTS "create_jarvis_voice.py"
call :MOVE_IF_EXISTS "create_risk_engine.py"
call :MOVE_IF_EXISTS "create_voice_install.py"

call :MOVE_IF_EXISTS "install_jarvis_voice.py"
call :MOVE_IF_EXISTS "install_jarvis_financial_integration.py"

call :MOVE_IF_EXISTS "JARVIS_ONE_CLICK.bat"

call :MOVE_IF_EXISTS "Kenya_Financial_Analytics_JARVIS_dashboard.py"

echo.
echo [OK] JARVIS files removed from active project.
echo.

REM ============================================================
REM 5. PROTECT FINANCIAL FILES
REM ============================================================

echo ============================================================
echo [4/6] VERIFYING FINANCIAL SYSTEM
echo ============================================================
echo.

call :CHECK_FILE "app.py"
call :CHECK_FILE "dashboard.py"
call :CHECK_FILE "portfolio_engine.py"
call :CHECK_FILE "cbk_fetcher.py"
call :CHECK_FILE "cbk_data.py"
call :CHECK_FILE "treasury_bills.py"
call :CHECK_FILE "fixed_income.py"
call :CHECK_FILE "requirements.txt"
call :CHECK_FILE "kenya_market.db"

echo.
echo ============================================================
echo FINANCIAL FILES HAVE NOT BEEN DELETED
echo ============================================================
echo.

REM ============================================================
REM 6. START ORIGINAL FINANCIAL APPLICATION
REM ============================================================

echo ============================================================
echo [5/6] STARTING KENYA FINANCIAL ANALYTICS
echo ============================================================
echo.

if exist "app.py" (

    echo Starting app.py...
    echo.

    start "KENYA FINANCIAL ANALYTICS" cmd /k ^
    ""%PYTHON%" -m streamlit run app.py --server.port 8501 --server.headless true"

) else (

    echo [ERROR] app.py was not found.
    echo.
    echo Your financial files were NOT deleted.
    echo.
    pause
    exit /b 1
)

echo [OK] Financial Analytics is starting.
echo.

REM ============================================================
REM WAIT FOR SERVER
REM ============================================================

echo ============================================================
echo [6/6] WAITING FOR DASHBOARD
echo ============================================================
echo.

timeout /t 7 /nobreak >nul

start "" "http://localhost:8501"

echo.
echo ============================================================
echo          RESTORATION COMPLETE
echo ============================================================
echo.
echo Kenya Financial Analytics:
echo http://localhost:8501
echo.
echo JARVIS has been removed from the active project.
echo.
echo Your financial application remains intact.
echo.
echo Backup location:
echo %BACKUP%
echo.
echo ============================================================
echo.
echo You can close this window.
echo.

timeout /t 8 /nobreak >nul

exit /b 0


REM ============================================================
REM FUNCTION: MOVE FILE TO BACKUP
REM ============================================================

:MOVE_IF_EXISTS

if exist "%~1" (

    echo Moving:
    echo    %~1

    move /Y "%~1" "%BACKUP%\" >nul 2>&1

    if exist "%BACKUP%\%~1" (
        echo    [BACKED UP]
    ) else (
        echo    [WARNING - COULD NOT MOVE]
    )

) else (

    echo %~1
    echo    [NOT FOUND - SKIPPED]

)

exit /b 0


REM ============================================================
REM FUNCTION: CHECK FINANCIAL FILE
REM ============================================================

:CHECK_FILE

if exist "%~1" (
    echo [KEEP] %~1
) else (
    echo [MISSING] %~1
)

exit /b 0