
"""
KENYA FINANCIAL ANALYTICS
YIELD CURVE ENGINE
"""

from cbk_data import get_all_treasury_bills


def get_curve_data():
    data = get_all_treasury_bills()

    return [
        {
            "days": days,
            "years": days / 365,
            "rate": data[days]["rate"],
            "name": data[days]["name"],
        }
        for days in [91, 182, 364]
    ]


def interpolate_rate(target_days):

    curve = get_curve_data()

    if target_days < 91 or target_days > 364:
        raise ValueError(
            "Maturity must be between 91 and 364 days."
        )

    for left, right in zip(curve, curve[1:]):

        if left["days"] <= target_days <= right["days"]:

            return left["rate"] + (
                (target_days - left["days"])
                / (right["days"] - left["days"])
            ) * (
                right["rate"] - left["rate"]
            )

    return None


def curve_slope():

    curve = get_curve_data()

    return curve[-1]["rate"] - curve[0]["rate"]


def curve_shape():

    curve = get_curve_data()

    short = curve[0]["rate"]
    medium = curve[1]["rate"]
    long = curve[2]["rate"]

    if short <= medium <= long:
        return "UPWARD / NORMAL"

    if short >= medium >= long:
        return "DOWNWARD / INVERTED"

    return "MIXED / HUMPED"


def forward_rate(start_days, end_days):

    if start_days >= end_days:
        raise ValueError(
            "End maturity must be greater than start maturity."
        )

    r1 = interpolate_rate(start_days)
    r2 = interpolate_rate(end_days)

    t1 = start_days / 365
    t2 = end_days / 365

    return (
        ((1 + r2) ** t2)
        / ((1 + r1) ** t1)
    ) ** (1 / (t2 - t1)) - 1


def display_curve():

    curve = get_curve_data()

    print()
    print("=" * 65)
    print("KENYA TREASURY BILL YIELD CURVE")
    print("=" * 65)

    print(
        f"{'Maturity':<15}"
        f"{'Years':<15}"
        f"{'Yield':<15}"
    )

    print("-" * 65)

    for point in curve:

        print(
            f"{point['days']} days"
            f"{'':<7}"
            f"{point['years']:<15.4f}"
            f"{point['rate'] * 100:.4f}%"
        )

    print("-" * 65)

    print(
        f"Curve Slope : {curve_slope() * 100:.4f}%"
    )

    print(
        f"Curve Shape : {curve_shape()}"
    )

    print("=" * 65)


def run_test():

    display_curve()

    print()
    print("INTERPOLATION TEST")
    print("-" * 40)

    for days in [120, 150, 210, 270, 300]:

        rate = interpolate_rate(days)

        print(
            f"{days} days -> {rate * 100:.4f}%"
        )

    print()
    print("FORWARD RATE TEST")
    print("-" * 40)

    for start, end in [
        (91, 182),
        (182, 364),
        (91, 364),
    ]:

        rate = forward_rate(start, end)

        print(
            f"{start} -> {end} days: "
            f"{rate * 100:.4f}%"
        )

    print()
    print("=" * 65)
    print("YIELD CURVE ENGINE WORKING")
    print("=" * 65)


if __name__ == "__main__":
    run_test()
