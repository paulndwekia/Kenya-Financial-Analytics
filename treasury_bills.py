"""
KENYA FINANCIAL ANALYTICS
Treasury Bill Engine

Kenyan Treasury Bill calculator for:
    - 91-day Treasury Bills
    - 182-day Treasury Bills
    - 364-day Treasury Bills

Calculates:
    - Purchase price
    - Discount
    - Investment return
    - Annualized return
    - Profit
    - Maturity value

This version is standalone and does NOT depend on
the pricing package or CBK modules.
"""

from dataclasses import dataclass


# ============================================================
# TREASURY BILL DATA MODEL
# ============================================================

@dataclass
class TreasuryBillResult:
    tenor_days: int
    face_value: float
    annual_rate: float
    purchase_price: float
    discount: float
    profit: float
    annualized_return: float


# ============================================================
# VALID KENYAN TREASURY BILL TENORS
# ============================================================

VALID_TENORS = {
    91: "91-Day Treasury Bill",
    182: "182-Day Treasury Bill",
    364: "364-Day Treasury Bill",
}


# ============================================================
# VALIDATION
# ============================================================

def validate_inputs(
    face_value: float,
    annual_rate: float,
    tenor_days: int
) -> None:

    if face_value <= 0:
        raise ValueError("Face value must be greater than zero.")

    if annual_rate < 0:
        raise ValueError("Interest rate cannot be negative.")

    if tenor_days not in VALID_TENORS:
        raise ValueError(
            "Invalid tenor. Kenyan Treasury Bills supported by "
            "this engine are 91, 182 and 364 days."
        )


# ============================================================
# TREASURY BILL PRICING
# ============================================================

def calculate_treasury_bill(
    face_value: float,
    annual_rate: float,
    tenor_days: int
) -> TreasuryBillResult:

    validate_inputs(
        face_value,
        annual_rate,
        tenor_days
    )

    """
    Treasury bill pricing formula:

        Price = Face Value / (1 + r × days / 365)

    where:

        r    = annualized rate
        days = remaining days to maturity
    """

    price = face_value / (
        1 + annual_rate * tenor_days / 365
    )

    discount = face_value - price

    profit = discount

    # Annualized return based on actual investment amount
    annualized_return = (
        profit / price
    ) * (
        365 / tenor_days
    )

    return TreasuryBillResult(
        tenor_days=tenor_days,
        face_value=face_value,
        annual_rate=annual_rate,
        purchase_price=price,
        discount=discount,
        profit=profit,
        annualized_return=annualized_return,
    )


# ============================================================
# FORMAT RESULTS
# ============================================================

def display_result(result: TreasuryBillResult) -> None:

    print()
    print("=" * 60)
    print(VALID_TENORS[result.tenor_days])
    print("=" * 60)

    print(
        f"Tenor              : "
        f"{result.tenor_days} days"
    )

    print(
        f"Face Value         : "
        f"KES {result.face_value:,.2f}"
    )

    print(
        f"Annual Rate        : "
        f"{result.annual_rate * 100:.4f}%"
    )

    print(
        f"Purchase Price     : "
        f"KES {result.purchase_price:,.2f}"
    )

    print(
        f"Discount            : "
        f"KES {result.discount:,.2f}"
    )

    print(
        f"Profit              : "
        f"KES {result.profit:,.2f}"
    )

    print(
        f"Annualized Return   : "
        f"{result.annualized_return * 100:.4f}%"
    )

    print("=" * 60)


# ============================================================
# PORTFOLIO CALCULATOR
# ============================================================

def calculate_portfolio(
    investment: float,
    annual_rate: float,
    tenor_days: int
) -> TreasuryBillResult:

    return calculate_treasury_bill(
        face_value=investment,
        annual_rate=annual_rate,
        tenor_days=tenor_days
    )


# ============================================================
# COMPARE ALL THREE TENORS
# ============================================================

def compare_tenors(
    investment: float,
    rate_91: float,
    rate_182: float,
    rate_364: float
) -> None:

    rates = {
        91: rate_91,
        182: rate_182,
        364: rate_364,
    }

    print()
    print("=" * 80)
    print("KENYAN TREASURY BILL COMPARISON")
    print("=" * 80)

    print(
        f"{'Tenor':<12}"
        f"{'Rate':<15}"
        f"{'Purchase Price':<20}"
        f"{'Profit':<20}"
    )

    print("-" * 80)

    for tenor, rate in rates.items():

        result = calculate_treasury_bill(
            investment,
            rate,
            tenor
        )

        print(
            f"{tenor:<12}"
            f"{rate * 100:<15.4f}"
            f"KES {result.purchase_price:<15,.2f}"
            f"KES {result.profit:<15,.2f}"
        )

    print("=" * 80)


# ============================================================
# USER INPUT MODE
# ============================================================

def interactive_calculator() -> None:

    print()
    print("=" * 60)
    print("KENYA TREASURY BILL CALCULATOR")
    print("=" * 60)

    print()
    print("Available Treasury Bills:")
    print("1. 91-Day")
    print("2. 182-Day")
    print("3. 364-Day")

    print()

    try:

        investment = float(
            input("Enter face value / investment (KES): ")
        )

        tenor = int(
            input("Enter tenor (91, 182 or 364): ")
        )

        rate_percent = float(
            input("Enter annual rate (%): ")
        )

        rate = rate_percent / 100

        result = calculate_treasury_bill(
            investment,
            rate,
            tenor
        )

        display_result(result)

    except ValueError as error:

        print()
        print("ERROR:")
        print(error)


# ============================================================
# ENGINE TEST
# ============================================================

def run_engine_test() -> None:

    print()
    print("=" * 60)
    print("KENYA TREASURY BILL ENGINE")
    print("ENGINE TEST")
    print("=" * 60)

    # Example rates for testing only.
    # These are NOT live CBK rates.
    rate_91 = 0.0800
    rate_182 = 0.0850
    rate_364 = 0.0900

    investment = 100_000

    compare_tenors(
        investment,
        rate_91,
        rate_182,
        rate_364
    )

    print()
    print("TESTING INDIVIDUAL BILL")
    print("-" * 60)

    result = calculate_treasury_bill(
        face_value=100_000,
        annual_rate=rate_91,
        tenor_days=91
    )

    display_result(result)

    print()
    print("TREASURY BILL ENGINE TEST COMPLETE")
    print("=" * 60)


# ============================================================
# MAIN PROGRAM
# ============================================================

if __name__ == "__main__":

    run_engine_test()

    print()
    choice = input(
        "Would you like to use the calculator? (y/n): "
    ).strip().lower()

    if choice == "y":
        interactive_calculator()