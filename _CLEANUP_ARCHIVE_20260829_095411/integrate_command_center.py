from pathlib import Path
import shutil

dashboard = Path("dashboard.py")

if not dashboard.exists():
    print("ERROR: dashboard.py was not found.")
    raise SystemExit(1)

# ============================================================
# BACKUP CURRENT DASHBOARD
# ============================================================

backup = Path("dashboard_backup_before_command_center.py")

shutil.copy2(
    dashboard,
    backup
)

print()
print("=" * 70)
print("DASHBOARD BACKUP CREATED")
print("=" * 70)
print()
print(f"Backup: {backup.resolve()}")

# ============================================================
# READ DASHBOARD
# ============================================================

text = dashboard.read_text(
    encoding="utf-8"
)

# ============================================================
# ADD COMMAND CENTER PAGE
# ============================================================

if '"Command Center"' not in text:

    # Add to common page lists if they exist.
    replacements = [
        (
            '["Dashboard",',
            '["Command Center", "Dashboard",'
        ),
        (
            "['Dashboard',",
            "['Command Center', 'Dashboard',"
        ),
    ]

    for old, new in replacements:

        if old in text:

            text = text.replace(
                old,
                new,
                1
            )

            break

# ============================================================
# CREATE COMMAND CENTER PAGE
# ============================================================

marker = 'if page == "Command Center":'

if marker not in text:

    # Find first page condition.
    possible_markers = [
        'if page == "Dashboard":',
        'elif page == "Dashboard":',
    ]

    insert_position = -1

    for possible in possible_markers:

        position = text.find(
            possible
        )

        if position != -1:

            insert_position = position

            break

    if insert_position != -1:

        command_center = r'''
if page == "Command Center":

    st.title(
        "🇰🇪 Kenya Financial Analytics"
    )

    st.subheader(
        "Quantitative Finance Command Center"
    )

    st.caption(
        "CBK market data • Fixed income • "
        "Risk • Portfolio • Backtesting • Stress Testing"
    )

    st.divider()

    # ========================================================
    # DATABASE
    # ========================================================

    import sqlite3
    from pathlib import Path
    import pandas as pd

    database = Path(
        "kenya_market.db"
    )

    if database.exists():

        connection = sqlite3.connect(
            str(database)
        )

        try:

            treasury = pd.read_sql_query(
                """
                SELECT *
                FROM treasury_bill_rates
                """,
                connection
            )

        except Exception:

            treasury = pd.DataFrame()

        connection.close()

    else:

        treasury = pd.DataFrame()

    # ========================================================
    # LATEST CBK RATES
    # ========================================================

    st.header(
        "🇰🇪 Latest CBK Treasury Bill Rates"
    )

    latest = {}

    if not treasury.empty:

        columns = {
            str(c).lower(): c
            for c in treasury.columns
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
        )

        if tenor_col and rate_col:

            for tenor in [
                91,
                182,
                364
            ]:

                rows = treasury[
                    pd.to_numeric(
                        treasury[tenor_col],
                        errors="coerce"
                    ) == tenor
                ].copy()

                if rows.empty:
                    continue

                if date_col:

                    rows["_date"] = pd.to_datetime(
                        rows[date_col],
                        errors="coerce"
                    )

                    rows = rows.sort_values(
                        "_date"
                    )

                row = rows.iloc[-1]

                try:

                    rate = float(
                        row[rate_col]
                    )

                    if abs(rate) > 1:
                        rate /= 100

                    latest[tenor] = rate

                except Exception:

                    pass

    c1, c2, c3 = st.columns(3)

    with c1:

        if 91 in latest:

            st.metric(
                "91-Day",
                f"{latest[91] * 100:.4f}%"
            )

        else:

            st.metric(
                "91-Day",
                "No data"
            )

    with c2:

        if 182 in latest:

            st.metric(
                "182-Day",
                f"{latest[182] * 100:.4f}%"
            )

        else:

            st.metric(
                "182-Day",
                "No data"
            )

    with c3:

        if 364 in latest:

            st.metric(
                "364-Day",
                f"{latest[364] * 100:.4f}%"
            )

        else:

            st.metric(
                "364-Day",
                "No data"
            )

    # ========================================================
    # YIELD CURVE
    # ========================================================

    st.divider()

    st.header(
        "Yield Curve"
    )

    if latest:

        curve = pd.DataFrame(
            {
                "Yield (%)": {
                    f"{tenor}-Day":
                        rate * 100
                    for tenor, rate
                    in latest.items()
                }
            }
        )

        st.line_chart(
            curve,
            use_container_width=True
        )

    # ========================================================
    # DATA STATUS
    # ========================================================

    st.divider()

    st.header(
        "System Status"
    )

    c1, c2, c3 = st.columns(3)

    with c1:

        if database.exists():

            st.success(
                "Database ONLINE"
            )

        else:

            st.error(
                "Database OFFLINE"
            )

    with c2:

        st.metric(
            "Historical Records",
            f"{len(treasury):,}"
        )

    with c3:

        engines = [
            "pricing_engine.py",
            "risk_engine.py",
            "portfolio_engine.py",
            "backtest_engine.py",
            "stress_engine.py"
        ]

        online = sum(
            Path(engine).exists()
            for engine in engines
        )

        st.metric(
            "Analytics Engines",
            f"{online}/{len(engines)}"
        )

    # ========================================================
    # QUICK NAVIGATION
    # ========================================================

    st.divider()

    st.header(
        "Analytics Platform"
    )

    c1, c2, c3 = st.columns(3)

    with c1:

        st.info(
            "💰 Treasury Bills\n\n"
            "Price Kenyan Treasury Bills "
            "using CBK rates."
        )

        st.info(
            "🏦 Bond Pricing\n\n"
            "Government bond valuation, "
            "duration and convexity."
        )

    with c2:

        st.info(
            "🔢 Options & Greeks\n\n"
            "Black-Scholes, Binomial and "
            "Monte Carlo valuation."
        )

        st.info(
            "🛡️ Risk Analysis\n\n"
            "VaR, Expected Shortfall, "
            "Sharpe and drawdown."
        )

    with c3:

        st.info(
            "💼 Portfolio\n\n"
            "Allocation, return, risk "
            "and diversification."
        )

        st.info(
            "🔬 Backtesting\n\n"
            "Historical CBK strategy "
            "analysis."
        )

        st.info(
            "⚠️ Stress Testing\n\n"
            "Kenyan interest-rate "
            "scenario analysis."
        )

'''
        text = (
            text[:insert_position]
            + command_center
            + "\n"
            + text[insert_position:]
        )

# ============================================================
# SAVE
# ============================================================

dashboard.write_text(
    text,
    encoding="utf-8"
)

print()
print("=" * 70)
print("COMMAND CENTER INTEGRATED")
print("=" * 70)
print()
print("Original dashboard backup:")
print(backup.resolve())
print()
print("Updated dashboard:")
print(dashboard.resolve())
print()
print("Start with:")
print("python -m streamlit run dashboard.py")
print("=" * 70)
