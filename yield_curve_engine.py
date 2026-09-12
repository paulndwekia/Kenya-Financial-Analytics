
"""
KENYA FINANCIAL ANALYTICS
KENYAN TREASURY BILL YIELD CURVE ENGINE

Uses Treasury Bill observations stored in kenya_market.db.

Supported maturities:
    91 days
    182 days
    364 days

The engine calculates:
    - Latest yield by tenor
    - Curve slope
    - Average yield
    - Interpolated yield
    - Curve classification
"""

import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

DATABASE = BASE_DIR / "kenya_market.db"


# ============================================================
# LOAD DATABASE
# ============================================================

def load_latest_rates():

    connection = sqlite3.connect(
        DATABASE
    )

    cursor = connection.cursor()

    rates = {}

    for tenor in [91, 182, 364]:

        cursor.execute(
            """
            SELECT
                auction_date,
                rate
            FROM treasury_bill_rates
            WHERE tenor_days = ?
            ORDER BY auction_date DESC
            LIMIT 1
            """,
            (tenor,)
        )

        row = cursor.fetchone()

        if row:

            rates[tenor] = {
                "date": row[0],
                "rate": row[1],
            }

    connection.close()

    return rates


# ============================================================
# CURVE SLOPES
# ============================================================

def calculate_slopes(rates):

    result = {}

    if 91 in rates and 182 in rates:

        result["91_to_182"] = (
            rates[182]["rate"]
            - rates[91]["rate"]
        )

    if 182 in rates and 364 in rates:

        result["182_to_364"] = (
            rates[364]["rate"]
            - rates[182]["rate"]
        )

    if 91 in rates and 364 in rates:

        result["91_to_364"] = (
            rates[364]["rate"]
            - rates[91]["rate"]
        )

    return result


# ============================================================
# CURVE CLASSIFICATION
# ============================================================

def classify_curve(rates):

    if len(rates) < 2:

        return "INSUFFICIENT DATA"

    ordered = [
        rates[tenor]["rate"]
        for tenor in [91, 182, 364]
        if tenor in rates
    ]

    if len(ordered) < 2:

        return "INSUFFICIENT DATA"

    if all(
        ordered[i] <= ordered[i + 1]
        for i in range(len(ordered) - 1)
    ):

        return "UPWARD SLOPING"

    if all(
        ordered[i] >= ordered[i + 1]
        for i in range(len(ordered) - 1)
    ):

        return "DOWNWARD SLOPING"

    return "MIXED / HUMPED"


# ============================================================
# AVERAGE YIELD
# ============================================================

def calculate_average_yield(rates):

    values = [
        item["rate"]
        for item in rates.values()
    ]

    if not values:

        return 0.0

    return sum(values) / len(values)


# ============================================================
# LINEAR INTERPOLATION
# ============================================================

def interpolate_yield(
    maturity_days,
    rates
):

    points = sorted(
        [
            (
                tenor,
                item["rate"]
            )
            for tenor, item
            in rates.items()
        ]
    )

    if not points:

        return None

    if maturity_days <= points[0][0]:

        return points[0][1]

    if maturity_days >= points[-1][0]:

        return points[-1][1]

    for i in range(
        len(points) - 1
    ):

        x1, y1 = points[i]

        x2, y2 = points[i + 1]

        if x1 <= maturity_days <= x2:

            return (
                y1
                + (
                    (maturity_days - x1)
                    / (x2 - x1)
                )
                * (y2 - y1)
            )

    return None


# ============================================================
# FULL CURVE REPORT
# ============================================================

def build_curve_report():

    rates = load_latest_rates()

    slopes = calculate_slopes(
        rates
    )

    classification = classify_curve(
        rates
    )

    average = calculate_average_yield(
        rates
    )

    return {
        "rates": rates,
        "slopes": slopes,
        "classification":
            classification,
        "average":
            average,
    }


# ============================================================
# DISPLAY
# ============================================================

def display_curve():

    report = build_curve_report()

    print()
    print("=" * 75)
    print("KENYA FINANCIAL ANALYTICS")
    print("KENYAN TREASURY BILL YIELD CURVE")
    print("=" * 75)

    print()

    rates = report["rates"]

    print(
        f"{'Tenor':<15}"
        f"{'Date':<18}"
        f"{'Yield':<15}"
    )

    print("-" * 50)

    for tenor in [
        91,
        182,
        364
    ]:

        if tenor not in rates:

            print(
                f"{tenor}-Day"
                f"{'DATA NOT AVAILABLE':>30}"
            )

            continue

        print(
            f"{tenor}-Day"
            f"{rates[tenor]['date']:>18}"
            f"{rates[tenor]['rate'] * 100:>13.4f}%"
        )

    print("-" * 50)

    print()

    print(
        "Curve Classification:"
    )

    print(
        report["classification"]
    )

    print()

    print(
        "Average Yield:"
    )

    print(
        f"{report['average'] * 100:.4f}%"
    )

    print()

    print(
        "CURVE SLOPES"
    )

    for name, value in report[
        "slopes"
    ].items():

        print(
            f"{name:<15}"
            f"{value * 100:+.4f}%"
        )

    print()

    # Interpolation examples
    print(
        "INTERPOLATED YIELDS"
    )

    for maturity in [
        120,
        150,
        200,
        250,
        300
    ]:

        value = interpolate_yield(
            maturity,
            rates
        )

        if value is not None:

            print(
                f"{maturity:>3} days:"
                f" {value * 100:.4f}%"
            )

    print()
    print("=" * 75)


# ============================================================
# TEST
# ============================================================

def run_test():

    print()
    print(
        "Loading Kenyan Treasury Bill data..."
    )

    display_curve()

    print()

    print(
        "YIELD CURVE ENGINE WORKING"
    )

    print("=" * 75)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    run_test()
