"""
Monte Carlo Option Pricing Engine
=================================

Prices European Call and Put options using
Geometric Brownian Motion.

This is a research/pricing engine and is designed
to later connect to the larger quantitative platform.
"""

import math
import random


# ============================================================
# MONTE CARLO PRICING
# ============================================================

def monte_carlo_price(
    option_type,
    S,
    K,
    T,
    r,
    sigma,
    simulations=100000,
    seed=42,
):
    """
    Calculate a European option price using Monte Carlo.

    Parameters
    ----------
    option_type : str
        "call" or "put"

    S : float
        Current underlying price

    K : float
        Strike price

    T : float
        Time to maturity in years

    r : float
        Continuously compounded risk-free rate

    sigma : float
        Volatility

    simulations : int
        Number of Monte Carlo simulations

    seed : int
        Random seed for reproducibility
    """

    option_type = option_type.lower().strip()

    if option_type not in ("call", "put"):
        raise ValueError(
            "option_type must be 'call' or 'put'."
        )

    if S <= 0:
        raise ValueError(
            "Underlying price S must be greater than zero."
        )

    if K <= 0:
        raise ValueError(
            "Strike price K must be greater than zero."
        )

    if T <= 0:
        raise ValueError(
            "Time to maturity T must be greater than zero."
        )

    if sigma <= 0:
        raise ValueError(
            "Volatility sigma must be greater than zero."
        )

    if simulations <= 0:
        raise ValueError(
            "simulations must be greater than zero."
        )

    # Reproducible simulation
    random.seed(seed)

    # Discount factor
    discount_factor = math.exp(-r * T)

    total_payoff = 0.0

    # ========================================================
    # SIMULATE TERMINAL STOCK PRICES
    # ========================================================

    drift = (
        r - 0.5 * sigma ** 2
    ) * T

    diffusion_scale = (
        sigma * math.sqrt(T)
    )

    for _ in range(simulations):

        z = random.gauss(0.0, 1.0)

        terminal_price = (
            S
            * math.exp(
                drift
                + diffusion_scale * z
            )
        )

        # ====================================================
        # OPTION PAYOFF
        # ====================================================

        if option_type == "call":

            payoff = max(
                terminal_price - K,
                0.0,
            )

        else:

            payoff = max(
                K - terminal_price,
                0.0,
            )

        total_payoff += payoff

    # ========================================================
    # PRESENT VALUE
    # ========================================================

    average_payoff = (
        total_payoff / simulations
    )

    price = (
        discount_factor
        * average_payoff
    )

    return price


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def monte_carlo_call(
    S,
    K,
    T,
    r,
    sigma,
    simulations=100000,
    seed=42,
):
    """
    Monte Carlo European Call price.
    """

    return monte_carlo_price(
        option_type="call",
        S=S,
        K=K,
        T=T,
        r=r,
        sigma=sigma,
        simulations=simulations,
        seed=seed,
    )


def monte_carlo_put(
    S,
    K,
    T,
    r,
    sigma,
    simulations=100000,
    seed=42,
):
    """
    Monte Carlo European Put price.
    """

    return monte_carlo_price(
        option_type="put",
        S=S,
        K=K,
        T=T,
        r=r,
        sigma=sigma,
        simulations=simulations,
        seed=seed,
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

    simulations = 100000

    call = monte_carlo_call(
        S,
        K,
        T,
        r,
        sigma,
        simulations,
    )

    put = monte_carlo_put(
        S,
        K,
        T,
        r,
        sigma,
        simulations,
    )

    print("=" * 60)
    print("MONTE CARLO PRICING ENGINE TEST")
    print("=" * 60)

    print()
    print(f"Underlying Price : {S:.2f}")
    print(f"Strike Price     : {K:.2f}")
    print(f"Maturity         : {T:.2f} years")
    print(f"Risk-Free Rate   : {r:.2%}")
    print(f"Volatility       : {sigma:.2%}")
    print(f"Simulations      : {simulations:,}")

    print()
    print(f"Monte Carlo Call : {call:.4f}")
    print(f"Monte Carlo Put  : {put:.4f}")

    print()
    print("MONTE CARLO ENGINE WORKING")
    print("=" * 60)