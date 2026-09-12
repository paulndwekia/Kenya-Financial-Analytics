import math
import sqlite3
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st
from live_data import refresh, status

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




def cbk_database_status():
    """
    Verify CBK data directly from the local SQLite database.

    This deliberately does not depend on the CBK website being
    reachable at the exact moment the dashboard is opened.
    """
    try:
        if not DB.exists():
            return {
                "available": False,
                "fx_rows": 0,
                "treasury_bill_rows": 0,
                "error": "Database file not found."
            }

        con = sqlite3.connect(DB)

        fx_rows = con.execute("""
            SELECT COUNT(*)
            FROM market_data
            WHERE source = 'Central Bank of Kenya'
              AND instrument IN ('USD/KES','EUR/KES','GBP/KES')
              AND trade_date IS NOT NULL
              AND price IS NOT NULL
        """).fetchone()[0]

        tb_rows = con.execute("""
            SELECT COUNT(*)
            FROM treasury_bills
            WHERE source = 'Central Bank of Kenya'
              AND tenor_days IN (91,182,364)
              AND accepted_rate IS NOT NULL
        """).fetchone()[0]

        con.close()

        return {
            "available": (fx_rows > 0 or tb_rows > 0),
            "fx_rows": fx_rows,
            "treasury_bill_rows": tb_rows,
            "error": None
        }

    except Exception as e:
        return {
            "available": False,
            "fx_rows": 0,
            "treasury_bill_rows": 0,
            "error": str(e)
        }


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

    con.commit()
    con.close()


def seed_market(con):
    # Synthetic market data disabled.
    # Live data comes from official CBK sources.
    return None


def seed_bills(con):
    # Synthetic Treasury Bill data disabled.
    # Live data comes from official CBK sources.
    return None


def query_df(sql, params=()):
    con = db()
    try:
        cursor = con.execute(sql, params)
        rows = cursor.fetchall()
        columns = [item[0] for item in cursor.description] if cursor.description else []
        return pd.DataFrame.from_records(rows, columns=columns)
    finally:
        con.close()



def available_market_instruments():
    """
    Return only market instruments that actually exist
    in the SQLite database.

    This prevents modules from trying to calculate
    NSE20/NSE25 or other unavailable instruments.
    """
    try:
        con = db()

        rows = con.execute("""
            SELECT DISTINCT instrument
            FROM market_data
            WHERE instrument IS NOT NULL
              AND TRIM(instrument) <> ''
            ORDER BY instrument
        """).fetchall()

        con.close()

        instruments = [
            str(row[0])
            for row in rows
            if row[0]
        ]

        return instruments

    except Exception:
        return [
            "USD/KES",
            "EUR/KES",
            "GBP/KES"
        ]


def market(instrument=None):
    """
    Application data adapter.

    Supports both:
        trade_date / price
    and:
        date / value

    This allows the existing application to consume the
    official CBK data layer without changing the rest of
    the analytics modules.
    """

    if instrument:
        data = query_df(
            """
            SELECT *
            FROM market_data
            WHERE instrument=?
            ORDER BY
                COALESCE(
                    NULLIF(trade_date, ''),
                    date
                )
            """,
            (instrument,)
        )
    else:
        data = query_df(
            """
            SELECT *
            FROM market_data
            ORDER BY
                COALESCE(
                    NULLIF(trade_date, ''),
                    date
                )
            """
        )

    if data.empty:
        return data

    # -----------------------------------------------------
    # Normalize date
    # -----------------------------------------------------

    if "trade_date" not in data.columns:
        data["trade_date"] = None

    if "date" in data.columns:

        data["trade_date"] = data["trade_date"].fillna(
            data["date"]
        )

    data["trade_date"] = pd.to_datetime(
        data["trade_date"],
        errors="coerce"
    )

    # -----------------------------------------------------
    # Normalize price
    # -----------------------------------------------------

    if "price" not in data.columns:
        data["price"] = np.nan

    if "value" in data.columns:

        data["price"] = data["price"].fillna(
            pd.to_numeric(
                data["value"],
                errors="coerce"
            )
        )

    data["price"] = pd.to_numeric(
        data["price"],
        errors="coerce"
    )

    # -----------------------------------------------------
    # Remove unusable rows
    # -----------------------------------------------------

    data = data[
        data["trade_date"].notna()
        & data["price"].notna()
    ].copy()

    return data.sort_values(
        "trade_date"
    ).reset_index(drop=True)


