"""
KENYA FINANCIAL ANALYTICS
=========================

CBK MARKET DATA STORE

This module manages Kenyan Treasury Bill market data.

Supported:
    91-Day
    182-Day
    364-Day

The data layer provides:

    - Current CBK rates
    - Local cache
    - Data timestamps
    - Historical observations
    - Safe access for the dashboard
"""

import json
import os
from datetime import datetime


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

CACHE_FILE = os.path.join(
    BASE_DIR,
    "cbk_cache.json"
)


# ============================================================
# CURRENT CBK DATA
# ============================================================

CURRENT_DATA = {

    91: {
        "name": "91-Day Treasury Bill",
        "days": 91,
        "rate": 0.087700,
        "source": "Central Bank of Kenya",
    },

    182: {
        "name": "182-Day Treasury Bill",
        "days": 182,
        "rate": 0.089480,
        "source": "Central Bank of Kenya",
    },

    364: {
        "name": "364-Day Treasury Bill",
        "days": 364,
        "rate": 0.090365,
        "source": "Central Bank of Kenya",
    },
}


# ============================================================
# METADATA
# ============================================================

DATA_METADATA = {

    "source": "Central Bank of Kenya",

    "description": (
        "Kenyan Treasury Bill previous "
        "average interest rates"
    ),

    "retrieved_date": "2026-08-26",

    "status": "Official CBK published data",

}


# ============================================================
# HISTORICAL DATA
# ============================================================

HISTORICAL_DATA = []


# ============================================================
# VALIDATE TENOR
# ============================================================

def validate_tenor(days):

    if days not in CURRENT_DATA:

        raise ValueError(
            "Invalid Treasury Bill tenor. "
            "Use 91, 182 or 364."
        )


# ============================================================
# GET ONE TREASURY BILL
# ============================================================

def get_treasury_bill(days):

    validate_tenor(days)

    return CURRENT_DATA[days]


# ============================================================
# GET ALL TREASURY BILLS
# ============================================================

def get_all_treasury_bills():

    return CURRENT_DATA


# ============================================================
# GET RATE
# ============================================================

def get_rate(days):

    validate_tenor(days)

    return CURRENT_DATA[days]["rate"]


# ============================================================
# UPDATE RATE
# ============================================================

def update_rate(
    days,
    rate,
    source="Central Bank of Kenya"
):

    validate_tenor(days)

    if rate < 0:

        raise ValueError(
            "Rate cannot be negative."
        )

    CURRENT_DATA[days]["rate"] = rate

    CURRENT_DATA[days]["source"] = source


# ============================================================
# SAVE CACHE
# ============================================================

def save_cache():

    data = {

        "metadata": DATA_METADATA,

        "treasury_bills": CURRENT_DATA,

        "historical_data": HISTORICAL_DATA,

    }

    try:

        with open(
            CACHE_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=4
            )

        return True

    except OSError:

        return False


# ============================================================
# LOAD CACHE
# ============================================================

def load_cache():

    if not os.path.exists(
        CACHE_FILE
    ):

        return False

    try:

        with open(
            CACHE_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        treasury_bills = data.get(
            "treasury_bills",
            {}
        )

        for key, value in treasury_bills.items():

            days = int(key)

            if days in CURRENT_DATA:

                CURRENT_DATA[days].update(
                    value
                )

        historical = data.get(
            "historical_data",
            []
        )

        HISTORICAL_DATA.clear()

        HISTORICAL_DATA.extend(
            historical
        )

        return True

    except (
        OSError,
        json.JSONDecodeError,
        ValueError
    ):

        return False


# ============================================================
# ADD HISTORICAL OBSERVATION
# ============================================================

def add_historical_observation(
    date,
    days,
    rate,
    issue_number=None
):

    validate_tenor(days)

    observation = {

        "date": date,

        "tenor_days": days,

        "rate": rate,

        "issue_number": issue_number,

        "source": (
            "Central Bank of Kenya"
        ),

    }

    HISTORICAL_DATA.append(
        observation
    )


# ============================================================
# GET HISTORICAL DATA
# ============================================================

def get_historical_data(
    tenor=None
):

    if tenor is None:

        return HISTORICAL_DATA

    validate_tenor(tenor)

    return [
        item
        for item in HISTORICAL_DATA
        if item["tenor_days"] == tenor
    ]


# ============================================================
# DATA STATUS
# ============================================================

def get_data_status():

    return {

        "source": DATA_METADATA[
            "source"
        ],

        "retrieved_date": DATA_METADATA[
            "retrieved_date"
        ],

        "status": DATA_METADATA[
            "status"
        ],

        "cache_file": CACHE_FILE,

    }


# ============================================================
# DISPLAY DATA
# ============================================================

def display_market_data():

    print()
    print("=" * 70)
    print("KENYA FINANCIAL ANALYTICS")
    print("CENTRAL BANK OF KENYA MARKET DATA")
    print("=" * 70)

    print()

    print(
        f"Source: "
        f"{DATA_METADATA['source']}"
    )

    print(
        f"Date: "
        f"{DATA_METADATA['retrieved_date']}"
    )

    print()

    print(
        f"{'Treasury Bill':<28}"
        f"{'Rate':>12}"
        f"{'Tenor':>12}"
    )

    print("-" * 70)

    for days in [91, 182, 364]:

        bill = CURRENT_DATA[days]

        print(
            f"{bill['name']:<28}"
            f"{bill['rate'] * 100:>11.4f}%"
            f"{days:>10} days"
        )

    print("=" * 70)


# ============================================================
# LOAD TEST DATA
#
# IMPORTANT:
# This function is retained because app.py currently
# imports it.
#
# It does NOT invent new values.
# It loads the official CBK published values
# already stored above.
# ============================================================

def load_test_data():

    save_cache()

    return CURRENT_DATA


# ============================================================
# INITIALIZE DATA
# ============================================================

def initialize_data():

    # We intentionally start with the official
    # published CBK values above.

    save_cache()


# ============================================================
# MAIN TEST
# ============================================================

if __name__ == "__main__":

    print()
    print(
        "CBK DATA ENGINE"
    )

    print()

    initialize_data()

    display_market_data()

    print()

    status = get_data_status()

    print(
        "DATA STATUS"
    )

    print(
        f"Source: "
        f"{status['source']}"
    )

    print(
        f"Retrieved: "
        f"{status['retrieved_date']}"
    )

    print(
        f"Cache: "
        f"{status['cache_file']}"
    )

    print()

    print(
        "CBK DATA ENGINE WORKING"
    )