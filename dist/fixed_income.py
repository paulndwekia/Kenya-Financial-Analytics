
"""
KENYA FINANCIAL ANALYTICS
=========================

CENTRAL KENYAN FIXED-INCOME ENGINE

Combines:
    CBK Treasury Bill data
    Treasury Bill pricing
    Yield curve
    Bond pricing
    Duration
    Convexity
    Interest-rate scenarios
"""

from cbk_data import get_all_treasury_bills
from treasury_bills import calculate_treasury_bill
from yield_curve import (
    get_curve_data,
    interpolate_rate,
    curve_slope,
    curve_shape,
    forward_rate,
)
from bond_pricing import (
    analyze_bond,
    price_sensitivity,
)


# ============================================================
# MARKET OVERVIEW
# ============================================================

def market_overview():

    data = get_all_treasury_bills()

    results = []

    for days in [91, 182, 364]:

        bill = data[days]

        results.append(
            {
                "tenor": days,
                "name": bill["name"],
                "rate": bill["rate"],
            }
        )

    return results


# ============================================================
# TREASURY BILL ANALYSIS
# ============================================================

def analyze_treasury_bills(
    investment=100_000
):

    data = get_all_treasury_bills()

    results = []

    for days in [91, 182, 364]:

        bill = data[days]

        result = calculate_treasury_bill(
            face_value=investment,
            annual_rate=bill["rate"],
            tenor_days=days,
        )

        results.append(
            {
                "tenor": days,
                "rate": bill["rate"],
                "purchase_price":
                    result.purchase_price,
                "profit":
                    result.profit,
                "annualized_return":
                    result.annualized_return,
            }
        )

    return results


# ============================================================
# YIELD CURVE ANALYSIS
# ============================================================

def analyze_yield_curve():

    curve = get_curve_data()

    return {
        "curve": curve,
        "slope": curve_slope(),
        "shape": curve_shape(),
    }


# ============================================================
# INTERPOLATED YIELD
# ============================================================

def estimated_yield(
    maturity_days
):

    return interpolate_rate(
        maturity_days
    )


# ============================================================
# FORWARD RATE
# ============================================================

def estimated_forward_rate(
    start_days,
    end_days
):

    return forward_rate(
        start_days,
        end_days
    )


# ============================================================
# BOND ANALYSIS
# ============================================================

def analyze_fixed_income_bond(
    face_value,
    coupon_rate,
    yield_rate,
    maturity_years,
    payments_per_year=2,
):

    return analyze_bond(
        face_value=face_value,
        coupon_rate=coupon_rate,
        yield_rate=yield_rate,
        years=maturity_years,
        payments_per_year=payments_per_year,
    )


# ============================================================
# INTEREST-RATE STRESS TEST
# ============================================================

def stress_test_bond(
    face_value,
    coupon_rate,
    yield_rate,
    maturity_years,
    yield_change,
    payments_per_year=2,
):

    return price_sensitivity(
        face_value=face_value,
        coupon_rate=coupon_rate,
        yield_rate=yield_rate,
        years=maturity_years,
        yield_change=yield_change,
        payments_per_year=payments_per_year,
    )


# ============================================================
# COMPLETE MARKET ANALYSIS
# ============================================================

def complete_analysis(
    investment=100_000
):

    return {
        "market": market_overview(),

        "treasury_bills":
            analyze_treasury_bills(
                investment
            ),

        "yield_curve":
            analyze_yield_curve(),
    }


# ============================================================
# DISPLAY MARKET
# ============================================================

def display_market():

    data = market_overview()

    print()
    print("=" * 75)
    print("KENYA FIXED-INCOME MARKET")
    print("=" * 75)

    print()
    print(
        f"{'Instrument':<30}"
        f"{'Tenor':<12}"
        f"{'Yield':<15}"
    )

    print("-" * 75)

    for item in data:

        print(
            f"{item['name']:<30}"
            f"{item['tenor']} days"
            f"{'':<4}"
            f"{item['rate'] * 100:.4f}%"
        )

    print("=" * 75)


