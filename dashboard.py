# ============================================================
# KENYA FINANCIAL ANALYTICS
# CLEAN STANDALONE DASHBOARD
# Version 1.0
#
# This file is intentionally independent from app.py.
# It creates/uses its own SQLite database and contains
# the core analytics engines required by the dashboard.
# ============================================================

import os
import math
import sqlite3
from datetime import datetime, date, timedelta

import numpy as np
import pandas as pd
import streamlit as st

# Optional plotting
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except Exception:
    PLOTLY_AVAILABLE = False


# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Kenya Financial Analytics",
    page_icon="🇰🇪",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "kenya_market.db")


# ============================================================
# DATABASE
# ============================================================

def get_connection():
    """Create a SQLite connection."""
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def initialize_database():
    """Create all required database tables safely."""

    con = get_connection()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS market_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date TEXT NOT NULL,
            instrument TEXT NOT NULL,
            price REAL,
            yield REAL,
            volume REAL,
            source TEXT DEFAULT 'LOCAL',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS treasury_bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            auction_date TEXT,
            tenor_days INTEGER,
            accepted_rate REAL,
            amount_offered REAL,
            amount_accepted REAL,
            source TEXT DEFAULT 'CBK'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bonds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            maturity TEXT,
            coupon REAL,
            face_value REAL,
            market_price REAL,
            yield REAL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset TEXT,
            quantity REAL,
            price REAL,
            weight REAL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_date TEXT,
            report_type TEXT,
            content TEXT
        )
    """)

    con.commit()
    con.close()


# Always initialize safely
initialize_database()


# ============================================================
# DATABASE HELPERS
# ============================================================

def execute_query(sql, params=()):
    con = get_connection()
    try:
        return pd.read_sql_query(sql, con, params=params)
    finally:
        con.close()


def execute_write(sql, params=()):
    con = get_connection()
    try:
        con.execute(sql, params)
        con.commit()
    finally:
        con.close()


def insert_market_data(trade_date, instrument, price, yield_value,
                       volume=0, source="LOCAL"):

    execute_write(
        """
        INSERT INTO market_data
        (trade_date, instrument, price, yield, volume, source)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            str(trade_date),
            instrument,
            float(price),
            float(yield_value),
            float(volume),
            source,
        ),
    )


# ============================================================
# DEMO / LOCAL KENYAN MARKET DATA
# ============================================================

def seed_market_data():

    existing = execute_query(
        "SELECT COUNT(*) AS n FROM market_data"
    )

    if int(existing.iloc[0]["n"]) > 0:
        return

    rng = np.random.default_rng(42)

    instruments = {
        "NSE 20 Share Index": 1850,
        "NSE All Share Index": 145,
        "USD/KES": 129,
        "EUR/KES": 150,
        "GBP/KES": 175,
        "KES/USD": 1 / 129,
    }

    today = date.today()

    for instrument, base in instruments.items():

        price = float(base)

        for i in range(365):

            trade_day = today - timedelta(days=364 - i)

            if trade_day.weekday() >= 5:
                continue

            shock = rng.normal(0, 0.008)

            price = max(
                0.01,
                price * (1 + shock)
            )

            yld = 0.0

            if "KES" in instrument or "Index" not in instrument:
                yld = max(
                    0,
                    8 + rng.normal(0, 0.5)
                )

            insert_market_data(
                trade_day,
                instrument,
                price,
                yld,
                rng.integers(1000, 100000),
                "LOCAL DEMO"
            )


def seed_treasury_data():

    existing = execute_query(
        "SELECT COUNT(*) AS n FROM treasury_bills"
    )

    if int(existing.iloc[0]["n"]) > 0:
        return

    data = [
        (date.today(), 91, 15.20, 10000000000, 8500000000),
        (date.today(), 182, 15.65, 10000000000, 9200000000),
        (date.today(), 364, 16.10, 10000000000, 9700000000),
    ]

    for row in data:

        execute_write(
            """
            INSERT INTO treasury_bills
            (auction_date, tenor_days, accepted_rate,
             amount_offered, amount_accepted, source)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(row[0]),
                row[1],
                row[2],
                row[3],
                row[4],
                "LOCAL DEMO / CBK STRUCTURE",
            )
        )


def seed_bonds():

    existing = execute_query(
        "SELECT COUNT(*) AS n FROM bonds"
    )

    if int(existing.iloc[0]["n"]) > 0:
        return

    data = [
        ("KENYA 2027", "2027-06-15", 10.50, 100, 98.20, 11.10),
        ("KENYA 2030", "2030-07-01", 12.00, 100, 96.50, 12.55),
        ("KENYA 2034", "2034-02-15", 13.50, 100, 101.20, 13.20),
        ("KENYA 2040", "2040-08-20", 12.75, 100, 94.10, 13.80),
    ]

    for row in data:

        execute_write(
            """
            INSERT INTO bonds
            (name, maturity, coupon, face_value,
             market_price, yield)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            row
        )


