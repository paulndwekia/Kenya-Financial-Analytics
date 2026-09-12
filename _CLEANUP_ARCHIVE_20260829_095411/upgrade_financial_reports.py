from pathlib import Path
import shutil
import py_compile
from datetime import datetime

BASE = Path(__file__).resolve().parent
DASHBOARD = BASE / "dashboard.py"
MODULE = BASE / "kenya_financial_reports.py"

# ============================================================
# BACKUP
# ============================================================

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

backup = BASE / (
    f"dashboard_backup_before_financial_reports_{timestamp}.py"
)

shutil.copy2(DASHBOARD, backup)

# ============================================================
# CREATE REPORT ENGINE
# ============================================================

code = r'''
import sqlite3
from pathlib import Path
from datetime import datetime
import io

import pandas as pd
import streamlit as st


DATABASE = Path(__file__).resolve().parent / "kenya_market.db"


def load_market_data():

    if not DATABASE.exists():
        return pd.DataFrame()

    connection = sqlite3.connect(DATABASE)

    try:

        data = pd.read_sql_query(
            """
            SELECT
                auction_date,
                tenor_days,
                rate
            FROM treasury_bill_rates
            ORDER BY auction_date ASC
            """,
            connection
        )

    finally:

        connection.close()

    if data.empty:
        return data

    data["auction_date"] = pd.to_datetime(
        data["auction_date"],
        errors="coerce"
    )

    data["tenor_days"] = pd.to_numeric(
        data["tenor_days"],
        errors="coerce"
    )

    data["rate"] = pd.to_numeric(
        data["rate"],
        errors="coerce"
    )

    data = data.dropna(
        subset=[
            "auction_date",
            "tenor_days",
            "rate"
        ]
    )

    data["tenor_days"] = (
        data["tenor_days"].astype(int)
    )

    return data


def build_summary(data):

    if data.empty:
        return pd.DataFrame()

    rows = []

    for tenor in sorted(
        data["tenor_days"].unique()
    ):

        subset = data[
            data["tenor_days"] == tenor
        ].sort_values(
            "auction_date"
        )

        if subset.empty:
            continue

        rates = subset["rate"]

        latest = float(
            rates.iloc[-1]
        )

        average = float(
            rates.mean()
        )

        highest = float(
            rates.max()
        )

        lowest = float(
            rates.min()
        )

        volatility = float(
            rates.std()
        ) if len(rates) > 1 else 0.0

        rows.append({
            "Tenor (Days)": tenor,
            "Observations": len(subset),
            "First Date":
                subset["auction_date"]
                .min()
                .strftime("%Y-%m-%d"),
            "Latest Date":
                subset["auction_date"]
                .max()
                .strftime("%Y-%m-%d"),
            "Latest Yield (%)":
                latest * 100,
            "Average Yield (%)":
                average * 100,
            "Highest Yield (%)":
                highest * 100,
            "Lowest Yield (%)":
                lowest * 100,
            "Yield Volatility (%)":
                volatility * 100
        })

    return pd.DataFrame(rows)


def create_html_report(
    summary,
    total_observations,
    first_date,
    latest_date
):

    generated = datetime.now().strftime(
        "%d %B %Y, %H:%M:%S"
    )

    if summary.empty:

        table_html = (
            "<p>No Treasury Bill data available.</p>"
        )

    else:

        display = summary.copy()

        for column in [
            "Latest Yield (%)",
            "Average Yield (%)",
            "Highest Yield (%)",
            "Lowest Yield (%)",
            "Yield Volatility (%)"
        ]:

            display[column] = display[column].map(
                lambda x: f"{x:.4f}%"
            )

        table_html = display.to_html(
            index=False,
            border=0,
            classes="report-table"
        )

    return f"""
<!DOCTYPE html>
<html>
<head>

<meta charset="UTF-8">

<title>
Kenya Financial Analytics Report
</title>

<style>

body {{
    font-family: Arial, sans-serif;
    margin: 40px;
    color: #222;
}}

.header {{
    border-bottom: 3px solid #222;
    padding-bottom: 15px;
    margin-bottom: 25px;
}}

h1 {{
    margin-bottom: 5px;
}}

h2 {{
    margin-top: 30px;
}}

.summary {{
    display: grid;
    grid-template-columns:
        repeat(3, 1fr);
    gap: 15px;
    margin: 25px 0;
}}

.card {{
    border: 1px solid #ccc;
    padding: 18px;
}}

.card-title {{
    font-size: 13px;
    color: #666;
}}

.card-value {{
    font-size: 22px;
    font-weight: bold;
    margin-top: 8px;
}}

.report-table {{
    border-collapse: collapse;
    width: 100%;
}}

.report-table th,
.report-table td {{
    border: 1px solid #ccc;
    padding: 9px;
    text-align: left;
}}

.report-table th {{
    font-weight: bold;
}}

.footer {{
    margin-top: 40px;
    border-top: 1px solid #ccc;
    padding-top: 15px;
    font-size: 12px;
    color: #666;
}}

@media print {{
    body {{
        margin: 20px;
    }}
}}

</style>

</head>

<body>

<div class="header">

<h1>
KENYA FINANCIAL ANALYTICS
</h1>

<p>
CBK Historical Treasury Bill Market Report
</p>

<p>
Generated: {generated}
</p>

</div>

<div class="summary">

<div class="card">

<div class="card-title">
Total Observations
</div>

<div class="card-value">
{total_observations:,}
</div>

</div>

<div class="card">

<div class="card-title">
First Observation
</div>

<div class="card-value">
{first_date}
</div>

</div>

<div class="card">

<div class="card-title">
Latest Observation
</div>

<div class="card-value">
{latest_date}
</div>

</div>

</div>

<h2>
Treasury Bill Market Summary
</h2>

{table_html}

<h2>
Interpretation
</h2>

<p>
This report summarizes historical Treasury Bill
observations stored in the Kenya Financial Analytics
local market database.
</p>

<p>
The report is intended for financial research,
portfolio analysis and historical market intelligence.
Historical observations do not guarantee future results.
</p>

<div class="footer">

Kenya Financial Analytics<br>
Historical CBK market database<br>
Generated automatically by the Financial Reports engine.

</div>

</body>
</html>
"""


def render_financial_reports():

    st.header(
        "📑 Kenya Financial Reports"
    )

    st.caption(
        "Generate and export reports from the "
        "Kenya Financial Analytics market database."
    )

    data = load_market_data()

    if data.empty:

        st.warning(
            "No Treasury Bill data is available "
            "for report generation."
        )

        return

    # ========================================================
    # REPORT OVERVIEW
    # ========================================================

    summary = build_summary(data)

    first_date = (
        data["auction_date"]
        .min()
        .strftime("%Y-%m-%d")
    )

    latest_date = (
        data["auction_date"]
        .max()
        .strftime("%Y-%m-%d")
    )

    total_observations = len(data)

    st.subheader(
        "Report Overview"
    )

    c1, c2, c3 = st.columns(3)

    with c1:

        st.metric(
            "Observations",
            f"{total_observations:,}"
        )

    with c2:

        st.metric(
            "First Date",
            first_date
        )

    with c3:

        st.metric(
            "Latest Date",
            latest_date
        )

    # ========================================================
    # MARKET SUMMARY
    # ========================================================

    st.divider()

    st.subheader(
        "Treasury Bill Summary"
    )

    st.dataframe(
        summary,
        use_container_width=True,
        hide_index=True
    )

    # ========================================================
    # CSV EXPORT
    # ========================================================

    st.divider()

    st.subheader(
        "Export Market Data"
    )

    csv_data = data.copy()

    csv_data["auction_date"] = (
        csv_data["auction_date"]
        .dt.strftime("%Y-%m-%d")
    )

    csv_bytes = csv_data.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        label="⬇ Download CBK Data CSV",
        data=csv_bytes,
        file_name=(
            "kenya_cbk_treasury_bill_history.csv"
        ),
        mime="text/csv"
    )

    # ========================================================
    # EXCEL EXPORT
    # ========================================================

    try:

        excel_buffer = io.BytesIO()

        with pd.ExcelWriter(
            excel_buffer,
            engine="openpyxl"
        ) as writer:

            data.to_excel(
                writer,
                sheet_name="CBK History",
                index=False
            )

            summary.to_excel(
                writer,
                sheet_name="Market Summary",
                index=False
            )

        excel_bytes = (
            excel_buffer.getvalue()
        )

        st.download_button(
            label="⬇ Download Excel Report",
            data=excel_bytes,
            file_name=(
                "kenya_financial_market_report.xlsx"
            ),
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )
        )

    except Exception as error:

        st.warning(
            "Excel export is unavailable: "
            + str(error)
        )

    # ========================================================
    # HTML REPORT
    # ========================================================

    st.divider()

    st.subheader(
        "Professional Report"
    )

    html_report = create_html_report(
        summary,
        total_observations,
        first_date,
        latest_date
    )

    st.download_button(
        label="⬇ Download Professional HTML Report",
        data=html_report.encode("utf-8"),
        file_name=(
            "kenya_financial_analytics_report.html"
        ),
        mime="text/html"
    )

    st.info(
        "Open the HTML report in your browser and "
        "use Print → Save as PDF if you need a PDF copy."
    )

    # ========================================================
    # REPORT DATA
    # ========================================================

    st.divider()

    st.subheader(
        "Report Data"
    )

    st.dataframe(
        data,
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        "Report generated from the local Kenya Financial "
        "Analytics historical Treasury Bill database."
    )
'''

