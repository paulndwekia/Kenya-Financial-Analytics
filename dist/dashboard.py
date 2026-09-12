
import streamlit as st
import pandas as pd
import app
import stress_engine
import backtest_engine
import portfolio_engine
import risk_engine
from math import erf, exp, log, sqrt
import random





import pricing_engine
import cbk_pricing

import subprocess
import sys
import json
from pathlib import Path



st.set_page_config(
    page_title="Kenya Financial Analytics",
    page_icon="",
    layout="wide"
)


# ============================================================
# TITLE
# ============================================================

st.title("KENYA FINANCIAL ANALYTICS")

st.caption(
    "Quantitative Finance Research & Analytics Platform"
)


# ============================================================
# DATABASE
# ============================================================

app.initialize_database()

latest = app.get_latest_rates()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Select Module",
    [
        "Dashboard",
        "Kenyan Market",
        "Yield Curve",
        "Treasury Bills",
        "Bond Pricing",
        "Options & Greeks",
        "Risk Analysis",
        "Historical Market Explorer",
        "Portfolio",
        "Backtesting",
        "Stress Testing"
    ]
)


# ============================================================
# DASHBOARD
# ============================================================



# ===== CBK REFRESH CONTROL =====

with st.sidebar:

    st.divider()

    st.subheader(
        "🔄 CBK Data"
    )

    status_file = Path(
        "cbk_refresh_status.json"
    )

    if status_file.exists():

        try:

            status_data = json.loads(
                status_file.read_text(
                    encoding="utf-8"
                )
            )

            status = status_data.get(
                "status",
                "UNKNOWN"
            )

            last_attempt = status_data.get(
                "last_attempt",
                "Unknown"
            )

            if status == "SUCCESS":

                st.success(
                    "CBK data is up to date"
                )

            elif status in [
                "FAILED",
                "ERROR"
            ]:

                st.error(
                    "Last CBK refresh failed"
                )

            else:

                st.info(
                    f"CBK status: {status}"
                )

            st.caption(
                f"Last attempt: {last_attempt}"
            )

        except Exception:

            st.warning(
                "CBK status file could not be read."
            )

    else:

        st.info(
            "CBK refresh has not been run yet."
        )

    if st.button(
        "🔄 Refresh CBK Data",
        use_container_width=True
    ):

        refresh_script = Path(
            "cbk_refresh.py"
        )

        if not refresh_script.exists():

            st.error(
                "cbk_refresh.py was not found."
            )

        else:

            with st.spinner(
                "Connecting to CBK and importing new data..."
            ):

                try:

                    result = subprocess.run(
                        [
                            sys.executable,
                            str(refresh_script)
                        ],
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=180
                    )

                    output = (
                        result.stdout
                        + "\n"
                        + result.stderr
                    )

                    if result.returncode == 0:

                        st.success(
                            "CBK data refresh completed."
                        )

                        with st.expander(
                            "Refresh details"
                        ):

                            st.code(
                                output[-5000:]
                            )

                        st.rerun()

                    else:

                        st.error(
                            "CBK refresh failed."
                        )

                        with st.expander(
                            "CBK error details"
                        ):

                            st.code(
                                output[-5000:]
                            )

                except subprocess.TimeoutExpired:

                    st.error(
                        "CBK refresh timed out after "
                        "180 seconds."
                    )

                except Exception as error:

                    st.error(
                        f"CBK refresh error: {error}"
                    )


if page == "Dashboard":

    st.header("Market Overview")

    c1, c2, c3 = st.columns(3)

    with c1:

        if 91 in latest:

            st.metric(
                "91-Day T-Bill",
                f"{latest[91]['rate'] * 100:.4f}%"
            )

        else:

            st.metric(
                "91-Day T-Bill",
                "No data"
            )

    with c2:

        if 182 in latest:

            st.metric(
                "182-Day T-Bill",
                f"{latest[182]['rate'] * 100:.4f}%"
            )

        else:

            st.metric(
                "182-Day T-Bill",
                "No data"
            )

    with c3:

        if 364 in latest:

            st.metric(
                "364-Day T-Bill",
                f"{latest[364]['rate'] * 100:.4f}%"
            )

        else:

            st.metric(
                "364-Day T-Bill",
                "No data"
            )

    st.divider()

    st.subheader("System")

    st.success(
        "Kenya Financial Analytics engine is running."
    )

    st.info(
        "Data source: Central Bank of Kenya "
        "records imported into the local database."
    )


# ============================================================
# KENYAN MARKET
# ============================================================

elif page == "Kenyan Market":

    st.header("KENYAN MARKET DATA")

    rows = app.get_market_data()

    if rows:

        table = []

        for row in rows:

            table.append({
                "Auction Date": row[0],
                "Tenor": f"{row[1]} days",
                "Rate": f"{row[2] * 100:.4f}%",
                "Source": row[4]
            })

        st.dataframe(
            table,
            use_container_width=True
        )

    else:

        st.warning(
            "No market data has been imported yet."
        )


# ============================================================
# YIELD CURVE
# ============================================================

