# Kenya Financial Analytics — New Desktop Edition

This edition leaves the old desktop launcher untouched and uses:
- `dashboard_desktop.py` — unified dashboard with the project modules
- `desktop_app_new.py` — new desktop window launcher
- `BUILD_NEW_DESKTOP_APP.bat` — builds a Windows EXE
- `RUN_NEW_DESKTOP_APP.bat` — runs desktop mode directly from the project
- `icons/kenya_financial_analytics.ico` — existing project icon

The dashboard uses `kenya_market.db` and detects both old/new market-data column names, including `date` vs `trade_date` and `yield_rate` vs `yield`.
