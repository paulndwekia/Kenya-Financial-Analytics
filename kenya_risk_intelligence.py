
import sqlite3
from pathlib import Path
import pandas as pd
import streamlit as st

DATABASE = Path(__file__).resolve().parent / "kenya_market.db"


def load_cbk_history():

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


def classify_risk(volatility):

    if volatility >= 0.20:
        return "HIGH"

    if volatility >= 0.10:
        return "MODERATE"

    return "LOW"


def render_risk_intelligence():

    st.header("🇰🇪 Kenya Risk Intelligence")

    st.caption(
        "Historical CBK Treasury Bill risk analysis."
    )

    data = load_cbk_history()

    if data.empty:

        st.warning(
            "No CBK Treasury Bill data is available."
        )

        return

    available = sorted(
        data["tenor_days"].unique().tolist()
    )

    preferred = [91, 182, 364]

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
            f"{x}-Day Treasury Bill"
    )

    if not selected:
        st.info(
            "Select at least one tenor."
        )
        return

    filtered = data[
        data["tenor_days"].isin(selected)
    ].copy()

    filtered = filtered.sort_values(
        "auction_date"
    )

    # ========================================================
    # OVERVIEW
    # ========================================================

    st.subheader("Risk Overview")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Observations",
            f"{len(filtered):,}"
        )

    with c2:
        st.metric(
            "Tenors",
            f"{len(selected)}"
        )

    with c3:
        st.metric(
            "First Date",
            filtered["auction_date"]
            .min()
            .strftime("%d %b %Y")
        )

    with c4:
        st.metric(
            "Latest Date",
            filtered["auction_date"]
            .max()
            .strftime("%d %b %Y")
        )

    # ========================================================
    # RISK TABLE
    # ========================================================

    st.divider()

    st.subheader(
        "Treasury Bill Risk Metrics"
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

        latest = float(
            rates.iloc[-1]
        )

        average = float(
            rates.mean()
        )

        highest = float(
            rates.max()
        )

        lowest = float(
            rates.min()
        )

        volatility = float(
            rates.std()
        )

        movement = (
            latest
            - float(rates.iloc[0])
        )

        rows.append({
            "Tenor":
                f"{tenor}-Day",

            "Latest Yield":
                f"{latest * 100:.4f}%",

            "Average Yield":
                f"{average * 100:.4f}%",

            "Highest Yield":
                f"{highest * 100:.4f}%",

            "Lowest Yield":
                f"{lowest * 100:.4f}%",

            "Total Movement":
                f"{movement * 100:+.4f} pp",

            "Volatility":
                f"{volatility * 100:.4f}%",

            "Risk Level":
                classify_risk(
                    volatility
                )
        })

    if rows:

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True
        )

    # ========================================================
    # INDIVIDUAL ANALYSIS
    # ========================================================

    st.divider()

    st.subheader(
        "Automatic Risk Interpretation"
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

        volatility = float(
            rates.std()
        )

        change = (
            latest
            - float(rates.iloc[0])
        )

        st.markdown(
            f"### {tenor}-Day Treasury Bill"
        )

        if change > 0.0005:

            direction = "increased"

        elif change < -0.0005:

            direction = "decreased"

        else:

            direction = "remained broadly stable"

        st.write(
            f"The historical yield has **{direction}** "
            f"by {change * 100:+.4f} percentage points "
            f"between the first and latest observation."
        )

        difference = latest - average

        if difference > 0.0005:

            st.info(
                f"The latest yield is "
                f"{difference * 100:.4f} percentage points "
                f"above its historical average."
            )

        elif difference < -0.0005:

            st.info(
                f"The latest yield is "
                f"{abs(difference) * 100:.4f} percentage points "
                f"below its historical average."
            )

        else:

            st.info(
                "The latest yield is close to its "
                "historical average."
            )

        st.write(
            f"Historical yield volatility: "
            f"**{volatility * 100:.4f}%** "
            f"— classified as **{classify_risk(volatility)}** "
            f"under this model."
        )

    # ========================================================
    # TREND
    # ========================================================

    st.divider()

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
    # RECENT MOVEMENT
    # ========================================================

    st.subheader(
        "Recent Yield Movement"
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
            pd.DataFrame(movement_rows),
            use_container_width=True,
            hide_index=True
        )

    # ========================================================
    # DATA QUALITY
    # ========================================================

    st.divider()

    st.subheader(
        "Data Quality"
    )

    duplicates = data.duplicated(
        subset=[
            "auction_date",
            "tenor_days"
        ]
    ).sum()

    if duplicates == 0:

        st.success(
            "No duplicate date/tenor observations detected."
        )

    else:

        st.warning(
            f"{duplicates} duplicate observations detected."
        )

    st.caption(
        "This module describes historical market behaviour. "
        "It is not a forecast or investment recommendation."
    )
