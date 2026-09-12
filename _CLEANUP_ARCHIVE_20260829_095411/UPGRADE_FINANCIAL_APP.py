from pathlib import Path
from datetime import datetime
import shutil
import re

# ============================================================
# KENYA FINANCIAL ANALYTICS
# SAFE APPLICATION UPGRADER
# ============================================================

BASE = Path(__file__).resolve().parent
APP = BASE / "app.py"
FETCHER = BASE / "cbk_fetcher.py"

if not APP.exists():
    print("ERROR: app.py was not found.")
    print(f"Expected location: {APP}")
    raise SystemExit(1)

print("=" * 70)
print("KENYA FINANCIAL ANALYTICS - APPLICATION UPGRADER")
print("=" * 70)

# ------------------------------------------------------------
# 1. CREATE BACKUP
# ------------------------------------------------------------

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / f"app_backup_before_upgrade_{timestamp}.py"

shutil.copy2(APP, backup)

print()
print("[1/5] Backup created:")
print(backup)

# ------------------------------------------------------------
# 2. READ APP
# ------------------------------------------------------------

text = APP.read_text(encoding="utf-8")

original_text = text

# ------------------------------------------------------------
# 3. REMOVE/REPLACE VISIBLE JARVIS REFERENCES
# ------------------------------------------------------------

replacements = {
    "System ready. NO JARVIS dependency is required.": "System ready.",
    "NO JARVIS dependency is required": "System ready.",
    "No Jarvis dependency": "",
    "No JARVIS dependency": "",
    "JARVIS dependency": "",
    "Jarvis dependency": "",
    "JARVIS STANDBY": "SYSTEM READY",
    "JARVIS ACTIVE": "SYSTEM READY",
    "JARVIS INACTIVE": "SYSTEM READY",
    "ACTIVATE JARVIS": "",
    "DEACTIVATE JARVIS": "",
    "AUTO SPEECH": "",
    "Speech Mode: AUTO": "",
    "Online: ENABLED": "",
    "Offline: ENABLED": "",
}

for old, new in replacements.items():
    text = text.replace(old, new)

# Remove obvious Jarvis status HTML blocks if present.
text = re.sub(
    r'<div\s+class=["\']jarvis-status[^>]*>.*?</div>',
    '',
    text,
    flags=re.IGNORECASE | re.DOTALL,
)

text = re.sub(
    r'<div\s+class=["\']jarvis-info["\']>.*?</div>',
    '',
    text,
    flags=re.IGNORECASE | re.DOTALL,
)

# ------------------------------------------------------------
# 4. ADD FINANCIAL SYSTEM CONTROLS
# ------------------------------------------------------------

