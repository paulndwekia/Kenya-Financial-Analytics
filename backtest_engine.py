
"""
============================================================
KENYA FINANCIAL ANALYTICS
CBK TREASURY BILL BACKTESTING ENGINE
============================================================

Uses historical observations from kenya_market.db.

Strategies:
    - Buy-and-hold style analysis
    - Auction-to-auction rolling
    - 91-day
    - 182-day
    - 364-day

IMPORTANT:
Historical results are not guarantees of future returns.
============================================================
"""

import sqlite3
import math
import statistics
from datetime import datetime


DATABASE = "kenya_market.db"


# ============================================================
# LOAD HISTORICAL DATA
# ============================================================

def load_history(tenor):

    connection = sqlite3.connect(
        DATABASE
    )

    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            auction_date,
            tenor_days,
            rate
        FROM treasury_bill_rates
        WHERE tenor_days = ?
        ORDER BY auction_date ASC
    """, (int(tenor),))

    rows = cursor.fetchall()

    connection.close()

    return rows


# ============================================================
# NORMALIZE DATABASE STRUCTURE
# ============================================================

def get_history(tenor):

    rows = load_history(
        tenor
    )

    results = []

    for row in rows:

        try:

            date = datetime.strptime(
                row[0],
                "%Y-%m-%d"
            )

            rate = float(
                row[2]
            )

            if rate > 1:
                rate /= 100

            results.append({
                "date": date,
                "rate": rate,
                "tenor": int(tenor)
            })

        except Exception:

            continue

    return results


# ============================================================
# SINGLE T-BILL RETURN
# ============================================================

def tbill_return(
    face_value,
    rate,
    tenor
):

    price = (
        face_value
        /
        (
            1
            + rate * tenor / 365
        )
    )

    profit = (
        face_value - price
    )

    return {
        "price": price,
        "profit": profit,
        "return": profit / price
    }


# ============================================================
# ROLLING BACKTEST
# ============================================================

def rolling_backtest(
    tenor,
    initial_capital=1_000_000
):

    history = get_history(
        tenor
    )

    if len(history) < 2:

        raise ValueError(
            f"Not enough historical data for "
            f"{tenor}-day Treasury Bills."
        )

    capital = float(
        initial_capital
    )

    starting_capital = capital

    observations = []

    peak = capital

    maximum_drawdown = 0.0

    for item in history:

        rate = item["rate"]

        result = tbill_return(
            capital,
            rate,
            tenor
        )

        profit = result[
            "profit"
        ]

        capital += profit

        if capital > peak:

            peak = capital

        drawdown = (
            capital - peak
        ) / peak

        if drawdown < maximum_drawdown:

            maximum_drawdown = drawdown

        observations.append({
            "date":
                item["date"].strftime(
                    "%Y-%m-%d"
                ),

            "rate":
                rate,

            "starting_value":
                capital - profit,

            "profit":
                profit,

            "ending_value":
                capital,

            "period_return":
                result["return"]
        })

    total_return = (
        capital / starting_capital
    ) - 1

    years = (
        (
            history[-1]["date"]
            - history[0]["date"]
        ).days
        / 365
    )

    if years > 0:

        annualized_return = (
            (
                capital
                / starting_capital
            )
            ** (1 / years)
            - 1
        )

    else:

        annualized_return = 0.0

    returns = [
        item["period_return"]
        for item in observations
    ]

    if len(returns) > 1:

        volatility = (
            statistics.stdev(
                returns
            )
            * math.sqrt(
                len(returns)
            )
        )

    else:

        volatility = 0.0

    return {
        "tenor": tenor,
        "initial_capital":
            starting_capital,

        "final_value":
            capital,

        "total_profit":
            capital - starting_capital,

        "total_return":
            total_return,

        "annualized_return":
            annualized_return,

        "volatility":
            volatility,

        "maximum_drawdown":
            maximum_drawdown,

        "observations":
            observations
    }


# ============================================================
# COMPARE TENORS
# ============================================================

def compare_tenors(
    initial_capital=1_000_000
):

    results = []

    for tenor in [
        91,
        182,
        364
    ]:

        try:

            result = rolling_backtest(
                tenor,
                initial_capital
            )

            results.append(
                result
            )

        except ValueError:

            continue

    return results


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print("KENYA FINANCIAL ANALYTICS")
    print("CBK TREASURY BILL BACKTEST")
    print("=" * 70)

    results = compare_tenors(
        1_000_000
    )

    if not results:

        print()
        print(
            "Not enough historical data."
        )

    else:

        for result in results:

            print()
            print(
                f"{result['tenor']}-DAY T-BILL"
            )

            print(
                "Initial Capital:",
                f"KES {result['initial_capital']:,.2f}"
            )

            print(
                "Final Value:",
                f"KES {result['final_value']:,.2f}"
            )

            print(
                "Total Profit:",
                f"KES {result['total_profit']:,.2f}"
            )

            print(
                "Total Return:",
                f"{result['total_return'] * 100:.4f}%"
            )

            print(
                "Annualized Return:",
                f"{result['annualized_return'] * 100:.4f}%"
            )

            print(
                "Maximum Drawdown:",
                f"{result['maximum_drawdown'] * 100:.4f}%"
            )

            print(
                "Observations:",
                len(result["observations"])
            )

    print()
    print("=" * 70)
    print("BACKTEST ENGINE TEST COMPLETE")
    print("=" * 70)
