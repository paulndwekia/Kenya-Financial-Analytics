from pathlib import Path
import shutil

dashboard = Path("dashboard.py")

if not dashboard.exists():
    print("ERROR: dashboard.py was not found.")
    raise SystemExit(1)

# ============================================================
# BACKUP
# ============================================================

backup = Path(
    "dashboard_backup_before_cbk_refresh.py"
)

shutil.copy2(
    dashboard,
    backup
)

text = dashboard.read_text(
    encoding="utf-8"
)

# ============================================================
# ADD REQUIRED IMPORTS
# ============================================================

imports = """
import subprocess
import sys
import json
from pathlib import Path
"""

if "import subprocess" not in text:

    # Insert after the first import section.
    lines = text.splitlines()

    insert_at = 0

    for i, line in enumerate(lines):

        if line.startswith("import ") or line.startswith("from "):

            insert_at = i + 1

    lines.insert(
        insert_at,
        imports
    )

    text = "\n".join(lines) + "\n"


# ============================================================
# CBK REFRESH UI
# ============================================================

marker = "# ===== CBK REFRESH CONTROL ====="

if marker not in text:

    refresh_block = r'''

# ===== CBK REFRESH CONTROL =====

with st.sidebar:

    st.divider()

    st.subheader(
        "🔄 CBK Data"
    )

    status_file = Path(
        "cbk_refresh_status.json"
    )

    if status_file.exists():

        try:

            status_data = json.loads(
                status_file.read_text(
                    encoding="utf-8"
                )
            )

            status = status_data.get(
                "status",
                "UNKNOWN"
            )

            last_attempt = status_data.get(
                "last_attempt",
                "Unknown"
            )

            if status == "SUCCESS":

                st.success(
                    "CBK data is up to date"
                )

            elif status in [
                "FAILED",
                "ERROR"
            ]:

                st.error(
                    "Last CBK refresh failed"
                )

            else:

                st.info(
                    f"CBK status: {status}"
                )

            st.caption(
                f"Last attempt: {last_attempt}"
            )

        except Exception:

            st.warning(
                "CBK status file could not be read."
            )

    else:

        st.info(
            "CBK refresh has not been run yet."
        )

    if st.button(
        "🔄 Refresh CBK Data",
        use_container_width=True
    ):

        refresh_script = Path(
            "cbk_refresh.py"
        )

        if not refresh_script.exists():

            st.error(
                "cbk_refresh.py was not found."
            )

        else:

            with st.spinner(
                "Connecting to CBK and importing new data..."
            ):

                try:

                    result = subprocess.run(
                        [
                            sys.executable,
                            str(refresh_script)
                        ],
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=180
                    )

                    output = (
                        result.stdout
                        + "\n"
                        + result.stderr
                    )

                    if result.returncode == 0:

                        st.success(
                            "CBK data refresh completed."
                        )

                        with st.expander(
                            "Refresh details"
                        ):

                            st.code(
                                output[-5000:]
                            )

                        st.rerun()

                    else:

                        st.error(
                            "CBK refresh failed."
                        )

                        with st.expander(
                            "CBK error details"
                        ):

                            st.code(
                                output[-5000:]
                            )

                except subprocess.TimeoutExpired:

                    st.error(
                        "CBK refresh timed out after "
                        "180 seconds."
                    )

                except Exception as error:

                    st.error(
                        f"CBK refresh error: {error}"
                    )

'''

    # ========================================================
    # FIND FIRST PAGE LOGIC
    # ========================================================

    positions = []

    for marker_text in [
        'if page == "',
        "if selected_module",
        "if module ==",
        'if page_name == "'
    ]:

        position = text.find(
            marker_text
        )

        if position != -1:

            positions.append(
                position
            )

    if positions:

        insert_position = min(
            positions
        )

        text = (
            text[:insert_position]
            + refresh_block
            + "\n"
            + text[insert_position:]
        )

    else:

        # Fallback: add before the final
        # application footer.
        text += "\n" + refresh_block


# ============================================================
# SAVE
# ============================================================

dashboard.write_text(
    text,
    encoding="utf-8"
)

print()
print("=" * 70)
print("CBK REFRESH BUTTON INSTALLED")
print("=" * 70)
print()
print(
    "Backup:",
    backup.resolve()
)
print()
print(
    "Dashboard:",
    dashboard.resolve()
)
print()
print("Start dashboard with:")
print(
    "python -m streamlit run dashboard.py"
)
print("=" * 70)