# ============================================================
# DISPLAY TREASURY BILL ANALYSIS
# ============================================================

def display_treasury_analysis():

    results = analyze_treasury_bills()

    print()
    print("=" * 75)
    print("TREASURY BILL INVESTMENT ANALYSIS")
    print("=" * 75)

    print()
    print(
        f"{'Tenor':<12}"
        f"{'Rate':<14}"
        f"{'Purchase Price':<22}"
        f"{'Profit':<18}"
    )

    print("-" * 75)

    for item in results:

        print(
            f"{item['tenor']} days"
            f"{'':<4}"
            f"{item['rate'] * 100:.4f}%"
            f"{'':<5}"
            f"KES {item['purchase_price']:,.2f}"
            f"{'':<4}"
            f"KES {item['profit']:,.2f}"
        )

    print("=" * 75)


# ============================================================
# DISPLAY YIELD CURVE
# ============================================================

def display_yield_curve():

    analysis = analyze_yield_curve()

    print()
    print("=" * 75)
    print("KENYAN TREASURY BILL YIELD CURVE")
    print("=" * 75)

    print()

    for point in analysis["curve"]:

        print(
            f"{point['days']:>3} days : "
            f"{point['rate'] * 100:.4f}%"
        )

    print()

    print(
        f"Slope : "
        f"{analysis['slope'] * 100:.4f}%"
    )

    print(
        f"Shape : "
        f"{analysis['shape']}"
    )

    print("=" * 75)


# ============================================================
# BOND TEST
# ============================================================

def display_bond_analysis():

    result = analyze_fixed_income_bond(
        face_value=1_000_000,
        coupon_rate=0.10,
        yield_rate=0.095,
        maturity_years=5,
        payments_per_year=2,
    )

    print()
    print("=" * 75)
    print("KENYAN BOND ANALYSIS")
    print("=" * 75)

    print()

    print(
        f"Face Value        : "
        f"KES {result['face_value']:,.2f}"
    )

    print(
        f"Coupon Rate       : "
        f"{result['coupon_rate'] * 100:.4f}%"
    )

    print(
        f"Yield             : "
        f"{result['yield_rate'] * 100:.4f}%"
    )

    print(
        f"Maturity          : "
        f"{result['years']:.2f} years"
    )

    print(
        f"Bond Price        : "
        f"KES {result['price']:,.2f}"
    )

    print(
        f"Macaulay Duration : "
        f"{result['macaulay_duration']:.4f}"
    )

    print(
        f"Modified Duration : "
        f"{result['modified_duration']:.4f}"
    )

    print(
        f"Convexity         : "
        f"{result['convexity']:.4f}"
    )

    print("=" * 75)


# ============================================================
# STRESS TEST
# ============================================================

def display_stress_test():

    result = stress_test_bond(
        face_value=1_000_000,
        coupon_rate=0.10,
        yield_rate=0.095,
        maturity_years=5,
        yield_change=0.01,
        payments_per_year=2,
    )

    print()
    print("=" * 75)
    print("INTEREST-RATE STRESS TEST")
    print("=" * 75)

    print()

    print(
        "Scenario: Yield increases by 1.00%"
    )

    print()

    print(
        f"Current Price      : "
        f"KES {result['current_price']:,.2f}"
    )

    print(
        f"Estimated Price    : "
        f"KES {result['estimated_price']:,.2f}"
    )

    print(
        f"Estimated Change   : "
        f"{result['estimated_change_percent']:.4f}%"
    )

    print("=" * 75)


# ============================================================
# ENGINE TEST
# ============================================================

def run_test():

    print()
    print("=" * 75)
    print("KENYA FINANCIAL ANALYTICS")
    print("CENTRAL FIXED-INCOME ENGINE")
    print("=" * 75)

    display_market()

    display_treasury_analysis()

    display_yield_curve()

    display_bond_analysis()

    display_stress_test()

    print()
    print("=" * 75)
    print("FIXED-INCOME ENGINE WORKING")
    print("=" * 75)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    run_test()
