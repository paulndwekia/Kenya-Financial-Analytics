"""
Black-Scholes Option Pricing Engine
===================================

Supports:
    - European Call
    - European Put
    - d1 and d2
    - Basic input validation

Inputs:
    S     = Stock/underlying price
    K     = Strike price
    T     = Time to maturity in years
    r     = Risk-free interest rate
    sigma = Volatility
"""

import math


def _validate_inputs(S, K, T, r, sigma):
    """Validate Black-Scholes inputs."""

    if S <= 0:
        raise ValueError("Underlying price S must be greater than zero.")

    if K <= 0:
        raise ValueError("Strike price K must be greater than zero.")

    if T <= 0:
        raise ValueError("Time to maturity T must be greater than zero.")

    if sigma <= 0:
        raise ValueError("Volatility sigma must be greater than zero.")


def _normal_cdf(x):
    """
    Standard normal cumulative distribution function.
    """

    return 0.5 * (
        1.0 + math.erf(x / math.sqrt(2.0))
    )


def d1(S, K, T, r, sigma):
    """
    Calculate Black-Scholes d1.
    """

    _validate_inputs(
        S,
        K,
        T,
        r,
        sigma,
    )

    return (
        math.log(S / K)
        + (r + 0.5 * sigma ** 2) * T
    ) / (
        sigma * math.sqrt(T)
    )


def d2(S, K, T, r, sigma):
    """
    Calculate Black-Scholes d2.
    """

    value_d1 = d1(
        S,
        K,
        T,
        r,
        sigma,
    )

    return value_d1 - sigma * math.sqrt(T)


def call_price(S, K, T, r, sigma):
    """
    Calculate European Call option price.
    """

    value_d1 = d1(
        S,
        K,
        T,
        r,
        sigma,
    )

    value_d2 = d2(
        S,
        K,
        T,
        r,
        sigma,
    )

    return (
        S * _normal_cdf(value_d1)
        - K
        * math.exp(-r * T)
        * _normal_cdf(value_d2)
    )


def put_price(S, K, T, r, sigma):
    """
    Calculate European Put option price.
    """

    value_d1 = d1(
        S,
        K,
        T,
        r,
        sigma,
    )

    value_d2 = d2(
        S,
        K,
        T,
        r,
        sigma,
    )

    return (
        K
        * math.exp(-r * T)
        * _normal_cdf(-value_d2)
        - S
        * _normal_cdf(-value_d1)
    )


def price_option(
    option_type,
    S,
    K,
    T,
    r,
    sigma,
):
    """
    General option-pricing function.

    option_type:
        "call"
        "put"
    """

    option_type = option_type.lower().strip()

    if option_type == "call":

        return call_price(
            S,
            K,
            T,
            r,
            sigma,
        )

    if option_type == "put":

        return put_price(
            S,
            K,
            T,
            r,
            sigma,
        )

    raise ValueError(
        "option_type must be 'call' or 'put'."
    )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    # Example parameters
    S = 100.0
    K = 100.0
    T = 1.0
    r = 0.05
    sigma = 0.20

    call = call_price(
        S,
        K,
        T,
        r,
        sigma,
    )

    put = put_price(
        S,
        K,
        T,
        r,
        sigma,
    )

    print("=" * 60)
    print("BLACK-SCHOLES PRICING ENGINE TEST")
    print("=" * 60)

    print()
    print(f"Underlying Price : {S:.2f}")
    print(f"Strike Price     : {K:.2f}")
    print(f"Maturity         : {T:.2f} years")
    print(f"Risk-Free Rate   : {r:.2%}")
    print(f"Volatility       : {sigma:.2%}")

    print()
    print(f"Call Price       : {call:.4f}")
    print(f"Put Price        : {put:.4f}")

    print()
    print("BLACK-SCHOLES ENGINE WORKING")
    print("=" * 60)