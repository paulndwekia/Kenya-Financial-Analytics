import math

from black_scholes import d1, d2, _normal_cdf


def normal_pdf(x):
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def delta_call(S, K, T, r, sigma):
    return _normal_cdf(d1(S, K, T, r, sigma))


def delta_put(S, K, T, r, sigma):
    return _normal_cdf(d1(S, K, T, r, sigma)) - 1


def gamma(S, K, T, r, sigma):
    d1_value = d1(S, K, T, r, sigma)

    return normal_pdf(d1_value) / (
        S * sigma * math.sqrt(T)
    )


def vega(S, K, T, r, sigma):
    d1_value = d1(S, K, T, r, sigma)

    return (
        S
        * normal_pdf(d1_value)
        * math.sqrt(T)
    )


def theta_call(S, K, T, r, sigma):
    d1_value = d1(S, K, T, r, sigma)
    d2_value = d2(S, K, T, r, sigma)

    first = (
        -S
        * normal_pdf(d1_value)
        * sigma
        / (2 * math.sqrt(T))
    )

    second = (
        -r
        * K
        * math.exp(-r * T)
        * _normal_cdf(d2_value)
    )

    return first + second


def theta_put(S, K, T, r, sigma):
    d1_value = d1(S, K, T, r, sigma)
    d2_value = d2(S, K, T, r, sigma)

    first = (
        -S
        * normal_pdf(d1_value)
        * sigma
        / (2 * math.sqrt(T))
    )

    second = (
        r
        * K
        * math.exp(-r * T)
        * _normal_cdf(-d2_value)
    )

    return first + second


def rho_call(S, K, T, r, sigma):
    d2_value = d2(S, K, T, r, sigma)

    return (
        K
        * T
        * math.exp(-r * T)
        * _normal_cdf(d2_value)
    )


def rho_put(S, K, T, r, sigma):
    d2_value = d2(S, K, T, r, sigma)

    return (
        -K
        * T
        * math.exp(-r * T)
        * _normal_cdf(-d2_value)
    )


def calculate_greeks(
    option_type,
    S,
    K,
    T,
    r,
    sigma
):

    option_type = option_type.lower()

    if option_type == "call":

        return {
            "Delta": delta_call(
                S, K, T, r, sigma
            ),

            "Gamma": gamma(
                S, K, T, r, sigma
            ),

            "Vega": vega(
                S, K, T, r, sigma
            ),

            "Theta": theta_call(
                S, K, T, r, sigma
            ),

            "Rho": rho_call(
                S, K, T, r, sigma
            ),
        }

    elif option_type == "put":

        return {
            "Delta": delta_put(
                S, K, T, r, sigma
            ),

            "Gamma": gamma(
                S, K, T, r, sigma
            ),

            "Vega": vega(
                S, K, T, r, sigma
            ),

            "Theta": theta_put(
                S, K, T, r, sigma
            ),

            "Rho": rho_put(
                S, K, T, r, sigma
            ),
        }

    else:

        raise ValueError(
            "option_type must be 'call' or 'put'"
        )


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    S = 100
    K = 100
    T = 1
    r = 0.05
    sigma = 0.20

    print("=" * 50)
    print("GREEKS ENGINE TEST")
    print("=" * 50)

    call_greeks = calculate_greeks(
        "call",
        S,
        K,
        T,
        r,
        sigma
    )

    print("\nCALL GREEKS")
    print("-" * 50)

    for name, value in call_greeks.items():
        print(f"{name}: {value:.6f}")

    put_greeks = calculate_greeks(
        "put",
        S,
        K,
        T,
        r,
        sigma
    )

    print("\nPUT GREEKS")
    print("-" * 50)

    for name, value in put_greeks.items():
        print(f"{name}: {value:.6f}")

    print("\n" + "=" * 50)
    print("GREEKS ENGINE WORKING")
    print("=" * 50)