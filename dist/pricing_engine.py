
"""
============================================================
KENYA FINANCIAL ANALYTICS
KENYAN PRICING ENGINE
============================================================

Purpose:
    Treasury Bill pricing
    Government bond pricing
    Yield calculations
    Duration
    Modified duration
    Convexity
    Price sensitivity

Currency:
    KES

Market convention:
    Kenyan Treasury Bills use a 365-day year.

This module contains calculations only.
It does NOT invent market data.
============================================================
"""

from math import exp


# ============================================================
# CONSTANTS
# ============================================================

DAY_COUNT = 365


# ============================================================
# VALIDATE INPUTS
# ============================================================

def _positive(value, name):

    value = float(value)

    if value <= 0:

        raise ValueError(
            f"{name} must be greater than zero."
        )

    return value


def _rate(value):

    value = float(value)

    # Allow either 0.09 or 9.0
    if abs(value) > 1:

        value /= 100

    return value


# ============================================================
# TREASURY BILL
# ============================================================

def tbill_price(
    face_value,
    annual_yield,
    days
):
    """
    Calculate Treasury Bill purchase price.

    Formula:

        Price = Face / (1 + yield * days / 365)

    Returns KES.
    """

    face_value = _positive(
        face_value,
        "Face value"
    )

    annual_yield = _rate(
        annual_yield
    )

    days = _positive(
        days,
        "Days"
    )

    price = (
        face_value
        /
        (
            1
            + annual_yield
            * days
            / DAY_COUNT
        )
    )

    return price


def tbill_discount_price(
    face_value,
    discount_rate,
    days
):
    """
    Calculate Treasury Bill price using
    a discount-rate convention.
    """

    face_value = _positive(
        face_value,
        "Face value"
    )

    discount_rate = _rate(
        discount_rate
    )

    days = _positive(
        days,
        "Days"
    )

    price = (
        face_value
        *
        (
            1
            -
            discount_rate
            * days
            / DAY_COUNT
        )
    )

    return price


def tbill_yield(
    face_value,
    price,
    days
):
    """
    Calculate annualized investment yield
    from Treasury Bill purchase price.
    """

    face_value = _positive(
        face_value,
        "Face value"
    )

    price = _positive(
        price,
        "Price"
    )

    days = _positive(
        days,
        "Days"
    )

    if price >= face_value:

        return 0.0

    return (
        (
            face_value / price
        )
        - 1
    ) * DAY_COUNT / days


def tbill_discount_rate(
    face_value,
    price,
    days
):
    """
    Calculate Treasury Bill discount rate.
    """

    face_value = _positive(
        face_value,
        "Face value"
    )

    price = _positive(
        price,
        "Price"
    )

    days = _positive(
        days,
        "Days"
    )

    return (
        (
            face_value - price
        )
        / face_value
    ) * DAY_COUNT / days


def tbill_return(
    face_value,
    annual_yield,
    days
):
    """
    Complete Treasury Bill calculation.
    """

    price = tbill_price(
        face_value,
        annual_yield,
        days
    )

    profit = (
        face_value - price
    )

    simple_return = (
        profit / price
    )

    annualized_return = (
        simple_return
        * DAY_COUNT
        / days
    )

    return {
        "face_value": face_value,
        "days": days,
        "yield": _rate(annual_yield),
        "purchase_price": price,
        "profit": profit,
        "holding_period_return":
            simple_return,
        "annualized_return":
            annualized_return
    }


# ============================================================
# TREASURY BILL VALIDATION
# ============================================================

VALID_TENORS = {
    91,
    182,
    364
}


def validate_tbill_tenor(
    days
):

    days = int(days)

    if days not in VALID_TENORS:

        raise ValueError(
            "Kenyan Treasury Bill tenor must be "
            "91, 182 or 364 days."
        )

    return days


# ============================================================
# GOVERNMENT BOND CASH FLOWS
# ============================================================

