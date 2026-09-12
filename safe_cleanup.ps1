# ============================================================
# KENYA FINANCIAL ANALYTICS
# SAFE PROJECT CLEANUP
#
# IMPORTANT:
# - Does NOT modify app.py
# - Does NOT modify databases
# - Does NOT modify pricing engines
# - Does NOT modify CBK data
# - Does NOT permanently delete project files
# - Old/unwanted files are MOVED to an archive
# ============================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "   KENYA FINANCIAL ANALYTICS - SAFE CLEANUP" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host ""

# ------------------------------------------------------------
# 1. FIND PROJECT ROOT
# ------------------------------------------------------------

$ProjectRoot = Get-Location

Write-Host "Project folder:" -ForegroundColor Yellow
Write-Host $ProjectRoot
Write-Host ""

# ------------------------------------------------------------
# 2. VERIFY THIS REALLY LOOKS LIKE OUR PROJECT
# ------------------------------------------------------------

$AppFile = Join-Path $ProjectRoot "app.py"

if (-not (Test-Path $AppFile)) {
    Write-Host "ERROR: app.py was not found." -ForegroundColor Red
    Write-Host ""
    Write-Host "Run this script from your Kenya_Financial_Analytics folder."
    Write-Host ""
    pause
    exit
}

Write-Host "Working app.py FOUND." -ForegroundColor Green

# ------------------------------------------------------------
# 3. CREATE SAFE ARCHIVE
# ------------------------------------------------------------

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"

$ArchiveRoot = Join-Path $ProjectRoot "_CLEANUP_ARCHIVE_$Timestamp"

New-Item -ItemType Directory -Path $ArchiveRoot -Force | Out-Null

Write-Host ""
Write-Host "Safety archive created:" -ForegroundColor Green
Write-Host $ArchiveRoot

# ------------------------------------------------------------
# 4. FILES THAT ARE SAFE TO ARCHIVE
#
# We MOVE them, not delete them.
# If something turns out to be needed, it can be restored.
# ------------------------------------------------------------

$FilesToArchive = @(
    "desktop_app.py",
    "desktop_app_packaging_safe.py",
    "desktop_launcher.py",
    "desktop_launcher_backup.py",

    "build_desktop_app.bat",
    "install_desktop_mode.bat",
    "Run_Kenya_Financial_Analytics_Desktop.bat",
    "Launch_Kenya_Financial_Analytics.bat",
    "Launch_Kenya_Financial_Analytics.vbs",

    "Kenya Financial Analytics.spec",

    "UPGRADE_FINANCIAL_APP.py",
    "upgrade_financial_reports.py",
    "upgrade_intelligence.py",
    "upgrade_portfolio_intelligence.py",
    "upgrade_research_intelligence.py",
    "upgrade_risk_intelligence.py",

    "install_cbk_refresh.py",
    "install_market_explorer.py",
    "integrate_command_center.py",
    "connect_risk_intelligence.py",
    "add_history_navigation.py",
    "repair_market_database.py",

    "system_check.py",
    "startup_screen.py",
    "command_center.py",

    "dashboard_backup_before_cbk_refresh.py",
    "dashboard_backup_before_financial_reports_20260827_141248.py",
    "dashboard_backup_before_history_nav.py",
    "dashboard_backup_before_intelligence_20260827_121329.py",
    "dashboard_backup_before_market_explorer.py",
    "dashboard_backup_before_portfolio_intelligence_20260827_140243.py",
    "dashboard_backup_before_research_intelligence_20260827_140711.py",
    "dashboard_backup_before_risk_connection.py",
    "dashboard_backup_before_risk_intelligence_20260827_125933.py",

    "jarvis_v11_FINAL_SPEAKING.py",
    "JARVIS_V11_FINAL_CLEAN.py",
    "CREATE_JARVIS_DESKTOP_SHORTCUT.ps1",
    "Create_Kenya_Financial_Analytics_Shortcut.bat"
)

# ------------------------------------------------------------
# 5. MOVE FILES SAFELY
# ------------------------------------------------------------

$MovedCount = 0

