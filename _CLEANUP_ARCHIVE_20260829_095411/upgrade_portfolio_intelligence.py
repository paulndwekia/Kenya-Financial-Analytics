from pathlib import Path
import shutil
import py_compile
from datetime import datetime

BASE = Path(__file__).resolve().parent
DASHBOARD = BASE / "dashboard.py"
MODULE = BASE / "kenya_portfolio_intelligence.py"

# ============================================================
# BACKUP
# ============================================================

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

backup = BASE / (
    f"dashboard_backup_before_portfolio_intelligence_{timestamp}.py"
)

shutil.copy2(DASHBOARD, backup)

# ============================================================
# CREATE PORTFOLIO INTELLIGENCE MODULE
# ============================================================

code = r'''
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


DATABASE = Path(__file__).resolve().parent / "kenya_market.db"


ASSETS = [
    "91-Day Treasury Bill",
    "182-Day Treasury Bill",
    "364-Day Treasury Bill",
    "Government Bond",
    "Cash"
]


def load_cbk_data():

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


def get_latest_rate(data, tenor):

    rows = data[
        data["tenor_days"] == tenor
    ].sort_values(
        "auction_date"
    )

    if rows.empty:
        return None

    return float(
        rows["rate"].iloc[-1]
    )


def get_historical_volatility(data, tenor):

    rows = data[
        data["tenor_days"] == tenor
    ].sort_values(
        "auction_date"
    )

    if len(rows) < 2:
        return 0.0

    changes = rows["rate"].diff().dropna()

    return float(
        changes.std()
    )


def render_portfolio_intelligence():

    st.header(
        "🇰🇪 Portfolio Intelligence"
    )

    st.caption(
        "Portfolio analysis combining KES portfolio inputs "
        "with historical CBK Treasury Bill observations."
    )

    data = load_cbk_data()

    if data.empty:

        st.warning(
            "kenya_market.db contains no Treasury Bill history."
        )

        return

    # ========================================================
    # PORTFOLIO INPUTS
    # ========================================================

    st.subheader(
        "Portfolio Construction"
    )

    st.info(
        "Enter the amount invested in each asset. "
        "Treasury Bill expected returns are automatically "
        "linked to the latest CBK observation."
    )

    portfolio = []

    for asset in ASSETS:

        c1, c2 = st.columns(2)

        with c1:

            value = st.number_input(
                f"{asset} Value (KES)",
                min_value=0.0,
                value=0.0,
                step=10_000.0,
                key=f"pi_value_{asset}"
            )

        automatic_return = None

        if asset.startswith("91-Day"):

            automatic_return = get_latest_rate(
                data,
                91
            )

        elif asset.startswith("182-Day"):

            automatic_return = get_latest_rate(
                data,
                182
            )

        elif asset.startswith("364-Day"):

            automatic_return = get_latest_rate(
                data,
                364
            )

        with c2:

            if automatic_return is not None:

                st.metric(
                    f"{asset} Latest CBK Yield",
                    f"{automatic_return * 100:.4f}%"
                )

                expected_return = automatic_return

            else:

                expected_return = (
                    st.number_input(
                        f"{asset} Expected Return (%)",
                        min_value=-100.0,
                        max_value=100.0,
                        value=0.0,
                        step=0.10,
                        key=f"pi_return_{asset}"
                    )
                    / 100
                )

        if value > 0:

            portfolio.append({
                "asset":
                    asset,

                "value":
                    value,

                "expected_return":
                    expected_return
            })

    if not portfolio:

        st.info(
            "Enter a value for at least one portfolio asset."
        )

        return

    # ========================================================
    # PORTFOLIO CALCULATIONS
    # ========================================================

    total_value = sum(
        item["value"]
        for item in portfolio
    )

    expected_pnl = sum(
        item["value"]
        * item["expected_return"]
        for item in portfolio
    )

    expected_return = (
        expected_pnl / total_value
        if total_value > 0
        else 0.0
    )

    for item in portfolio:

        item["weight"] = (
            item["value"]
            / total_value
        )

        item["expected_pnl"] = (
            item["value"]
            * item["expected_return"]
        )

    # ========================================================
    # OVERVIEW
    # ========================================================

    st.divider()

    st.subheader(
        "Portfolio Intelligence Summary"
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.metric(
            "Portfolio Value",
            f"KES {total_value:,.2f}"
        )

    with c2:

        st.metric(
            "Expected Return",
            f"{expected_return * 100:.4f}%"
        )

    with c3:

        st.metric(
            "Expected Annual P&L",
            f"KES {expected_pnl:,.2f}"
        )

    with c4:

        st.metric(
            "Positions",
            f"{len(portfolio)}"
        )

    # ========================================================
    # ALLOCATION
    # ========================================================

    st.subheader(
        "Portfolio Allocation"
    )

    allocation = pd.DataFrame([
        {
            "Asset":
                item["asset"],

            "Value":
                f"KES {item['value']:,.2f}",

            "Weight":
                f"{item['weight'] * 100:.2f}%",

            "Expected Return":
                f"{item['expected_return'] * 100:.4f}%",

            "Expected P&L":
                f"KES {item['expected_pnl']:,.2f}"
        }

        for item in portfolio
    ])

    st.dataframe(
        allocation,
        use_container_width=True,
        hide_index=True
    )

    # ========================================================
    # CONCENTRATION
    # ========================================================

    st.divider()

    st.subheader(
        "Portfolio Concentration"
    )

    largest = max(
        portfolio,
        key=lambda x: x["weight"]
    )

    largest_weight = largest["weight"]

    c1, c2, c3 = st.columns(3)

    with c1:

        st.metric(
            "Largest Position",
            largest["asset"]
        )

    with c2:

        st.metric(
            "Largest Weight",
            f"{largest_weight * 100:.2f}%"
        )

    with c3:

        st.metric(
            "Number of Assets",
            len(portfolio)
        )

    if largest_weight >= 0.60:

        st.warning(
            "Portfolio concentration is high: "
            "one position represents at least 60% "
            "of the portfolio."
        )

    elif largest_weight >= 0.40:

        st.info(
            "Portfolio concentration is moderate."
        )

    else:

        st.success(
            "No single position exceeds 40% "
            "of the portfolio."
        )

    # ========================================================
    # CBK RATE EXPOSURE
    # ========================================================

    st.divider()

    st.subheader(
        "CBK Treasury Exposure"
    )

    tbill_assets = [
        item for item in portfolio
        if "Treasury Bill" in item["asset"]
    ]

    tbill_value = sum(
        item["value"]
        for item in tbill_assets
    )

    tbill_weight = (
        tbill_value / total_value
        if total_value > 0
        else 0
    )

    c1, c2 = st.columns(2)

    with c1:

        st.metric(
            "Treasury Bill Exposure",
            f"KES {tbill_value:,.2f}"
        )

    with c2:

        st.metric(
            "Treasury Bill Weight",
            f"{tbill_weight * 100:.2f}%"
        )

    # ========================================================
    # HISTORICAL CBK RISK
    # ========================================================

    st.divider()

    st.subheader(
        "Historical CBK Risk Contribution"
    )

    risk_rows = []

    for item in tbill_assets:

        if item["asset"].startswith("91-Day"):

            tenor = 91

        elif item["asset"].startswith("182-Day"):

            tenor = 182

        else:

            tenor = 364

        volatility = get_historical_volatility(
            data,
            tenor
        )

        latest = get_latest_rate(
            data,
            tenor
        )

        risk_rows.append({
            "Asset":
                item["asset"],

            "Portfolio Weight":
                f"{item['weight'] * 100:.2f}%",

            "Latest CBK Yield":
                (
                    f"{latest * 100:.4f}%"
                    if latest is not None
                    else "N/A"
                ),

            "Historical Yield Change Volatility":
                f"{volatility * 100:.4f}%"
        })

    if risk_rows:

        st.dataframe(
            pd.DataFrame(risk_rows),
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "No Treasury Bill positions were entered."
        )

    # ========================================================
    # PORTFOLIO INTELLIGENCE
    # ========================================================

    st.divider()

    st.subheader(
        "Automatic Portfolio Intelligence"
    )

    if tbill_weight >= 0.70:

        st.warning(
            "The portfolio is heavily exposed to "
            "Treasury Bills. Changes in the Kenyan "
            "short-term interest-rate environment "
            "may materially affect reinvestment returns."
        )

    elif tbill_weight >= 0.40:

        st.info(
            "Treasury Bills represent a significant "
            "portion of the portfolio. Monitor CBK "
            "auction yields and reinvestment conditions."
        )

    else:

        st.success(
            "Treasury Bill exposure is below 40% "
            "of the entered portfolio."
        )

    if expected_return > 0:

        st.write(
            f"The portfolio's weighted expected annual "
            f"return based on the entered assumptions and "
            f"latest CBK Treasury Bill yields is "
            f"**{expected_return * 100:.4f}%**."
        )

    elif expected_return < 0:

        st.warning(
            f"The entered portfolio assumptions imply "
            f"a negative weighted expected return of "
            f"{expected_return * 100:.4f}%."
        )

    else:

        st.info(
            "The entered portfolio has approximately "
            "zero weighted expected return."
        )

    st.caption(
        "CBK-linked returns are based on the latest "
        "historical observations available in the local "
        "database. This is an analytical tool, not investment advice."
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
# CONNECT TO DASHBOARD
# ============================================================

dashboard = DASHBOARD.read_text(
    encoding="utf-8"
)

# Import
if "import kenya_portfolio_intelligence" not in dashboard:

    marker = "import kenya_risk_intelligence"

    if marker in dashboard:

        dashboard = dashboard.replace(
            marker,
            marker
            + "\nimport kenya_portfolio_intelligence",
            1
        )

    else:

        dashboard = (
            "import kenya_portfolio_intelligence\n"
            + dashboard
        )

# Navigation
if '"Portfolio Intelligence"' not in dashboard:

    marker = '        "Portfolio",\n'

    if marker not in dashboard:

        raise RuntimeError(
            "Portfolio navigation entry was not found."
        )

    dashboard = dashboard.replace(
        marker,
        '        "Portfolio Intelligence",\n'
        + marker,
        1
    )

# Page
if 'elif page == "Portfolio Intelligence":' not in dashboard:

    marker = 'elif page == "Portfolio":'

    if marker not in dashboard:

        raise RuntimeError(
            "Portfolio page was not found."
        )

    new_page = '''elif page == "Portfolio Intelligence":

    kenya_portfolio_intelligence.render_portfolio_intelligence()


'''

    dashboard = dashboard.replace(
        marker,
        new_page + marker,
        1
    )

# Write
DASHBOARD.write_text(
    dashboard,
    encoding="utf-8"
)

# Final syntax checks
py_compile.compile(
    str(DASHBOARD),
    doraise=True
)

print()
print("=" * 70)
print("STEP 7 - PORTFOLIO INTELLIGENCE")
print("=" * 70)
print()
print("[SUCCESS] Portfolio Intelligence engine created.")
print("[SUCCESS] CBK-linked Treasury Bill returns enabled.")
print("[SUCCESS] Portfolio Intelligence added to navigation.")
print("[SUCCESS] Dashboard syntax verified.")
print("[SUCCESS] Engine syntax verified.")
print()
print("Backup:")
print(backup)
print()
print("NEW MODULE:")
print("    Portfolio Intelligence")
print()
print("Run:")
print("    .\\.venv\\Scripts\\python.exe -m streamlit run dashboard.py")
print()
print("=" * 70)
