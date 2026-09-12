$ErrorActionPreference = "Stop"

$project = Join-Path $env:USERPROFILE "Desktop\Quantative Finance Project\Kenya_Financial_Analytics"
$desktop = [Environment]::GetFolderPath("Desktop")
$launcher = Join-Path $project "Launch_Kenya_Financial_Analytics.vbs"
$sourceIcon = Join-Path $PSScriptRoot "kenya_financial_analytics.ico"
$iconsDir = Join-Path $project "icons"
$destIcon = Join-Path $iconsDir "kenya_financial_analytics.ico"
$shortcutPath = Join-Path $desktop "Kenya Financial Analytics.lnk"

if (-not (Test-Path $project)) { throw "Project folder not found: $project" }
if (-not (Test-Path $launcher)) { throw "Launcher not found: $launcher" }
if (-not (Test-Path $sourceIcon)) { throw "Icon file not found beside this script: $sourceIcon" }

New-Item -ItemType Directory -Force -Path $iconsDir | Out-Null
Copy-Item -Force $sourceIcon $destIcon

$ws = New-Object -ComObject WScript.Shell
$shortcut = $ws.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "wscript.exe"
$shortcut.Arguments = "`"$launcher`""
$shortcut.WorkingDirectory = $project
$shortcut.Description = "Kenya Financial Analytics"
$shortcut.IconLocation = "$destIcon,0"
$shortcut.Save()

# Ask Windows Explorer to refresh its icon cache/display.
Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
Start-Process explorer.exe

Write-Host ""
Write-Host "DONE: Kenya Financial Analytics shortcut updated." -ForegroundColor Green
Write-Host "Icon: $destIcon"
Write-Host "Shortcut: $shortcutPath"
