
"""
KENYA FINANCIAL ANALYTICS
HISTORICAL BACKTESTING ENGINE

Connects:
    Kenya Market Database
        ?
    Historical Treasury Bill Data
        ?
    Backtesting
        ?
    Performance Analysis
        ?
    Risk Metrics

IMPORTANT:
This is a research and simulation engine.
It does not place real trades.
"""

import math
import statistics

from historical_data import (
    initialize_database,
    get_tenor_history,
    seed_current_cbk_data,
)


# ============================================================
# LOAD HISTORICAL CBK DATA
# ============================================================

def load_historical_rates(tenor_days):

    initialize_database()

    seed_current_cbk_data()

    rows = get_tenor_history(
        tenor_days
    )

    if not rows:

        raise ValueError(
            f"No historical data found for "
            f"{tenor_days}-day Treasury Bills."
        )

    return [
        {
            "date": row[0],
            "tenor": row[1],
            "rate": row[2],
            "source": row[4],
        }
        for row in rows
    ]


# ============================================================
# RATE RETURNS
# ============================================================

def calculate_rate_changes(data):

    if len(data) < 2:

        return []

    changes = []

    for previous, current in zip(
        data,
        data[1:]
    ):

        previous_rate = previous["rate"]
        current_rate = current["rate"]

        if previous_rate == 0:

            continue

        changes.append(
            (
                current_rate
                - previous_rate
            )
            / previous_rate
        )

    return changes


# ============================================================
# RATE MOMENTUM STRATEGY
# ============================================================

def generate_signals(
    data,
    window=2
):

    if window <= 0:

        raise ValueError(
            "Window must be greater than zero."
        )

    rates = [
        item["rate"]
        for item in data
    ]

    signals = [0] * len(rates)

    for i in range(
        window,
        len(rates)
    ):

        recent = rates[
            i - window:i
        ]

        average = (
            sum(recent)
            / len(recent)
        )

        if rates[i] > average:

            # Rising yield signal
            signals[i] = 1

        else:

            signals[i] = 0

    return signals


# ============================================================
# HISTORICAL RATE BACKTEST
# ============================================================

def run_rate_backtest(
    data,
    initial_capital=1_000_000,
    window=2
):

    if len(data) < window + 1:

        raise ValueError(
            "Not enough historical observations "
            "for this backtest."
        )

    signals = generate_signals(
        data,
        window
    )

    capital = initial_capital

    portfolio_values = [
        capital
    ]

    trades = []

    position = False

    for i in range(
        1,
        len(data)
    ):

        signal = signals[i]

        current_rate = data[i][
            "rate"
        ]

        previous_rate = data[i - 1][
            "rate"
        ]

        # ====================================================
        # ENTER POSITION
        # ====================================================

        if signal == 1 and not position:

            position = True

            trades.append(
                {
                    "date":
                        data[i]["date"],

                    "action":
                        "ENTER",

                    "rate":
                        current_rate,
                }
            )

        # ====================================================
        # EXIT POSITION
        # ====================================================

        elif signal == 0 and position:

            position = False

            trades.append(
                {
                    "date":
                        data[i]["date"],

                    "action":
                        "EXIT",

                    "rate":
                        current_rate,
                }
            )

        # ====================================================
        # SIMULATED PORTFOLIO CHANGE
        # ====================================================

        if position:

            rate_change = (
                previous_rate
                - current_rate
            )

            # Simplified fixed-income price
            # sensitivity approximation.
            portfolio_change = (
                -rate_change
                * 5
            )

            capital *= (
                1
                + portfolio_change
            )

        portfolio_values.append(
            capital
        )

    return {
        "initial_capital":
            initial_capital,

        "final_value":
            capital,

        "portfolio_values":
            portfolio_values,

        "trades":
            trades,
    }


# ============================================================
# PERFORMANCE
# ============================================================

