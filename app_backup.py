import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from treasury_bills import compare_treasury_bills
from cbk_data import (
    get_treasury_bill_rates,
    get_exchange_rates,
    get_key_rates,
    get_data_date,
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Kenya Financial Analytics",
    page_icon="🇰🇪",
    layout="wide",
)


# ============================================================
# HEADER
# ============================================================

st.title("🇰🇪 Kenya Financial Markets Analytics")

st.markdown(
    """
    **Treasury Bills • FX • Kenyan Market Indicators**
    
    A quantitative-finance dashboard focused on the Kenyan
    financial market.
    """
)

st.divider()


# ============================================================
# CBK MARKET DATA
# ============================================================

st.header("🏦 CBK Market Overview")

data_date = get_data_date()

st.caption(
    f"Market data reference date: {data_date}"
)


# ------------------------------------------------------------
# TREASURY BILL RATES
# ------------------------------------------------------------

tb_rates = get_treasury_bill_rates()

st.subheader("📊 Treasury Bill Rates")

tb1, tb2, tb3 = st.columns(3)


with tb1:

    rate_91 = tb_rates.get("91 Days")

    if rate_91 is not None:

        st.metric(
            "91-Day T-Bill",
            f"{rate_91:.3f}%"
        )

    else:

        st.metric(
            "91-Day T-Bill",
            "N/A"
        )


with tb2:

    rate_182 = tb_rates.get("182 Days")

    if rate_182 is not None:

        st.metric(
            "182-Day T-Bill",
            f"{rate_182:.3f}%"
        )

    else:

        st.metric(
            "182-Day T-Bill",
            "N/A"
        )


with tb3:

    rate_364 = tb_rates.get("364 Days")

    if rate_364 is not None:

        st.metric(
            "364-Day T-Bill",
            f"{rate_364:.3f}%"
        )

    else:

        st.metric(
            "364-Day T-Bill",
            "N/A"
        )


# ============================================================
# FOREIGN EXCHANGE
# ============================================================

st.subheader("💱 Kenyan Shilling Exchange Rates")

fx_rates = get_exchange_rates()

fx1, fx2, fx3 = st.columns(3)


with fx1:

    st.metric(
        "USD / KES",
        f"{fx_rates['USD']:.2f}"
    )


with fx2:

    st.metric(
        "GBP / KES",
        f"{fx_rates['GBP']:.2f}"
    )


with fx3:

    st.metric(
        "EUR / KES",
        f"{fx_rates['EUR']:.2f}"
    )


# ============================================================
# KEY KENYAN RATES
# ============================================================

st.subheader("📈 Kenyan Key Financial Indicators")

key_rates = get_key_rates()

k1, k2, k3, k4 = st.columns(4)


with k1:

    st.metric(
        "CBR",
        f"{key_rates['CBR']:.2f}%"
    )


with k2:

    st.metric(
        "KESONIA",
        f"{key_rates['KESONIA']:.2f}%"
    )


with k3:

    st.metric(
        "CBK Discount Window",
        f"{key_rates['CBK Discount Window']:.2f}%"
    )


with k4:

    st.metric(
        "Inflation",
        f"{key_rates['Inflation']:.2f}%"
    )


st.divider()


# ============================================================
# TREASURY BILL INVESTMENT ANALYZER
# ============================================================

st.header("💰 Treasury Bill Investment Analyzer")

st.write(
    "Enter your investment amount and the applicable "
    "Treasury Bill rates to compare the three standard "
    "Kenyan Treasury Bill maturities."
)


# ============================================================
# INVESTMENT INPUT
# ============================================================

col1, col2 = st.columns(2)


with col1:

    investment = st.number_input(
        "Investment Amount (KSh)",
        min_value=1_000.0,
        value=100_000.0,
        step=10_000.0,
        format="%.2f",
    )


with col2:

    purchase_date = st.date_input(
        "Purchase / Value Date"
    )


# ============================================================
# TREASURY BILL RATES
# ============================================================

st.subheader("Treasury Bill Rates")

st.caption(
    "Enter the applicable auction or market rate. "
    "The 91-day rate is pre-filled from the CBK data module."
)


r1, r2, r3 = st.columns(3)


with r1:

    default_91 = (
        float(rate_91)
        if rate_91 is not None
        else 8.77
    )

    input_rate_91 = st.number_input(
        "91-Day Rate (%)",
        min_value=0.0,
        value=default_91,
        step=0.01,
        format="%.3f",
    )


with r2:

    default_182 = (
        float(rate_182)
        if rate_182 is not None
        else 8.77
    )

    input_rate_182 = st.number_input(
        "182-Day Rate (%)",
        min_value=0.0,
        value=default_182,
        step=0.01,
        format="%.3f",
    )


