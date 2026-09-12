
"""
============================================================
CBK -> KENYAN PRICING ENGINE BRIDGE
============================================================

Connects the latest genuine CBK observations in
kenya_market.db to pricing_engine.py.

No market data is invented.
============================================================
"""

import app
import pricing_engine


VALID_TENORS = [91, 182, 364]


def latest_cbk_rates():

    latest = app.get_latest_rates()

    result = {}

    for tenor in VALID_TENORS:

        if tenor in latest:

            result[tenor] = {
                "rate":
                    latest[tenor]["rate"],

                "date":
                    latest[tenor]["date"]
            }

    return result


def get_latest_rate(tenor):

    tenor = int(tenor)

    if tenor not in VALID_TENORS:

        raise ValueError(
            "Kenyan Treasury Bill tenor must be "
            "91, 182 or 364 days."
        )

    rates = latest_cbk_rates()

    if tenor not in rates:

        raise ValueError(
            f"No CBK rate is currently available "
            f"for the {tenor}-day Treasury Bill."
        )

    return rates[tenor]


def price_using_latest_cbk(
    face_value,
    tenor
):

    data = get_latest_rate(
        tenor
    )

    result = pricing_engine.tbill_report(
        face_value=face_value,
        rate=data["rate"],
        tenor=tenor
    )

    result["cbk_auction_date"] = data["date"]

    result["data_source"] = (
        "Central Bank of Kenya"
    )

    return result


def all_current_tbill_prices(
    face_value
):

    results = {}

    for tenor in VALID_TENORS:

        try:

            results[tenor] = (
                price_using_latest_cbk(
                    face_value,
                    tenor
                )
            )

        except ValueError:

            continue

    return results


def run_test():

    print()
    print("=" * 70)
    print("CBK -> KENYAN PRICING ENGINE TEST")
    print("=" * 70)

    rates = latest_cbk_rates()

    print()
    print("LATEST CBK RATES")
    print("-" * 70)

    for tenor in VALID_TENORS:

        if tenor in rates:

            print(
                f"{tenor}-Day: "
                f"{rates[tenor]['rate'] * 100:.4f}% "
                f""
                f"({rates[tenor]['date']})"
            )

    print()
    print("T-BILL PRICES FOR KES 1,000,000")
    print("-" * 70)

    results = all_current_tbill_prices(
        1_000_000
    )

    for tenor in VALID_TENORS:

        if tenor not in results:

            print(
                f"{tenor}-Day: No CBK data"
            )

            continue

        result = results[tenor]

        print()
        print(
            f"{tenor}-Day Treasury Bill"
        )

        print(
            f"CBK Yield: "
            f"{result['annual_yield'] * 100:.4f}%"
        )

        print(
            f"Purchase Price: "
            f"KES {result['purchase_price']:,.2f}"
        )

        print(
            f"Profit: "
            f"KES {result['profit']:,.2f}"
        )

        print(
            f"Auction Date: "
            f"{result['cbk_auction_date']}"
        )

    print()
    print("=" * 70)
    print("CBK PRICING BRIDGE WORKING")
    print("=" * 70)


if __name__ == "__main__":

    run_test()