seed_market_data()
seed_treasury_data()
seed_bonds()


# ============================================================
# FINANCIAL MATHEMATICS
# ============================================================

def normal_cdf(x):
    return 0.5 * (
        1 + math.erf(x / math.sqrt(2))
    )


def normal_pdf(x):
    return (
        math.exp(-0.5 * x * x)
        / math.sqrt(2 * math.pi)
    )


def black_scholes(
    S,
    K,
    T,
    r,
    sigma,
    option_type="Call"
):

    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        return np.nan

    d1 = (
        math.log(S / K)
        + (r + 0.5 * sigma ** 2) * T
    ) / (sigma * math.sqrt(T))

    d2 = d1 - sigma * math.sqrt(T)

    if option_type.lower() == "call":

        return (
            S * normal_cdf(d1)
            - K * math.exp(-r * T)
            * normal_cdf(d2)
        )

    return (
        K * math.exp(-r * T)
        * normal_cdf(-d2)
        - S * normal_cdf(-d1)
    )


def option_greeks(
    S,
    K,
    T,
    r,
    sigma,
    option_type="Call"
):

    d1 = (
        math.log(S / K)
        + (r + 0.5 * sigma ** 2) * T
    ) / (sigma * math.sqrt(T))

    d2 = d1 - sigma * math.sqrt(T)

    pdf = normal_pdf(d1)

    is_call = option_type.lower() == "call"

    if is_call:

        delta = normal_cdf(d1)

        theta = (
            -S * pdf * sigma
            / (2 * math.sqrt(T))
            - r * K * math.exp(-r * T)
            * normal_cdf(d2)
        )

        rho = (
            K * T
            * math.exp(-r * T)
            * normal_cdf(d2)
        )

    else:

        delta = normal_cdf(d1) - 1

        theta = (
            -S * pdf * sigma
            / (2 * math.sqrt(T))
            + r * K * math.exp(-r * T)
            * normal_cdf(-d2)
        )

        rho = (
            -K * T
            * math.exp(-r * T)
            * normal_cdf(-d2)
        )

    gamma = pdf / (
        S * sigma * math.sqrt(T)
    )

    vega = (
        S * pdf * math.sqrt(T)
    )

    return {
        "Delta": delta,
        "Gamma": gamma,
        "Vega": vega,
        "Theta": theta,
        "Rho": rho,
    }


def bond_price(
    face,
    coupon_rate,
    yield_rate,
    years,
    frequency=2
):

    periods = max(
        1,
        int(round(years * frequency))
    )

    coupon = face * coupon_rate / frequency
    y = yield_rate / frequency

    price = 0

    for t in range(1, periods + 1):

        price += coupon / (
            (1 + y) ** t
        )

    price += face / (
        (1 + y) ** periods
    )

    return price


def treasury_bill_price(
    face,
    annual_yield,
    days
):

    return face / (
        1 + annual_yield * days / 365
    )


# ============================================================
# RISK ENGINE
# ============================================================

def calculate_var(returns, confidence=0.95):

    if len(returns) < 2:
        return np.nan

    return -np.percentile(
        returns,
        (1 - confidence) * 100
    )


def calculate_max_drawdown(values):

    values = np.asarray(values)

    if len(values) == 0:
        return np.nan

    running_max = np.maximum.accumulate(values)

    drawdown = (
        values - running_max
    ) / running_max

    return abs(drawdown.min())


def calculate_sharpe(returns, risk_free=0):

    if len(returns) < 2:
        return np.nan

    excess = returns - risk_free

    if excess.std() == 0:
        return np.nan

    return (
        excess.mean()
        / excess.std()
        * math.sqrt(252)
    )


