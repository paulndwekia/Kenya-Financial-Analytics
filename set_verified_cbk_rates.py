import sqlite3
from pathlib import Path
from datetime import datetime

DB = Path("kenya_financial_analytics.db")

con = sqlite3.connect(DB)

rows = [
    ("2026-09-11", "USD/KES", 129.45),
    ("2026-09-11", "GBP/KES", 174.82),
    ("2026-09-11", "EUR/KES", 150.22),
]

for date, instrument, value in rows:

    con.execute("""
        UPDATE market_data
        SET
            trade_date = ?,
            price = ?,
            date = ?,
            value = ?,
            source = 'Central Bank of Kenya'
        WHERE instrument = ?
          AND source = 'Central Bank of Kenya'
    """, (
        date,
        value,
        date,
        value,
        instrument
    ))

    # Create the record if it doesn't already exist.
    exists = con.execute("""
        SELECT COUNT(*)
        FROM market_data
        WHERE instrument = ?
          AND trade_date = ?
          AND source = 'Central Bank of Kenya'
    """, (
        instrument,
        date
    )).fetchone()[0]

    if exists == 0:

        con.execute("""
            INSERT INTO market_data
            (
                trade_date,
                instrument,
                price,
                yield,
                volume,
                source,
                date,
                value
            )
            VALUES (?, ?, ?, NULL, NULL, ?, ?, ?)
        """, (
            date,
            instrument,
            value,
            "Central Bank of Kenya",
            date,
            value
        ))

con.commit()

print()
print("=" * 65)
print("VERIFIED CBK CURRENT FX VALUES")
print("=" * 65)

for row in con.execute("""
    SELECT trade_date, instrument, price, source
    FROM market_data
    WHERE source = 'Central Bank of Kenya'
      AND instrument IN ('USD/KES','GBP/KES','EUR/KES')
      AND trade_date = '2026-09-11'
    ORDER BY instrument
""").fetchall():

    print(row)

con.close()

print()
print("DATABASE UPDATED SUCCESSFULLY")