foreach ($FileName in $FilesToArchive) {

    $Source = Join-Path $ProjectRoot $FileName

    if (Test-Path $Source) {

        try {

            Move-Item `
                -Path $Source `
                -Destination $ArchiveRoot `
                -Force

            Write-Host "Archived: $FileName" -ForegroundColor DarkYellow

            $MovedCount++

        }
        catch {

            Write-Host "Could not move: $FileName" -ForegroundColor Red
        }
    }
}

# ------------------------------------------------------------
# 6. ARCHIVE DESKTOP/JARVIS FOLDERS
# ------------------------------------------------------------

$FoldersToArchive = @(
    "Kenya_Financial_Analytics_Desktop_Icon_Final",
    "Kenya_Financial_Analytics_Desktop_Icon_Final.zip"
)

foreach ($FolderName in $FoldersToArchive) {

    $Source = Join-Path $ProjectRoot $FolderName

    if (Test-Path $Source) {

        try {

            Move-Item `
                -Path $Source `
                -Destination $ArchiveRoot `
                -Force

            Write-Host "Archived folder: $FolderName" -ForegroundColor DarkYellow

        }
        catch {

            Write-Host "Could not move: $FolderName" -ForegroundColor Red
        }
    }
}

# ------------------------------------------------------------
# 7. REMOVE PYTHON CACHE ONLY
#
# __pycache__ contains generated Python cache files.
# It is safe to recreate.
# ------------------------------------------------------------

Write-Host ""
Write-Host "Cleaning Python cache..." -ForegroundColor Cyan

$CacheFolders = Get-ChildItem `
    -Path $ProjectRoot `
    -Directory `
    -Recurse `
    -Force `
    -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -eq "__pycache__" }

foreach ($Cache in $CacheFolders) {

    try {

        Remove-Item `
            -Path $Cache.FullName `
            -Recurse `
            -Force

        Write-Host "Removed cache: $($Cache.FullName)" -ForegroundColor Gray

    }
    catch {

        Write-Host "Could not remove cache: $($Cache.FullName)" -ForegroundColor DarkYellow
    }
}

# ------------------------------------------------------------
# 8. DO NOT TOUCH THESE IMPORTANT FILES
# ------------------------------------------------------------

Write-Host ""
Write-Host "IMPORTANT PROJECT FILES PRESERVED:" -ForegroundColor Green

$ProtectedFiles = @(
    "app.py",
    "requirements.txt",
    "kenya_market.db",
    "kenya_financial_analytics.db",
    "cbk_data.py",
    "cbk_fetcher.py",
    "cbk_auto_importer.py",
    "cbk_historical_importer.py",
    "cbk_pricing.py",
    "cbk_refresh.py",
    "historical_data.py",
    "treasury_bills.py",
    "yield_curve.py",
    "yield_curve_engine.py",
    "bond_pricing.py",
    "fixed_income.py",
    "pricing_engine.py",
    "risk_engine.py",
    "portfolio_engine.py",
    "stress_engine.py",
    "backtest_engine.py",
    "backtesting_engine.py",
    "kenya_market_intelligence.py",
    "kenya_portfolio_intelligence.py",
    "kenya_research_intelligence.py",
    "kenya_risk_intelligence.py",
    "kenya_financial_reports.py"
)

foreach ($FileName in $ProtectedFiles) {

    $Path = Join-Path $ProjectRoot $FileName

    if (Test-Path $Path) {
        Write-Host "  PRESERVED: $FileName" -ForegroundColor Green
    }
}

# ------------------------------------------------------------
# 9. CHECK app.py SYNTAX
# ------------------------------------------------------------

Write-Host ""
Write-Host "Checking app.py syntax..." -ForegroundColor Cyan

$PythonCommand = Get-Command python -ErrorAction SilentlyContinue

if ($null -ne $PythonCommand) {

    python -m py_compile $AppFile

    if ($LASTEXITCODE -eq 0) {

        Write-Host ""
        Write-Host "SUCCESS: app.py syntax is OK." -ForegroundColor Green

    }
    else {

        Write-Host ""
        Write-Host "WARNING: app.py has a Python syntax error." -ForegroundColor Red
        Write-Host "NO changes were made to app.py." -ForegroundColor Yellow
    }

}
else {

    Write-Host ""
    Write-Host "Python command was not found." -ForegroundColor DarkYellow
    Write-Host "The cleanup itself is still complete." -ForegroundColor Yellow
}

# ------------------------------------------------------------
# 10. FINAL REPORT
# ------------------------------------------------------------

Write-Host ""
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "                 CLEANUP COMPLETE" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Files archived: $MovedCount" -ForegroundColor Green

Write-Host ""
Write-Host "Your working app.py was NOT modified." -ForegroundColor Green
Write-Host "Your databases were NOT modified." -ForegroundColor Green
Write-Host "Your CBK modules were NOT modified." -ForegroundColor Green
Write-Host "Your pricing/risk engines were NOT modified." -ForegroundColor Green

Write-Host ""
Write-Host "Old files are here:" -ForegroundColor Yellow
Write-Host $ArchiveRoot

Write-Host ""
Write-Host "DO NOT delete the archive yet." -ForegroundColor Yellow
Write-Host "First confirm that the application still runs."
Write-Host ""

pause