elif page == "Yield Curve":

    st.header("Kenyan Treasury Bill Yield Curve")

    st.caption(
        "Historical analysis based on CBK Treasury Bill "
        "auction observations stored in kenya_market.db."
    )

    latest = app.get_latest_rates()

    # ========================================================
    # CURRENT RATES
    # ========================================================

    st.subheader("Latest CBK Rates")

    c1, c2, c3 = st.columns(3)

    for column, tenor in zip(
        [c1, c2, c3],
        [91, 182, 364]
    ):

        with column:

            if tenor in latest:

                st.metric(
                    f"{tenor}-Day T-Bill",
                    f"{latest[tenor]['rate'] * 100:.4f}%"
                )

                st.caption(
                    f"Auction: {latest[tenor]['date']}"
                )

            else:

                st.metric(
                    f"{tenor}-Day T-Bill",
                    "No data"
                )

    st.divider()

    # ========================================================
    # HISTORICAL DATA
    # ========================================================

    rows = app.get_market_data()

    if not rows:

        st.warning(
            "No CBK historical observations are available."
        )

    else:

        records = []

        for row in rows:

            try:

                records.append({
                    "date": pd.to_datetime(row[0]),
                    "tenor": int(row[1]),
                    "rate": float(row[2]) * 100,
                    "source": row[4]
                })

            except Exception:

                continue

        if not records:

            st.warning(
                "The database contains records, "
                "but they could not be read."
            )

        else:

            df = pd.DataFrame(records)

            # =================================================
            # HISTORICAL YIELD CHART
            # =================================================

            st.subheader(
                "Historical Treasury Bill Yields"
            )

            history = (
                df
                .pivot_table(
                    index="date",
                    columns="tenor",
                    values="rate",
                    aggfunc="last"
                )
                .sort_index()
            )

            history.columns = [
                f"{int(column)}-Day"
                for column in history.columns
            ]

            st.line_chart(
                history,
                use_container_width=True
            )

            # =================================================
            # CURRENT CURVE
            # =================================================

            st.subheader(
                "Current Yield Curve"
            )

            curve_rows = []

            for tenor in [91, 182, 364]:

                if tenor in latest:

                    curve_rows.append({
                        "Maturity":
                            f"{tenor} days",

                        "Yield":
                            f"{latest[tenor]['rate'] * 100:.4f}%"
                    })

            if curve_rows:

                st.dataframe(
                    curve_rows,
                    use_container_width=True,
                    hide_index=True
                )

                curve_values = {}

                for tenor in [91, 182, 364]:

                    if tenor in latest:

                        curve_values[
                            f"{tenor}-Day"
                        ] = (
                            latest[tenor]["rate"]
                            * 100
                        )

                st.line_chart(
                    curve_values,
                    use_container_width=True
                )

                st.info(
                    "Curve shape: "
                    + app.curve_classification()
                )

            # =================================================
            # SPREAD ANALYSIS
            # =================================================

            st.subheader(
                "Yield Curve Spreads"
            )

            spread_records = []

            grouped = (
                df
                .pivot_table(
                    index="date",
                    columns="tenor",
                    values="rate",
                    aggfunc="last"
                )
                .sort_index()
            )

            if (
                91 in grouped.columns
                and 182 in grouped.columns
            ):

                grouped["91-182 Spread"] = (
                    grouped[182]
                    - grouped[91]
                )

            if (
                182 in grouped.columns
                and 364 in grouped.columns
            ):

                grouped["182-364 Spread"] = (
                    grouped[364]
                    - grouped[182]
                )

            if (
                91 in grouped.columns
                and 364 in grouped.columns
            ):

                grouped["91-364 Spread"] = (
                    grouped[364]
                    - grouped[91]
                )

            spread_columns = [
                column
                for column in [
                    "91-182 Spread",
                    "182-364 Spread",
                    "91-364 Spread"
                ]
                if column in grouped.columns
            ]

            if spread_columns:

                spread_chart = grouped[
                    spread_columns
                ]

                st.line_chart(
                    spread_chart,
                    use_container_width=True
                )

                latest_spreads = (
                    spread_chart
                    .dropna(how="all")
                    .tail(1)
                )

                if not latest_spreads.empty:

                    st.write(
                        "Latest spreads"
                    )

                    latest_display = (
                        latest_spreads
                        .T
                    )

                    latest_display.columns = [
                        "Spread (%)"
                    ]

                    latest_display[
                        "Spread (%)"
                    ] = latest_display[
                        "Spread (%)"
                    ].map(
                        lambda x:
                        f"{x:+.4f}%"
                    )

                    st.dataframe(
                        latest_display,
                        use_container_width=True
                    )

            # =================================================
            # CURVE MOVEMENT
            # =================================================

            st.subheader(
                "Curve Movement"
            )

            if len(grouped) >= 2:

                previous = grouped.iloc[-2]
                current = grouped.iloc[-1]

                movement = []

                for tenor in [
                    91,
                    182,
                    364
                ]:

                    if (
                        tenor in previous.index
                        and tenor in current.index
                        and pd.notna(previous[tenor])
                        and pd.notna(current[tenor])
                    ):

                        change = (
                            current[tenor]
                            - previous[tenor]
                        )

                        movement.append({
                            "Tenor":
                                f"{tenor}-Day",

                            "Previous Yield":
                                f"{previous[tenor]:.4f}%",

                            "Latest Yield":
                                f"{current[tenor]:.4f}%",

                            "Change":
                                f"{change:+.4f}%"
                        })

                if movement:

                    st.dataframe(
                        movement,
                        use_container_width=True,
                        hide_index=True
                    )

            # =================================================
            # INTERPOLATION
            # =================================================

            st.subheader(
                "Interpolated Treasury Yields"
            )

            interpolation = []

            for maturity in [
                120,
                150,
                200,
                250,
                300
            ]:

                value = app.interpolate_yield(
                    maturity
                )

                if value is not None:

                    interpolation.append({
                        "Maturity":
                            f"{maturity} days",

                        "Interpolated Yield":
                            f"{value * 100:.4f}%"
                    })

            if interpolation:

                st.dataframe(
                    interpolation,
                    use_container_width=True,
                    hide_index=True
                )

            # =================================================
            # DATABASE SUMMARY
            # =================================================

            st.divider()

            st.subheader(
                "CBK Historical Database"
            )

            total_observations = len(df)

            auction_dates = (
                df["date"]
                .drop_duplicates()
                .sort_values()
            )

            c1, c2, c3 = st.columns(3)

            c1.metric(
                "Observations",
                total_observations
            )

            c2.metric(
                "Auction Dates",
                len(auction_dates)
            )

            c3.metric(
                "Latest Auction",
                auction_dates.iloc[-1].strftime(
                    "%Y-%m-%d"
                )
            )

            # =================================================
            # RAW CBK OBSERVATIONS
            # =================================================

            st.subheader(
                "CBK Auction Observations"
            )

            display_df = df.copy()

            display_df["date"] = (
                display_df["date"]
                .dt.strftime("%Y-%m-%d")
            )

            display_df["tenor"] = (
                display_df["tenor"]
                .astype(str)
                + " days"
            )

            display_df["rate"] = (
                display_df["rate"]
                .map(
                    lambda x:
                    f"{x:.4f}%"
                )
            )

            display_df = display_df.rename(
                columns={
                    "date":
                        "Auction Date",

                    "tenor":
                        "Tenor",

                    "rate":
                        "Yield",

                    "source":
                        "Source"
                }
            )

            st.dataframe(
                display_df.sort_values(
                    "Auction Date",
                    ascending=False
                ),
                use_container_width=True,
                hide_index=True
            )

# ============================================================
# TREASURY BILLS
# ============================================================

elif page == "Treasury Bills":

    st.header("Kenyan Treasury Bill Pricing")

    st.caption(
        "Pricing uses the latest genuine Central Bank of Kenya "
        "auction yield stored in kenya_market.db."
    )

    # --------------------------------------------------------
    # TENOR
    # --------------------------------------------------------

    tenor = st.selectbox(
        "Treasury Bill Tenor",
        [91, 182, 364],
        format_func=lambda x:
            f"{x}-Day Treasury Bill"
    )

    face_value = st.number_input(
        "Face Value (KES)",
        min_value=1.0,
        value=1_000_000.0,
        step=10_000.0
    )

    # --------------------------------------------------------
    # GET CBK RATE
    # --------------------------------------------------------

    try:

        cbk = cbk_pricing.get_latest_rate(
            tenor
        )

        cbk_rate = cbk["rate"]
        auction_date = cbk["date"]

        st.info(
            f"Latest CBK auction yield: "
            f"{cbk_rate * 100:.4f}%  |  "
            f"Auction date: {auction_date}"
        )

    except Exception as error:

        st.error(
            f"CBK rate unavailable: {error}"
        )

        cbk = None

    # --------------------------------------------------------
    # PRICE
    # --------------------------------------------------------

    if cbk is not None:

        if st.button(
            "Calculate Using Latest CBK Rate"
        ):

            result = (
                cbk_pricing.price_using_latest_cbk(
                    face_value,
                    tenor
                )
            )

            st.subheader(
                "CBK-Based Pricing Result"
            )

            c1, c2, c3 = st.columns(3)

            with c1:

                st.metric(
                    "CBK Yield",
                    f"{result['annual_yield'] * 100:.4f}%"
                )

            with c2:

                st.metric(
                    "Purchase Price",
                    f"KES {result['purchase_price']:,.2f}"
                )

            with c3:

                st.metric(
                    "Profit",
                    f"KES {result['profit']:,.2f}"
                )

            c1, c2, c3 = st.columns(3)

            with c1:

                st.metric(
                    "Face Value",
                    f"KES {result['face_value']:,.2f}"
                )

            with c2:

                st.metric(
                    "Holding Return",
                    f"{result['holding_return'] * 100:.4f}%"
                )

            with c3:

                st.metric(
                    "Annualized Return",
                    f"{result['annualized_return'] * 100:.4f}%"
                )

            st.divider()

            st.subheader(
                "Transaction Information"
            )

            st.write(
                f"**Instrument:** "
                f"{result['instrument']}"
            )

            st.write(
                f"**Tenor:** "
                f"{result['tenor_days']} days"
            )

            st.write(
                f"**CBK Auction Date:** "
                f"{result['cbk_auction_date']}"
            )

            st.write(
                f"**Data Source:** "
                f"{result['data_source']}"
            )

            st.success(
                "Pricing calculated from genuine CBK "
                "market data. No artificial market rate "
                "was used."
            )

        else:

            st.write(
                "Click the button above to calculate "
                "the T-Bill using the latest CBK rate."
            )

