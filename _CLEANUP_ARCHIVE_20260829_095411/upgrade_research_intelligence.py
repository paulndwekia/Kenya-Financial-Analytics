from pathlib import Path
import shutil
import py_compile
from datetime import datetime

BASE = Path(__file__).resolve().parent
DASHBOARD = BASE / "dashboard.py"
MODULE = BASE / "kenya_research_intelligence.py"

# ============================================================
# BACKUP
# ============================================================

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

backup = BASE / (
    f"dashboard_backup_before_research_intelligence_{timestamp}.py"
)

shutil.copy2(DASHBOARD, backup)

# ============================================================
# CREATE RESEARCH INTELLIGENCE ENGINE
# ============================================================

code = r'''
import sqlite3
from pathlib import Path

import pandas as pd
import numpy as np
import streamlit as st


DATABASE = Path(__file__).resolve().parent / "kenya_market.db"


def load_data():

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


def render_research_intelligence():

    st.header(
        "🇰🇪 Kenya Research & Backtesting Intelligence"
    )

    st.caption(
        "Historical research using Treasury Bill observations "
        "stored in the local CBK market database."
    )

    data = load_data()

    if data.empty:

        st.warning(
            "No historical CBK Treasury Bill data is available."
        )

        return

    # ========================================================
    # CONTROLS
    # ========================================================

    st.subheader(
        "Research Controls"
    )

    available_tenors = sorted(
        data["tenor_days"]
        .unique()
        .tolist()
    )

    preferred = [91, 182, 364]

    default_tenors = [
        x for x in preferred
        if x in available_tenors
    ]

    if not default_tenors:
        default_tenors = available_tenors

    selected_tenor = st.selectbox(
        "Treasury Bill Tenor",
        default_tenors,
        format_func=lambda x:
            f"{x}-Day Treasury Bill"
    )

    selected = data[
        data["tenor_days"] == selected_tenor
    ].copy()

    selected = selected.sort_values(
        "auction_date"
    )

    if len(selected) < 2:

        st.warning(
            "At least two historical observations are required."
        )

        return

    # ========================================================
    # DATE RANGE
    # ========================================================

    min_date = selected[
        "auction_date"
    ].min().date()

    max_date = selected[
        "auction_date"
    ].max().date()

    start_date, end_date = st.date_input(
        "Research Period",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    selected = selected[
        (selected["auction_date"].dt.date >= start_date)
        &
        (selected["auction_date"].dt.date <= end_date)
    ].copy()

    if len(selected) < 2:

        st.warning(
            "The selected period does not contain enough observations."
        )

        return

    # ========================================================
    # CORE STATISTICS
    # ========================================================

    rates = selected["rate"]

    latest = float(
        rates.iloc[-1]
    )

    first = float(
        rates.iloc[0]
    )

    average = float(
        rates.mean()
    )

    median = float(
        rates.median()
    )

    highest = float(
        rates.max()
    )

    lowest = float(
        rates.min()
    )

    standard_deviation = float(
        rates.std()
    )

    total_change = (
        latest - first
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    st.divider()

    st.subheader(
        "Historical Research Summary"
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.metric(
            "Latest Yield",
            f"{latest * 100:.4f}%"
        )

    with c2:

        st.metric(
            "Average Yield",
            f"{average * 100:.4f}%"
        )

    with c3:

        st.metric(
            "Historical High",
            f"{highest * 100:.4f}%"
        )

    with c4:

        st.metric(
            "Historical Low",
            f"{lowest * 100:.4f}%"
        )

    # ========================================================
    # STATISTICS
    # ========================================================

    st.subheader(
        "Research Statistics"
    )

    stats = pd.DataFrame([
        {
            "Metric": "Observations",
            "Value": f"{len(selected):,}"
        },
        {
            "Metric": "First Yield",
            "Value": f"{first * 100:.4f}%"
        },
        {
            "Metric": "Latest Yield",
            "Value": f"{latest * 100:.4f}%"
        },
        {
            "Metric": "Average",
            "Value": f"{average * 100:.4f}%"
        },
        {
            "Metric": "Median",
            "Value": f"{median * 100:.4f}%"
        },
        {
            "Metric": "Standard Deviation",
            "Value": f"{standard_deviation * 100:.4f}%"
        },
        {
            "Metric": "Total Yield Change",
            "Value": f"{total_change * 100:+.4f} pp"
        }
    ])

    st.dataframe(
        stats,
        use_container_width=True,
        hide_index=True
    )

    # ========================================================
    # HISTORICAL TREND
    # ========================================================

    st.divider()

    st.subheader(
        "Historical Yield Trend"
    )

    trend = selected.set_index(
        "auction_date"
    )[["rate"]].copy()

    trend["Yield (%)"] = (
        trend["rate"] * 100
    )

    st.line_chart(
        trend["Yield (%)"],
        use_container_width=True
    )

    # ========================================================
    # YIELD CHANGES
    # ========================================================

    selected["change"] = (
        selected["rate"].diff()
    )

    changes = selected[
        "change"
    ].dropna()

    if not changes.empty:

        st.subheader(
            "Yield Change Analysis"
        )

        positive = int(
            (changes > 0).sum()
        )

        negative = int(
            (changes < 0).sum()
        )

        stable = int(
            (changes == 0).sum()
        )

        c1, c2, c3 = st.columns(3)

        with c1:

            st.metric(
                "Yield Increases",
                positive
            )

        with c2:

            st.metric(
                "Yield Decreases",
                negative
            )

        with c3:

            st.metric(
                "Unchanged",
                stable
            )

    # ========================================================
    # ROLLING VOLATILITY
    # ========================================================

    st.divider()

    st.subheader(
        "Rolling Yield Volatility"
    )

    window = min(
        5,
        max(
            2,
            len(selected) // 3
        )
    )

    selected["rolling_volatility"] = (
        selected["rate"]
        .rolling(window)
        .std()
    )

    volatility_chart = selected.set_index(
        "auction_date"
    )["rolling_volatility"] * 100

    st.line_chart(
        volatility_chart,
        use_container_width=True
    )

    # ========================================================
    # BEST / WORST PERIODS
    # ========================================================

    st.divider()

    st.subheader(
        "Historical Best & Worst Yield Changes"
    )

    change_data = selected[
        [
            "auction_date",
            "change"
        ]
    ].dropna().copy()

    if not change_data.empty:

        best = change_data.nlargest(
            min(5, len(change_data)),
            "change"
        ).copy()

        worst = change_data.nsmallest(
            min(5, len(change_data)),
            "change"
        ).copy()

        best["Change"] = (
            best["change"] * 100
        )

        worst["Change"] = (
            worst["change"] * 100
        )

        c1, c2 = st.columns(2)

        with c1:

            st.markdown(
                "#### Largest Yield Increases"
            )

            st.dataframe(
                best[
                    [
                        "auction_date",
                        "Change"
                    ]
                ].rename(
                    columns={
                        "auction_date": "Date",
                        "Change": "Change (pp)"
                    }
                ),
                use_container_width=True,
                hide_index=True
            )

        with c2:

            st.markdown(
                "#### Largest Yield Decreases"
            )

            st.dataframe(
                worst[
                    [
                        "auction_date",
                        "Change"
                    ]
                ].rename(
                    columns={
                        "auction_date": "Date",
                        "Change": "Change (pp)"
                    }
                ),
                use_container_width=True,
                hide_index=True
            )

    # ========================================================
    # SIMPLE HISTORICAL STRATEGY
    # ========================================================

    st.divider()

    st.subheader(
        "Historical Yield Strategy Research"
    )

    threshold = st.number_input(
        "Yield Entry Threshold (%)",
        min_value=0.0,
        max_value=100.0,
        value=float(average * 100),
        step=0.10
    )

    threshold_decimal = (
        threshold / 100
    )

    selected["above_threshold"] = (
        selected["rate"]
        >= threshold_decimal
    )

    observations_above = int(
        selected["above_threshold"].sum()
    )

    percentage_above = (
        observations_above
        / len(selected)
        * 100
    )

    c1, c2 = st.columns(2)

    with c1:

        st.metric(
            "Observations Above Threshold",
            observations_above
        )

    with c2:

        st.metric(
            "Percentage Above Threshold",
            f"{percentage_above:.2f}%"
        )

    if latest >= threshold_decimal:

        st.success(
            f"The latest {selected_tenor}-day yield is "
            "above the research threshold."
        )

    else:

        st.info(
            f"The latest {selected_tenor}-day yield is "
            "below the research threshold."
        )

    # ========================================================
    # RESEARCH INTERPRETATION
    # ========================================================

    st.divider()

    st.subheader(
        "Research Interpretation"
    )

    if total_change > 0.0005:

        st.write(
            f"The {selected_tenor}-day Treasury Bill yield "
            f"finished the selected research period "
            f"{abs(total_change) * 100:.4f} percentage points "
            "higher than where it began."
        )

    elif total_change < -0.0005:

        st.write(
            f"The {selected_tenor}-day Treasury Bill yield "
            f"finished the selected research period "
            f"{abs(total_change) * 100:.4f} percentage points "
            "lower than where it began."
        )

    else:

        st.write(
            f"The {selected_tenor}-day Treasury Bill yield "
            "was broadly stable across the selected period."
        )

    if latest > average:

        st.info(
            "The latest yield is above the historical "
            "average for the selected research period."
        )

    elif latest < average:

        st.info(
            "The latest yield is below the historical "
            "average for the selected research period."
        )

    else:

        st.info(
            "The latest yield is approximately equal "
            "to the historical average."
        )

    st.caption(
        "Historical research describes past observations "
        "and does not guarantee future performance."
    )
'''

