
"""
============================================================
KENYA FINANCIAL ANALYTICS
KENYAN FIXED-INCOME STRESS ENGINE
============================================================

Scenario analysis for Kenyan fixed-income portfolios.

Scenarios include:

    - CBK rate increase
    - CBK rate decrease
    - Yield curve steepening
    - Yield curve flattening
    - Bond yield shock
    - T-Bill reinvestment shock
    - Market-value shock
    - Combined severe scenario

This is analytical scenario modelling.
It does not predict future market movements.
============================================================
"""

import math


# ============================================================
# BASIC SHOCK
# ============================================================

def apply_shock(
    value,
    shock
):

    value = float(value)
    shock = float(shock)

    return {
        "starting_value": value,
        "shock": shock,
        "change": value * shock,
        "ending_value": value * (1 + shock)
    }


# ============================================================
# BOND PRICE APPROXIMATION
# ============================================================

def bond_price_shock(
    market_value,
    modified_duration,
    convexity,
    yield_change
):
    """
    Approximate bond price change:

        ?P/P ? -D ? ?y + 0.5 ? C ? ?y?
    """

    market_value = float(
        market_value
    )

    duration = float(
        modified_duration
    )

    convexity = float(
        convexity
    )

    yield_change = float(
        yield_change
    )

    percentage_change = (
        -duration * yield_change
        +
        0.5 * convexity * yield_change ** 2
    )

    change = (
        market_value
        * percentage_change
    )

    return {
        "starting_value":
            market_value,

        "yield_change":
            yield_change,

        "percentage_change":
            percentage_change,

        "change":
            change,

        "ending_value":
            market_value + change
    }


# ============================================================
# T-BILL REINVESTMENT SHOCK
# ============================================================

def tbill_reinvestment_shock(
    principal,
    current_rate,
    rate_change,
    tenor
):

    principal = float(
        principal
    )

    current_rate = float(
        current_rate
    )

    rate_change = float(
        rate_change
    )

    tenor = int(
        tenor
    )

    current_rate = (
        current_rate
        if current_rate <= 1
        else current_rate / 100
    )

    new_rate = (
        current_rate
        + rate_change
    )

    current_income = (
        principal
        * current_rate
        * tenor
        / 365
    )

    stressed_income = (
        principal
        * new_rate
        * tenor
        / 365
    )

    income_change = (
        stressed_income
        - current_income
    )

    return {
        "principal":
            principal,

        "current_rate":
            current_rate,

        "stressed_rate":
            new_rate,

        "current_income":
            current_income,

        "stressed_income":
            stressed_income,

        "income_change":
            income_change
    }


# ============================================================
# YIELD CURVE SCENARIOS
# ============================================================

def curve_scenario(
    rates,
    short_change,
    long_change
):

    result = {}

    for tenor, rate in rates.items():

        if tenor <= 182:

            change = short_change

        else:

            change = long_change

        result[tenor] = {
            "current_rate":
                rate,

            "stressed_rate":
                rate + change,

            "change":
                change
        }

    return result


def steepening(
    rates,
    magnitude=0.01
):

    return curve_scenario(
        rates,
        -magnitude / 2,
        magnitude / 2
    )


def flattening(
    rates,
    magnitude=0.01
):

    return curve_scenario(
        rates,
        magnitude / 2,
        -magnitude / 2
    )


# ============================================================
# COMPLETE PORTFOLIO SCENARIO
# ============================================================

def portfolio_scenario(
    portfolio_value,
    market_shock
):

    return apply_shock(
        portfolio_value,
        market_shock
    )


# ============================================================
# KENYAN RATE SCENARIOS
# ============================================================

def cbk_rate_scenarios():

    return [
        {
            "name":
                "CBK +50 bps",

            "rate_change":
                0.005
        },

        {
            "name":
                "CBK +100 bps",

            "rate_change":
                0.010
        },

        {
            "name":
                "CBK +200 bps",

            "rate_change":
                0.020
        },

        {
            "name":
                "CBK -50 bps",

            "rate_change":
                -0.005
        },

        {
            "name":
                "CBK -100 bps",

            "rate_change":
                -0.010
        }
    ]


# ============================================================
# COMPLETE STRESS REPORT
# ============================================================

def stress_report(
    portfolio_value,
    bond_value,
    modified_duration,
    convexity,
    tbill_value,
    tbill_rate,
    tbill_tenor
):

    scenarios = []

    for scenario in cbk_rate_scenarios():

        rate_change = scenario[
            "rate_change"
        ]

        bond_result = bond_price_shock(
            bond_value,
            modified_duration,
            convexity,
            rate_change
        )

        tbill_result = (
            tbill_reinvestment_shock(
                tbill_value,
                tbill_rate,
                rate_change,
                tbill_tenor
            )
        )

        total_change = (
            bond_result["change"]
            +
            tbill_result["income_change"]
        )

        ending_value = (
            portfolio_value
            + total_change
        )

        scenarios.append({

            "scenario":
                scenario["name"],

            "rate_change":
                rate_change,

            "bond_change":
                bond_result["change"],

            "tbill_change":
                tbill_result["income_change"],

            "total_change":
                total_change,

            "ending_value":
                ending_value
        })

    return scenarios


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    portfolio = 1_000_000

    bond = 400_000

    tbill = 600_000

    results = stress_report(
        portfolio_value=portfolio,
        bond_value=bond,
        modified_duration=4.5,
        convexity=25.0,
        tbill_value=tbill,
        tbill_rate=0.09,
        tbill_tenor=91
    )

    print()
    print("=" * 70)
    print("KENYA FINANCIAL ANALYTICS")
    print("STRESS ENGINE TEST")
    print("=" * 70)

    for result in results:

        print()
        print(
            result["scenario"]
        )

        print(
            "Rate Shock:",
            f"{result['rate_change'] * 100:+.2f}%"
        )

        print(
            "Bond Impact:",
            f"KES {result['bond_change']:,.2f}"
        )

        print(
            "T-Bill Impact:",
            f"KES {result['tbill_change']:,.2f}"
        )

        print(
            "Total Impact:",
            f"KES {result['total_change']:,.2f}"
        )

        print(
            "Ending Portfolio:",
            f"KES {result['ending_value']:,.2f}"
        )

    print()
    print("=" * 70)
    print("STRESS ENGINE TEST COMPLETE")
    print("=" * 70)
