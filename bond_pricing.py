
"""
KENYA FINANCIAL ANALYTICS
KENYAN FIXED-INCOME BOND PRICING ENGINE
"""

from math import isfinite


# ============================================================
# VALIDATION
# ============================================================

def validate_inputs(
    face_value,
    coupon_rate,
    yield_rate,
    years,
    payments_per_year
):

    if face_value <= 0:
        raise ValueError("Face value must be greater than zero.")

    if coupon_rate < 0:
        raise ValueError("Coupon rate cannot be negative.")

    if yield_rate <= -1:
        raise ValueError("Yield rate is invalid.")

    if years <= 0:
        raise ValueError("Years to maturity must be greater than zero.")

    if payments_per_year <= 0:
        raise ValueError("Payment frequency must be greater than zero.")


# ============================================================
# BOND PRICE
# ============================================================

def bond_price(
    face_value,
    coupon_rate,
    yield_rate,
    years,
    payments_per_year=2
):

    validate_inputs(
        face_value,
        coupon_rate,
        yield_rate,
        years,
        payments_per_year
    )

    periods = round(
        years * payments_per_year
    )

    coupon = (
        face_value
        * coupon_rate
        / payments_per_year
    )

    periodic_yield = (
        yield_rate
        / payments_per_year
    )

    price = 0.0

    for t in range(1, periods + 1):

        cash_flow = coupon

        if t == periods:
            cash_flow += face_value

        price += (
            cash_flow
            / (1 + periodic_yield) ** t
        )

    return price


# ============================================================
# CASH FLOWS
# ============================================================

def cash_flows(
    face_value,
    coupon_rate,
    years,
    payments_per_year=2
):

    periods = round(
        years * payments_per_year
    )

    coupon = (
        face_value
        * coupon_rate
        / payments_per_year
    )

    flows = []

    for t in range(1, periods + 1):

        amount = coupon

        if t == periods:
            amount += face_value

        flows.append(
            {
                "period": t,
                "time_years": (
                    t / payments_per_year
                ),
                "cash_flow": amount,
            }
        )

    return flows


# ============================================================
# YIELD TO MATURITY
# ============================================================

def yield_to_maturity(
    market_price,
    face_value,
    coupon_rate,
    years,
    payments_per_year=2
):

    if market_price <= 0:
        raise ValueError(
            "Market price must be greater than zero."
        )

    low = -0.99
    high = 2.0

    for _ in range(200):

        mid = (low + high) / 2

        price = bond_price(
            face_value,
            coupon_rate,
            mid,
            years,
            payments_per_year
        )

        if abs(price - market_price) < 1e-10:
            return mid

        if price > market_price:
            low = mid
        else:
            high = mid

    return (low + high) / 2


# ============================================================
# MACAULAY DURATION
# ============================================================

def macaulay_duration(
    face_value,
    coupon_rate,
    yield_rate,
    years,
    payments_per_year=2
):

    price = bond_price(
        face_value,
        coupon_rate,
        yield_rate,
        years,
        payments_per_year
    )

    flows = cash_flows(
        face_value,
        coupon_rate,
        years,
        payments_per_year
    )

    periodic_yield = (
        yield_rate
        / payments_per_year
    )

    weighted_time = 0.0

    for item in flows:

        t = item["period"]

        pv = (
            item["cash_flow"]
            / (1 + periodic_yield) ** t
        )

        weighted_time += (
            (t / payments_per_year)
            * pv
        )

    return weighted_time / price


# ============================================================
# MODIFIED DURATION
# ============================================================

def modified_duration(
    face_value,
    coupon_rate,
    yield_rate,
    years,
    payments_per_year=2
):

    macaulay = macaulay_duration(
        face_value,
        coupon_rate,
        yield_rate,
        years,
        payments_per_year
    )

    return (
        macaulay
        / (
            1
            + yield_rate / payments_per_year
        )
    )


# ============================================================
# CONVEXITY
# ============================================================

