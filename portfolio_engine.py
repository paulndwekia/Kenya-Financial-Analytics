
"""
============================================================
KENYA FINANCIAL ANALYTICS
PORTFOLIO ENGINE
============================================================

Portfolio construction and analysis.

Features:
    - Asset allocation
    - Weighted yield
    - Expected return
    - Portfolio volatility
    - Concentration
    - P&L
    - Diversification
    - Portfolio VaR
    - Stress testing

Currency:
    KES

This is an analytical engine.
It does not execute trades.
============================================================
"""

import math
import statistics


# ============================================================
# VALIDATION
# ============================================================

def validate_assets(assets):

    if not assets:

        raise ValueError(
            "At least one portfolio asset is required."
        )

    for asset in assets:

        required = [
            "name",
            "value",
            "expected_return",
            "volatility"
        ]

        for field in required:

            if field not in asset:

                raise ValueError(
                    f"Missing portfolio field: {field}"
                )

        if float(asset["value"]) < 0:

            raise ValueError(
                "Asset value cannot be negative."
            )


# ============================================================
# PORTFOLIO VALUE
# ============================================================

def total_value(assets):

    validate_assets(assets)

    return sum(
        float(asset["value"])
        for asset in assets
    )


# ============================================================
# ALLOCATION
# ============================================================

def allocation(assets):

    validate_assets(assets)

    total = total_value(
        assets
    )

    if total <= 0:

        raise ValueError(
            "Portfolio value must be greater than zero."
        )

    results = []

    for asset in assets:

        value = float(
            asset["value"]
        )

        weight = (
            value / total
        )

        results.append({
            "name":
                asset["name"],

            "value":
                value,

            "weight":
                weight
        })

    return results


# ============================================================
# WEIGHTED EXPECTED RETURN
# ============================================================

def expected_return(assets):

    validate_assets(assets)

    total = total_value(
        assets
    )

    if total <= 0:
        return 0.0

    result = 0.0

    for asset in assets:

        weight = (
            float(asset["value"])
            / total
        )

        result += (
            weight
            * float(
                asset["expected_return"]
            )
        )

    return result


# ============================================================
# WEIGHTED YIELD
# ============================================================

def weighted_yield(assets):

    return expected_return(
        assets
    )


# ============================================================
# PORTFOLIO VOLATILITY
# ============================================================

def portfolio_volatility(
    assets
):

    validate_assets(assets)

    total = total_value(
        assets
    )

    if total <= 0:
        return 0.0

    # Independent-asset approximation.
    variance = 0.0

    for asset in assets:

        weight = (
            float(asset["value"])
            / total
        )

        volatility = float(
            asset["volatility"]
        )

        variance += (
            weight ** 2
            * volatility ** 2
        )

    return math.sqrt(
        variance
    )


# ============================================================
# PORTFOLIO P&L
# ============================================================

def portfolio_pnl(
    assets
):

    validate_assets(assets)

    total = total_value(
        assets
    )

    expected = expected_return(
        assets
    )

    return {
        "expected_annual_pnl":
            total * expected,

        "portfolio_value":
            total,

        "expected_return":
            expected
    }


# ============================================================
# CONCENTRATION
# ============================================================

def concentration(
    assets
):

    weights = [
        item["weight"]
        for item in allocation(
            assets
        )
    ]

    if not weights:

        return 0.0

    largest = max(
        weights
    )

    hhi = sum(
        weight ** 2
        for weight in weights
    )

    return {
        "largest_weight":
            largest,

        "largest_weight_percent":
            largest * 100,

        "hhi":
            hhi
    }


# ============================================================
# DIVERSIFICATION SCORE
# ============================================================

def diversification_score(
    assets
):

    data = concentration(
        assets
    )

    hhi = data["hhi"]

    # 1 = well diversified
    # 0 = completely concentrated

    score = max(
        0.0,
        min(
            1.0,
            1.0 - hhi
        )
    )

    return score


# ============================================================
# PORTFOLIO VAR
# ============================================================

def portfolio_var(
    assets,
    confidence=0.95
):

    total = total_value(
        assets
    )

    volatility = portfolio_volatility(
        assets
    )

    if confidence >= 0.99:

        z = 2.32635

    elif confidence >= 0.95:

        z = 1.64485

    else:

        z = 1.28155

    return (
        z
        * volatility
        * total
        / math.sqrt(252)
    )


# ============================================================
# STRESS TEST
# ============================================================

def stress_test(
    assets,
    shock
):

    total = total_value(
        assets
    )

    shock = float(
        shock
    )

    change = (
        total * shock
    )

    return {
        "portfolio_value":
            total,

        "shock":
            shock,

        "change":
            change,

        "ending_value":
            total + change
    }


# ============================================================
# COMPLETE REPORT
# ============================================================

def portfolio_report(
    assets
):

    total = total_value(
        assets
    )

    expected = expected_return(
        assets
    )

    volatility = portfolio_volatility(
        assets
    )

    concentration_data = concentration(
        assets
    )

    return {
        "total_value":
            total,

        "expected_return":
            expected,

        "expected_pnl":
            total * expected,

        "volatility":
            volatility,

        "var_95":
            portfolio_var(
                assets,
                0.95
            ),

        "var_99":
            portfolio_var(
                assets,
                0.99
            ),

        "concentration":
            concentration_data,

        "diversification_score":
            diversification_score(
                assets
            )
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    sample_assets = [

        {
            "name":
                "91-Day Treasury Bill",

            "value":
                300_000,

            "expected_return":
                0.085,

            "volatility":
                0.02
        },

        {
            "name":
                "182-Day Treasury Bill",

            "value":
                300_000,

            "expected_return":
                0.088,

            "volatility":
                0.025
        },

        {
            "name":
                "364-Day Treasury Bill",

            "value":
                250_000,

            "expected_return":
                0.090,

            "volatility":
                0.035
        },

        {
            "name":
                "Government Bond",

            "value":
                150_000,

            "expected_return":
                0.100,

            "volatility":
                0.08
        }
    ]

    report = portfolio_report(
        sample_assets
    )

    print()
    print("=" * 70)
    print("KENYA FINANCIAL ANALYTICS")
    print("PORTFOLIO ENGINE TEST")
    print("=" * 70)

    print(
        f"Portfolio Value: "
        f"KES {report['total_value']:,.2f}"
    )

    print(
        f"Expected Return: "
        f"{report['expected_return'] * 100:.4f}%"
    )

    print(
        f"Expected Annual P&L: "
        f"KES {report['expected_pnl']:,.2f}"
    )

    print(
        f"Portfolio Volatility: "
        f"{report['volatility'] * 100:.4f}%"
    )

    print(
        f"VaR 95%: "
        f"KES {report['var_95']:,.2f}"
    )

    print(
        f"VaR 99%: "
        f"KES {report['var_99']:,.2f}"
    )

    print(
        f"Largest Position: "
        f"{report['concentration']['largest_weight_percent']:.2f}%"
    )

    print(
        f"Diversification Score: "
        f"{report['diversification_score']:.4f}"
    )

    print()
    print("=" * 70)
    print("PORTFOLIO ENGINE TEST COMPLETE")
    print("=" * 70)