# ============================================================
# BOND PRICING
# ============================================================

elif page == "Bond Pricing":

    st.header("Kenyan Government Bond Pricing")

    st.caption(
        "Fixed-income valuation, yield analysis and "
        "interest-rate risk analytics."
    )

    st.info(
        "Bond calculations use the assumptions entered below. "
        "CBK Treasury Bill rates are not automatically treated "
        "as government bond yields."
    )

    # ========================================================
    # INPUTS
    # ========================================================

    st.subheader("Bond Parameters")

    c1, c2 = st.columns(2)

    with c1:

        face_value = st.number_input(
            "Face Value (KES)",
            min_value=1.0,
            value=1_000_000.0,
            step=10_000.0
        )

        coupon_rate = st.number_input(
            "Annual Coupon Rate (%)",
            min_value=0.0,
            max_value=100.0,
            value=10.0,
            step=0.01
        )

    with c2:

        yield_rate = st.number_input(
            "Yield to Maturity (%)",
            min_value=-99.0,
            max_value=100.0,
            value=9.0,
            step=0.01
        )

        years = st.number_input(
            "Years to Maturity",
            min_value=0.1,
            max_value=100.0,
            value=5.0,
            step=0.5
        )

    frequency = st.selectbox(
        "Coupon Frequency",
        [2, 1],
        format_func=lambda x:
            "Semi-Annual" if x == 2
            else "Annual"
    )

    # ========================================================
    # CALCULATE
    # ========================================================

    if st.button(
        "Calculate Bond"
    ):

        try:

            price = pricing_engine.bond_price(
                face_value,
                coupon_rate,
                yield_rate,
                years,
                frequency
            )

            calculated_ytm = (
                pricing_engine.bond_ytm(
                    face_value,
                    coupon_rate,
                    price,
                    years,
                    frequency
                )
            )

            macaulay, modified = (
                pricing_engine.bond_duration(
                    face_value,
                    coupon_rate,
                    yield_rate,
                    years,
                    frequency
                )
            )

            convexity = (
                pricing_engine.bond_convexity(
                    face_value,
                    coupon_rate,
                    yield_rate,
                    years,
                    frequency
                )
            )

            # =================================================
            # MAIN RESULTS
            # =================================================

            st.subheader(
                "Bond Valuation"
            )

            c1, c2, c3 = st.columns(3)

            with c1:

                st.metric(
                    "Clean Model Price",
                    f"KES {price:,.2f}"
                )

            with c2:

                st.metric(
                    "Coupon Rate",
                    f"{coupon_rate:.4f}%"
                )

            with c3:

                st.metric(
                    "Yield to Maturity",
                    f"{yield_rate:.4f}%"
                )

            # =================================================
            # DURATION / CONVEXITY
            # =================================================

            st.subheader(
                "Interest-Rate Risk"
            )

            c1, c2, c3 = st.columns(3)

            with c1:

                st.metric(
                    "Macaulay Duration",
                    f"{macaulay:.4f} years"
                )

            with c2:

                st.metric(
                    "Modified Duration",
                    f"{modified:.4f}"
                )

            with c3:

                st.metric(
                    "Convexity",
                    f"{convexity:.4f}"
                )

            # =================================================
            # PRICE VS FACE
            # =================================================

            premium_discount = (
                price - face_value
            )

            if premium_discount > 0:

                st.success(
                    "Bond is trading at a premium "
                    "to face value."
                )

            elif premium_discount < 0:

                st.warning(
                    "Bond is trading at a discount "
                    "to face value."
                )

            else:

                st.info(
                    "Bond is trading approximately "
                    "at par."
                )

            # =================================================
            # PRICE SENSITIVITY
            # =================================================

            st.divider()

            st.subheader(
                "Yield Shock Analysis"
            )

            shock = st.slider(
                "Yield Change (%)",
                min_value=-5.0,
                max_value=5.0,
                value=1.0,
                step=0.10
            )

            sensitivity = (
                pricing_engine.bond_price_sensitivity(
                    face_value,
                    coupon_rate,
                    yield_rate,
                    years,
                    shock,
                    frequency
                )
            )

            c1, c2, c3 = st.columns(3)

            with c1:

                st.metric(
                    "Current Price",
                    f"KES {sensitivity['current_price']:,.2f}"
                )

            with c2:

                st.metric(
                    "Estimated Price",
                    f"KES {sensitivity['estimated_price']:,.2f}"
                )

            with c3:

                st.metric(
                    "Estimated Price Change",
                    f"{sensitivity['percentage_change'] * 100:+.4f}%"
                )

            st.caption(
                "Sensitivity uses the duration/convexity "
                "approximation and is an estimate, not a "
                "guaranteed market price."
            )

            # =================================================
            # CASH FLOWS
            # =================================================

            st.divider()

            st.subheader(
                "Projected Bond Cash Flows"
            )

            cash_flows = (
                pricing_engine.bond_cash_flows(
                    face_value,
                    coupon_rate,
                    years,
                    frequency
                )
            )

            cash_flow_rows = []

            for item in cash_flows:

                cash_flow_rows.append({
                    "Period":
                        item["period"],

                    "Time (Years)":
                        f"{item['time']:.2f}",

                    "Cash Flow (KES)":
                        f"{item['cash_flow']:,.2f}"
                })

            st.dataframe(
                cash_flow_rows,
                use_container_width=True,
                hide_index=True
            )

            # =================================================
            # VALIDATION
            # =================================================

            st.divider()

            st.subheader(
                "Model Validation"
            )

            st.write(
                f"Calculated YTM from model price: "
                f"**{calculated_ytm * 100:.6f}%**"
            )

            difference = (
                calculated_ytm
                - yield_rate / 100
            )

            if abs(difference) < 0.000001:

                st.success(
                    "Price/YTM consistency check passed."
                )

            else:

                st.warning(
                    "Small numerical difference detected "
                    "during YTM validation."
                )

            st.caption(
                "Model convention: fixed-rate bond with "
                f"{'semi-annual' if frequency == 2 else 'annual'} "
                "coupon payments."
            )

        except Exception as error:

            st.error(
                f"Bond calculation failed: {error}"
            )