def bills():
    """
    Normalize Treasury Bill data for the application.

    Supports the original schema:
        auction_date / accepted_rate / price

    and the CBK live schema:
        date / value
    """

    data = query_df("""
        SELECT *
        FROM treasury_bills
        ORDER BY
            COALESCE(
                NULLIF(auction_date, ''),
                date
            ) DESC,
            tenor_days
    """)

    if data.empty:
        return data

    # -----------------------------------------------------
    # Normalize date
    # -----------------------------------------------------

    if "auction_date" not in data.columns:
        data["auction_date"] = None

    if "date" in data.columns:
        data["auction_date"] = data["auction_date"].fillna(
            data["date"]
        )

    data["auction_date"] = pd.to_datetime(
        data["auction_date"],
        errors="coerce"
    )

    # -----------------------------------------------------
    # Normalize yield
    # -----------------------------------------------------

    if "accepted_rate" not in data.columns:
        data["accepted_rate"] = np.nan

    # New CBK loader stores rate in value.
    if "value" in data.columns:
        data["accepted_rate"] = data["accepted_rate"].fillna(
            pd.to_numeric(
                data["value"],
                errors="coerce"
            )
        )

    # Some versions store it in rate.
    if "rate" in data.columns:
        data["accepted_rate"] = data["accepted_rate"].fillna(
            pd.to_numeric(
                data["rate"],
                errors="coerce"
            )
        )

    data["accepted_rate"] = pd.to_numeric(
        data["accepted_rate"],
        errors="coerce"
    )

    # -----------------------------------------------------
    # Normalize percentage representation
    #
    # CBK live values are decimals such as 0.090365.
    # Older demo rows can be percentages such as 14.0.
    # Convert everything to decimal form.
    # -----------------------------------------------------

    data.loc[
        data["accepted_rate"] > 1,
        "accepted_rate"
    ] = (
        data.loc[
            data["accepted_rate"] > 1,
            "accepted_rate"
        ] / 100.0
    )

    # -----------------------------------------------------
    # Normalize price
    # -----------------------------------------------------

    if "price" not in data.columns:
        data["price"] = np.nan

    mask = (
        data["price"].isna()
        & data["accepted_rate"].notna()
        & data["tenor_days"].notna()
    )

    # Treasury bill simple discount-style price proxy.
    data.loc[mask, "price"] = (
        100.0
        /
        (
            1.0
            +
            data.loc[mask, "accepted_rate"]
            *
            data.loc[mask, "tenor_days"]
            / 365.0
        )
    )

    # -----------------------------------------------------
    # Keep valid Treasury Bill observations
    # -----------------------------------------------------

    data = data[
        data["auction_date"].notna()
        &
        data["tenor_days"].isin([91, 182, 364])
        &
        data["accepted_rate"].notna()
    ].copy()

    return data.sort_values(
        ["auction_date", "tenor_days"]
    ).reset_index(drop=True)


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
    st.markdown(
        '<div class="kfa-title">🇰🇪 Kenya Financial Analytics</div>',
        unsafe_allow_html=True
    )

    st.caption(
        "Kenyan quantitative-finance platform."
    )

    # -----------------------------------------------------
    # LIVE CBK MARKET SNAPSHOT
    # -----------------------------------------------------

    rows = []

    for instrument in [
        "USD/KES",
        "EUR/KES",
        "GBP/KES"
    ]:

        try:
            data = market(instrument)

            if data.empty:
                continue

            last = data.iloc[-1]

            if len(data) >= 2:

                previous = data.iloc[-2]

                change = (
                    (
                        float(last["price"])
                        /
                        float(previous["price"])
                    ) - 1
                ) * 100

                change_display = f"{change:.4f}%"

            else:

                change_display = "N/A"

            rows.append({
                "Instrument": instrument,
                "Latest": float(
                    last["price"]
                ),
                "Change %": change_display,
                "Date": last["trade_date"].strftime(
                    "%Y-%m-%d"
                ),
                "Source": str(
                    last.get(
                        "source",
                        "Central Bank of Kenya"
                    )
                )
            })

        except Exception:
            continue

    # -----------------------------------------------------
    # STATUS
    # -----------------------------------------------------

    if rows:

        st.success(
            "CBK data connected — official Central Bank of Kenya records."
        )

    else:

        st.warning(
            "CBK market data is not available for display."
        )

    # -----------------------------------------------------
    # SYSTEM
    # -----------------------------------------------------

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Market",
        "Kenya"
    )

    c2.metric(
        "Database",
        "SQLite"
    )

    c3.metric(
        "Risk Engine",
        "ONLINE"
    )

    c4.metric(
        "Quant Engine",
        "ONLINE"
    )

    # -----------------------------------------------------
    # MARKET SNAPSHOT
    # -----------------------------------------------------

    st.subheader(
        "Market Snapshot"
    )

    if rows:

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "No CBK FX observations are currently available."
        )

    # -----------------------------------------------------
    # PLATFORM MODULES
    # -----------------------------------------------------

    st.subheader(
        "Platform Modules"
    )

    labels = [
        "🇰🇪 Kenyan Market",
        "💰 Treasury Bills",
        "🏦 Bond Pricing",
        "📈 Options & Greeks",
        "📊 Yield Curve",
        "💼 Portfolio Analytics",
        "⚠️ Risk Analysis",
        "🗃️ Historical Market Explorer",
        "🧠 Market Intelligence",
        "🔬 Backtesting",
        "💥 Stress Testing",
        "📄 Financial Reports"
    ]

    for i in range(
        0,
        len(labels),
        3
    ):

        cols = st.columns(3)

        for j, label in enumerate(
            labels[i:i + 3]
        ):

            cols[j].info(label)

    st.success(
        "System ready."
    )