UPGRADE_BLOCK = r'''

# ============================================================
# KENYA FINANCIAL ANALYTICS - SYSTEM CONTROLS
# ============================================================

def _kfa_refresh_app():
    """
    Clear Streamlit caches and reload the application.
    """
    try:
        st.cache_data.clear()
    except Exception:
        pass

    try:
        st.cache_resource.clear()
    except Exception:
        pass

    st.rerun()


def _kfa_update_cbk():
    """
    Run the existing CBK fetcher and refresh the application.

    The project keeps the CBK fetching logic in cbk_fetcher.py.
    This button deliberately uses the project's existing fetcher
    instead of replacing it with a second data pipeline.
    """
    import subprocess
    import sys

    fetcher = Path(__file__).resolve().parent / "cbk_fetcher.py"

    if not fetcher.exists():
        st.error("CBK fetcher not found: cbk_fetcher.py")
        return

    with st.spinner("Updating Kenya financial data from CBK..."):
        try:
            result = subprocess.run(
                [sys.executable, str(fetcher)],
                cwd=str(fetcher.parent),
                capture_output=True,
                text=True,
                timeout=180,
            )

            if result.returncode == 0:
                st.success("CBK data update completed successfully.")

                if result.stdout.strip():
                    with st.expander("CBK update details"):
                        st.code(result.stdout[-6000:])

                # Clear cached financial data after the database update.
                try:
                    st.cache_data.clear()
                except Exception:
                    pass

                st.rerun()

            else:
                st.error("CBK data update returned an error.")

                if result.stdout.strip():
                    st.code(result.stdout[-4000:])

                if result.stderr.strip():
                    st.code(result.stderr[-4000:])

        except subprocess.TimeoutExpired:
            st.error(
                "CBK update timed out after 180 seconds. "
                "Check your internet connection and cbk_fetcher.py."
            )

        except Exception as exc:
            st.error(f"CBK update failed: {exc}")


# ------------------------------------------------------------
# SIDEBAR SYSTEM CONTROLS
# ------------------------------------------------------------

with st.sidebar:

    st.markdown("---")

    st.subheader("System Controls")

    refresh_clicked = st.button(
        "🔄 REFRESH APP",
        use_container_width=True,
        help="Clear cached application data and reload the dashboard.",
    )

    if refresh_clicked:
        _kfa_refresh_app()

    cbk_clicked = st.button(
        "🇰🇪 UPDATE CBK DATA",
        use_container_width=True,
        help="Run the project's CBK data fetcher and refresh the application.",
    )

    if cbk_clicked:
        _kfa_update_cbk()

    st.caption("Kenya Financial Analytics")
    st.caption("CBK data • Quantitative Finance • Risk Analytics")

# ============================================================
# END SYSTEM CONTROLS
# ============================================================
'''

# ------------------------------------------------------------
# IMPORTANT:
# Do not insert the block twice.
# ------------------------------------------------------------

if "KENYA FINANCIAL ANALYTICS - SYSTEM CONTROLS" not in text:

    # We need the block to execute after Streamlit is imported.
    # Find the first occurrence of "import streamlit as st".
    marker = "import streamlit as st"

    if marker in text:
        position = text.find(marker)

        # Find the end of that import line.
        line_end = text.find("\n", position)

        if line_end == -1:
            line_end = len(text)

        text = (
            text[:line_end + 1]
            + "\n"
            + UPGRADE_BLOCK
            + "\n"
            + text[line_end + 1:]
        )

        print("[2/5] System controls added.")
    else:
        print("[2/5] WARNING: Could not find 'import streamlit as st'.")
        print("        No controls were inserted.")
else:
    print("[2/5] System controls already exist. Skipping duplicate.")

# ------------------------------------------------------------
# 5. WRITE APP
# ------------------------------------------------------------

if text != original_text:
    APP.write_text(text, encoding="utf-8")
    print("[3/5] app.py updated.")
else:
    print("[3/5] No changes were necessary.")

# ------------------------------------------------------------
# VERIFY
# ------------------------------------------------------------

updated = APP.read_text(encoding="utf-8")

checks = {
    "Refresh control": "REFRESH APP" in updated,
    "CBK update control": "UPDATE CBK DATA" in updated,
    "CBK fetcher": "_kfa_update_cbk" in updated,
    "Cache refresh": "st.cache_data.clear()" in updated,
}

print()
print("[4/5] Verification:")

all_ok = True

for name, result in checks.items():
    status = "OK" if result else "MISSING"
    print(f"    [{status}] {name}")

    if not result:
        all_ok = False

# ------------------------------------------------------------
# FINAL
# ------------------------------------------------------------

print()
print("[5/5] Upgrade complete.")
print()

if all_ok:
    print("SUCCESS!")
    print()
    print("Your application now has:")
    print("  1. REFRESH APP")
    print("  2. UPDATE CBK DATA")
    print("  3. Automatic cache clearing")
    print("  4. Automatic application rerun")
    print("  5. CBK fetcher integration")
    print("  6. Jarvis wording cleanup")
else:
    print("WARNING: Some controls could not be verified.")

print()
print("Backup:")
print(backup)

print()
print("=" * 70)
print("IMPORTANT")
print("=" * 70)
print()
print("If Streamlit is currently running, stop it with:")
print("    Ctrl + C")
print()
print("Then start the application again with:")
print("    python -m streamlit run app.py --server.port 8503")
print()