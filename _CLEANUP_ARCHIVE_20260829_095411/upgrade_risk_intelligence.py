from pathlib import Path
import shutil
from datetime import datetime

BASE = Path(__file__).resolve().parent
DASHBOARD = BASE / "dashboard.py"
RISK_FILE = BASE / "kenya_risk_intelligence.py"

# ============================================================
# BACKUP
# ============================================================

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / f"dashboard_backup_before_risk_intelligence_{timestamp}.py"

shutil.copy2(
    DASHBOARD,
    backup
)

# ============================================================
# CREATE RISK INTELLIGENCE ENGINE
# ============================================================

risk_code = r'''
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


DATABASE = Path(__file__).resolve().parent / "kenya_market.db"


def load_cbk_history():

    if not DATABASE.exists():
        return pd.DataFrame()

    connection = sqlite3.connect(
        DATABASE
    )

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
        data["tenor_days"]
        .astype(int)
    )

    return data


def risk_level(volatility):

    if volatility >= 0.20:
        return "HIGH"

    if volatility >= 0.10:
        return "MODERATE"

    return "LOW"


def render_risk_intelligence():

    st.header(
        "🇰🇪 Kenya Risk Intelligence"
    )

    st.caption(
        "Historical Treasury Bill risk analysis using "
        "CBK observations stored in the local market database."
    )

    data = load_cbk_history()

    if data.empty:

        st.warning(
            "No CBK Treasury Bill history is available."
        )

        return

    # ========================================================
    # TENOR SELECTION
    # ========================================================

    available = sorted(
        data["tenor_days"]
        .unique()
        .tolist()
    )

    preferred = [
        91,
        182,
        364
    ]

    tenors = [
        x for x in preferred
        if x in available
    ]

    if not tenors:
        tenors = available

    selected = st.multiselect(
        "Select Treasury Bill Tenors",
        tenors,
        default=tenors,
        format_func=lambda x:
            f"{x}-Day"
    )

    if not selected:

        st.info(
            "Select at least one Treasury Bill tenor."
        )

        return

    # ========================================================
    # DATA
    # ========================================================

    filtered = data[
        data["tenor_days"].isin(selected)
    ].copy()

    filtered = filtered.sort_values(
        "auction_date"
    )

    # ========================================================
    # MARKET RISK SUMMARY
    # ========================================================

    st.subheader(
        "Market Risk Summary"
    )

    rows = []

    for tenor in selected:

        series = filtered[
            filtered["tenor_days"] == tenor
        ].sort_values(
            "auction_date"
        )

        if len(series) < 2:
            continue

        rates = series["rate"]

        changes = rates.diff().dropna()

        latest = float(
            rates.iloc[-1]
        )

        average = float(
            rates.mean()
        )

        high = float(
            rates.max()
        )

        low = float(
            rates.min()
        )

        rate_volatility = float(
            rates.std()
        )

        change_volatility = float(
            changes.std()
        )

        first = float(
            rates.iloc[0]
        )

        total_change = (
            latest - first
        )

        rows.append({
            "Tenor":
                f"{tenor}-Day",

            "Latest Yield":
                f"{latest * 100:.4f}%",

            "Average Yield":
                f"{average * 100:.4f}%",

            "Highest Yield":
                f"{high * 100:.4f}%",

            "Lowest Yield":
                f"{low * 100:.4f}%",

            "Yield Change":
                f"{total_change * 100:+.4f} pp",

            "Yield Volatility":
                f"{rate_volatility * 100:.4f}%",

            "Risk Level":
                risk_level(
                    rate_volatility
                )
        })

    if rows:

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True
        )

    # ========================================================
    # RISK METRICS
    # ========================================================

    st.divider()

    st.subheader(
        "Risk Metrics"
    )

    for tenor in selected:

        series = filtered[
            filtered["tenor_days"] == tenor
        ].sort_values(
            "auction_date"
        )

        if len(series) < 2:
            continue

        rates = series["rate"]

        latest = float(
            rates.iloc[-1]
        )

        average = float(
            rates.mean()
        )

        high = float(
            rates.max()
        )

        low = float(
            rates.min()
        )

        volatility = float(
            rates.std()
        )

        range_value = (
            high - low
        )

        st.markdown(
            f"### {tenor}-Day Treasury Bill"
        )

        c1, c2, c3, c4 = st.columns(4)

        with c1:

            st.metric(
                "Latest Yield",
                f"{latest * 100:.4f}%"
            )

        with c2:

            st.metric(
                "Yield Volatility",
                f"{volatility * 100:.4f}%"
            )

        with c3:

            st.metric(
                "Historical Range",
                f"{range_value * 100:.4f} pp"
            )

        with c4:

            st.metric(
                "Risk Level",
                risk_level(volatility)
            )

        # ====================================================
        # POSITION RELATIVE TO HISTORY
        # ====================================================

        if latest > average:

            st.info(
                f"The latest {tenor}-day yield is "
                f"{(latest - average) * 100:.4f} percentage points "
                f"above its historical average."
            )

        elif latest < average:

            st.info(
                f"The latest {tenor}-day yield is "
                f"{(average - latest) * 100:.4f} percentage points "
                f"below its historical average."
            )

        else:

            st.info(
                f"The latest {tenor}-day yield is approximately "
                f"at its historical average."
            )

    # ========================================================
    # YIELD MOVEMENT
    # ========================================================

    st.divider()

    st.subheader(
        "Yield Movement Analysis"
    )

    movement_rows = []

    for tenor in selected:

        series = filtered[
            filtered["tenor_days"] == tenor
        ].sort_values(
            "auction_date"
        )

        if len(series) < 2:
            continue

        latest = float(
            series["rate"].iloc[-1]
        )

        previous = float(
            series["rate"].iloc[-2]
        )

        movement = (
            latest - previous
        )

        if movement > 0.0005:
            direction = "Increasing"

        elif movement < -0.0005:
            direction = "Decreasing"

        else:
            direction = "Stable"

        movement_rows.append({
            "Tenor":
                f"{tenor}-Day",

            "Latest Yield":
                f"{latest * 100:.4f}%",

            "Previous Yield":
                f"{previous * 100:.4f}%",

            "Movement":
                f"{movement * 100:+.4f} pp",

            "Direction":
                direction
        })

    if movement_rows:

        st.dataframe(
            pd.DataFrame(
                movement_rows
            ),
            use_container_width=True,
            hide_index=True
        )

    # ========================================================
    # RISK TREND
    # ========================================================

    st.subheader(
        "Historical Yield Risk Trend"
    )

    chart = filtered.copy()

    chart["Tenor"] = (
        chart["tenor_days"]
        .astype(str)
        + "-Day"
    )

    chart = chart.pivot_table(
        index="auction_date",
        columns="Tenor",
        values="rate",
        aggfunc="mean"
    ).sort_index()

    if not chart.empty:

        st.line_chart(
            chart * 100,
            use_container_width=True
        )

    # ========================================================
    # EXTREME LEVELS
    # ========================================================

    st.divider()

    st.subheader(
        "Historical Risk Extremes"
    )

    extremes = []

    for tenor in selected:

        series = filtered[
            filtered["tenor_days"] == tenor
        ].sort_values(
            "auction_date"
        )

        if series.empty:
            continue

        highest_row = series.loc[
            series["rate"].idxmax()
        ]

        lowest_row = series.loc[
            series["rate"].idxmin()
        ]

        extremes.append({
            "Tenor":
                f"{tenor}-Day",

            "Highest Yield":
                f"{highest_row['rate'] * 100:.4f}%",

            "High Date":
                highest_row[
                    "auction_date"
                ].strftime("%d %b %Y"),

            "Lowest Yield":
                f"{lowest_row['rate'] * 100:.4f}%",

            "Low Date":
                lowest_row[
                    "auction_date"
                ].strftime("%d %b %Y")
        })

    if extremes:

        st.dataframe(
            pd.DataFrame(extremes),
            use_container_width=True,
            hide_index=True
        )

    # ========================================================
    # OVERALL INTERPRETATION
    # ========================================================

    st.divider()

    st.subheader(
        "Kenyan Market Risk Interpretation"
    )

    latest_rates = {}

    for tenor in selected:

        series = filtered[
            filtered["tenor_days"] == tenor
        ].sort_values(
            "auction_date"
        )

        if not series.empty:

            latest_rates[tenor] = float(
                series["rate"].iloc[-1]
            )

    if len(latest_rates) >= 2:

        ordered = sorted(
            latest_rates.items()
        )

        short_rate = ordered[0][1]
        long_rate = ordered[-1][1]

        spread = (
            long_rate - short_rate
        )

        if spread > 0.0005:

            st.success(
                "The latest selected Treasury Bill curve "
                "is upward sloping."
            )

        elif spread < -0.0005:

            st.warning(
                "The latest selected Treasury Bill curve "
                "is downward sloping."
            )

        else:

            st.info(
                "The latest selected Treasury Bill curve "
                "is relatively flat."
            )

    st.caption(
        "Risk indicators are calculated from historical CBK "
        "Treasury Bill observations. They describe historical "
        "market behaviour and are not forecasts or investment advice."
    )
'''