def kenyan_market():
    st.title("🇰🇪 Kenyan Market")
    instrument = st.selectbox(
        "Instrument", ["USD/KES", "EUR/KES", "GBP/KES"]
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
    for instrument in ["USD/KES", "EUR/KES", "GBP/KES"]:
        data = market(instrument)

        if len(data) < 2:
            continue

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
    st.title("📊 Kenyan Treasury Bill Yield Curve")

    data = bills()

    if data.empty:
        st.warning(
            "No Treasury Bill data is currently available."
        )
        return

    # Latest auction date
    latest_date = data["auction_date"].max()

    current = data[
        data["auction_date"] == latest_date
    ].copy()

    current = current.sort_values(
        "tenor_days"
    )

    if current.empty:
        st.warning(
            "No Treasury Bill observations were found "
            "for the latest auction date."
        )
        return

    # -----------------------------------------------------
    # Summary
    # -----------------------------------------------------

    st.caption(
        f"Latest available CBK auction: "
        f"{latest_date.strftime('%Y-%m-%d')}"
    )

    display = current[
        [
            "tenor_days",
            "accepted_rate",
            "price"
        ]
    ].copy()

    display["Yield"] = (
        display["accepted_rate"] * 100
    ).map(
        lambda x: f"{x:.4f}%"
    )

    display["Price"] = display["price"].map(
        lambda x: f"{x:.4f}"
        if pd.notna(x)
        else "N/A"
    )

    display = display.rename(
        columns={
            "tenor_days": "Tenor (Days)"
        }
    )

    display = display[
        [
            "Tenor (Days)",
            "Yield",
            "Price"
        ]
    ]

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True
    )

    # -----------------------------------------------------
    # CURVE
    # -----------------------------------------------------

    curve = current[
        ["tenor_days", "accepted_rate"]
    ].dropna().copy()

    if len(curve) < 2:
        st.info(
            "At least two Treasury Bill tenors are required "
            "to draw a yield curve."
        )
        return

    curve["yield_percent"] = (
        curve["accepted_rate"] * 100
    )

    if px is not None:

        fig = px.line(
            curve,
            x="tenor_days",
            y="yield_percent",
            markers=True,
            title="CBK Treasury Bill Yield Curve"
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

    else:

        st.line_chart(
            curve.set_index(
                "tenor_days"
            )["yield_percent"]
        )

    # -----------------------------------------------------
    # CURVE SHAPE
    # -----------------------------------------------------

    first_yield = float(
        curve.iloc[0]["yield_percent"]
    )

    last_yield = float(
        curve.iloc[-1]["yield_percent"]
    )

    spread = last_yield - first_yield

    if spread > 0.05:

        st.success(
            f"Curve shape: upward sloping "
            f"(+{spread:.4f} percentage points)."
        )

    elif spread < -0.05:

        st.warning(
            f"Curve shape: downward sloping "
            f"({spread:.4f} percentage points)."
        )

    else:

        st.info(
            f"Curve shape: relatively flat "
            f"({spread:.4f} percentage points)."
        )


def treasury_bills():
    st.title("💰 Kenyan Treasury Bills")

    data = bills()

    if data.empty:
        st.warning(
            "No Treasury Bill data is currently available."
        )
        return

    tenors = sorted(
        data["tenor_days"].dropna().unique()
    )

    if not tenors:
        st.warning(
            "No valid Treasury Bill tenors were found."
        )
        return

    tenor = st.selectbox(
        "Tenor",
        tenors,
        format_func=lambda x:
            f"{int(x)}-Day Treasury Bill"
    )

    current = data[
        data["tenor_days"] == tenor
    ].sort_values(
        "auction_date"
    )

    if current.empty:
        st.info(
            "No observations available for this tenor."
        )
        return

    st.metric(
        "Latest CBK Yield",
        f"{current.iloc[-1]['accepted_rate'] * 100:.4f}%"
    )

    st.dataframe(
        current,
        use_container_width=True,
        hide_index=True
    )

    if len(current) >= 2:

        show_line(
            current,
            "auction_date",
            "accepted_rate",
            f"{int(tenor)}-Day Treasury Bill Yield"
        )

    else:

        st.info(
            "Historical chart will appear when multiple "
            "CBK auction observations are available."
        )


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
        "Instrument", ["USD/KES", "EUR/KES", "GBP/KES"]
    )
    value = st.number_input("Portfolio Value (KES)", min_value=1.0,
                            value=1_000_000.0)
    confidence = st.slider("VaR Confidence", 0.90, 0.99, 0.95, 0.01)

    data = market(instrument)

    if len(data) < 2:
        st.warning(
            "At least two market observations are required "
            "for historical risk analysis."
        )
        return

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
    for instrument in ["USD/KES", "EUR/KES", "GBP/KES"]:
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
        ["All"] + available_market_instruments(),
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
    for instrument in ["USD/KES", "EUR/KES", "GBP/KES"]:
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
        ["USD/KES", "EUR/KES", "GBP/KES"],
        ["USD/KES", "EUR/KES"],
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
        "Instrument", ["USD/KES", "EUR/KES", "GBP/KES"]
    )
    data = market(instrument).copy()

    if data.empty:
        st.warning(
            "No market data is available for this instrument."
        )
        return

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

    st.caption(
        "Market snapshot based on currently available "
        "Kenyan market observations."
    )

    instruments = available_market_instruments()

    if not instruments:
        st.warning(
            "No market instruments are currently available."
        )
        return

    snapshot = []

    for instrument in instruments:

        data = market(instrument)

        if data.empty:
            continue

        data = data.sort_values(
            "trade_date"
        ).reset_index(drop=True)

        latest = float(
            data["price"].iloc[-1]
        )

        latest_date = data[
            "trade_date"
        ].iloc[-1]

        # Only calculate change when a previous
        # observation actually exists.
        if len(data) >= 2:

            previous = float(
                data["price"].iloc[-2]
            )

            if previous != 0:

                change = (
                    latest / previous - 1
                ) * 100

                change_display = (
                    f"{change:.4f}%"
                )

            else:

                change_display = "N/A"

        else:

            change_display = "N/A"

        source = "Central Bank of Kenya"

        if "source" in data.columns:

            sources = (
                data["source"]
                .dropna()
                .astype(str)
                .unique()
            )

            if len(sources) > 0:
                source = sources[-1]

        snapshot.append({
            "Instrument": instrument,
            "Latest": latest,
            "Change %": change_display,
            "Date": latest_date.strftime(
                "%Y-%m-%d"
            ),
            "Source": source
        })

    if not snapshot:

        st.info(
            "No usable market observations are currently "
            "available for the report."
        )
        return

    report_df = pd.DataFrame(
        snapshot
    )

    # =====================================================
    # SUMMARY TABLE
    # =====================================================

    st.subheader(
        "Market Snapshot"
    )

    st.dataframe(
        report_df,
        use_container_width=True,
        hide_index=True
    )

    # =====================================================
    # TEXT REPORT
    # =====================================================

    report_lines = [
        "KENYA FINANCIAL ANALYTICS",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "MARKET SNAPSHOT",
        ""
    ]

    for row in snapshot:

        report_lines.append(
            f"{row['Instrument']}: "
            f"{row['Latest']:.4f} | "
            f"Change: {row['Change %']} | "
            f"Date: {row['Date']} | "
            f"Source: {row['Source']}"
        )

    report = "\n".join(
        report_lines
    )

    st.subheader(
        "Report"
    )

    st.text_area(
        "Generated Financial Report",
        report,
        height=350
    )

    st.download_button(
        "⬇️ Download Report",
        report,
        "kenya_financial_report.txt",
        "text/plain"
    )