# ============================================================
# OPTIONS
# ============================================================


elif page == "Options & Greeks":

    st.header("Options Pricing & Greeks")

    st.caption(
        "Black-Scholes, Binomial Tree and Monte Carlo "
        "valuation with complete option Greeks."
    )

    # ========================================================
    # NORMAL DISTRIBUTION
    # ========================================================

    def normal_cdf(x):

        return 0.5 * (
            1.0 + erf(
                x / sqrt(2.0)
            )
        )


    def normal_pdf(x):

        return (
            exp(-0.5 * x * x)
            / sqrt(2.0 * 3.141592653589793)
        )


    # ========================================================
    # BLACK-SCHOLES
    # ========================================================

    def bs_calculate(
        S,
        K,
        r,
        sigma,
        T,
        option
    ):

        d1 = (
            log(S / K)
            + (r + 0.5 * sigma ** 2) * T
        ) / (
            sigma * sqrt(T)
        )

        d2 = (
            d1
            - sigma * sqrt(T)
        )

        if option == "call":

            price = (
                S * normal_cdf(d1)
                - K
                * exp(-r * T)
                * normal_cdf(d2)
            )

            delta = normal_cdf(d1)

            rho = (
                K * T
                * exp(-r * T)
                * normal_cdf(d2)
            )

            theta = (
                -(
                    S
                    * normal_pdf(d1)
                    * sigma
                    / (2 * sqrt(T))
                )
                - r
                * K
                * exp(-r * T)
                * normal_cdf(d2)
            )

        else:

            price = (
                K
                * exp(-r * T)
                * normal_cdf(-d2)
                - S
                * normal_cdf(-d1)
            )

            delta = (
                normal_cdf(d1) - 1
            )

            rho = (
                -K * T
                * exp(-r * T)
                * normal_cdf(-d2)
            )

            theta = (
                -(
                    S
                    * normal_pdf(d1)
                    * sigma
                    / (2 * sqrt(T))
                )
                + r
                * K
                * exp(-r * T)
                * normal_cdf(-d2)
            )

        gamma = (
            normal_pdf(d1)
            / (
                S
                * sigma
                * sqrt(T)
            )
        )

        vega = (
            S
            * normal_pdf(d1)
            * sqrt(T)
        )

        return {
            "price": price,
            "delta": delta,
            "gamma": gamma,
            "vega": vega,
            "theta": theta,
            "rho": rho,
            "d1": d1,
            "d2": d2
        }


    # ========================================================
    # BINOMIAL TREE
    # ========================================================

    def binomial_price(
        S,
        K,
        r,
        sigma,
        T,
        steps,
        option
    ):

        dt = T / steps

        u = exp(
            sigma * sqrt(dt)
        )

        d = 1 / u

        discount = exp(
            -r * dt
        )

        p = (
            exp(r * dt) - d
        ) / (
            u - d
        )

        prices = []

        for j in range(
            steps + 1
        ):

            stock = (
                S
                * (u ** j)
                * (d ** (steps - j))
            )

            if option == "call":

                value = max(
                    stock - K,
                    0
                )

            else:

                value = max(
                    K - stock,
                    0
                )

            prices.append(value)

        for i in range(
            steps - 1,
            -1,
            -1
        ):

            for j in range(
                i + 1
            ):

                prices[j] = (
                    discount
                    * (
                        p * prices[j + 1]
                        + (1 - p) * prices[j]
                    )
                )

        return prices[0]


    # ========================================================
    # MONTE CARLO
    # ========================================================

    def monte_carlo_price(
        S,
        K,
        r,
        sigma,
        T,
        paths,
        option
    ):

        total = 0.0

        for _ in range(paths):

            z = random.gauss(
                0,
                1
            )

            ST = (
                S
                * exp(
                    (
                        r
                        - 0.5 * sigma ** 2
                    ) * T
                    + sigma
                    * sqrt(T)
                    * z
                )
            )

            if option == "call":

                payoff = max(
                    ST - K,
                    0
                )

            else:

                payoff = max(
                    K - ST,
                    0
                )

            total += payoff

        return (
            exp(-r * T)
            * total
            / paths
        )


    # ========================================================
    # USER INPUTS
    # ========================================================

    st.subheader(
        "Option Parameters"
    )

    c1, c2 = st.columns(2)

    with c1:

        spot = st.number_input(
            "Underlying Price",
            min_value=0.0001,
            value=100.0,
            step=1.0
        )

        strike = st.number_input(
            "Strike Price",
            min_value=0.0001,
            value=100.0,
            step=1.0
        )

        risk_free_rate = st.number_input(
            "Risk-Free Rate (%)",
            value=9.0,
            step=0.01
        )

    with c2:

        volatility = st.number_input(
            "Volatility (%)",
            min_value=0.01,
            value=20.0,
            step=0.1
        )

        time_to_maturity = st.number_input(
            "Time to Maturity (Years)",
            min_value=0.01,
            value=1.0,
            step=0.1
        )

        option_type = st.selectbox(
            "Option Type",
            ["call", "put"]
        )

    binomial_steps = st.slider(
        "Binomial Tree Steps",
        10,
        500,
        100,
        10
    )

    monte_carlo_paths = st.slider(
        "Monte Carlo Simulations",
        1000,
        100000,
        10000,
        1000
    )

    # ========================================================
    # CALCULATION
    # ========================================================

    if st.button(
        "Calculate Option"
    ):

        try:

            S = float(spot)

            K = float(strike)

            r = (
                float(risk_free_rate)
                / 100
            )

            sigma = (
                float(volatility)
                / 100
            )

            T = float(
                time_to_maturity
            )

            # -------------------------------
            # BLACK-SCHOLES
            # -------------------------------

            bs = bs_calculate(
                S,
                K,
                r,
                sigma,
                T,
                option_type
            )

            # -------------------------------
            # BINOMIAL
            # -------------------------------

            tree = binomial_price(
                S,
                K,
                r,
                sigma,
                T,
                int(binomial_steps),
                option_type
            )

            # -------------------------------
            # MONTE CARLO
            # -------------------------------

            mc = monte_carlo_price(
                S,
                K,
                r,
                sigma,
                T,
                int(monte_carlo_paths),
                option_type
            )

            # =================================================
            # MODEL RESULTS
            # =================================================

            st.subheader(
                "Model Comparison"
            )

            c1, c2, c3 = st.columns(3)

            with c1:

                st.metric(
                    "Black-Scholes",
                    f"{bs['price']:,.6f}"
                )

            with c2:

                st.metric(
                    "Binomial Tree",
                    f"{tree:,.6f}"
                )

            with c3:

                st.metric(
                    "Monte Carlo",
                    f"{mc:,.6f}"
                )

            # =================================================
            # GREEKS
            # =================================================

            st.divider()

            st.subheader(
                "Option Greeks"
            )

            g1, g2, g3 = st.columns(3)

            with g1:

                st.metric(
                    "Delta",
                    f"{bs['delta']:.6f}"
                )

                st.metric(
                    "Gamma",
                    f"{bs['gamma']:.6f}"
                )

            with g2:

                st.metric(
                    "Vega",
                    f"{bs['vega']:.6f}"
                )

                st.metric(
                    "Theta",
                    f"{bs['theta']:.6f}"
                )

            with g3:

                st.metric(
                    "Rho",
                    f"{bs['rho']:.6f}"
                )

                st.metric(
                    "d1",
                    f"{bs['d1']:.6f}"
                )

            # =================================================
            # INTERPRETATION
            # =================================================

            st.subheader(
                "Risk Interpretation"
            )

            st.write(
                f"**Delta:** {bs['delta']:.6f}"
            )

            st.write(
                f"**Gamma:** {bs['gamma']:.6f}"
            )

            st.write(
                f"**Vega:** {bs['vega']:.6f}"
            )

            st.write(
                f"**Theta:** {bs['theta']:.6f}"
            )

            st.write(
                f"**Rho:** {bs['rho']:.6f}"
            )

            # =================================================
            # MODEL DIFFERENCES
            # =================================================

            st.divider()

            st.subheader(
                "Model Differences"
            )

            st.write(
                "Binomial vs Black-Scholes: "
                f"{tree - bs['price']:+.6f}"
            )

            st.write(
                "Monte Carlo vs Black-Scholes: "
                f"{mc - bs['price']:+.6f}"
            )

            st.success(
                "Option valuation completed successfully."
            )

        except Exception as error:

            st.error(
                f"Option calculation failed: {error}"
            )

