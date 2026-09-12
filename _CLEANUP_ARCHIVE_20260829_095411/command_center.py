
import sqlite3
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Kenya Financial Analytics",
    page_icon="🇰🇪",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# DATABASE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATABASE = BASE_DIR / "kenya_market.db"


def get_connection():

    return sqlite3.connect(
        str(DATABASE)
    )


def get_tables():

    if not DATABASE.exists():

        return []

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        ORDER BY name
    """)

    tables = [
        row[0]
        for row in cursor.fetchall()
    ]

    connection.close()

    return tables


def get_table_count(
    table
):

    connection = get_connection()

    cursor = connection.cursor()

    try:

        cursor.execute(
            f'SELECT COUNT(*) FROM "{table}"'
        )

        result = cursor.fetchone()[0]

    except Exception:

        result = 0

    connection.close()

    return result


# ============================================================
# TREASURY DATA
# ============================================================

def get_treasury_data():

    if not DATABASE.exists():

        return pd.DataFrame()

    connection = get_connection()

    try:

        df = pd.read_sql_query(
            """
            SELECT *
            FROM treasury_bill_rates
            """,
            connection
        )

    except Exception:

        df = pd.DataFrame()

    connection.close()

    return df


def normalize_rate(
    value
):

    try:

        value = float(value)

    except Exception:

        return None

    if abs(value) > 1:

        return value / 100

    return value


def latest_rates():

    df = get_treasury_data()

    if df.empty:

        return {}

    columns = {
        str(column).lower():
            column
        for column in df.columns
    }

    tenor_col = (
        columns.get("tenor_days")
        or columns.get("tenor")
    )

    rate_col = (
        columns.get("rate")
        or columns.get("yield")
        or columns.get("yield_rate")
    )

    date_col = (
        columns.get("auction_date")
        or columns.get("date")
        or columns.get("auction")
    )

    if not tenor_col or not rate_col:

        return {}

    result = {}

    for tenor in [91, 182, 364]:

        rows = df[
            pd.to_numeric(
                df[tenor_col],
                errors="coerce"
            ) == tenor
        ].copy()

        if rows.empty:

            continue

        if date_col:

            rows["_date_sort"] = pd.to_datetime(
                rows[date_col],
                errors="coerce"
            )

            rows = rows.sort_values(
                "_date_sort"
            )

        row = rows.iloc[-1]

        rate = normalize_rate(
            row[rate_col]
        )

        if rate is None:

            continue

        auction_date = ""

        if date_col:

            auction_date = str(
                row[date_col]
            )

        result[tenor] = {
            "rate": rate,
            "date": auction_date
        }

    return result


# ============================================================
# SYSTEM STATUS
# ============================================================

def module_status():

    modules = [
        "pricing_engine.py",
        "cbk_pricing.py",
        "risk_engine.py",
        "portfolio_engine.py",
        "backtest_engine.py",
        "stress_engine.py",
    ]

    result = []

    for module in modules:

        path = BASE_DIR / module

        result.append({
            "Module": module,
            "Status":
                "ONLINE"
                if path.exists()
                else "MISSING"
        })

    return result


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title(
        "🇰🇪 Kenya Financial Analytics"
    )

    st.caption(
        "Quantitative Finance Command Center"
    )

    st.divider()

    st.subheader(
        "System"
    )

    if DATABASE.exists():

        st.success(
            "Database Online"
        )

    else:

        st.error(
            "Database Missing"
        )

    tables = get_tables()

    st.write(
        f"Database tables: **{len(tables)}**"
    )

    st.divider()

    st.caption(
        "Research and simulation platform"
    )

    st.caption(
        "No real trades are executed."
    )


# ============================================================
# HEADER
# ============================================================

st.title(
    "🇰🇪 Kenya Financial Analytics"
)

st.subheader(
    "Quantitative Finance Command Center"
)

st.caption(
    "CBK market data • Fixed income • Risk • Portfolio • "
    "Backtesting • Stress Testing"
)

st.divider()


# ============================================================
# MARKET DATA
# ============================================================

st.header(
    "🇰🇪 Kenyan Fixed-Income Market"
)

rates = latest_rates()


c1, c2, c3 = st.columns(3)


for column, tenor in zip(
    [c1, c2, c3],
    [91, 182, 364]
):

    with column:

        if tenor in rates:

            rate = rates[
                tenor
            ]["rate"]

            date = rates[
                tenor
            ]["date"]

            st.metric(
                f"{tenor}-Day T-Bill",
                f"{rate * 100:.4f}%"
            )

            if date:

                st.caption(
                    f"Latest auction: {date}"
                )

        else:

            st.metric(
                f"{tenor}-Day T-Bill",
                "No data"
            )


# ============================================================
# YIELD CURVE
# ============================================================

st.divider()

st.header(
    "Yield Curve"
)

if rates:

    curve_rows = []

    for tenor in [91, 182, 364]:

        if tenor in rates:

            curve_rows.append({
                "Tenor":
                    f"{tenor} Days",

                "Yield":
                    rates[tenor]["rate"] * 100,

                "Auction Date":
                    rates[tenor]["date"]
            })

    if curve_rows:

        curve_df = pd.DataFrame(
            curve_rows
        )

        curve_df = curve_df.set_index(
            "Tenor"
        )

        st.line_chart(
            curve_df["Yield"],
            use_container_width=True
        )

        display_df = pd.DataFrame(
            curve_rows
        )

        display_df["Yield"] = (
            display_df["Yield"]
            .map(
                lambda x:
                f"{x:.4f}%"
            )
        )

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True
        )

else:

    st.info(
        "No current Treasury Bill rates available."
    )


# ============================================================
# DATABASE OVERVIEW
# ============================================================

st.divider()

st.header(
    "Historical Data Engine"
)

if DATABASE.exists():

    treasury = get_treasury_data()

    c1, c2, c3 = st.columns(3)

    with c1:

        st.metric(
            "Database",
            "ONLINE"
        )

    with c2:

        st.metric(
            "Treasury Observations",
            f"{len(treasury):,}"
        )

    with c3:

        st.metric(
            "Database Tables",
            f"{len(tables):,}"
        )

    if not treasury.empty:

        st.subheader(
            "Recent CBK Observations"
        )

        st.dataframe(
            treasury.tail(10),
            use_container_width=True,
            hide_index=True
        )

else:

    st.error(
        "kenya_market.db was not found."
    )


# ============================================================
# ANALYTICS ENGINES
# ============================================================

st.divider()

st.header(
    "Analytics Engines"
)

status = module_status()

status_df = pd.DataFrame(
    status
)

c1, c2, c3 = st.columns(3)

online = sum(
    item["Status"] == "ONLINE"
    for item in status
)

total = len(status)

with c1:

    st.metric(
        "Engines Online",
        f"{online}/{total}"
    )

with c2:

    if online == total:

        st.success(
            "ALL SYSTEMS ONLINE"
        )

    else:

        st.warning(
            "PARTIAL SYSTEM"
        )

with c3:

    st.metric(
        "Checked",
        datetime.now().strftime(
            "%H:%M:%S"
        )
    )

st.dataframe(
    status_df,
    use_container_width=True,
    hide_index=True
)


# ============================================================
# MODULE MAP
# ============================================================

st.divider()

st.header(
    "Platform Modules"
)

module_columns = st.columns(3)

modules = [
    ("📊", "Market Data", "CBK Treasury Bill data"),
    ("📈", "Yield Curve", "Kenyan fixed-income curve"),
    ("💰", "Pricing", "T-Bills and government bonds"),
    ("🔢", "Options & Greeks", "Black-Scholes and simulation"),
    ("🛡️", "Risk Analysis", "VaR, volatility and drawdown"),
    ("💼", "Portfolio", "Allocation and portfolio risk"),
    ("🔬", "Backtesting", "Historical strategy testing"),
    ("⚠️", "Stress Testing", "CBK rate scenarios"),
    ("🗄️", "Historical Database", "Long-term market history"),
]

for index, item in enumerate(
    modules
):

    icon, title, description = item

    with module_columns[
        index % 3
    ]:

        st.markdown(
            f"""
            ### {icon} {title}

            {description}
            """
        )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Kenya Financial Analytics | "
    "Quantitative research and simulation platform | "
    "No real trades are executed."
)