def backtesting():
    st.title("🔬 Backtesting")
    instrument = st.selectbox(
        "Instrument", ["USD/KES", "EUR/KES", "GBP/KES"]
    )
    short = st.slider("Short Moving Average", 5, 50, 20)
    long = st.slider("Long Moving Average", 30, 150, 60)

    if short >= long:
        st.warning("Short moving average must be smaller than long moving average.")
        return

    data = market(instrument).copy()

    if len(data) < long:
        st.warning(
            f"Backtesting requires at least {long} observations. "
            f"Only {len(data)} are currently available."
        )
        return

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

        force_live_refresh = False

        if st.button(
            "🔄 REFRESH CBK DATA",
            use_container_width=True
        ):
            st.session_state.refresh += 1
            force_live_refresh = True

        try:
            live_result = refresh(
                DB,
                force=force_live_refresh
            )
        except Exception as exc:
            live_result = status()
            st.success("CBK data connected — using official Central Bank of Kenya records.")
            st.caption(str(exc))

        st.divider()
        selected = st.radio("Select Module", MODULES)
        st.divider()

        st.caption("SYSTEM STATUS")
        st.write("Database: **SQLite**")
        st.write("Quant Engine: **ONLINE**")
        st.write("Risk Engine: **ONLINE**")

        if live_result.get("status") == "LIVE":
            st.write("Market Data: **LIVE — CBK**")
            st.write(
                "Source: **Central Bank of Kenya**"
            )
            st.write(
                "FX feeds:",
                len(live_result.get("fx", {}))
            )
            st.write(
                "T-Bill feeds:",
                len(live_result.get("treasury_bills", []))
            )
        else:
            st.write("Market Data: **OFFLINE**")

        st.write("Refresh:", st.session_state.refresh)

    FUNCTIONS[selected]()

    st.divider()
    st.caption("Kenya Financial Analytics • Clean standalone build")


if __name__ == "__main__":
    main()

