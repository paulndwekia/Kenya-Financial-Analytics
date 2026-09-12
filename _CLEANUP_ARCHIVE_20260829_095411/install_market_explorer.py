from pathlib import Path
import shutil

dashboard = Path("dashboard.py")

if not dashboard.exists():
    print("ERROR: dashboard.py not found.")
    raise SystemExit(1)

# Backup first
backup = Path("dashboard_backup_before_market_explorer.py")
shutil.copy2(dashboard, backup)

text = dashboard.read_text(encoding="utf-8")

# ------------------------------------------------------------
# IMPORT PANDAS IF NEEDED
# ------------------------------------------------------------

if "import pandas as pd" not in text:
    text = "import pandas as pd\n" + text

# ------------------------------------------------------------
# ADD HISTORICAL MARKET EXPLORER
# ------------------------------------------------------------

if 'page == "Historical Market Explorer"' not in text:

    page_code = r'''
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

'''

    # --------------------------------------------------------
    # FIND A PAGE TO INSERT BEFORE
    # --------------------------------------------------------

    page_markers = [
        'elif page == "Backtesting":',
        'elif page == "Stress Testing":',
        'elif page == "Portfolio":'
    ]

    positions = []

    for marker in page_markers:

        position = text.find(marker)

        if position != -1:

            positions.append(position)

    if positions:

        insert_position = min(positions)

        text = (
            text[:insert_position]
            + page_code
            + "\n"
            + text[insert_position:]
        )

    else:

        print(
            "WARNING: Could not locate an existing page "
            "section automatically."
        )

# ------------------------------------------------------------
# SAVE
# ------------------------------------------------------------

dashboard.write_text(
    text,
    encoding="utf-8"
)

print()
print("=" * 70)
print("HISTORICAL MARKET EXPLORER INSTALLED")
print("=" * 70)
print()
print("Backup:")
print(backup.resolve())
print()
print("Dashboard:")
print(dashboard.resolve())
print()
print("Start with:")
print(
    "python -m streamlit run dashboard.py"
)
print("=" * 70)