MODULE.write_text(
    code,
    encoding="utf-8"
)

# ============================================================
# VERIFY NEW MODULE
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

if "import kenya_research_intelligence" not in dashboard:

    marker = "import kenya_portfolio_intelligence"

    if marker in dashboard:

        dashboard = dashboard.replace(
            marker,
            marker
            + "\nimport kenya_research_intelligence",
            1
        )

    else:

        dashboard = (
            "import kenya_research_intelligence\n"
            + dashboard
        )

# ============================================================
# NAVIGATION
# ============================================================

if '"Research Intelligence"' not in dashboard:

    marker = '        "Backtesting",\n'

    if marker not in dashboard:

        raise RuntimeError(
            "Backtesting navigation entry was not found."
        )

    dashboard = dashboard.replace(
        marker,
        '        "Research Intelligence",\n'
        + marker,
        1
    )

# ============================================================
# PAGE
# ============================================================

if 'elif page == "Research Intelligence":' not in dashboard:

    marker = 'elif page == "Backtesting":'

    if marker not in dashboard:

        raise RuntimeError(
            "Backtesting page was not found."
        )

    new_page = '''elif page == "Research Intelligence":

    kenya_research_intelligence.render_research_intelligence()


'''

    dashboard = dashboard.replace(
        marker,
        new_page + marker,
        1
    )

# ============================================================
# SAVE + VERIFY
# ============================================================

DASHBOARD.write_text(
    dashboard,
    encoding="utf-8"
)

py_compile.compile(
    str(DASHBOARD),
    doraise=True
)

print()
print("=" * 70)
print("STEP 8 - RESEARCH & BACKTESTING INTELLIGENCE")
print("=" * 70)
print()
print("[SUCCESS] Research Intelligence engine created.")
print("[SUCCESS] Historical CBK research enabled.")
print("[SUCCESS] Research Intelligence added to navigation.")
print("[SUCCESS] Research engine syntax verified.")
print("[SUCCESS] Dashboard syntax verified.")
print()
print("Backup:")
print(backup)
print()
print("NEW MODULE:")
print("    Research Intelligence")
print()
print("Run:")
print("    .\\.venv\\Scripts\\python.exe -m streamlit run dashboard.py")
print()
print("=" * 70)