# ============================================================
# RISK
# ============================================================


elif page == "Risk Analysis":

    st.header(
        "Risk Analysis"
    )

    st.caption(
        "Portfolio risk measurement, loss estimation "
        "and stress testing."
    )

    # ========================================================
    # INPUTS
    # ========================================================

    st.subheader(
        "Portfolio Parameters"
    )

    portfolio_value = st.number_input(
        "Portfolio Value (KES)",
        min_value=1.0,
        value=1_000_000.0,
        step=10_000.0
    )

    risk_free = st.number_input(
        "Annual Risk-Free Rate (%)",
        min_value=0.0,
        value=9.0,
        step=0.01
    )

    st.subheader(
        "Return Observations"
    )

    returns_text = st.text_area(
        "Enter daily returns separated by commas",
        value=(
            "0.002, -0.004, 0.001, -0.006, "
            "0.003, -0.002, 0.004, -0.003, "
            "0.001, -0.005, 0.002, 0.003, "
            "-0.001, -0.004, 0.002, 0.001, "
            "-0.002, 0.003, -0.001, 0.002"
        )
    )

    if st.button(
        "Calculate Risk"
    ):

        try:

            returns = [
                float(x.strip())
                for x in returns_text.split(",")
                if x.strip()
            ]

            report = risk_engine.risk_report(
                returns,
                portfolio_value,
                risk_free / 100
            )

            # =================================================
            # VOLATILITY
            # =================================================

            st.subheader(
                "Portfolio Risk Overview"
            )

            c1, c2, c3 = st.columns(3)

            with c1:

                st.metric(
                    "Annualized Volatility",
                    f"{report['volatility'] * 100:.4f}%"
                )

            with c2:

                st.metric(
                    "Sharpe Ratio",
                    f"{report['sharpe']:.4f}"
                )

            with c3:

                st.metric(
                    "Sortino Ratio",
                    f"{report['sortino']:.4f}"
                )

            # =================================================
            # VAR
            # =================================================

            st.divider()

            st.subheader(
                "Value at Risk"
            )

            c1, c2 = st.columns(2)

            with c1:

                st.metric(
                    "Historical VaR 95%",
                    f"KES {report['historical_var_95']:,.2f}"
                )

                st.metric(
                    "Historical VaR 99%",
                    f"KES {report['historical_var_99']:,.2f}"
                )

            with c2:

                st.metric(
                    "Parametric VaR 95%",
                    f"KES {report['parametric_var_95']:,.2f}"
                )

                st.metric(
                    "Parametric VaR 99%",
                    f"KES {report['parametric_var_99']:,.2f}"
                )

            st.caption(
                "VaR estimates the potential portfolio loss "
                "over the modeled one-period horizon."
            )

            # =================================================
            # EXPECTED SHORTFALL
            # =================================================

            st.divider()

            st.subheader(
                "Expected Shortfall"
            )

            c1, c2 = st.columns(2)

            with c1:

                st.metric(
                    "Expected Shortfall 95%",
                    f"KES {report['expected_shortfall_95']:,.2f}"
                )

            with c2:

                st.metric(
                    "Expected Shortfall 99%",
                    f"KES {report['expected_shortfall_99']:,.2f}"
                )

            st.caption(
                "Expected Shortfall estimates the average "
                "loss in the worst tail of the distribution."
            )

            # =================================================
            # DRAWDOWN
            # =================================================

            st.divider()

            st.subheader(
                "Maximum Drawdown"
            )

            drawdown = report[
                "maximum_drawdown"
            ]

            c1, c2, c3 = st.columns(3)

            with c1:

                st.metric(
                    "Maximum Drawdown",
                    f"{drawdown['percentage']:.4f}%"
                )

            with c2:

                st.metric(
                    "Peak Value",
                    f"KES {drawdown['peak_value']:,.2f}"
                )

            with c3:

                st.metric(
                    "Ending Value",
                    f"KES {drawdown['ending_value']:,.2f}"
                )

            # =================================================
            # STRESS TEST
            # =================================================

            st.divider()

            st.subheader(
                "Portfolio Stress Testing"
            )

            scenarios = [
                ("Mild Stress", -0.05),
                ("Moderate Stress", -0.10),
                ("Severe Stress", -0.20),
                ("Extreme Stress", -0.30),
                ("Positive Scenario", 0.10)
            ]

            stress = risk_engine.stress_test(
                portfolio_value,
                scenarios
            )

            stress_table = []

            for row in stress:

                stress_table.append({
                    "Scenario":
                        row["Scenario"],

                    "Shock":
                        f"{row['Shock'] * 100:+.2f}%",

                    "Portfolio Change":
                        f"KES {row['Loss']:,.2f}",

                    "Ending Value":
                        f"KES {row['Ending Value']:,.2f}"
                })

            st.dataframe(
                stress_table,
                use_container_width=True,
                hide_index=True
            )

            st.success(
                "Risk analysis completed."
            )

        except Exception as error:

            st.error(
                f"Risk calculation failed: {error}"
            )

# ============================================================
# PORTFOLIO
# ============================================================



