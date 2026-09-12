import math
import sqlite3
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

try:
    from scipy.stats import norm
except ImportError:
    norm = None

try:
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError:
    px = None
    go = None

st.set_page_config(
    page_title="Kenya Financial Analytics",
    page_icon="🇰🇪",
    layout="wide",
)

BASE = Path(__file__).resolve().parent
DB = BASE / "kenya_financial_analytics.db"

MODULES = [
    "Dashboard", "Kenyan Market", "Market Intelligence", "Yield Curve",
    "Treasury Bills", "Bond Pricing", "Options & Greeks", "Risk Analysis",
    "Risk Intelligence", "Historical Market Explorer", "Portfolio Intelligence",
    "Portfolio", "Research Intelligence", "Financial Reports",
    "Backtesting", "Stress Testing"
]

st.markdown("""
<style>
.block-container {max-width: 1500px; padding-top: 1.2rem;}
.kfa-title {font-size: 2.4rem; font-weight: 800;}
</style>
""", unsafe_allow_html=True)


def db():
    return sqlite3.connect(DB)


def init_db():
    con = db()
    con.execute("""
        CREATE TABLE IF NOT EXISTS market_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date TEXT,
            instrument TEXT,
            price REAL,
            yield REAL,
            volume REAL,
            source TEXT
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS treasury_bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            auction_date TEXT,
            tenor_days INTEGER,
            accepted_rate REAL,
            price REAL,
            amount_offered REAL,
            amount_accepted REAL,
            source TEXT
        )
    """)
    if con.execute("SELECT COUNT(*) FROM market_data").fetchone()[0] == 0:
        seed_market(con)
    if con.execute("SELECT COUNT(*) FROM treasury_bills").fetchone()[0] == 0:
        seed_bills(con)
    con.commit()
    con.close()


def seed_market(con):
    rng = np.random.default_rng(42)
    dates = pd.bdate_range(end=pd.Timestamp.today(), periods=300)
    instruments = {
        "NSE20": 1900.0,
        "NSE25": 4200.0,
        "USD/KES": 129.5,
        "EUR/KES": 150.0,
        "GBP/KES": 174.0,
        "10Y KENYA": 13.4,
    }
    rows = []
    for instrument, start in instruments.items():
        value = start
        for date in dates:
            value *= 1 + rng.normal(0, 0.006)
            value = max(value, 0.01)
            rows.append((
                date.strftime("%Y-%m-%d"),
                instrument,
                value,
                None,
                float(abs(rng.normal(1_000_000, 250_000))),
                "Local SQLite demo data",
            ))
    con.executemany("""
        INSERT INTO market_data
        (trade_date, instrument, price, yield, volume, source)
        VALUES (?, ?, ?, ?, ?, ?)
    """, rows)


