
"""
KENYA FINANCIAL ANALYTICS
HISTORICAL MARKET DATA ENGINE

Local SQLite database for Kenyan financial-market data.

Current focus:
    - 91-Day Treasury Bills
    - 182-Day Treasury Bills
    - 364-Day Treasury Bills

The database is designed to grow into the historical
market-data foundation for the backtesting and risk engines.
"""

import sqlite3
from pathlib import Path
from datetime import datetime


# ============================================================
# DATABASE
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATABASE = BASE_DIR / "kenya_market.db"


# ============================================================
# CONNECTION
# ============================================================

def get_connection():

    return sqlite3.connect(
        DATABASE
    )


# ============================================================
# CREATE DATABASE
# ============================================================

def initialize_database():

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS treasury_bill_rates (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            auction_date TEXT NOT NULL,

            tenor_days INTEGER NOT NULL,

            rate REAL NOT NULL,

            issue_number TEXT,

            source TEXT NOT NULL,

            created_at TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_tbill_date
        ON treasury_bill_rates(auction_date)
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS
        idx_tbill_tenor
        ON treasury_bill_rates(tenor_days)
        """
    )

    connection.commit()

    connection.close()


# ============================================================
# ADD OBSERVATION
# ============================================================

def add_treasury_bill_rate(
    auction_date,
    tenor_days,
    rate,
    issue_number=None,
    source="Central Bank of Kenya"
):

    if tenor_days not in [91, 182, 364]:

        raise ValueError(
            "Tenor must be 91, 182 or 364 days."
        )

    if rate < 0:

        raise ValueError(
            "Rate cannot be negative."
        )

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO treasury_bill_rates
        (
            auction_date,
            tenor_days,
            rate,
            issue_number,
            source,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            auction_date,
            tenor_days,
            rate,
            issue_number,
            source,
            datetime.now().isoformat(
                timespec="seconds"
            ),
        )
    )

    connection.commit()

    connection.close()


# ============================================================
# PREVENT DUPLICATES
# ============================================================

def add_unique_rate(
    auction_date,
    tenor_days,
    rate,
    issue_number=None,
    source="Central Bank of Kenya"
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT id
        FROM treasury_bill_rates
        WHERE auction_date = ?
        AND tenor_days = ?
        """,
        (
            auction_date,
            tenor_days,
        )
    )

    existing = cursor.fetchone()

    connection.close()

    if existing:

        return False

    add_treasury_bill_rate(
        auction_date,
        tenor_days,
        rate,
        issue_number,
        source,
    )

    return True


# ============================================================
# GET ALL DATA
# ============================================================

def get_all_data():

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            auction_date,
            tenor_days,
            rate,
            issue_number,
            source
        FROM treasury_bill_rates
        ORDER BY auction_date ASC, tenor_days ASC
        """
    )

    rows = cursor.fetchall()

    connection.close()

    return rows


# ============================================================
# GET DATA BY TENOR
# ============================================================

def get_tenor_history(
    tenor_days
):

    if tenor_days not in [91, 182, 364]:

        raise ValueError(
            "Tenor must be 91, 182 or 364 days."
        )

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            auction_date,
            tenor_days,
            rate,
            issue_number,
            source
        FROM treasury_bill_rates
        WHERE tenor_days = ?
        ORDER BY auction_date ASC
        """,
        (tenor_days,)
    )

    rows = cursor.fetchall()

    connection.close()

    return rows


# ============================================================
# LATEST OBSERVATION
# ============================================================

def get_latest_rate(
    tenor_days
):

    history = get_tenor_history(
        tenor_days
    )

    if not history:

        return None

    return history[-1]


# ============================================================
# DATABASE SUMMARY
# ============================================================

def database_summary():

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM treasury_bill_rates
        """
    )

    total = cursor.fetchone()[0]

    cursor.execute(
        """
        SELECT COUNT(DISTINCT auction_date)
        FROM treasury_bill_rates
        """
    )

    dates = cursor.fetchone()[0]

    connection.close()

    return {
        "database": str(DATABASE),
        "observations": total,
        "auction_dates": dates,
    }


# ============================================================
# SEED CURRENT CBK DATA
#
# These are the current published CBK reference rates already
# used by our working CBK data layer.
# ============================================================

def seed_current_cbk_data():

    observations = [

        (
            "2026-08-26",
            91,
            0.087700,
        ),

        (
            "2026-08-26",
            182,
            0.089480,
        ),

        (
            "2026-08-26",
            364,
            0.090365,
        ),

    ]

    for date, tenor, rate in observations:

        add_unique_rate(
            auction_date=date,
            tenor_days=tenor,
            rate=rate,
            source="Central Bank of Kenya",
        )


# ============================================================
# DISPLAY DATA
# ============================================================

def display_data():

    rows = get_all_data()

    print()
    print("=" * 75)
    print("KENYA HISTORICAL MARKET DATABASE")
    print("=" * 75)

    print()

    if not rows:

        print(
            "No historical observations found."
        )

        return

    print(
        f"{'Date':<15}"
        f"{'Tenor':<12}"
        f"{'Rate':<15}"
        f"{'Source':<30}"
    )

    print("-" * 75)

    for row in rows:

        date = row[0]
        tenor = row[1]
        rate = row[2]
        source = row[4]

        print(
            f"{date:<15}"
            f"{tenor:<12}"
            f"{rate * 100:<14.4f}%"
            f"{source:<30}"
        )

    print("-" * 75)


# ============================================================
# TEST
# ============================================================

def run_test():

    print()
    print("=" * 75)
    print("KENYA FINANCIAL ANALYTICS")
    print("HISTORICAL DATA ENGINE")
    print("=" * 75)

    initialize_database()

    seed_current_cbk_data()

    summary = database_summary()

    print()

    print(
        f"Database: "
        f"{summary['database']}"
    )

    print(
        f"Observations: "
        f"{summary['observations']}"
    )

    print(
        f"Auction Dates: "
        f"{summary['auction_dates']}"
    )

    display_data()

    print()
    print("=" * 75)
    print("HISTORICAL DATA ENGINE WORKING")
    print("=" * 75)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    run_test()
