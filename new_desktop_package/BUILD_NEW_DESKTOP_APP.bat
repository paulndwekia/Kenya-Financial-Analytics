@echo off
setlocal
cd /d "%~dp0"
title Building Kenya Financial Analytics Desktop
if not exist ".venv\Scripts\python.exe" (
  echo ERROR: .venv was not found in this project folder.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install --upgrade pyinstaller pywebview
if errorlevel 1 goto :fail
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onedir --windowed --name "Kenya Financial Analytics" --icon "icons\kenya_financial_analytics.ico" --add-data "dashboard_desktop.py;." --add-data "kenya_market.db;." --add-data "kenya_financial.db;." --add-data "kenya_financial_analytics.db;." --add-data "icons\kenya_financial_analytics.ico;icons" --collect-all streamlit --collect-all pywebview --hidden-import=pricing --hidden-import=pricing.black_scholes --hidden-import=pricing.greeks --hidden-import=pricing.binomial_tree --hidden-import=pricing.monte_carlo --hidden-import=pricing.convergence --hidden-import=pricing_engine --hidden-import=cbk_pricing --hidden-import=risk_engine --hidden-import=portfolio_engine --hidden-import=backtest_engine --hidden-import=stress_engine --hidden-import=fixed_income --hidden-import=yield_curve --hidden-import=historical_data --hidden-import=kenya_market_intelligence --hidden-import=kenya_risk_intelligence --hidden-import=kenya_portfolio_intelligence --hidden-import=kenya_research_intelligence --hidden-import=kenya_financial_reports --hidden-import=command_center desktop_app_new.py
if errorlevel 1 goto :fail
copy /y "icons\kenya_financial_analytics.ico" "dist\Kenya Financial Analytics\kenya_financial_analytics.ico" >nul
(
 echo @echo off
 echo cd /d "%%~dp0"
 echo start "" "Kenya Financial Analytics.exe"
) > "dist\Kenya Financial Analytics\Run Kenya Financial Analytics.bat"
echo.
echo BUILD SUCCESSFUL
 echo Desktop app: dist\Kenya Financial Analytics\Kenya Financial Analytics.exe
pause
exit /b 0
:fail
echo.
echo BUILD FAILED - read the error above.
pause
exit /b 1
