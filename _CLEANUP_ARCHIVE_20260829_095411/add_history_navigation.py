from pathlib import Path
import shutil

dashboard = Path("dashboard.py")

if not dashboard.exists():
    print("ERROR: dashboard.py not found.")
    raise SystemExit(1)

backup = Path("dashboard_backup_before_history_nav.py")
shutil.copy2(dashboard, backup)

text = dashboard.read_text(encoding="utf-8")

# Add Historical Market Explorer to common navigation lists.
patterns = [
    (
        '"Kenyan Market", "Yield Curve"',
        '"Kenyan Market", "Historical Market Explorer", "Yield Curve"'
    ),
    (
        '"Kenyan Market",\n',
        '"Kenyan Market", "Historical Market Explorer",\n'
    ),
    (
        "'Kenyan Market', 'Yield Curve'",
        "'Kenyan Market', 'Historical Market Explorer', 'Yield Curve'"
    ),
    (
        "'Kenyan Market',\n",
        "'Kenyan Market', 'Historical Market Explorer',\n"
    ),
]

added = False

for old, new in patterns:

    if "Historical Market Explorer" in text:
        added = True
        break

    if old in text:

        text = text.replace(
            old,
            new,
            1
        )

        added = True
        break

if not added:

    print(
        "Could not automatically locate the navigation list."
    )

    print(
        "No changes were made to dashboard.py."
    )

    raise SystemExit(1)

dashboard.write_text(
    text,
    encoding="utf-8"
)

print()
print("=" * 70)
print("HISTORICAL MARKET EXPLORER NAVIGATION ADDED")
print("=" * 70)
print()
print("Backup created:")
print(backup.resolve())
print()
print("Restart dashboard:")
print("python -m streamlit run dashboard.py")
print("=" * 70)
