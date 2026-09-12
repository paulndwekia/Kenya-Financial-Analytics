
"""
============================================================
KENYA FINANCIAL ANALYTICS
RISK ENGINE
============================================================

Portfolio risk analytics:

- Historical VaR
- Parametric VaR
- Expected Shortfall / CVaR
- Volatility
- Sharpe Ratio
- Sortino Ratio
- Maximum Drawdown
- Stress Testing
- Scenario Analysis

All calculations are research/analysis tools.
They do not execute real trades.
============================================================
"""

import math
import statistics


# ============================================================
# VALIDATION
# ============================================================

def validate_returns(returns):

    values = [
        float(x)
        for x in returns
        if x is not None
    ]

    if len(values) < 2:
        raise ValueError(
            "At least two return observations are required."
        )

    return values


def validate_confidence(confidence):

    confidence = float(confidence)

    if not 0 < confidence < 1:
        raise ValueError(
            "Confidence must be between 0 and 1."
        )

    return confidence


# ============================================================
# VOLATILITY
# ============================================================

def volatility(
    returns,
    annualization=252
):

    values = validate_returns(
        returns
    )

    return (
        statistics.stdev(values)
        * math.sqrt(annualization)
    )


# ============================================================
# HISTORICAL VAR
# ============================================================

def historical_var(
    returns,
    portfolio_value,
    confidence=0.95
):

    values = validate_returns(
        returns
    )

    confidence = validate_confidence(
        confidence
    )

    sorted_returns = sorted(
        values
    )

    index = int(
        (1 - confidence)
        * len(sorted_returns)
    )

    index = max(
        0,
        min(
            index,
            len(sorted_returns) - 1
        )
    )

    loss_return = sorted_returns[
        index
    ]

    return max(
        0,
        -loss_return
        * portfolio_value
    )


# ============================================================
# PARAMETRIC VAR
# ============================================================

def parametric_var(
    returns,
    portfolio_value,
    confidence=0.95
):

    values = validate_returns(
        returns
    )

    confidence = validate_confidence(
        confidence
    )

    mean = statistics.mean(
        values
    )

    stdev = statistics.stdev(
        values
    )

    # Standard normal approximation
    if confidence >= 0.99:
        z = 2.32635
    elif confidence >= 0.975:
        z = 1.95996
    elif confidence >= 0.95:
        z = 1.64485
    else:
        z = 1.28155

    loss = (
        z * stdev - mean
    )

    return max(
        0,
        loss * portfolio_value
    )


# ============================================================
# EXPECTED SHORTFALL
# ============================================================

def expected_shortfall(
    returns,
    portfolio_value,
    confidence=0.95
):

    values = validate_returns(
        returns
    )

    confidence = validate_confidence(
        confidence
    )

    sorted_returns = sorted(
        values
    )

    cutoff = int(
        (1 - confidence)
        * len(sorted_returns)
    )

    cutoff = max(
        1,
        cutoff
    )

    tail = sorted_returns[
        :cutoff
    ]

    average_tail = statistics.mean(
        tail
    )

    return max(
        0,
        -average_tail
        * portfolio_value
    )


# ============================================================
# SHARPE
# ============================================================

def sharpe_ratio(
    returns,
    risk_free_rate=0.0,
    annualization=252
):

    values = validate_returns(
        returns
    )

    rf_daily = (
        float(risk_free_rate)
        / annualization
    )

    excess = [
        value - rf_daily
        for value in values
    ]

    deviation = statistics.stdev(
        values
    )

    if deviation == 0:
        return 0.0

    return (
        statistics.mean(excess)
        / deviation
        * math.sqrt(annualization)
    )


# ============================================================
# SORTINO
# ============================================================

def sortino_ratio(
    returns,
    target_return=0.0,
    annualization=252
):

    values = validate_returns(
        returns
    )

    downside = [
        min(
            value - target_return,
            0
        )
        for value in values
    ]

    downside_squared = [
        value ** 2
        for value in downside
    ]

    downside_deviation = math.sqrt(
        statistics.mean(
            downside_squared
        )
    )

    if downside_deviation == 0:
        return 0.0

    annual_return = (
        statistics.mean(values)
        * annualization
    )

    annual_target = (
        target_return
        * annualization
    )

    return (
        annual_return - annual_target
    ) / (
        downside_deviation
        * math.sqrt(annualization)
    )


