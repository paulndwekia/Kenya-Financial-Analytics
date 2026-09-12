from pathlib import Path
import shutil
from datetime import datetime

BASE = Path(__file__).resolve().parent
DASHBOARD = BASE / "dashboard.py"
INTELLIGENCE = BASE / "kenya_market_intelligence.py"

# ============================================================
# BACKUP
# ============================================================

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup = BASE / f"dashboard_backup_before_intelligence_{timestamp}.py"

shutil.copy2(DASHBOARD, backup)

# ============================================================
# CREATE MARKET INTELLIGENCE ENGINE
# ============================================================

intelligence_code = r'''
import sqlite3
from pathlib import Path
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
                rate,
                issue_number,
                source
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

    data["tenor_days"] = data[
        "tenor_days"
    ].astype(int)

    return data


def direction_text(change):
    if change > 0.0005:
        return "increased"
    elif change < -0.0005:
        return "decreased"
    return "remained broadly stable"


def curve_interpretation(rates):
    if len(rates) < 2:
        return "Insufficient tenor data for a curve interpretation."

    ordered = sorted(rates.items())

    first_rate = ordered[0][1]
    last_rate = ordered[-1][1]

    difference = last_rate - first_rate

    if difference > 0.0005:
        return (
            "The observed Treasury Bill curve is upward sloping: "
            "the longer selected tenor has a higher yield than "
            "the shorter selected tenor."
        )

    if difference < -0.0005:
        return (
            "The observed Treasury Bill curve is downward sloping: "
            "the longer selected tenor has a lower yield than "
            "the shorter selected tenor."
        )

    return (
        "The observed Treasury Bill curve is relatively flat "
        "across the selected tenors."
    )


def render_market_intelligence():

    st.header(
        "🇰🇪 Kenya Market Intelligence"
    )

    st.caption(
        "Data-driven analysis of historical CBK Treasury Bill "
        "observations stored in the Kenya Financial Analytics database."
    )

    data = load_market_data()

    if data.empty:
        st.warning(
            "No Treasury Bill market data is available."
        )
        return

    # ========================================================
    # MARKET OVERVIEW
    # ========================================================

    st.subheader(
        "Market Overview"
    )

    latest_date = data["auction_date"].max()

    latest_data = data[
        data["auction_date"] == latest_date
    ].copy()

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Latest Auction",
            latest_date.strftime("%d %b %Y")
        )

    with c2:
        st.metric(
            "Observations",
            f"{len(data):,}"
        )

    with c3:
        st.metric(
            "Tenors",
            f"{data['tenor_days'].nunique()}"
        )

    with c4:
        st.metric(
            "Historical Dates",
            f"{data['auction_date'].nunique():,}"
        )

    st.divider()

    # ========================================================
    # TENOR ANALYSIS
    # ========================================================

    st.subheader(
        "Treasury Bill Intelligence"
    )

    available_tenors = [
        x for x in [91, 182, 364]
        if x in data["tenor_days"].unique()
    ]

    if not available_tenors:
        available_tenors = sorted(
            data["tenor_days"].unique().tolist()
        )

    selected_tenors = st.multiselect(
        "Select Tenors",
        available_tenors,
        default=available_tenors,
        format_func=lambda x:
            f"{x}-Day Treasury Bill"
    )

    if not selected_tenors:
        st.info(
            "Select at least one tenor."
        )
        return

    analysis = data[
        data["tenor_days"].isin(
            selected_tenors
        )
    ].copy()

    analysis = analysis.sort_values(
        "auction_date"
    )

    # ========================================================
    # AUTOMATIC INSIGHTS
    # ========================================================

    st.subheader(
        "Automatic Market Insights"
    )

    for tenor in selected_tenors:

        tenor_data = analysis[
            analysis["tenor_days"] == tenor
        ].sort_values(
            "auction_date"
        )

        if tenor_data.empty:
            continue

        first = float(
            tenor_data["rate"].iloc[0]
        )

        latest = float(
            tenor_data["rate"].iloc[-1]
        )

        average = float(
            tenor_data["rate"].mean()
        )

        highest = float(
            tenor_data["rate"].max()
        )

        lowest = float(
            tenor_data["rate"].min()
        )

        change = latest - first

        vs_average = latest - average

        direction = direction_text(
            change
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
                "Historical Average",
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

        st.write(
            f"**Trend:** The yield has **{direction}** "
            f"by {change * 100:+.4f} percentage points "
            f"between the first and latest available observations."
        )

        if vs_average > 0.0005:
            st.info(
                f"The latest {tenor}-day yield is "
                f"{abs(vs_average) * 100:.4f} percentage points "
                f"above its historical average in the selected dataset."
            )

        elif vs_average < -0.0005:
            st.info(
                f"The latest {tenor}-day yield is "
                f"{abs(vs_average) * 100:.4f} percentage points "
                f"below its historical average in the selected dataset."
            )

        else:
            st.info(
                f"The latest {tenor}-day yield is "
                f"close to its historical average in the selected dataset."
            )

    # ========================================================
    # CURRENT CURVE
    # ========================================================

    st.divider()

    st.subheader(
        "Latest Treasury Bill Curve"
    )

    curve_rates = {}

    for tenor in selected_tenors:

        tenor_data = latest_data[
            latest_data["tenor_days"] == tenor
        ]

        if not tenor_data.empty:

            curve_rates[tenor] = float(
                tenor_data["rate"].iloc[-1]
            )

    if curve_rates:

        curve_rows = []

        for tenor in sorted(curve_rates):

            curve_rows.append({
                "Tenor":
                    f"{tenor}-Day",

                "Latest Yield":
                    f"{curve_rates[tenor] * 100:.4f}%"
            })

        st.dataframe(
            pd.DataFrame(curve_rows),
            use_container_width=True,
            hide_index=True
        )

        st.line_chart(
            pd.DataFrame(
                {
                    "Yield (%)": {
                        f"{tenor}-Day":
                            rate * 100
                        for tenor, rate
                        in sorted(
                            curve_rates.items()
                        )
                    }
                }
            ),
            use_container_width=True
        )

        st.success(
            curve_interpretation(
                curve_rates
            )
        )

    else:

        st.warning(
            "The latest auction does not contain "
            "the selected tenors."
        )

    # ========================================================
    # RECENT MOMENTUM
    # ========================================================

    st.divider()

    st.subheader(
        "Recent Yield Movement"
    )

    recent_rows = []

    for tenor in selected_tenors:

        tenor_data = analysis[
            analysis["tenor_days"] == tenor
        ].sort_values(
            "auction_date"
        )

        if len(tenor_data) < 2:
            continue

        latest_row = tenor_data.iloc[-1]
        previous_row = tenor_data.iloc[-2]

        latest_rate = float(
            latest_row["rate"]
        )

        previous_rate = float(
            previous_row["rate"]
        )

        movement = (
            latest_rate
            - previous_rate
        )

        recent_rows.append({
            "Tenor":
                f"{tenor}-Day",

            "Latest Date":
                latest_row[
                    "auction_date"
                ].strftime("%d %b %Y"),

            "Previous Date":
                previous_row[
                    "auction_date"
                ].strftime("%d %b %Y"),

            "Latest Yield":
                f"{latest_rate * 100:.4f}%",

            "Previous Yield":
                f"{previous_rate * 100:.4f}%",

            "Movement":
                f"{movement * 100:+.4f} pp",

            "Direction":
                direction_text(movement)
        })

    if recent_rows:

        st.dataframe(
            pd.DataFrame(recent_rows),
            use_container_width=True,
            hide_index=True
        )

    # ========================================================
    # TREND CHART
    # ========================================================

    st.subheader(
        "Historical Yield Trends"
    )

    chart = analysis.copy()

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
    # DATA QUALITY
    # ========================================================

    st.divider()

    st.subheader(
        "Market Data Quality"
    )

    duplicate_count = data.duplicated(
        subset=[
            "auction_date",
            "tenor_days"
        ]
    ).sum()

    q1, q2, q3 = st.columns(3)

    with q1:
        st.metric(
            "Duplicate Observations",
            f"{duplicate_count:,}"
        )

    with q2:
        st.metric(
            "First Date",
            data["auction_date"]
            .min()
            .strftime("%d %b %Y")
        )

    with q3:
        st.metric(
            "Latest Date",
            data["auction_date"]
            .max()
            .strftime("%d %b %Y")
        )

    if duplicate_count == 0:

        st.success(
            "Market dataset passes the duplicate observation check."
        )

    else:

        st.warning(
            "Duplicate date/tenor observations were detected. "
            "Review the market database before using the data "
            "for historical analysis."
        )

    st.caption(
        "This intelligence layer describes patterns in the stored "
        "CBK observations. It does not constitute investment advice "
        "or a prediction of future market prices."
    )
'''