def seed_bills(con):
    rng = np.random.default_rng(7)
    today = pd.Timestamp.today().normalize()
    rows = []
    for i in range(52):
        date = today - pd.Timedelta(days=7 * i)
        for tenor, base_rate in ((91, 14.0), (182, 14.4), (364, 15.0)):
            rate = float(base_rate + rng.normal(0, 0.18))
            price = 100 / (1 + rate / 100 * tenor / 365)
            offered = float(abs(rng.normal(30_000_000_000, 5_000_000_000)))
            accepted = float(offered * rng.uniform(0.65, 1.0))
            rows.append((
                date.strftime("%Y-%m-%d"), tenor, rate, price,
                offered, accepted, "Local SQLite demo data"
            ))
    con.executemany("""
        INSERT INTO treasury_bills
        (auction_date, tenor_days, accepted_rate, price,
         amount_offered, amount_accepted, source)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, rows)


def query_df(sql, params=()):
    con = db()
    try:
        cursor = con.execute(sql, params)
        rows = cursor.fetchall()
        columns = [item[0] for item in cursor.description] if cursor.description else []
        return pd.DataFrame.from_records(rows, columns=columns)
    finally:
        con.close()


def market(instrument=None):
    if instrument:
        data = query_df(
            "SELECT * FROM market_data WHERE instrument=? ORDER BY trade_date",
            (instrument,)
        )
    else:
        data = query_df("SELECT * FROM market_data ORDER BY trade_date")
    if not data.empty:
        data["trade_date"] = pd.to_datetime(data["trade_date"])
    return data


def bills():
    data = query_df(
        "SELECT * FROM treasury_bills ORDER BY auction_date DESC, tenor_days"
    )
    if not data.empty:
        data["auction_date"] = pd.to_datetime(data["auction_date"])
    return data


def normal_cdf(x):
    if norm is not None:
        return float(norm.cdf(x))
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def normal_pdf(x):
    if norm is not None:
        return float(norm.pdf(x))
    return math.exp(-x * x / 2) / math.sqrt(2 * math.pi)


def black_scholes(S, K, T, r, sigma, option):
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    if option == "Call":
        return S * normal_cdf(d1) - K * math.exp(-r * T) * normal_cdf(d2)
    return K * math.exp(-r * T) * normal_cdf(-d2) - S * normal_cdf(-d1)


def calculate_greeks(S, K, T, r, sigma, option):
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    if option == "Call":
        delta = normal_cdf(d1)
        theta = -(S * normal_pdf(d1) * sigma) / (2 * math.sqrt(T)) \
                - r * K * math.exp(-r * T) * normal_cdf(d2)
        rho = K * T * math.exp(-r * T) * normal_cdf(d2)
    else:
        delta = normal_cdf(d1) - 1
        theta = -(S * normal_pdf(d1) * sigma) / (2 * math.sqrt(T)) \
                + r * K * math.exp(-r * T) * normal_cdf(-d2)
        rho = -K * T * math.exp(-r * T) * normal_cdf(-d2)

    return {
        "Delta": delta,
        "Gamma": normal_pdf(d1) / (S * sigma * math.sqrt(T)),
        "Vega": S * normal_pdf(d1) * math.sqrt(T),
        "Theta": theta,
        "Rho": rho,
    }


def max_drawdown(series):
    series = pd.Series(series).dropna()
    if series.empty:
        return 0.0
    return float((series / series.cummax() - 1).min())


def show_line(data, x, y, title):
    if px is not None:
        st.plotly_chart(
            px.line(data, x=x, y=y, title=title),
            use_container_width=True
        )
    else:
        st.line_chart(data.set_index(x)[y])


def dashboard():
    st.markdown('<div class="kfa-title">🇰🇪 Kenya Financial Analytics</div>',
                unsafe_allow_html=True)
    st.caption("Kenyan quantitative-finance platform.")

    rows = []
    for instrument in ["NSE20", "NSE25", "USD/KES", "EUR/KES", "GBP/KES", "10Y KENYA"]:
        data = market(instrument)
        if len(data) >= 2:
            last = data.iloc[-1]
            previous = data.iloc[-2]
            rows.append({
                "Instrument": instrument,
                "Latest": last["price"],
                "Change %": (last["price"] / previous["price"] - 1) * 100,
                "Date": last["trade_date"].date(),
            })

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Market", "Kenya")
    c2.metric("Database", "SQLite")
    c3.metric("Risk Engine", "ONLINE")
    c4.metric("Quant Engine", "ONLINE")

    st.subheader("Market Snapshot")
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.subheader("Platform Modules")
    labels = [
        "🇰🇪 Kenyan Market", "💰 Treasury Bills", "🏦 Bond Pricing",
        "📈 Options & Greeks", "📊 Yield Curve", "💼 Portfolio Analytics",
        "⚠️ Risk Analysis", "🗃️ Historical Market Explorer",
        "🧠 Market Intelligence", "🔬 Backtesting", "💥 Stress Testing",
        "📄 Financial Reports"
    ]
    for i in range(0, len(labels), 3):
        cols = st.columns(3)
        for j, label in enumerate(labels[i:i + 3]):
            cols[j].info(label)

    st.success("System ready.")


def kenyan_market():
    st.title("🇰🇪 Kenyan Market")
    instrument = st.selectbox(
        "Instrument", ["NSE20", "NSE25", "USD/KES", "EUR/KES", "GBP/KES", "10Y KENYA"]
    )
    data = market(instrument)
    show_line(data, "trade_date", "price", f"{instrument} History")

    returns = data["price"].pct_change().dropna()
    a, b, c = st.columns(3)
    a.metric("Latest", f"{data['price'].iloc[-1]:,.4f}")
    b.metric("Annual Volatility", f"{returns.std() * math.sqrt(252) * 100:.2f}%")
    c.metric("Max Drawdown", f"{max_drawdown(data['price']) * 100:.2f}%")


def market_intelligence():
    st.title("🧠 Market Intelligence")
    rows = []
    for instrument in ["NSE20", "NSE25", "USD/KES", "EUR/KES", "GBP/KES"]:
        data = market(instrument)
        returns = data["price"].pct_change().dropna()
        change = (data["price"].iloc[-1] / data["price"].iloc[-2] - 1) * 100
        rows.append({
            "Instrument": instrument,
            "Latest": data["price"].iloc[-1],
            "Change %": change,
            "Volatility %": returns.std() * math.sqrt(252) * 100,
            "Signal": "POSITIVE" if change > 0.5 else "NEGATIVE" if change < -0.5 else "NEUTRAL",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def yield_curve():
    st.title("📊 Yield Curve")
    data = bills()
    latest = data["auction_date"].max()
    current = data[data["auction_date"] == latest].sort_values("tenor_days")

    st.dataframe(
        current[["tenor_days", "accepted_rate", "price",
                 "amount_offered", "amount_accepted"]],
        use_container_width=True,
        hide_index=True,
    )

    if px is not None:
        st.plotly_chart(
            px.line(current, x="tenor_days", y="accepted_rate",
                    markers=True, title="Treasury Bill Yield Curve"),
            use_container_width=True,
        )
    else:
        st.line_chart(current.set_index("tenor_days")["accepted_rate"])


def treasury_bills():
    st.title("💰 Treasury Bills")
    data = bills()
    tenor = st.selectbox("Tenor", sorted(data["tenor_days"].unique()))
    current = data[data["tenor_days"] == tenor].sort_values("auction_date")
    st.dataframe(current, use_container_width=True, hide_index=True)
    show_line(current, "auction_date", "accepted_rate",
              f"{tenor}-Day Treasury Bill Rate")


def bond_pricing():
    st.title("🏦 Bond Pricing")
    a, b = st.columns(2)

    face = a.number_input("Face Value (KES)", min_value=1.0, value=100000.0)
    coupon = a.number_input("Coupon (%)", min_value=0.0, value=12.0)
    years = b.number_input("Years", min_value=0.25, value=5.0)
    ytm = b.number_input("YTM (%)", min_value=0.0, value=13.0)
    frequency = b.selectbox("Coupon Frequency", [1, 2, 4], index=1)

    periods = max(1, round(years * frequency))
    coupon_payment = face * coupon / 100 / frequency
    rate = ytm / 100 / frequency
    price = sum(
        coupon_payment / (1 + rate) ** i for i in range(1, periods + 1)
    ) + face / (1 + rate) ** periods

    st.metric("Estimated Bond Price", f"KES {price:,.2f}")


def options_greeks():
    st.title("📈 Options & Greeks")
    a, b, c = st.columns(3)

    S = a.number_input("Spot Price", min_value=0.01, value=100.0)
    K = a.number_input("Strike Price", min_value=0.01, value=100.0)
    T = b.number_input("Maturity (years)", min_value=0.01, value=1.0)
    r = b.number_input("Risk-Free Rate (%)", value=13.0)
    sigma = c.number_input("Volatility (%)", min_value=0.1, value=20.0)
    option = c.selectbox("Option Type", ["Call", "Put"])

    price = black_scholes(S, K, T, r / 100, sigma / 100, option)
    greeks = calculate_greeks(S, K, T, r / 100, sigma / 100, option)

    st.metric(f"Black-Scholes {option}", f"{price:.6f}")
    cols = st.columns(5)
    for col, (name, value) in zip(cols, greeks.items()):
        col.metric(name, f"{value:.6f}")


def risk_analysis():
    st.title("⚠️ Risk Analysis")
    instrument = st.selectbox(
        "Instrument", ["NSE20", "NSE25", "USD/KES", "EUR/KES", "GBP/KES"]
    )
    value = st.number_input("Portfolio Value (KES)", min_value=1.0,
                            value=1_000_000.0)
    confidence = st.slider("VaR Confidence", 0.90, 0.99, 0.95, 0.01)

    data = market(instrument)
    returns = data["price"].pct_change().dropna()
    var = -returns.quantile(1 - confidence) * value

    a, b, c = st.columns(3)
    a.metric("Historical VaR", f"KES {var:,.2f}")
    b.metric("Annual Volatility", f"{returns.std() * math.sqrt(252) * 100:.2f}%")
    c.metric("Max Drawdown", f"{max_drawdown(data['price']) * 100:.2f}%")

    if px is not None:
        st.plotly_chart(
            px.histogram(returns, nbins=40, title="Daily Return Distribution"),
            use_container_width=True,
        )


def risk_intelligence():
    st.title("🛡️ Risk Intelligence")
    rows = []
    for instrument in ["NSE20", "NSE25", "USD/KES", "EUR/KES", "GBP/KES"]:
        data = market(instrument)
        returns = data["price"].pct_change().dropna()
        rows.append({
            "Instrument": instrument,
            "Volatility %": returns.std() * math.sqrt(252) * 100,
            "Max Drawdown %": max_drawdown(data["price"]) * 100,
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def historical_explorer():
    st.title("🗃️ Historical Market Explorer")
    instrument = st.selectbox(
        "Instrument",
        ["All", "NSE20", "NSE25", "USD/KES", "EUR/KES", "GBP/KES", "10Y KENYA"],
    )
    data = market(None if instrument == "All" else instrument)
    st.dataframe(data.tail(500), use_container_width=True, hide_index=True)
    st.download_button(
        "⬇️ Export CSV",
        data.to_csv(index=False),
        "kenya_market_history.csv",
        "text/csv",
    )


def portfolio_intelligence():
    st.title("💼 Portfolio Intelligence")
    rows = []
    for instrument in ["NSE20", "NSE25", "USD/KES", "EUR/KES", "GBP/KES"]:
        data = market(instrument)
        returns = data["price"].pct_change().dropna()
        rows.append({
            "Asset": instrument,
            "Return %": (data["price"].iloc[-1] / data["price"].iloc[0] - 1) * 100,
            "Volatility %": returns.std() * math.sqrt(252) * 100,
            "Max Drawdown %": max_drawdown(data["price"]) * 100,
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def portfolio():
    st.title("📁 Portfolio")
    assets = st.multiselect(
        "Assets",
        ["NSE20", "NSE25", "USD/KES", "EUR/KES", "GBP/KES"],
        ["NSE20", "NSE25"],
    )
    if not assets:
        st.info("Select at least one asset.")
        return

    rows = []
    default_weight = 100 / len(assets)
    for asset in assets:
        weight = st.number_input(
            f"{asset} weight (%)", min_value=0.0, max_value=100.0,
            value=default_weight, key=f"weight_{asset}"
        )
        rows.append({"Asset": asset, "Weight %": weight})

    result = pd.DataFrame(rows)
    st.dataframe(result, use_container_width=True, hide_index=True)
    st.metric("Total Weight", f"{result['Weight %'].sum():.2f}%")


def research_intelligence():
    st.title("🔬 Research Intelligence")
    instrument = st.selectbox(
        "Instrument", ["NSE20", "NSE25", "USD/KES", "EUR/KES", "GBP/KES"]
    )
    data = market(instrument).copy()
    data["MA20"] = data["price"].rolling(20).mean()
    data["MA60"] = data["price"].rolling(60).mean()

    if go is not None:
        fig = go.Figure()
        fig.add_scatter(x=data["trade_date"], y=data["price"], name="Price")
        fig.add_scatter(x=data["trade_date"], y=data["MA20"], name="MA20")
        fig.add_scatter(x=data["trade_date"], y=data["MA60"], name="MA60")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.line_chart(data.set_index("trade_date")[["price", "MA20", "MA60"]])


def financial_reports():
    st.title("📄 Financial Reports")
    snapshot = []
    for instrument in ["NSE20", "NSE25", "USD/KES", "EUR/KES", "GBP/KES"]:
        data = market(instrument)
        snapshot.append({
            "Instrument": instrument,
            "Latest": data["price"].iloc[-1],
            "Change %": (data["price"].iloc[-1] / data["price"].iloc[-2] - 1) * 100,
        })

    report = (
        "KENYA FINANCIAL ANALYTICS\n"
        f"Generated: {datetime.now().isoformat()}\n\n"
        "MARKET SNAPSHOT\n"
        + pd.DataFrame(snapshot).to_string(index=False)
    )

    st.text_area("Report", report, height=350)
    st.download_button(
        "⬇️ Download Report",
        report,
        "kenya_financial_report.txt",
        "text/plain",
    )


def backtesting():
    st.title("🔬 Backtesting")
    instrument = st.selectbox(
        "Instrument", ["NSE20", "NSE25", "USD/KES", "EUR/KES", "GBP/KES"]
    )
    short = st.slider("Short Moving Average", 5, 50, 20)
    long = st.slider("Long Moving Average", 30, 150, 60)

    if short >= long:
        st.warning("Short moving average must be smaller than long moving average.")
        return

    data = market(instrument).copy()
    data["short_ma"] = data["price"].rolling(short).mean()
    data["long_ma"] = data["price"].rolling(long).mean()
    data["return"] = data["price"].pct_change().fillna(0)
    data["signal"] = (data["short_ma"] > data["long_ma"]).astype(int)

    strategy = (1 + data["signal"].shift(1).fillna(0) * data["return"]).cumprod()
    buy_hold = (1 + data["return"]).cumprod()

    a, b = st.columns(2)
    a.metric("Strategy Return", f"{(strategy.iloc[-1] - 1) * 100:.2f}%")
    b.metric("Buy & Hold", f"{(buy_hold.iloc[-1] - 1) * 100:.2f}%")

    if px is not None:
        chart_data = pd.DataFrame({
            "Date": data["trade_date"],
            "Strategy": strategy,
            "Buy & Hold": buy_hold,
        })
        st.plotly_chart(
            px.line(chart_data, x="Date", y=["Strategy", "Buy & Hold"]),
            use_container_width=True,
        )


def stress_testing():
    st.title("💥 Stress Testing")
    value = st.number_input("Portfolio Value (KES)", min_value=1.0,
                            value=1_000_000.0)
    shock = st.slider("Market Shock (%)", -50.0, 50.0, -10.0, 1.0)

    a, b, c = st.columns(3)
    a.metric("Starting", f"KES {value:,.2f}")
    b.metric("P/L", f"KES {value * shock / 100:,.2f}")
    c.metric("Stressed Value", f"KES {value * (1 + shock / 100):,.2f}")

    shocks = pd.DataFrame({"Shock %": [-30, -20, -15, -10, -5, 0, 5, 10]})
    shocks["Portfolio Value"] = value * (1 + shocks["Shock %"] / 100)
    shocks["P/L"] = value * shocks["Shock %"] / 100
    st.dataframe(shocks, use_container_width=True, hide_index=True)


FUNCTIONS = {
    "Dashboard": dashboard,
    "Kenyan Market": kenyan_market,
    "Market Intelligence": market_intelligence,
    "Yield Curve": yield_curve,
    "Treasury Bills": treasury_bills,
    "Bond Pricing": bond_pricing,
    "Options & Greeks": options_greeks,
    "Risk Analysis": risk_analysis,
    "Risk Intelligence": risk_intelligence,
    "Historical Market Explorer": historical_explorer,
    "Portfolio Intelligence": portfolio_intelligence,
    "Portfolio": portfolio,
    "Research Intelligence": research_intelligence,
    "Financial Reports": financial_reports,
    "Backtesting": backtesting,
    "Stress Testing": stress_testing,
}


def main():
    init_db()

    if "refresh" not in st.session_state:
        st.session_state.refresh = 0

    with st.sidebar:
        st.markdown("## 🇰🇪 Navigation")

        if st.button("🔄 REFRESH", use_container_width=True):
            st.session_state.refresh += 1
            st.rerun()

        st.divider()
        selected = st.radio("Select Module", MODULES)
        st.divider()

        st.caption("SYSTEM STATUS")
        st.write("Database: **SQLite**")
        st.write("Quant Engine: **ONLINE**")
        st.write("Risk Engine: **ONLINE**")
        st.write("Refresh:", st.session_state.refresh)

    FUNCTIONS[selected]()

    st.divider()
    st.caption("Kenya Financial Analytics • Clean standalone build")


if __name__ == "__main__":
    main()