# ============================================================
# MAXIMUM DRAWDOWN
# ============================================================

def maximum_drawdown(
    returns,
    initial_value=1_000_000
):

    values = validate_returns(
        returns
    )

    portfolio = float(
        initial_value
    )

    peak = portfolio
    max_drawdown = 0.0

    for daily_return in values:

        portfolio *= (
            1 + daily_return
        )

        if portfolio > peak:
            peak = portfolio

        drawdown = (
            portfolio - peak
        ) / peak

        if drawdown < max_drawdown:
            max_drawdown = drawdown

    return {
        "drawdown":
            max_drawdown,

        "percentage":
            max_drawdown * 100,

        "ending_value":
            portfolio,

        "peak_value":
            peak
    }


# ============================================================
# STRESS TEST
# ============================================================

def stress_test(
    portfolio_value,
    scenarios
):

    results = []

    portfolio_value = float(
        portfolio_value
    )

    for name, shock in scenarios:

        shock = float(
            shock
        )

        loss = (
            portfolio_value
            * shock
        )

        ending_value = (
            portfolio_value
            + loss
        )

        results.append({
            "Scenario": name,
            "Shock": shock,
            "Loss": loss,
            "Ending Value":
                ending_value
        })

    return results


# ============================================================
# COMPLETE RISK REPORT
# ============================================================

def risk_report(
    returns,
    portfolio_value,
    risk_free_rate=0.0
):

    return {

        "volatility":
            volatility(
                returns
            ),

        "historical_var_95":
            historical_var(
                returns,
                portfolio_value,
                0.95
            ),

        "historical_var_99":
            historical_var(
                returns,
                portfolio_value,
                0.99
            ),

        "parametric_var_95":
            parametric_var(
                returns,
                portfolio_value,
                0.95
            ),

        "parametric_var_99":
            parametric_var(
                returns,
                portfolio_value,
                0.99
            ),

        "expected_shortfall_95":
            expected_shortfall(
                returns,
                portfolio_value,
                0.95
            ),

        "expected_shortfall_99":
            expected_shortfall(
                returns,
                portfolio_value,
                0.99
            ),

        "sharpe":
            sharpe_ratio(
                returns,
                risk_free_rate
            ),

        "sortino":
            sortino_ratio(
                returns
            ),

        "maximum_drawdown":
            maximum_drawdown(
                returns,
                portfolio_value
            )
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    sample_returns = [
        0.002,
        -0.004,
        0.001,
        -0.006,
        0.003,
        -0.002,
        0.004,
        -0.003,
        0.001,
        -0.005,
        0.002,
        0.003,
        -0.001,
        -0.004,
        0.002,
        0.001,
        -0.002,
        0.003,
        -0.001,
        0.002
    ]

    report = risk_report(
        sample_returns,
        1_000_000,
        0.09
    )

    print()
    print("=" * 70)
    print("KENYA FINANCIAL ANALYTICS")
    print("RISK ENGINE TEST")
    print("=" * 70)

    print(
        f"Annualized Volatility: "
        f"{report['volatility'] * 100:.4f}%"
    )

    print(
        f"Historical VaR 95%: "
        f"KES {report['historical_var_95']:,.2f}"
    )

    print(
        f"Historical VaR 99%: "
        f"KES {report['historical_var_99']:,.2f}"
    )

    print(
        f"Parametric VaR 95%: "
        f"KES {report['parametric_var_95']:,.2f}"
    )

    print(
        f"Parametric VaR 99%: "
        f"KES {report['parametric_var_99']:,.2f}"
    )

    print(
        f"Expected Shortfall 95%: "
        f"KES {report['expected_shortfall_95']:,.2f}"
    )

    print(
        f"Expected Shortfall 99%: "
        f"KES {report['expected_shortfall_99']:,.2f}"
    )

    print(
        f"Sharpe Ratio: "
        f"{report['sharpe']:.4f}"
    )

    print(
        f"Sortino Ratio: "
        f"{report['sortino']:.4f}"
    )

    print(
        f"Maximum Drawdown: "
        f"{report['maximum_drawdown']['percentage']:.4f}%"
    )

    print()
    print("=" * 70)
    print("RISK ENGINE TEST COMPLETE")
    print("=" * 70)