MODULE.write_text(
    code,
    encoding="utf-8"
)

# ============================================================
# VERIFY MODULE
# ============================================================

py_compile.compile(
    str(MODULE),
    doraise=True
)

# ============================================================
# CONNECT DASHBOARD
# ============================================================

dashboard = DASHBOARD.read_text(
    encoding="utf-8"
)

# ------------------------------------------------------------
# IMPORT
# ------------------------------------------------------------

if "import kenya_financial_reports" not in dashboard:

    marker = "import kenya_research_intelligence"

    if marker in dashboard:

        dashboard = dashboard.replace(
            marker,
            marker
            + "\nimport kenya_financial_reports",
            1
        )

    else:

        dashboard = (
            "import kenya_financial_reports\n"
            + dashboard
        )

# ------------------------------------------------------------
# NAVIGATION
# ------------------------------------------------------------

if '"Financial Reports"' not in dashboard:

    marker = '        "Research Intelligence",\n'

    if marker not in dashboard:

        raise RuntimeError(
            "Research Intelligence navigation entry "
            "was not found."
        )

    dashboard = dashboard.replace(
        marker,
        marker
        + '        "Financial Reports",\n',
        1
    )

# ------------------------------------------------------------
# PAGE
# ------------------------------------------------------------

if 'elif page == "Financial Reports":' not in dashboard:

    marker = (
        'elif page == "Research Intelligence":'
    )

    if marker not in dashboard:

        raise RuntimeError(
            "Research Intelligence page was not found."
        )

    new_page = '''elif page == "Financial Reports":

    kenya_financial_reports.render_financial_reports()


'''

    dashboard = dashboard.replace(
        marker,
        new_page + marker,
        1
    )

# ============================================================
# SAVE
# ============================================================

DASHBOARD.write_text(
    dashboard,
    encoding="utf-8"
)

# ============================================================
# FINAL VERIFICATION
# ============================================================

py_compile.compile(
    str(MODULE),
    doraise=True
)

py_compile.compile(
    str(DASHBOARD),
    doraise=True
)

print()
print("=" * 70)
print("STEP 9 - FINANCIAL REPORTS & EXPORT")
print("=" * 70)
print()
print("[SUCCESS] Financial Reports engine created.")
print("[SUCCESS] CBK market report enabled.")
print("[SUCCESS] CSV export enabled.")
print("[SUCCESS] Excel export enabled.")
print("[SUCCESS] Professional HTML report enabled.")
print("[SUCCESS] Financial Reports added to navigation.")
print("[SUCCESS] Report engine syntax verified.")
print("[SUCCESS] Dashboard syntax verified.")
print()
print("Backup:")
print(backup)
print()
print("NEW MODULE:")
print("    Financial Reports")
print()
print("Run:")
print("    .\\.venv\\Scripts\\python.exe -m streamlit run dashboard.py")
print()
print("=" * 70)