elif page == "Historical Market Explorer":

    st.header(
        "🇰🇪 Historical Market Explorer"
    )

    st.caption(
        "Explore historical CBK Treasury Bill observations "
        "stored in the Kenya Financial Analytics database."
    )

    import sqlite3
    import pandas as pd
    from pathlib import Path

    database = Path(
        "kenya_market.db"
    )

    if not database.exists():

        st.error(
            "kenya_market.db was not found."
        )

    else:

        connection = sqlite3.connect(
            str(database)
        )

        try:

            history = pd.read_sql_query(
                """
                SELECT *
                FROM treasury_bill_rates
                """,
                connection
            )

        except Exception as error:

            history = pd.DataFrame()

            st.error(
                f"Could not read market history: {error}"
            )

        connection.close()

        if history.empty:

            st.warning(
                "No historical Treasury Bill data is available."
            )

        else:

            # =================================================
            # DETECT COLUMNS
            # =================================================

            columns = {
                str(c).lower(): c
                for c in history.columns
            }

            tenor_column = (
                columns.get("tenor_days")
                or columns.get("tenor")
            )

            rate_column = (
                columns.get("rate")
                or columns.get("yield")
                or columns.get("yield_rate")
            )

            date_column = (
                columns.get("auction_date")
                or columns.get("date")
                or columns.get("auction")
            )

            # =================================================
            # FILTERS
            # =================================================

            st.subheader(
                "Market Filters"
            )

            c1, c2 = st.columns(2)

            with c1:

                available_tenors = [91, 182, 364]

                if tenor_column:

                    detected = sorted(
                        pd.to_numeric(
                            history[tenor_column],
                            errors="coerce"
                        )
                        .dropna()
                        .astype(int)
                        .unique()
                        .tolist()
                    )

                    available_tenors = [
                        x
                        for x in [91, 182, 364]
                        if x in detected
                    ]

                selected_tenor = st.selectbox(
                    "Treasury Bill Tenor",
                    available_tenors,
                    format_func=lambda x:
                        f"{x}-Day"
                )

            with c2:

                show_all = st.checkbox(
                    "Show all historical observations",
                    value=False
                )

            # =================================================
            # FILTER DATA
            # =================================================

            filtered = history.copy()

            if tenor_column:

                filtered = filtered[
                    pd.to_numeric(
                        filtered[tenor_column],
                        errors="coerce"
                    ) == selected_tenor
                ]

            if date_column:

                filtered["_parsed_date"] = pd.to_datetime(
                    filtered[date_column],
                    errors="coerce"
                )

                filtered = filtered.sort_values(
                    "_parsed_date"
                )

            # =================================================
            # SUMMARY
            # =================================================

            st.divider()

            st.subheader(
                f"{selected_tenor}-Day Historical Summary"
            )

            c1, c2, c3, c4 = st.columns(4)

            with c1:

                st.metric(
                    "Observations",
                    f"{len(filtered):,}"
                )

            if rate_column and not filtered.empty:

                numeric_rates = pd.to_numeric(
                    filtered[rate_column],
                    errors="coerce"
                ).dropna()

                if not numeric_rates.empty:

                    # Normalize only for display
                    display_rates = numeric_rates.copy()

                    if display_rates.abs().median() > 1:

                        display_rates = (
                            display_rates / 100
                        )

                    with c2:

                        st.metric(
                            "Latest Yield",
                            f"{display_rates.iloc[-1] * 100:.4f}%"
                        )

                    with c3:

                        st.metric(
                            "Average Yield",
                            f"{display_rates.mean() * 100:.4f}%"
                        )

                    with c4:

                        st.metric(
                            "Highest Yield",
                            f"{display_rates.max() * 100:.4f}%"
                        )

            # =================================================
            # HISTORICAL CHART
            # =================================================

            st.divider()

            st.subheader(
                "Historical Yield"
            )

            if (
                date_column
                and rate_column
                and not filtered.empty
            ):

                chart = filtered[
                    [
                        "_parsed_date",
                        rate_column
                    ]
                ].copy()

                chart[rate_column] = pd.to_numeric(
                    chart[rate_column],
                    errors="coerce"
                )

                chart = chart.dropna()

                if not chart.empty:

                    if chart[rate_column].abs().median() > 1:

                        chart[rate_column] = (
                            chart[rate_column] / 100
                        )

                    chart = chart.set_index(
                        "_parsed_date"
                    )

                    chart.columns = [
                        "Yield (%)"
                    ]

                    chart["Yield (%)"] = (
                        chart["Yield (%)"] * 100
                    )

                    st.line_chart(
                        chart,
                        use_container_width=True
                    )

            # =================================================
            # RATE CHANGE
            # =================================================

            st.subheader(
                "Auction-to-Auction Change"
            )

            if (
                rate_column
                and not filtered.empty
            ):

                changes = filtered.copy()

                changes["_numeric_rate"] = pd.to_numeric(
                    changes[rate_column],
                    errors="coerce"
                )

                if (
                    not changes["_numeric_rate"].dropna().empty
                    and
                    changes["_numeric_rate"].dropna().abs().median() > 1
                ):

                    changes["_numeric_rate"] = (
                        changes["_numeric_rate"] / 100
                    )

                changes["Change"] = (
                    changes["_numeric_rate"]
                    .diff()
                )

                if date_column:

                    changes["Date"] = (
                        changes[date_column]
                    )

                change_display = changes[
                    [
                        column
                        for column in [
                            "Date",
                            "_numeric_rate",
                            "Change"
                        ]
                        if column in changes.columns
                    ]
                ].copy()

                if "_numeric_rate" in change_display.columns:

                    change_display[
                        "Yield"
                    ] = (
                        change_display[
                            "_numeric_rate"
                        ] * 100
                    )

                    change_display = (
                        change_display.drop(
                            columns=["_numeric_rate"]
                        )
                    )

                if "Change" in change_display.columns:

                    change_display[
                        "Change"
                    ] = (
                        change_display[
                            "Change"
                        ] * 100
                    )

                st.dataframe(
                    change_display.tail(20),
                    use_container_width=True,
                    hide_index=True
                )

            # =================================================
            # DATA TABLE
            # =================================================

            st.divider()

            st.subheader(
                "Historical Observations"
            )

            display = filtered.copy()

            if "_parsed_date" in display.columns:

                display = display.drop(
                    columns=["_parsed_date"]
                )

            if not show_all:

                display = display.tail(25)

            st.dataframe(
                display,
                use_container_width=True,
                hide_index=True
            )

            st.caption(
                "The explorer displays observations stored "
                "in your local CBK database. It does not "
                "invent missing historical values."
            )


