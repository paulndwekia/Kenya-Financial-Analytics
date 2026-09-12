"""
Pricing Validation Engine

Compares:
1. Black-Scholes
2. Binomial Tree
3. Monte Carlo

Used to check whether the pricing models
produce similar results.
"""

from pricing.black_scholes import call_price, put_price
from pricing.binomial_tree import european_call, european_put
from pricing.monte_carlo import monte_carlo_call, monte_carlo_put


def percentage_error(model_price, reference_price):
    """Calculate percentage difference."""

    if reference_price == 0:
        return 0.0

    return abs(model_price - reference_price) / abs(reference_price) * 100


def validate_call(
    S,
    K,
    T,
    r,
    sigma,
    steps=100,
    simulations=100000
):
    """Compare Call prices."""

    bs = call_price(
        S,
        K,
        T,
        r,
        sigma
    )

    binomial = european_call(
        S,
        K,
        T,
        r,
        sigma,
        steps
    )

    monte_carlo = monte_carlo_call(
        S,
        K,
        T,
        r,
        sigma,
        simulations
    )

    return {
        "Black-Scholes": bs,
        "Binomial": binomial,
        "Monte Carlo": monte_carlo
    }


def validate_put(
    S,
    K,
    T,
    r,
    sigma,
    steps=100,
    simulations=100000
):
    """Compare Put prices."""

    bs = put_price(
        S,
        K,
        T,
        r,
        sigma
    )

    binomial = european_put(
        S,
        K,
        T,
        r,
        sigma,
        steps
    )

    monte_carlo = monte_carlo_put(
        S,
        K,
        T,
        r,
        sigma,
        simulations
    )

    return {
        "Black-Scholes": bs,
        "Binomial": binomial,
        "Monte Carlo": monte_carlo
    }


def show_results(title, results):
    """Display pricing results."""

    print()
    print(title)
    print("-" * 45)

    for model, price in results.items():
        print(f"{model:<18}: {price:.6f}")


def run_validation():
    """Run the complete validation."""

    # Example market inputs
    S = 100.0
    K = 100.0
    T = 1.0
    r = 0.05
    sigma = 0.20

    print("=" * 55)
    print("PRICING VALIDATION ENGINE")
    print("=" * 55)

    print()
    print("INPUTS")
    print("-" * 55)

    print(f"Underlying Price : {S}")
    print(f"Strike Price     : {K}")
    print(f"Maturity         : {T} years")
    print(f"Interest Rate    : {r:.2%}")
    print(f"Volatility       : {sigma:.2%}")

    # Calculate Call prices
    call_results = validate_call(
        S,
        K,
        T,
        r,
        sigma
    )

    # Calculate Put prices
    put_results = validate_put(
        S,
        K,
        T,
        r,
        sigma
    )

    # Display results
    show_results(
        "CALL PRICES",
        call_results
    )

    show_results(
        "PUT PRICES",
        put_results
    )

    # --------------------------------------------------------
    # CALL ERRORS
    # --------------------------------------------------------

    call_reference = call_results["Black-Scholes"]

    call_binomial_error = percentage_error(
        call_results["Binomial"],
        call_reference
    )

    call_monte_carlo_error = percentage_error(
        call_results["Monte Carlo"],
        call_reference
    )

    print()
    print("CALL MODEL ERRORS")
    print("-" * 45)

    print(
        f"Binomial Error    : {call_binomial_error:.4f}%"
    )

    print(
        f"Monte Carlo Error : {call_monte_carlo_error:.4f}%"
    )

    # --------------------------------------------------------
    # PUT ERRORS
    # --------------------------------------------------------

    put_reference = put_results["Black-Scholes"]

    put_binomial_error = percentage_error(
        put_results["Binomial"],
        put_reference
    )

    put_monte_carlo_error = percentage_error(
        put_results["Monte Carlo"],
        put_reference
    )

    print()
    print("PUT MODEL ERRORS")
    print("-" * 45)

    print(
        f"Binomial Error    : {put_binomial_error:.4f}%"
    )

    print(
        f"Monte Carlo Error : {put_monte_carlo_error:.4f}%"
    )

    print()
    print("=" * 55)
    print("PRICING VALIDATION ENGINE WORKING")
    print("=" * 55)


if __name__ == "__main__":
    run_validation()