with r3:

    default_364 = (
        float(rate_364)
        if rate_364 is not None
        else 8.77
    )

    input_rate_364 = st.number_input(
        "364-Day Rate (%)",
        min_value=0.0,
        value=default_364,
        step=0.01,
        format="%.3f",
    )


st.divider()


# ============================================================
# CALCULATION BUTTON
# ============================================================

calculate = st.button(
    "🧮 Calculate & Compare",
    type="primary",
    use_container_width=True,
)


if calculate:

    try:

        rates = {
            "91 Days": input_rate_91 / 100,
            "182 Days": input_rate_182 / 100,
            "364 Days": input_rate_364 / 100,
        }


        # ----------------------------------------------------
        # CALCULATE
        # ----------------------------------------------------

        results = compare_treasury_bills(
            investment=investment,
            rates=rates,
            purchase_date=purchase_date,
        )


        st.success(
            "Treasury Bill analysis completed successfully."
        )


        # ====================================================
        # SUMMARY CARDS
        # ====================================================

        st.header("📊 Investment Results")


        cards = st.columns(3)


        for card, (tenor, result) in zip(
            cards,
            results.items(),
        ):

            with card:

                st.subheader(tenor)

                st.metric(
                    "Maturity Value",
                    f"KSh {result['face_value']:,.2f}",
                )

                st.metric(
                    "Profit",
                    f"KSh {result['profit']:,.2f}",
                )

                st.metric(
                    "Return",
                    f"{result['return']:.2%}",
                )

                st.write(
                    f"**Maturity Date:** "
                    f"{result['maturity_date']}"
                )


        st.divider()


        # ====================================================
        # DETAILED TABLE
        # ====================================================

        st.header("📋 Detailed Comparison")


        rows = []


        for tenor, result in results.items():

            rows.append(
                {
                    "Tenor": tenor,
                    "Rate": result["interest_rate"],
                    "Investment": result["investment"],
                    "Maturity Value": result["face_value"],
                    "Profit": result["profit"],
                    "Return": result["return"],
                    "Annualized Return":
                        result["annualized_return"],
                    "Maturity Date":
                        result["maturity_date"],
                }
            )


        df = pd.DataFrame(rows)


        st.dataframe(
            df.style.format(
                {
                    "Rate": "{:.3%}",
                    "Investment": "KSh {:,.2f}",
                    "Maturity Value": "KSh {:,.2f}",
                    "Profit": "KSh {:,.2f}",
                    "Return": "{:.2%}",
                    "Annualized Return": "{:.2%}",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )


        st.divider()


        # ====================================================
        # PROFIT CHART
        # ====================================================

        st.header("📈 Profit Comparison")


        chart_data = pd.DataFrame(
            {
                "Tenor": list(results.keys()),
                "Profit": [
                    result["profit"]
                    for result in results.values()
                ],
            }
        )


        fig, ax = plt.subplots()


        ax.bar(
            chart_data["Tenor"],
            chart_data["Profit"],
        )


        ax.set_title(
            "Treasury Bill Profit by Tenor"
        )

        ax.set_xlabel(
            "Treasury Bill Tenor"
        )

        ax.set_ylabel(
            "Profit (KSh)"
        )


        plt.tight_layout()


        st.pyplot(fig)


        plt.close(fig)


        # ====================================================
        # BEST OPTION
        # ====================================================

        best_tenor = max(
            results,
            key=lambda tenor:
                results[tenor]["profit"],
        )


        best_result = results[best_tenor]


        st.divider()

        st.header("🏆 Highest Nominal Profit")


        st.success(
            f"The **{best_tenor}** Treasury Bill "
            f"produces the highest nominal profit "
            f"of **KSh {best_result['profit']:,.2f}** "
            f"based on the rates entered."
        )


        # ====================================================
        # INVESTMENT SUMMARY
        # ====================================================

        st.header("📝 Investment Summary")


        summary1, summary2, summary3 = st.columns(3)


        with summary1:

            st.metric(
                "Initial Investment",
                f"KSh {investment:,.2f}",
            )


        with summary2:

            st.metric(
                "Best Maturity Value",
                f"KSh {best_result['face_value']:,.2f}",
            )


        with summary3:

            st.metric(
                "Best Profit",
                f"KSh {best_result['profit']:,.2f}",
            )


        st.info(
            "This calculator provides mathematical "
            "analysis of Treasury Bill returns. "
            "It is not personalized investment advice."
        )


    except Exception as error:

        st.error(
            f"Calculation error: {error}"
        )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "🇰🇪 Kenya Financial Markets Analytics | "
    "Treasury Bills • FX • Market Indicators"
)