elif page == "Portfolio":

    st.header(
        "Kenyan Portfolio Management"
    )

    st.caption(
        "Construct and analyse a KES portfolio "
        "of Kenyan fixed-income instruments."
    )

    # ========================================================
    # ASSET INPUTS
    # ========================================================

    st.subheader(
        "Portfolio Assets"
    )

    st.info(
        "Enter the current value and expected annual "
        "return for each asset. Returns should be entered "
        "as percentages."
    )

    asset_names = [
        "91-Day Treasury Bill",
        "182-Day Treasury Bill",
        "364-Day Treasury Bill",
        "Government Bond",
        "Cash"
    ]

    assets = []

    for name in asset_names:

        c1, c2, c3 = st.columns(3)

        with c1:

            value = st.number_input(
                f"{name} Value (KES)",
                min_value=0.0,
                value=0.0,
                step=10_000.0,
                key=f"value_{name}"
            )

        with c2:

            expected = st.number_input(
                f"{name} Expected Return (%)",
                min_value=-100.0,
                max_value=100.0,
                value=0.0,
                step=0.10,
                key=f"return_{name}"
            )

        with c3:

            vol = st.number_input(
                f"{name} Volatility (%)",
                min_value=0.0,
                max_value=200.0,
                value=0.0,
                step=0.10,
                key=f"vol_{name}"
            )

        if value > 0:

            assets.append({
                "name":
                    name,

                "value":
                    value,

                "expected_return":
                    expected / 100,

                "volatility":
                    vol / 100
            })

    # ========================================================
    # CALCULATE
    # ========================================================

    if st.button(
        "Analyse Portfolio"
    ):

        try:

            if not assets:

                st.warning(
                    "Enter a value for at least one asset."
                )

            else:

                report = (
                    portfolio_engine
                    .portfolio_report(
                        assets
                    )
                )

                # =================================================
                # OVERVIEW
                # =================================================

                st.subheader(
                    "Portfolio Overview"
                )

                c1, c2, c3 = st.columns(3)

                with c1:

                    st.metric(
                        "Portfolio Value",
                        f"KES {report['total_value']:,.2f}"
                    )

                with c2:

                    st.metric(
                        "Expected Return",
                        f"{report['expected_return'] * 100:.4f}%"
                    )

                with c3:

                    st.metric(
                        "Expected Annual P&L",
                        f"KES {report['expected_pnl']:,.2f}"
                    )

                # =================================================
                # ALLOCATION
                # =================================================

                st.divider()

                st.subheader(
                    "Asset Allocation"
                )

                allocation = (
                    portfolio_engine
                    .allocation(
                        assets
                    )
                )

                allocation_table = []

                for item in allocation:

                    allocation_table.append({
                        "Asset":
                            item["name"],

                        "Value":
                            f"KES {item['value']:,.2f}",

                        "Weight":
                            f"{item['weight'] * 100:.2f}%"
                    })

                st.dataframe(
                    allocation_table,
                    use_container_width=True,
                    hide_index=True
                )

                chart_data = {
                    item["name"]:
                        item["weight"]
                    for item in allocation
                }

                st.bar_chart(
                    chart_data,
                    use_container_width=True
                )

                # =================================================
                # RISK
                # =================================================

                st.divider()

                st.subheader(
                    "Portfolio Risk"
                )

                c1, c2, c3 = st.columns(3)

                with c1:

                    st.metric(
                        "Volatility",
                        f"{report['volatility'] * 100:.4f}%"
                    )

                with c2:

                    st.metric(
                        "VaR 95%",
                        f"KES {report['var_95']:,.2f}"
                    )

                with c3:

                    st.metric(
                        "VaR 99%",
                        f"KES {report['var_99']:,.2f}"
                    )

                # =================================================
                # CONCENTRATION
                # =================================================

                st.divider()

                st.subheader(
                    "Diversification"
                )

                concentration = (
                    report["concentration"]
                )

                c1, c2 = st.columns(2)

                with c1:

                    st.metric(
                        "Largest Position",
                        f"{concentration['largest_weight_percent']:.2f}%"
                    )

                with c2:

                    st.metric(
                        "Diversification Score",
                        f"{report['diversification_score']:.4f}"
                    )

                if (
                    concentration[
                        "largest_weight"
                    ] > 0.50
                ):

                    st.warning(
                        "More than 50% of the portfolio "
                        "is concentrated in one position."
                    )

                else:

                    st.success(
                        "No single position exceeds "
                        "50% of the portfolio."
                    )

                # =================================================
                # STRESS TEST
                # =================================================

                st.divider()

                st.subheader(
                    "Portfolio Stress Test"
                )

                scenarios = [
                    ("-5% Market Shock", -0.05),
                    ("-10% Market Shock", -0.10),
                    ("-20% Market Shock", -0.20),
                    ("-30% Market Shock", -0.30),
                    ("+10% Positive Scenario", 0.10)
                ]

                stress_rows = []

                for name, shock in scenarios:

                    result = (
                        portfolio_engine
                        .stress_test(
                            assets,
                            shock
                        )
                    )

                    stress_rows.append({
                        "Scenario":
                            name,

                        "Shock":
                            f"{shock * 100:+.2f}%",

                        "Portfolio Change":
                            f"KES {result['change']:,.2f}",

                        "Ending Value":
                            f"KES {result['ending_value']:,.2f}"
                    })

                st.dataframe(
                    stress_rows,
                    use_container_width=True,
                    hide_index=True
                )

                st.success(
                    "Portfolio analysis completed."
                )

        except Exception as error:

            st.error(
                f"Portfolio analysis failed: {error}"
            )
# ============================================================
# BACKTESTING
# ============================================================


elif page == "Backtesting":

    st.header(
        "Kenyan Treasury Bill Backtesting"
    )

    st.caption(
        "Historical rolling analysis using genuine "
        "CBK Treasury Bill auction observations."
    )

    st.warning(
        "Backtested performance is historical analysis "
        "and does not guarantee future performance."
    )

    # ========================================================
    # PARAMETERS
    # ========================================================

    initial_capital = st.number_input(
        "Initial Capital (KES)",
        min_value=1.0,
        value=1_000_000.0,
        step=10_000.0
    )

    tenor = st.selectbox(
        "Treasury Bill Strategy",
        [91, 182, 364],
        format_func=lambda x:
            f"{x}-Day Treasury Bill"
    )

    if st.button(
        "Run Backtest"
    ):

        try:

            result = (
                backtest_engine
                .rolling_backtest(
                    tenor,
                    initial_capital
                )
            )

            # =================================================
            # SUMMARY
            # =================================================

            st.subheader(
                "Backtest Results"
            )

            c1, c2, c3 = st.columns(3)

            with c1:

                st.metric(
                    "Initial Capital",
                    f"KES {result['initial_capital']:,.2f}"
                )

            with c2:

                st.metric(
                    "Final Value",
                    f"KES {result['final_value']:,.2f}"
                )

            with c3:

                st.metric(
                    "Total Profit",
                    f"KES {result['total_profit']:,.2f}"
                )

            c1, c2, c3 = st.columns(3)

            with c1:

                st.metric(
                    "Total Return",
                    f"{result['total_return'] * 100:.4f}%"
                )

            with c2:

                st.metric(
                    "Annualized Return",
                    f"{result['annualized_return'] * 100:.4f}%"
                )

            with c3:

                st.metric(
                    "Maximum Drawdown",
                    f"{result['maximum_drawdown'] * 100:.4f}%"
                )

            # =================================================
            # EQUITY CURVE
            # =================================================

            st.divider()

            st.subheader(
                "Historical Portfolio Value"
            )

            chart_data = {}

            for item in result[
                "observations"
            ]:

                chart_data[
                    item["date"]
                ] = item["ending_value"]

            st.line_chart(
                chart_data,
                use_container_width=True
            )

            # =================================================
            # RATE HISTORY
            # =================================================

            st.subheader(
                "Historical CBK Yield"
            )

            rate_data = {}

            for item in result[
                "observations"
            ]:

                rate_data[
                    item["date"]
                ] = item["rate"] * 100

            st.line_chart(
                rate_data,
                use_container_width=True
            )

            # =================================================
            # AUCTION RESULTS
            # =================================================

            st.subheader(
                "Auction-by-Auction Results"
            )

            rows = []

            for item in reversed(
                result["observations"]
            ):

                rows.append({
                    "Auction Date":
                        item["date"],

                    "CBK Yield":
                        f"{item['rate'] * 100:.4f}%",

                    "Starting Value":
                        f"KES {item['starting_value']:,.2f}",

                    "Profit":
                        f"KES {item['profit']:,.2f}",

                    "Ending Value":
                        f"KES {item['ending_value']:,.2f}",

                    "Period Return":
                        f"{item['period_return'] * 100:.4f}%"
                })

            st.dataframe(
                rows,
                use_container_width=True,
                hide_index=True
            )

        except Exception as error:

            st.error(
                f"Backtest failed: {error}"
            )

            st.info(
                "This normally means there are not enough "
                "historical observations for the selected "
                "Treasury Bill tenor."
            )