def calculate_performance(
    result
):

    values = result[
        "portfolio_values"
    ]

    initial = result[
        "initial_capital"
    ]

    final = result[
        "final_value"
    ]

    total_return = (
        final / initial
    ) - 1

    if len(values) > 2:

        returns = []

        for previous, current in zip(
            values,
            values[1:]
        ):

            if previous > 0:

                returns.append(
                    current / previous - 1
                )

        if len(returns) >= 2:

            volatility = (
                statistics.stdev(
                    returns
                )
                * math.sqrt(252)
            )

        else:

            volatility = 0.0

    else:

        volatility = 0.0

    # ========================================================
    # MAXIMUM DRAWDOWN
    # ========================================================

    peak = values[0]

    maximum_drawdown = 0.0

    for value in values:

        if value > peak:

            peak = value

        drawdown = (
            value - peak
        ) / peak

        if drawdown < maximum_drawdown:

            maximum_drawdown = drawdown

    return {
        "total_return":
            total_return,

        "volatility":
            volatility,

        "maximum_drawdown":
            maximum_drawdown,

        "number_of_trades":
            len(result["trades"]),
    }


# ============================================================
# DISPLAY HISTORICAL DATA
# ============================================================

def display_historical_data(
    data
):

    print()
    print("=" * 75)
    print("HISTORICAL CBK TREASURY BILL DATA")
    print("=" * 75)

    print()

    print(
        f"{'Date':<18}"
        f"{'Tenor':<12}"
        f"{'Rate':<15}"
        f"{'Source':<25}"
    )

    print("-" * 75)

    for item in data:

        print(
            f"{item['date']:<18}"
            f"{item['tenor']:<12}"
            f"{item['rate'] * 100:<14.4f}%"
            f"{item['source']:<25}"
        )

    print("-" * 75)


# ============================================================
# DISPLAY BACKTEST
# ============================================================

def display_backtest(
    result,
    performance
):

    print()
    print("=" * 75)
    print("HISTORICAL TREASURY BILL BACKTEST")
    print("=" * 75)

    print()

    print(
        f"Initial Capital    : "
        f"KES {result['initial_capital']:,.2f}"
    )

    print(
        f"Final Value        : "
        f"KES {result['final_value']:,.2f}"
    )

    print(
        f"Total Return       : "
        f"{performance['total_return'] * 100:.4f}%"
    )

    print(
        f"Annualized Vol.    : "
        f"{performance['volatility'] * 100:.4f}%"
    )

    print(
        f"Maximum Drawdown   : "
        f"{performance['maximum_drawdown'] * 100:.4f}%"
    )

    print(
        f"Trades             : "
        f"{performance['number_of_trades']}"
    )

    print()

    print("TRADES")
    print("-" * 75)

    if not result["trades"]:

        print(
            "No trades generated."
        )

    else:

        for trade in result["trades"]:

            print(
                f"{trade['date']} | "
                f"{trade['action']:<6} | "
                f"Rate: "
                f"{trade['rate'] * 100:.4f}%"
            )

    print("=" * 75)


# ============================================================
# TEST
# ============================================================

def run_test():

    print()
    print("=" * 75)
    print("KENYA FINANCIAL ANALYTICS")
    print("HISTORICAL BACKTESTING ENGINE")
    print("=" * 75)

    tenor = 91

    data = load_historical_rates(
        tenor
    )

    display_historical_data(
        data
    )

    if len(data) < 3:

        print()
        print(
            "NOTICE:"
        )

        print(
            "The database currently contains "
            "only a small seed dataset."
        )

        print(
            "A meaningful historical backtest "
            "requires many verified CBK observations."
        )

        print()

        print(
            "The database connection is working."
        )

    else:

        result = run_rate_backtest(
            data,
            initial_capital=1_000_000,
            window=2
        )

        performance = calculate_performance(
            result
        )

        display_backtest(
            result,
            performance
        )

    print()
    print("=" * 75)
    print(
        "HISTORICAL BACKTESTING ENGINE WORKING"
    )
    print("=" * 75)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    run_test()