RISK_FILE.write_text(
    risk_code,
    encoding="utf-8"
)

# ============================================================
# UPDATE DASHBOARD
# ============================================================

dashboard = DASHBOARD.read_text(
    encoding="utf-8"
)

# Add import
if "import kenya_risk_intelligence" not in dashboard:

    marker = "import cbk_pricing\n"

    if marker in dashboard:

        dashboard = dashboard.replace(
            marker,
            marker
            + "import kenya_risk_intelligence\n",
            1
        )

    else:

        dashboard = (
            "import kenya_risk_intelligence\n"
            + dashboard
        )

# Add navigation item
if '"Risk Intelligence"' not in dashboard:

    marker = '        "Risk Analysis",\n'

    dashboard = dashboard.replace(
        marker,
        marker
        + '        "Risk Intelligence",\n',
        1
    )

# Add page
if 'elif page == "Risk Intelligence":' not in dashboard:

    marker = 'elif page == "Risk Analysis":'

    page_code = '''
elif page == "Risk Intelligence":

    kenya_risk_intelligence.render_risk_intelligence()


'''

    dashboard = dashboard.replace(
        marker,
        marker
        + "\n"
        + page_code,
        1
    )

DASHBOARD.write_text(
    dashboard,
    encoding="utf-8"
)

# ============================================================
# SYNTAX CHECK
# ============================================================

import py_compile

py_compile.compile(
    str(RISK_FILE),
    doraise=True
)

py_compile.compile(
    str(DASHBOARD),
    doraise=True
)

print()
print("=" * 70)
print("STEP 6 - KENYA RISK INTELLIGENCE")
print("=" * 70)
print()
print("[SUCCESS] Risk Intelligence engine created.")
print("[SUCCESS] Dashboard navigation updated.")
print("[SUCCESS] Risk Intelligence syntax verified.")
print("[SUCCESS] Dashboard syntax verified.")
print()
print("New module:")
print("    Risk Intelligence")
print()
print("Backup:")
print(backup)
print()
print("Run:")
print("    streamlit run dashboard.py")
print()
print("=" * 70)
