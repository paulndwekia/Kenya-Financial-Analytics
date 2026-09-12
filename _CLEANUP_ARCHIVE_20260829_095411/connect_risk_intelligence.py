from pathlib import Path
import shutil
import py_compile
from datetime import datetime

BASE = Path(__file__).resolve().parent
DASHBOARD = BASE / "dashboard.py"

# ============================================================
# BACKUP
# ============================================================

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

backup = BASE / (
    f"dashboard_backup_before_risk_connection_{timestamp}.py"
)

shutil.copy2(
    DASHBOARD,
    backup
)

# ============================================================
# READ DASHBOARD
# ============================================================

dashboard = DASHBOARD.read_text(
    encoding="utf-8"
)

# ============================================================
# ADD IMPORT
# ============================================================

if "import kenya_risk_intelligence" not in dashboard:

    import_marker = "import cbk_pricing"

    if import_marker in dashboard:

        dashboard = dashboard.replace(
            import_marker,
            import_marker
            + "\nimport kenya_risk_intelligence",
            1
        )

    else:

        dashboard = (
            "import kenya_risk_intelligence\n"
            + dashboard
        )

# ============================================================
# ADD NAVIGATION
# ============================================================

if '"Risk Intelligence"' not in dashboard:

    navigation_marker = (
        '        "Risk Analysis",\n'
    )

    if navigation_marker not in dashboard:

        raise RuntimeError(
            "Risk Analysis navigation entry was not found."
        )

    dashboard = dashboard.replace(
        navigation_marker,
        navigation_marker
        + '        "Risk Intelligence",\n',
        1
    )

# ============================================================
# ADD PAGE
# ============================================================

if 'elif page == "Risk Intelligence":' not in dashboard:

    page_marker = (
        'elif page == "Historical Market Explorer":'
    )

    if page_marker not in dashboard:

        raise RuntimeError(
            "Historical Market Explorer page was not found."
        )

    new_page = '''elif page == "Risk Intelligence":

    kenya_risk_intelligence.render_risk_intelligence()


'''

    dashboard = dashboard.replace(
        page_marker,
        new_page + page_marker,
        1
    )

# ============================================================
# WRITE
# ============================================================

DASHBOARD.write_text(
    dashboard,
    encoding="utf-8"
)

# ============================================================
# VERIFY
# ============================================================

py_compile.compile(
    str(DASHBOARD),
    doraise=True
)

print()
print("=" * 70)
print("RISK INTELLIGENCE CONNECTION")
print("=" * 70)
print()
print("[SUCCESS] Risk Intelligence import connected.")
print("[SUCCESS] Navigation updated.")
print("[SUCCESS] Risk Intelligence page connected.")
print("[SUCCESS] Dashboard syntax verified.")
print()
print("Backup created:")
print(backup)
print()
print("NEW SIDEBAR MODULE:")
print("    Risk Intelligence")
print()
print("Run:")
print("    streamlit run dashboard.py")
print()
print("=" * 70)