# ============================================================
# PAGE FUNCTIONS
# ============================================================

def dashboard_page():

    st.title("🇰🇪 Kenya Financial Analytics")

    st.caption(
        "Quantitative Finance Research & Analytics Platform"
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Market", "KENYA")
    c2.metric("Database", "SQLite")
    c3.metric("Risk Engine", "ONLINE")
    c4.metric("Quant Engine", "ONLINE")

    st.divider()

    st.subheader("Platform Modules")

    modules = [
        ("🇰🇪", "Kenyan Market"),
        ("💰", "Treasury Bills"),
        ("🏦", "Bond Pricing"),
        ("📈", "Options & Greeks"),
        ("📊", "Yield Curve"),
        ("💼", "Portfolio Analytics"),
        ("⚠️", "Risk Analysis"),
        ("🗄️", "Historical Market Explorer"),
        ("🧠", "Market Intelligence"),
        ("🔬", "Backtesting"),
        ("💥", "Stress Testing"),
        ("📄", "Financial Reports"),
    ]

    cols = st.columns(3)

    for i, (icon, name) in enumerate(modules):

        with cols[i % 3]:

            st.info(
                f"{icon} **{name}**"
            )

    st.success(
        "System ready. Database and quantitative engines are online."
    )


def kenya_market_page():

    st.title("🇰🇪 Kenyan Market")

    df = execute_query(
        """
        SELECT *
        FROM market_data
        ORDER BY trade_date
        """
    )

    if df.empty:

        st.warning("No market data available.")
        return

    instruments = sorted(
        df["instrument"].unique()
    )

    selected = st.selectbox(
        "Instrument",
        instruments
    )

    data = df[
        df["instrument"] == selected
    ].copy()

    data["trade_date"] = pd.to_datetime(
        data["trade_date"]
    )

    latest = data.iloc[-1]

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Latest Price",
        f"{latest['price']:,.4f}"
    )

    c2.metric(
        "Yield",
        f"{latest['yield']:.2f}%"
    )

    c3.metric(
        "Volume",
        f"{latest['volume']:,.0f}"
    )

    if PLOTLY_AVAILABLE:

        fig = px.line(
            data,
            x="trade_date",
            y="price",
            title=f"{selected} Historical Price"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    st.dataframe(
        data.tail(50),
        use_container_width=True
    )


def treasury_page():

    st.title("💰 Treasury Bills")

    df = execute_query(
        """
        SELECT *
        FROM treasury_bills
        ORDER BY tenor_days
        """
    )

    st.dataframe(
        df,
        use_container_width=True
    )

    st.subheader("T-Bill Calculator")

    c1, c2, c3 = st.columns(3)

    with c1:
        face = st.number_input(
            "Face Value (KES)",
            min_value=1000.0,
            value=100000.0
        )

    with c2:
        rate = st.number_input(
            "Annual Yield (%)",
            min_value=0.0,
            value=15.20
        )

    with c3:
        days = st.number_input(
            "Days",
            min_value=1,
            value=91
        )

    price = treasury_bill_price(
        face,
        rate / 100,
        days
    )

    st.metric(
        "Purchase Price",
        f"KES {price:,.2f}"
    )

    st.metric(
        "Discount / Return",
        f"KES {face - price:,.2f}"
    )


def bond_page():

    st.title("🏦 Bond Pricing")

    st.subheader("Kenyan Bond Calculator")

    c1, c2, c3 = st.columns(3)

    with c1:
        face = st.number_input(
            "Face Value",
            value=100000.0
        )

    with c2:
        coupon = st.number_input(
            "Coupon Rate (%)",
            value=12.0
        )

    with c3:
        years = st.number_input(
            "Years to Maturity",
            value=5.0
        )

    y = st.number_input(
        "Required Yield (%)",
        value=13.0
    )

    price = bond_price(
        face,
        coupon / 100,
        y / 100,
        years
    )

    st.metric(
        "Estimated Bond Price",
        f"KES {price:,.2f}"
    )

    bonds = execute_query(
        "SELECT * FROM bonds"
    )

    st.subheader("Kenyan Bond Database")

    st.dataframe(
        bonds,
        use_container_width=True
    )


def options_page():

    st.title("📈 Options & Greeks")

    c1, c2, c3 = st.columns(3)

    with c1:
        S = st.number_input(
            "Underlying Price",
            value=100.0
        )

    with c2:
        K = st.number_input(
            "Strike Price",
            value=100.0
        )

    with c3:
        T = st.number_input(
            "Time to Expiry (Years)",
            min_value=0.01,
            value=1.0
        )

    c4, c5, c6 = st.columns(3)

    with c4:
        r = st.number_input(
            "Risk-Free Rate (%)",
            value=10.0
        )

    with c5:
        sigma = st.number_input(
            "Volatility (%)",
            min_value=0.01,
            value=20.0
        )

    with c6:
        option_type = st.selectbox(
            "Option Type",
            ["Call", "Put"]
        )

    rate = r / 100
    volatility = sigma / 100

    price = black_scholes(
        S,
        K,
        T,
        rate,
        volatility,
        option_type
    )

    st.metric(
        f"Black-Scholes {option_type}",
        f"{price:,.4f}"
    )

    greeks = option_greeks(
        S,
        K,
        T,
        rate,
        volatility,
        option_type
    )

    st.subheader("Greeks")

    cols = st.columns(5)

    for col, (name, value) in zip(
        cols,
        greeks.items()
    ):

        col.metric(
            name,
            f"{value:.6f}"
        )


def yield_curve_page():

    st.title("📊 Kenya Yield Curve")

    data = execute_query(
        """
        SELECT tenor_days, accepted_rate
        FROM treasury_bills
        ORDER BY tenor_days
        """
    )

    if data.empty:
        st.warning("No yield data.")
        return

    if PLOTLY_AVAILABLE:

        fig = px.line(
            data,
            x="tenor_days",
            y="accepted_rate",
            markers=True,
            title="Treasury Bill Yield Curve"
        )

        fig.update_xaxes(
            title="Tenor (Days)"
        )

        fig.update_yaxes(
            title="Yield (%)"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    st.dataframe(
        data,
        use_container_width=True
    )


def portfolio_page():

    st.title("💼 Portfolio Analytics")

    st.subheader("Build Portfolio")

    assets = [
        "NSE 20 Share Index",
        "NSE All Share Index",
        "Treasury Bills",
        "Kenya Government Bonds",
        "USD/KES",
    ]

    portfolio = []

    for asset in assets:

        weight = st.slider(
            f"{asset} Weight (%)",
            0.0,
            100.0,
            0.0,
            1.0
        )

        if weight > 0:

            portfolio.append(
                {
                    "Asset": asset,
                    "Weight": weight
                }
            )

    if not portfolio:

        st.info(
            "Select portfolio weights above."
        )
        return

    p = pd.DataFrame(portfolio)

    total = p["Weight"].sum()

    p["Normalized Weight"] = (
        p["Weight"] / total
    )

    st.dataframe(
        p,
        use_container_width=True
    )

    st.metric(
        "Total Allocated",
        f"{total:.2f}%"
    )


def risk_page():

    st.title("⚠️ Risk Analysis")

    df = execute_query(
        """
        SELECT trade_date, price
        FROM market_data
        WHERE instrument='NSE 20 Share Index'
        ORDER BY trade_date
        """
    )

    if len(df) < 2:

        st.warning(
            "Insufficient historical data."
        )
        return

    returns = df["price"].pct_change().dropna()

    var = calculate_var(
        returns,
        0.95
    )

    drawdown = calculate_max_drawdown(
        df["price"].values
    )

    sharpe = calculate_sharpe(
        returns
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "95% Daily VaR",
        f"{var * 100:.2f}%"
    )

    c2.metric(
        "Maximum Drawdown",
        f"{drawdown * 100:.2f}%"
    )

    c3.metric(
        "Sharpe Ratio",
        f"{sharpe:.2f}"
    )

    if PLOTLY_AVAILABLE:

        temp = df.copy()

        temp["trade_date"] = pd.to_datetime(
            temp["trade_date"]
        )

        temp["Returns"] = (
            temp["price"].pct_change()
        )

        fig = px.line(
            temp,
            x="trade_date",
            y="Returns",
            title="Historical Returns"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


def historical_page():

    st.title("🗄️ Historical Market Explorer")

    df = execute_query(
        """
        SELECT *
        FROM market_data
        ORDER BY trade_date DESC
        """
    )

    if df.empty:

        st.warning(
            "Historical database is empty."
        )
        return

    instruments = sorted(
        df["instrument"].unique()
    )

    selected = st.multiselect(
        "Select Instruments",
        instruments,
        default=instruments[:1]
    )

    if selected:

        filtered = df[
            df["instrument"].isin(selected)
        ]

    else:

        filtered = df

    start = st.date_input(
        "Start Date",
        value=date.today() - timedelta(days=90)
    )

    end = st.date_input(
        "End Date",
        value=date.today()
    )

    filtered = filtered[
        (pd.to_datetime(
            filtered["trade_date"]
        ).dt.date >= start)
        &
        (pd.to_datetime(
            filtered["trade_date"]
        ).dt.date <= end)
    ]

    st.dataframe(
        filtered,
        use_container_width=True
    )

    csv = filtered.to_csv(
        index=False
    )

    st.download_button(
        "Download Historical Data",
        csv,
        "kenya_historical_market_data.csv",
        "text/csv"
    )


def intelligence_page():

    st.title("🧠 Market Intelligence")

    df = execute_query(
        """
        SELECT *
        FROM market_data
        ORDER BY trade_date
        """
    )

    if df.empty:

        st.warning(
            "No market data available."
        )
        return

    st.subheader(
        "Automated Market Observations"
    )

    for instrument in df["instrument"].unique():

        data = df[
            df["instrument"] == instrument
        ].copy()

        if len(data) < 2:
            continue

        first = data.iloc[0]["price"]
        last = data.iloc[-1]["price"]

        change = (
            (last - first)
            / first
            * 100
        )

        if change > 5:

            st.success(
                f"📈 {instrument}: "
                f"up {change:.2f}% over the selected history."
            )

        elif change < -5:

            st.error(
                f"📉 {instrument}: "
                f"down {abs(change):.2f}% over the selected history."
            )

        else:

            st.info(
                f"➡️ {instrument}: "
                f"relatively stable at {change:.2f}%."
            )


def backtesting_page():

    st.title("🔬 Backtesting")

    df = execute_query(
        """
        SELECT trade_date, price
        FROM market_data
        WHERE instrument='NSE 20 Share Index'
        ORDER BY trade_date
        """
    )

    if len(df) < 50:

        st.warning(
            "Not enough historical data."
        )
        return

    short_window = st.slider(
        "Short Moving Average",
        5,
        50,
        20
    )

    long_window = st.slider(
        "Long Moving Average",
        20,
        200,
        50
    )

    if short_window >= long_window:

        st.warning(
            "Short window must be smaller."
        )
        return

    data = df.copy()

    data["Short MA"] = (
        data["price"]
        .rolling(short_window)
        .mean()
    )

    data["Long MA"] = (
        data["price"]
        .rolling(long_window)
        .mean()
    )

    data["Signal"] = np.where(
        data["Short MA"]
        > data["Long MA"],
        1,
        0
    )

    data["Market Return"] = (
        data["price"]
        .pct_change()
        .fillna(0)
    )

    data["Strategy Return"] = (
        data["Signal"].shift(1)
        .fillna(0)
        * data["Market Return"]
    )

    cumulative_market = (
        1 + data["Market Return"]
    ).cumprod()

    cumulative_strategy = (
        1 + data["Strategy Return"]
    ).cumprod()

    c1, c2 = st.columns(2)

    c1.metric(
        "Buy & Hold",
        f"{(cumulative_market.iloc[-1] - 1) * 100:.2f}%"
    )

    c2.metric(
        "Strategy",
        f"{(cumulative_strategy.iloc[-1] - 1) * 100:.2f}%"
    )

    if PLOTLY_AVAILABLE:

        chart = pd.DataFrame({
            "Date": pd.to_datetime(
                data["trade_date"]
            ),
            "Buy & Hold": cumulative_market,
            "Strategy": cumulative_strategy,
        })

        fig = px.line(
            chart,
            x="Date",
            y=["Buy & Hold", "Strategy"],
            title="Backtest Performance"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


def stress_page():

    st.title("💥 Stress Testing")

    st.write(
        "Apply hypothetical shocks to a portfolio or market price."
    )

    current_value = st.number_input(
        "Portfolio Value (KES)",
        min_value=0.0,
        value=1000000.0
    )

    shock = st.slider(
        "Market Shock (%)",
        -50.0,
        50.0,
        -10.0,
        1.0
    )

    stressed_value = (
        current_value
        * (1 + shock / 100)
    )

    loss = (
        current_value
        - stressed_value
    )

    c1, c2 = st.columns(2)

    c1.metric(
        "Stressed Portfolio",
        f"KES {stressed_value:,.2f}"
    )

    c2.metric(
        "Profit / Loss",
        f"KES {(-loss):,.2f}"
    )

    st.subheader(
        "Scenario Table"
    )

    scenarios = []

    for s in [-30, -20, -10, -5, 0, 5, 10, 20, 30]:

        value = current_value * (
            1 + s / 100
        )

        scenarios.append({
            "Shock (%)": s,
            "Portfolio Value": value,
            "P/L": value - current_value
        })

    st.dataframe(
        pd.DataFrame(scenarios),
        use_container_width=True
    )


def reports_page():

    st.title("📄 Financial Reports")

    st.subheader(
        "Generate Platform Report"
    )

    market_count = execute_query(
        "SELECT COUNT(*) AS n FROM market_data"
    ).iloc[0]["n"]

    bond_count = execute_query(
        "SELECT COUNT(*) AS n FROM bonds"
    ).iloc[0]["n"]

    tbill_count = execute_query(
        "SELECT COUNT(*) AS n FROM treasury_bills"
    ).iloc[0]["n"]

    report = f"""
KENYA FINANCIAL ANALYTICS
QUANTITATIVE FINANCE REPORT
====================================

Report Date:
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

DATABASE
--------
Market Records: {market_count}
Treasury Bill Records: {tbill_count}
Bond Records: {bond_count}

SYSTEM STATUS
-------------
Database: ONLINE
Quant Engine: ONLINE
Risk Engine: ONLINE
Historical Database: ONLINE

MODULES
-------
Kenyan Market
Treasury Bills
Bond Pricing
Options & Greeks
Yield Curve
Portfolio Analytics
Risk Analysis
Historical Market Explorer
Market Intelligence
Backtesting
Stress Testing

NOTE
----
Market data shown as LOCAL/DEMO data unless
connected to a verified external source.
"""

    st.text_area(
        "Generated Report",
        report,
        height=450
    )

    st.download_button(
        "Download Report",
        report,
        "kenya_financial_report.txt",
        "text/plain"
    )


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🇰🇪 Kenya Financial Analytics")

st.sidebar.caption(
    "Quantitative Finance Platform"
)

if st.sidebar.button(
    "🔄 REFRESH DATA",
    use_container_width=True
):

    st.cache_data.clear()
    st.rerun()


pages = {
    "Dashboard": dashboard_page,
    "Kenyan Market": kenya_market_page,
    "Treasury Bills": treasury_page,
    "Bond Pricing": bond_page,
    "Options & Greeks": options_page,
    "Yield Curve": yield_curve_page,
    "Portfolio": portfolio_page,
    "Risk Analysis": risk_page,
    "Historical Market Explorer": historical_page,
    "Market Intelligence": intelligence_page,
    "Backtesting": backtesting_page,
    "Stress Testing": stress_page,
    "Financial Reports": reports_page,
}

selection = st.sidebar.radio(
    "Navigation",
    list(pages.keys())
)


# ============================================================
# SYSTEM STATUS
# ============================================================

st.sidebar.divider()

st.sidebar.subheader(
    "SYSTEM STATUS"
)

st.sidebar.success(
    "Database: ONLINE"
)

st.sidebar.success(
    "Quant Engine: ONLINE"
)

st.sidebar.success(
    "Risk Engine: ONLINE"
)

st.sidebar.success(
    "Historical DB: ONLINE"
)

st.sidebar.info(
    "Jarvis Dependency: NONE"
)


# ============================================================
# RUN PAGE
# ============================================================

try:

    pages[selection]()

except Exception as error:

    st.error(
        "The selected module encountered an error."
    )

    st.exception(error)


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Kenya Financial Analytics | Quantitative Finance Platform | "
    "Kenyan Market Focus"
)