INTELLIGENCE.write_text(
    intelligence_code,
    encoding="utf-8"
)

# ============================================================
# MODIFY DASHBOARD
# ============================================================

dashboard = DASHBOARD.read_text(
    encoding="utf-8"
)

# Add import
import_marker = "import cbk_pricing\n"

if "import kenya_market_intelligence" not in dashboard:

    if import_marker in dashboard:

        dashboard = dashboard.replace(
            import_marker,
            import_marker
            + "import kenya_market_intelligence\n",
            1
        )

    else:

        dashboard = (
            "import kenya_market_intelligence\n"
            + dashboard
        )

# Add navigation item
nav_marker = '        "Kenyan Market",\n'

if '"Market Intelligence"' not in dashboard:

    dashboard = dashboard.replace(
        nav_marker,
        nav_marker
        + '        "Market Intelligence",\n',
        1
    )

# Add page before Historical Market Explorer
page_marker = 'elif page == "Historical Market Explorer":'

if 'elif page == "Market Intelligence":' not in dashboard:

    intelligence_page = '''
elif page == "Market Intelligence":

    kenya_market_intelligence.render_market_intelligence()


'''

    dashboard = dashboard.replace(
        page_marker,
        intelligence_page + page_marker,
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
    str(INTELLIGENCE),
    doraise=True
)

py_compile.compile(
    str(DASHBOARD),
    doraise=True
)

print()
print("=" * 70)
print("KENYA MARKET INTELLIGENCE UPGRADE")
print("=" * 70)
print()
print("[SUCCESS] Market Intelligence engine created.")
print("[SUCCESS] Dashboard navigation updated.")
print("[SUCCESS] Dashboard syntax verified.")
print("[SUCCESS] Intelligence engine syntax verified.")
print()
print("New module:")
print("    Market Intelligence")
print()
print("Backup:")
print(backup)
print()
print("Run:")
print("    streamlit run dashboard.py")
print()
print("=" * 70)