def bond_cash_flows(
    face_value,
    coupon_rate,
    years,
    frequency=2
):
    """
    Generate fixed-rate government bond cash flows.

    Default:
        Semi-annual coupon payments.
    """

    face_value = _positive(
        face_value,
        "Face value"
    )

    coupon_rate = _rate(
        coupon_rate
    )

    years = _positive(
        years,
        "Years"
    )

    frequency = int(
        frequency
    )

    if frequency <= 0:

        raise ValueError(
            "Frequency must be positive."
        )

    periods = round(
        years * frequency
    )

    coupon = (
        face_value
        * coupon_rate
        / frequency
    )

    cash_flows = []

    for period in range(
        1,
        periods + 1
    ):

        payment = coupon

        if period == periods:

            payment += face_value

        time = (
            period / frequency
        )

        cash_flows.append(
            {
                "period": period,
                "time": time,
                "cash_flow": payment
            }
        )

    return cash_flows


# ============================================================
# BOND PRICE
# ============================================================

def bond_price(
    face_value,
    coupon_rate,
    yield_to_maturity,
    years,
    frequency=2
):
    """
    Present value of a fixed coupon bond.
    """

    face_value = _positive(
        face_value,
        "Face value"
    )

    coupon_rate = _rate(
        coupon_rate
    )

    ytm = _rate(
        yield_to_maturity
    )

    years = _positive(
        years,
        "Years"
    )

    frequency = int(
        frequency
    )

    cash_flows = bond_cash_flows(
        face_value,
        coupon_rate,
        years,
        frequency
    )

    periodic_yield = (
        ytm / frequency
    )

    price = 0.0

    for item in cash_flows:

        period = item["period"]

        cash_flow = item["cash_flow"]

        price += (
            cash_flow
            /
            (
                1 + periodic_yield
            ) ** period
        )

    return price


# ============================================================
# BOND YIELD
# ============================================================

def bond_ytm(
    face_value,
    coupon_rate,
    market_price,
    years,
    frequency=2,
    tolerance=1e-10,
    max_iterations=200
):
    """
    Solve yield to maturity using bisection.
    """

    market_price = _positive(
        market_price,
        "Market price"
    )

    low = -0.99

    high = 2.0

    for _ in range(
        max_iterations
    ):

        mid = (
            low + high
        ) / 2

        price = bond_price(
            face_value,
            coupon_rate,
            mid,
            years,
            frequency
        )

        difference = (
            price - market_price
        )

        if abs(difference) < tolerance:

            return mid

        if price > market_price:

            low = mid

        else:

            high = mid

    return (
        low + high
    ) / 2


# ============================================================
# DURATION
# ============================================================

def bond_duration(
    face_value,
    coupon_rate,
    yield_to_maturity,
    years,
    frequency=2
):
    """
    Returns:

        Macaulay duration
        Modified duration
    """

    ytm = _rate(
        yield_to_maturity
    )

    cash_flows = bond_cash_flows(
        face_value,
        coupon_rate,
        years,
        frequency
    )

    periodic_yield = (
        ytm / frequency
    )

    price = bond_price(
        face_value,
        coupon_rate,
        ytm,
        years,
        frequency
    )

    weighted_time = 0.0

    for item in cash_flows:

        period = item["period"]

        time = item["time"]

        cash_flow = item["cash_flow"]

        pv = (
            cash_flow
            /
            (
                1 + periodic_yield
            ) ** period
        )

        weighted_time += (
            time * pv
        )

    macaulay = (
        weighted_time / price
    )

    modified = (
        macaulay
        /
        (
            1
            + periodic_yield
        )
    )

    return (
        macaulay,
        modified
    )


# ============================================================
# CONVEXITY
# ============================================================

def bond_convexity(
    face_value,
    coupon_rate,
    yield_to_maturity,
    years,
    frequency=2
):
    """
    Calculate annualized bond convexity.
    """

    ytm = _rate(
        yield_to_maturity
    )

    cash_flows = bond_cash_flows(
        face_value,
        coupon_rate,
        years,
        frequency
    )

    periodic_yield = (
        ytm / frequency
    )

    price = bond_price(
        face_value,
        coupon_rate,
        ytm,
        years,
        frequency
    )

    convexity = 0.0

    for item in cash_flows:

        period = item["period"]

        cash_flow = item["cash_flow"]

        numerator = (
            period
            * (period + 1)
            * cash_flow
        )

        denominator = (
            frequency ** 2
            *
            (
                1
                + periodic_yield
            ) ** (period + 2)
        )

        convexity += (
            numerator
            / denominator
        )

    return (
        convexity / price
    )