# ============================================================
# STRESS TEST
# ============================================================


elif page == "Stress Testing":

    st.header(
        "Kenyan Fixed-Income Stress Testing"
    )

    st.caption(
        "Scenario analysis for CBK-sensitive "
        "fixed-income portfolios."
    )

    st.warning(
        "Stress scenarios are analytical assumptions. "
        "They are not forecasts of future CBK decisions "
        "or market prices."
    )

    # ========================================================
    # PORTFOLIO INPUTS
    # ========================================================

    st.subheader(
        "Portfolio Structure"
    )

    portfolio_value = st.number_input(
        "Total Portfolio Value (KES)",
        min_value=1.0,
        value=1_000_000.0,
        step=10_000.0
    )

    bond_value = st.number_input(
        "Government Bond Exposure (KES)",
        min_value=0.0,
        value=400_000.0,
        step=10_000.0
    )

    tbill_value = st.number_input(
        "Treasury Bill Exposure (KES)",
        min_value=0.0,
        value=600_000.0,
        step=10_000.0
    )

    # ========================================================
    # BOND RISK
    # ========================================================

    st.subheader(
        "Bond Risk Parameters"
    )

    modified_duration = st.number_input(
        "Modified Duration",
        min_value=0.0,
        value=4.5,
        step=0.1
    )

    convexity = st.number_input(
        "Convexity",
        min_value=0.0,
        value=25.0,
        step=1.0
    )

    # ========================================================
    # T-BILL PARAMETERS
    # ========================================================

    st.subheader(
        "Treasury Bill Parameters"
    )

    tbill_tenor = st.selectbox(
        "T-Bill Tenor",
        [91, 182, 364],
        format_func=lambda x:
            f"{x}-Day Treasury Bill"
    )

    tbill_rate = st.number_input(
        "Current T-Bill Rate (%)",
        min_value=0.0,
        value=9.0,
        step=0.01
    )

    if st.button(
        "Run Stress Test"
    ):

        try:

            # Validate exposures

            if (
                bond_value
                + tbill_value
                > portfolio_value
            ):

                st.error(
                    "Bond and T-Bill exposure cannot "
                    "exceed total portfolio value."
                )

            else:

                results = (
                    stress_engine
                    .stress_report(
                        portfolio_value,
                        bond_value,
                        modified_duration,
                        convexity,
                        tbill_value,
                        tbill_rate / 100,
                        tbill_tenor
                    )
                )

                # =================================================
                # SCENARIO TABLE
                # =================================================

                st.subheader(
                    "CBK Rate Shock Scenarios"
                )

                rows = []

                for result in results:

                    rows.append({

                        "Scenario":
                            result["scenario"],

                        "Rate Shock":
                            f"{result['rate_change'] * 100:+.2f}%",

                        "Bond Impact":
                            f"KES {result['bond_change']:,.2f}",

                        "T-Bill Impact":
                            f"KES {result['tbill_change']:,.2f}",

                        "Total Impact":
                            f"KES {result['total_change']:,.2f}",

                        "Ending Portfolio":
                            f"KES {result['ending_value']:,.2f}"
                    })

                st.dataframe(
                    rows,
                    use_container_width=True,
                    hide_index=True
                )

                # =================================================
                # WORST CASE
                # =================================================

                worst = min(
                    results,
                    key=lambda x:
                        x["total_change"]
                )

                st.divider()

                st.subheader(
                    "Worst Scenario"
                )

                c1, c2, c3 = st.columns(3)

                with c1:

                    st.metric(
                        "Scenario",
                        worst["scenario"]
                    )

                with c2:

                    st.metric(
                        "Portfolio Impact",
                        f"KES {worst['total_change']:,.2f}"
                    )

                with c3:

                    st.metric(
                        "Ending Value",
                        f"KES {worst['ending_value']:,.2f}"
                    )

                # =================================================
                # CHART
                # =================================================

                st.subheader(
                    "Scenario Impact"
                )

                chart = {
                    result["scenario"]:
                        result["total_change"]
                    for result in results
                }

                st.bar_chart(
                    chart,
                    use_container_width=True
                )

                # =================================================
                # CURVE SCENARIOS
                # =================================================

                st.divider()

                st.subheader(
                    "Yield Curve Stress"
                )

                current_rates = (
                    app.get_latest_rates()
                )

                curve_rates = {}

                for tenor in [
                    91,
                    182,
                    364
                ]:

                    if tenor in current_rates:

                        curve_rates[tenor] = (
                            current_rates[
                                tenor
                            ]["rate"]
                        )

                if curve_rates:

                    steep = (
                        stress_engine
                        .steepening(
                            curve_rates
                        )
                    )

                    flat = (
                        stress_engine
                        .flattening(
                            curve_rates
                        )
                    )

                    curve_rows = []

                    for tenor in [
                        91,
                        182,
                        364
                    ]:

                        if tenor not in curve_rates:
                            continue

                        curve_rows.append({

                            "Tenor":
                                f"{tenor}-Day",

                            "Current":
                                f"{curve_rates[tenor] * 100:.4f}%",

                            "Steepening":
                                f"{steep[tenor]['stressed_rate'] * 100:.4f}%",

                            "Flattening":
                                f"{flat[tenor]['stressed_rate'] * 100:.4f}%"
                        })

                    st.dataframe(
                        curve_rows,
                        use_container_width=True,
                        hide_index=True
                    )

                    st.caption(
                        "Yield-curve scenarios are constructed "
                        "from the latest CBK observations in "
                        "kenya_market.db."
                    )

                else:

                    st.info(
                        "Current CBK curve data is unavailable."
                    )

        except Exception as error:

            st.error(
                f"Stress test failed: {error}"
            )

# ============================================================
# FOOTER
# ============================================================

st.sidebar.divider()

st.sidebar.caption(
    "Kenya Financial Analytics"
)

st.sidebar.caption(
    "Research & simulation platform"
)

st.sidebar.caption(
    "No real trades are executed."
)
