"""
CRR Binomial Tree Option Pricing Engine
=======================================

Supports:
    - European Call
    - European Put
    - American Call
    - American Put
"""

import math


def validate_inputs(S, K, T, r, sigma, steps):

    if S <= 0:
        raise ValueError("S must be greater than zero.")

    if K <= 0:
        raise ValueError("K must be greater than zero.")

    if T <= 0:
        raise ValueError("T must be greater than zero.")

    if sigma <= 0:
        raise ValueError("sigma must be greater than zero.")

    if steps < 1:
        raise ValueError("steps must be at least 1.")


def binomial_price(
    option_type,
    exercise_style,
    S,
    K,
    T,
    r,
    sigma,
    steps=100,
):
    """
    Price an option using the Cox-Ross-Rubinstein model.

    option_type:
        call
        put

    exercise_style:
        european
        american
    """

    option_type = option_type.lower().strip()
    exercise_style = exercise_style.lower().strip()

    if option_type not in ("call", "put"):
        raise ValueError(
            "option_type must be 'call' or 'put'."
        )

    if exercise_style not in ("european", "american"):
        raise ValueError(
            "exercise_style must be 'european' or 'american'."
        )

    validate_inputs(
        S,
        K,
        T,
        r,
        sigma,
        steps,
    )

    dt = T / steps

    u = math.exp(
        sigma * math.sqrt(dt)
    )

    d = 1.0 / u

    discount = math.exp(
        -r * dt
    )

    growth = math.exp(
        r * dt
    )

    p = (
        growth - d
    ) / (
        u - d
    )

    if p <= 0 or p >= 1:
        raise ValueError(
            "Invalid risk-neutral probability."
        )

    # ========================================================
    # TERMINAL STOCK PRICES
    # ========================================================

    stock_prices = []

    for j in range(steps + 1):

        stock_price = (
            S
            * (u ** j)
            * (d ** (steps - j))
        )

        stock_prices.append(
            stock_price
        )

    # ========================================================
    # TERMINAL OPTION PAYOFFS
    # ========================================================

    option_values = []

    for stock_price in stock_prices:

        if option_type == "call":

            payoff = max(
                stock_price - K,
                0.0
            )

        else:

            payoff = max(
                K - stock_price,
                0.0
            )

        option_values.append(payoff)

    # ========================================================
    # WORK BACKWARDS THROUGH TREE
    # ========================================================

    for step in range(
        steps - 1,
        -1,
        -1,
    ):

        new_values = []

        for j in range(step + 1):

            continuation_value = (
                discount
                * (
                    p * option_values[j + 1]
                    + (1.0 - p)
                    * option_values[j]
                )
            )

            # European option
            if exercise_style == "european":

                value = continuation_value

            # American option
            else:

                stock_price = (
                    S
                    * (u ** j)
                    * (d ** (step - j))
                )

                if option_type == "call":

                    exercise_value = max(
                        stock_price - K,
                        0.0
                    )

                else:

                    exercise_value = max(
                        K - stock_price,
                        0.0
                    )

                value = max(
                    continuation_value,
                    exercise_value,
                )

            new_values.append(value)

        option_values = new_values

    return option_values[0]


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def european_call(
    S,
    K,
    T,
    r,
    sigma,
    steps=100,
):

    return binomial_price(
        "call",
        "european",
        S,
        K,
        T,
        r,
        sigma,
        steps,
    )


def european_put(
    S,
    K,
    T,
    r,
    sigma,
    steps=100,
):

    return binomial_price(
        "put",
        "european",
        S,
        K,
        T,
        r,
        sigma,
        steps,
    )


def american_call(
    S,
    K,
    T,
    r,
    sigma,
    steps=100,
):

    return binomial_price(
        "call",
        "american",
        S,
        K,
        T,
        r,
        sigma,
        steps,
    )


def american_put(
    S,
    K,
    T,
    r,
    sigma,
    steps=100,
):

    return binomial_price(
        "put",
        "american",
        S,
        K,
        T,
        r,
        sigma,
        steps,
    )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    S = 100.0
    K = 100.0
    T = 1.0
    r = 0.05
    sigma = 0.20
    steps = 100

    print("=" * 65)
    print("CRR BINOMIAL TREE PRICING ENGINE")
    print("=" * 65)

    print()
    print(f"Underlying Price : {S:.2f}")
    print(f"Strike Price     : {K:.2f}")
    print(f"Maturity         : {T:.2f} years")
    print(f"Risk-Free Rate   : {r:.2%}")
    print(f"Volatility       : {sigma:.2%}")
    print(f"Tree Steps       : {steps}")

    european_call_price = european_call(
        S,
        K,
        T,
        r,
        sigma,
        steps,
    )

    european_put_price = european_put(
        S,
        K,
        T,
        r,
        sigma,
        steps,
    )

    american_call_price = american_call(
        S,
        K,
        T,
        r,
        sigma,
        steps,
    )

    american_put_price = american_put(
        S,
        K,
        T,
        r,
        sigma,
        steps,
    )

    print()
    print("RESULTS")
    print("-" * 65)

    print(
        f"European Call : "
        f"{european_call_price:.6f}"
    )

    print(
        f"European Put  : "
        f"{european_put_price:.6f}"
    )

    print(
        f"American Call : "
        f"{american_call_price:.6f}"
    )

    print(
        f"American Put  : "
        f"{american_put_price:.6f}"
    )

    print()
    print("=" * 65)
    print("BINOMIAL TREE ENGINE WORKING")
    print("=" * 65)