# ============================================================
# PRICE SENSITIVITY
# ============================================================

def bond_price_sensitivity(
    face_value,
    coupon_rate,
    yield_to_maturity,
    years,
    yield_change,
    frequency=2
):
    """
    Estimate bond price using duration/convexity.

    ?P/P ? -Dmod ?y + 0.5 C (?y)^2
    """

    ytm = _rate(
        yield_to_maturity
    )

    yield_change = _rate(
        yield_change
    )

    price = bond_price(
        face_value,
        coupon_rate,
        ytm,
        years,
        frequency
    )

    _, modified_duration = (
        bond_duration(
            face_value,
            coupon_rate,
            ytm,
            years,
            frequency
        )
    )

    convexity = bond_convexity(
        face_value,
        coupon_rate,
        ytm,
        years,
        frequency
    )

    percentage_change = (
        -modified_duration
        * yield_change
        +
        0.5
        * convexity
        * yield_change ** 2
    )

    estimated_price = (
        price
        * (
            1
            + percentage_change
        )
    )

    return {
        "current_price": price,
        "estimated_price": estimated_price,
        "percentage_change":
            percentage_change,
        "modified_duration":
            modified_duration,
        "convexity":
            convexity
    }


# ============================================================
# T-BILL PRICE FROM CBK RATE
# ============================================================

def price_from_cbk_rate(
    face_value,
    cbk_rate,
    tenor
):
    """
    Price a Kenyan Treasury Bill using
    a CBK-derived annual yield.
    """

    tenor = validate_tbill_tenor(
        tenor
    )

    return tbill_price(
        face_value,
        cbk_rate,
        tenor
    )


# ============================================================
# COMPLETE T-BILL REPORT
# ============================================================

def tbill_report(
    face_value,
    rate,
    tenor
):

    tenor = validate_tbill_tenor(
        tenor
    )

    result = tbill_return(
        face_value,
        rate,
        tenor
    )

    return {
        "instrument":
            f"Kenya Treasury Bill "
            f"{tenor}-Day",

        "currency":
            "KES",

        "face_value":
            result["face_value"],

        "tenor_days":
            tenor,

        "annual_yield":
            result["yield"],

        "purchase_price":
            result["purchase_price"],

        "profit":
            result["profit"],

        "holding_return":
            result["holding_period_return"],

        "annualized_return":
            result["annualized_return"]
    }


# ============================================================
# TEST
# ============================================================

def run_tests():

    print()
    print("=" * 70)
    print("KENYAN PRICING ENGINE TEST")
    print("=" * 70)

    # Treasury Bill

    tbill = tbill_report(
        face_value=1_000_000,
        rate=0.09,
        tenor=91
    )

    print()
    print("TREASURY BILL")
    print(
        "Instrument:",
        tbill["instrument"]
    )

    print(
        "Face:",
        f"KES {tbill['face_value']:,.2f}"
    )

    print(
        "Yield:",
        f"{tbill['annual_yield'] * 100:.4f}%"
    )

    print(
        "Purchase Price:",
        f"KES {tbill['purchase_price']:,.2f}"
    )

    print(
        "Profit:",
        f"KES {tbill['profit']:,.2f}"
    )

    # Bond

    price = bond_price(
        1_000_000,
        0.10,
        0.09,
        5
    )

    ytm = bond_ytm(
        1_000_000,
        0.10,
        price,
        5
    )

    duration = bond_duration(
        1_000_000,
        0.10,
        0.09,
        5
    )

    convexity = bond_convexity(
        1_000_000,
        0.10,
        0.09,
        5
    )

    print()
    print("GOVERNMENT BOND")
    print(
        "Price:",
        f"KES {price:,.2f}"
    )

    print(
        "Calculated YTM:",
        f"{ytm * 100:.4f}%"
    )

    print(
        "Macaulay Duration:",
        f"{duration[0]:.4f}"
    )

    print(
        "Modified Duration:",
        f"{duration[1]:.4f}"
    )

    print(
        "Convexity:",
        f"{convexity:.4f}"
    )

    print()
    print("=" * 70)
    print("PRICING ENGINE TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":

    run_tests()
