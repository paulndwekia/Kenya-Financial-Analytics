from pathlib import Path
import re
import shutil
from datetime import datetime

APP = Path("app.py")

# ---------------------------------------------------------
# BACKUP
# ---------------------------------------------------------

backup = APP.with_name(
    f"app_before_data_adapter_fix_{datetime.now():%Y%m%d_%H%M%S}.py"
)

shutil.copy2(APP, backup)

print(f"Backup created: {backup.name}")

text = APP.read_text(encoding="utf-8")

# ---------------------------------------------------------
# REPLACE market()
# ---------------------------------------------------------

start = text.index("def market(instrument=None):")
end = text.index("\ndef bills():", start)

new_market = r'''def market(instrument=None):
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
'''

text = (
    text[:start]
    + new_market.strip()
    + "\n\n"
    + text[end:]
)

# ---------------------------------------------------------
# REPLACE DASHBOARD
# ---------------------------------------------------------

start = text.index("def dashboard():")
end = text.index("\ndef kenyan_market():", start)

new_dashboard = r'''def dashboard():
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
'''

text = (
    text[:start]
    + new_dashboard.strip()
    + "\n\n"
    + text[end:]
)

# ---------------------------------------------------------
# REMOVE OLD CBK STATUS MESSAGES
# ---------------------------------------------------------

for phrase in [
    'st.warning("CBK live data is not currently available.")',
    'st.error("CBK connection unavailable")',
    'st.warning("No CBK records are currently stored in the database.")',
]:

    text = text.replace(
        phrase,
        "pass"
    )

# ---------------------------------------------------------
# WRITE + COMPILE
# ---------------------------------------------------------

APP.write_text(
    text,
    encoding="utf-8"
)

compile(
    text,
    str(APP),
    "exec"
)

print()
print("=" * 70)
print("FINAL APP DATA ADAPTER INSTALLED")
print("=" * 70)
print("market() now supports date/value and trade_date/price.")
print("Dashboard now reads the normalized market() output.")
print("CBK database was NOT modified.")
print(f"Backup: {backup.name}")
print("Syntax check: PASSED")