def convexity(
    face_value,
    coupon_rate,
    yield_rate,
    years,
    payments_per_year=2
):

    flows = cash_flows(
        face_value,
        coupon_rate,
        years,
        payments_per_year
    )

    periodic_yield = (
        yield_rate
        / payments_per_year
    )

    price = bond_price(
        face_value,
        coupon_rate,
        yield_rate,
        years,
        payments_per_year
    )

    total = 0.0

    for item in flows:

        t = item["period"]

        cash = item["cash_flow"]

        total += (
            t
            * (t + 1)
            * cash
            / (
                (1 + periodic_yield)
                ** (t + 2)
            )
        )

    return (
        total
        / (
            price
            * payments_per_year ** 2
        )
    )


# ============================================================
# PRICE SENSITIVITY
# ============================================================

def price_sensitivity(
    face_value,
    coupon_rate,
    yield_rate,
    years,
    yield_change,
    payments_per_year=2
):

    price = bond_price(
        face_value,
        coupon_rate,
        yield_rate,
        years,
        payments_per_year
    )

    duration = modified_duration(
        face_value,
        coupon_rate,
        yield_rate,
        years,
        payments_per_year
    )

    conv = convexity(
        face_value,
        coupon_rate,
        yield_rate,
        years,
        payments_per_year
    )

    dy = yield_change

    estimated_change = (
        -duration * dy
        + 0.5 * conv * dy ** 2
    )

    estimated_price = (
        price
        * (1 + estimated_change)
    )

    return {
        "current_price": price,
        "estimated_price": estimated_price,
        "estimated_change_percent":
            estimated_change * 100,
    }


# ============================================================
# FULL ANALYSIS
# ============================================================

def analyze_bond(
    face_value,
    coupon_rate,
    yield_rate,
    years,
    payments_per_year=2
):

    price = bond_price(
        face_value,
        coupon_rate,
        yield_rate,
        years,
        payments_per_year
    )

    macaulay = macaulay_duration(
        face_value,
        coupon_rate,
        yield_rate,
        years,
        payments_per_year
    )

    modified = modified_duration(
        face_value,
        coupon_rate,
        yield_rate,
        years,
        payments_per_year
    )

    conv = convexity(
        face_value,
        coupon_rate,
        yield_rate,
        years,
        payments_per_year
    )

    return {
        "face_value": face_value,
        "coupon_rate": coupon_rate,
        "yield_rate": yield_rate,
        "years": years,
        "payments_per_year":
            payments_per_year,
        "price": price,
        "macaulay_duration": macaulay,
        "modified_duration": modified,
        "convexity": conv,
    }


# ============================================================
# TEST
# ============================================================

def run_test():

    print()
    print("=" * 70)
    print("KENYA FINANCIAL ANALYTICS")
    print("BOND PRICING ENGINE")
    print("=" * 70)

    # Example Kenyan fixed-income instrument
    face = 1_000_000
    coupon = 0.10
    market_yield = 0.095
    maturity = 5
    frequency = 2

    result = analyze_bond(
        face,
        coupon,
        market_yield,
        maturity,
        frequency
    )

    print()
    print("EXAMPLE BOND")
    print("-" * 70)

    print(
        f"Face Value        : "
        f"KES {result['face_value']:,.2f}"
    )

    print(
        f"Coupon Rate       : "
        f"{result['coupon_rate'] * 100:.4f}%"
    )

    print(
        f"Market Yield      : "
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
        f"{result['macaulay_duration']:.4f} years"
    )

    print(
        f"Modified Duration : "
        f"{result['modified_duration']:.4f}"
    )

    print(
        f"Convexity         : "
        f"{result['convexity']:.4f}"
    )

    sensitivity = price_sensitivity(
        face,
        coupon,
        market_yield,
        maturity,
        0.01,
        frequency
    )

    print()
    print("1% YIELD INCREASE SCENARIO")
    print("-" * 70)

    print(
        f"Estimated Price   : "
        f"KES {sensitivity['estimated_price']:,.2f}"
    )

    print(
        f"Estimated Change  : "
        f"{sensitivity['estimated_change_percent']:.4f}%"
    )

    print()
    print("=" * 70)
    print("BOND PRICING ENGINE WORKING")
    print("=" * 70)


if __name__ == "__main__":
    run_test()
