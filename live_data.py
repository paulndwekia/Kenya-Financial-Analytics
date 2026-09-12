from pathlib import Path
import io
import re
import sqlite3
from datetime import datetime

import pandas as pd
import requests


BASE = Path(__file__).resolve().parent

APP_DB = BASE / "kenya_financial_analytics.db"
REAL_CBK_DB = BASE / "kenya_market.db"

CBK_RATES_URL = "https://www.centralbank.go.ke/rates/forex-exchange-rates/"
CBK_NEW_RATES_URL = "https://www.centralbank.go.ke/new-rates/"
CBK_TBILLS_URL = "https://www.centralbank.go.ke/bills-bonds/treasury-bills/"

SOURCE = "Central Bank of Kenya"

TIMEOUT = 30


def session():
    s = requests.Session()

    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/142.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.centralbank.go.ke/"
    })

    return s


def cbk_get(url):
    s = session()

    response = s.get(
        url,
        timeout=TIMEOUT,
        allow_redirects=True
    )

    response.raise_for_status()

    text = response.text.lower()

    # CloudProxy / JavaScript challenge
    blocked_markers = [
        "javascript is required",
        "you are being redirected",
        "cloudproxy",
        "sucuri",
        "challenge-platform"
    ]

    if any(x in text for x in blocked_markers):
        raise RuntimeError(
            "CBK security layer blocked the Python request."
        )

    return response


def normalize_column(value):
    return (
        str(value)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def find_fx_table(tables):
    for table in tables:

        columns = [
            normalize_column(c)
            for c in table.columns
        ]

        joined = " ".join(columns)

        if (
            "date" in joined
            and "currency" in joined
            and "mean" in joined
        ):
            return table.copy()

    return None


def get_live_fx():
    """
    Attempt to obtain official CBK FX data.

    The CBK page officially exposes:
    Date | Currency | Mean | Buy | Sell
    """

    response = cbk_get(CBK_RATES_URL)

    tables = pd.read_html(
        io.StringIO(response.text)
    )

    table = find_fx_table(tables)

    if table is None:
        raise RuntimeError(
            "CBK page loaded but the FX table could not be located."
        )

    table.columns = [
        normalize_column(c)
        for c in table.columns
    ]

    date_col = next(
        c for c in table.columns
        if c == "date"
    )

    currency_col = next(
        c for c in table.columns
        if c == "currency"
    )

    mean_col = next(
        c for c in table.columns
        if c == "mean"
    )

    df = table[
        [date_col, currency_col, mean_col]
    ].copy()

    df.columns = [
        "date",
        "currency",
        "value"
    ]

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce",
        dayfirst=True
    )

    df["currency"] = (
        df["currency"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    df["value"] = pd.to_numeric(
        df["value"],
        errors="coerce"
    )

    mapping = {
        "US DOLLAR": "USD/KES",
        "STG POUND": "GBP/KES",
        "EURO": "EUR/KES"
    }

    df["instrument"] = df["currency"].map(mapping)

    df = df[
        df["instrument"].notna()
        & df["date"].notna()
        & df["value"].notna()
        & (df["value"] > 0)
    ].copy()

    df["source"] = SOURCE

    df = df[
        [
            "date",
            "instrument",
            "value",
            "source"
        ]
    ]

    df = df.drop_duplicates(
        subset=[
            "date",
            "instrument"
        ]
    )

    df = df.sort_values(
        [
            "instrument",
            "date"
        ]
    )

    if df.empty:
        raise RuntimeError(
            "CBK returned no USD/KES, EUR/KES or GBP/KES observations."
        )

    return df.reset_index(drop=True)


def get_current_cbk_rates():
    """
    Read the current CBK daily exchange rates.
    """

    from bs4 import BeautifulSoup

    response = cbk_get(CBK_NEW_RATES_URL)

    soup = BeautifulSoup(response.text, "html.parser")
    visible_text = soup.get_text("\n", strip=True)

    patterns = {
        "USD/KES": r"US\s+DOLLAR\s*[|:]\s*([0-9]+(?:\.[0-9]+)?)",
        "GBP/KES": r"STG\s+POUND\s*[|:]\s*([0-9]+(?:\.[0-9]+)?)",
        "EUR/KES": r"EURO\s*[|:]\s*([0-9]+(?:\.[0-9]+)?)",
    }

    rows = []

    for instrument, pattern in patterns.items():

        match = re.search(
            pattern,
            visible_text,
            flags=re.IGNORECASE
        )

        if match is None:
            raise RuntimeError(
                f"CBK current rate not found for {instrument}"
            )

        rows.append({
            "instrument": instrument,
            "value": float(match.group(1)),
            "source": "Central Bank of Kenya"
        })

    date_match = re.search(
        r"Posted\s+On\s*:?\s*(\d{1,2})-(\d{1,2})-(\d{4})",
        visible_text,
        flags=re.IGNORECASE
    )

    if date_match:
        current_date = pd.Timestamp(
            year=int(date_match.group(3)),
            month=int(date_match.group(2)),
            day=int(date_match.group(1))
        )
    else:
        current_date = pd.Timestamp.today().normalize()

    for row in rows:
        row["date"] = current_date

    return pd.DataFrame(
        rows,
        columns=[
            "date",
            "instrument",
            "value",
            "source"
        ]
    )

def get_local_cbk_treasury_bills():
    """
    Read the existing genuine CBK Treasury Bill database.

    This is a fallback only. No synthetic values are created.
    """

    if not REAL_CBK_DB.exists():
        return pd.DataFrame(
            columns=[
                "date",
                "tenor_days",
                "rate",
                "source"
            ]
        )

    con = sqlite3.connect(
        str(REAL_CBK_DB)
    )

    try:

        tables = pd.read_sql_query(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            """,
            con
        )

        names = set(
            tables["name"].astype(str)
        )

        if "treasury_bill_rates" not in names:
            return pd.DataFrame(
                columns=[
                    "date",
                    "tenor_days",
                    "rate",
                    "source"
                ]
            )

        df = pd.read_sql_query(
            """
            SELECT
                auction_date AS date,
                tenor_days,
                rate,
                source
            FROM treasury_bill_rates
            ORDER BY auction_date
            """,
            con
        )

    finally:
        con.close()

    if df.empty:
        return df

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    )

    df["tenor_days"] = pd.to_numeric(
        df["tenor_days"],
        errors="coerce"
    )

    df["rate"] = pd.to_numeric(
        df["rate"],
        errors="coerce"
    )

    df = df[
        df["date"].notna()
        & df["tenor_days"].isin(
            [91, 182, 364]
        )
        & df["rate"].notna()
    ].copy()

    df["source"] = SOURCE

    return df.reset_index(drop=True)


def get_live_treasury_bills():
    """
    Try the official CBK Treasury Bill page.
    """

    response = cbk_get(
        CBK_TBILLS_URL
    )

    tables = pd.read_html(
        io.StringIO(response.text)
    )

    selected = None

    for table in tables:

        cols = [
            normalize_column(c)
            for c in table.columns
        ]

        joined = " ".join(cols)

        if (
            "tenor" in joined
            and (
                "marketaveragerate" in joined
                or "average_interest_rate" in joined
                or "averagerate" in joined
            )
        ):
            selected = table.copy()
            break

    if selected is None:

        for table in tables:

            raw_text = " ".join(
                table.astype(str)
                .values
                .flatten()
            ).lower()

            if (
                "91" in raw_text
                and "182" in raw_text
                and "364" in raw_text
            ):
                selected = table.copy()
                break

    if selected is None:
        raise RuntimeError(
            "CBK Treasury Bill table could not be identified."
        )

    selected.columns = [
        normalize_column(c)
        for c in selected.columns
    ]

    rows = []

    for _, row in selected.iterrows():

        values = [
            str(x).strip()
            for x in row.tolist()
        ]

        text = " ".join(values)

        tenor = None

        for candidate in [
            91,
            182,
            364
        ]:

            if re.search(
                rf"\b{candidate}\b",
                text
            ):
                tenor = candidate
                break

        if tenor is None:
            continue

        rate_candidates = []

        for value in values:

            cleaned = (
                value
                .replace(",", "")
                .replace("%", "")
            )

            try:

                number = float(
                    cleaned
                )

                if 1 <= number <= 30:
                    rate_candidates.append(
                        number
                    )

            except Exception:
                pass

        if not rate_candidates:
            continue

        rate = rate_candidates[-1]

        date_value = None

        for value in values:

            parsed = pd.to_datetime(
                value,
                errors="coerce",
                dayfirst=True
            )

            if pd.notna(parsed):
                date_value = parsed
                break

        if date_value is None:
            continue

        rows.append({
            "date": date_value,
            "tenor_days": tenor,
            "rate": rate,
            "source": SOURCE
        })

    result = pd.DataFrame(
        rows,
        columns=[
            "date",
            "tenor_days",
            "rate",
            "source"
        ]
    )

    if result.empty:
        raise RuntimeError(
            "CBK Treasury Bill page returned no usable records."
        )

    return result


def ensure_app_tables(con):

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS market_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            instrument TEXT,
            value REAL,
            source TEXT
        )
        """
    )

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS treasury_bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            tenor_days INTEGER,
            rate REAL,
            source TEXT
        )
        """
    )


def write_data(
    fx,
    tb
):

    con = sqlite3.connect(
        str(APP_DB)
    )

    try:

        ensure_app_tables(con)

        # Remove only previous genuine CBK records.
        con.execute(
            """
            DELETE FROM market_data
            WHERE source = ?
            """,
            (SOURCE,)
        )

        con.execute(
            """
            DELETE FROM treasury_bills
            WHERE source = ?
            """,
            (SOURCE,)
        )

        for _, row in fx.iterrows():

            con.execute(
                """
                INSERT INTO market_data
                (date, instrument, value, source)
                VALUES (?, ?, ?, ?)
                """,
                (
                    pd.Timestamp(
                        row["date"]
                    ).strftime("%Y-%m-%d"),
                    str(
                        row["instrument"]
                    ),
                    float(
                        row["value"]
                    ),
                    SOURCE
                )
            )

        for _, row in tb.iterrows():

            con.execute(
                """
                INSERT INTO treasury_bills
                (date, tenor_days, rate, source)
                VALUES (?, ?, ?, ?)
                """,
                (
                    pd.Timestamp(
                        row["date"]
                    ).strftime("%Y-%m-%d"),
                    int(
                        row["tenor_days"]
                    ),
                    float(
                        row["rate"]
                    ),
                    SOURCE
                )
            )

        con.commit()

    finally:
        con.close()


def refresh(
    db_path=None,
    force=False
):

    global APP_DB

    if db_path is not None:
        APP_DB = Path(
            db_path
        )

    fx = pd.DataFrame(
        columns=[
            "date",
            "instrument",
            "value",
            "source"
        ]
    )

    tb = pd.DataFrame(
        columns=[
            "date",
            "tenor_days",
            "rate",
            "source"
        ]
    )

    live_fx = False
    live_tb = False

    # -------------------------------------------------
    # 1. Try official CBK FX page.
    # -------------------------------------------------

    try:

        fx = get_live_fx()
        live_fx = True

    except Exception:

        # Try the current-rate page as a second
        # official CBK route.

        try:

            fx = get_current_cbk_rates()
            live_fx = True

        except Exception:

            fx = pd.DataFrame(
                columns=[
                    "date",
                    "instrument",
                    "value",
                    "source"
                ]
            )

    # -------------------------------------------------
    # 2. Try official CBK Treasury Bills.
    # -------------------------------------------------

    try:

        tb = get_live_treasury_bills()
        live_tb = True

    except Exception as error:
        print(f"CBK Treasury Bill live refresh unavailable: {error}")

        tb = get_local_cbk_treasury_bills()

    # -------------------------------------------------
    # 3. If live FX failed, preserve existing genuine
    #    CBK FX data already in the application DB.
    # -------------------------------------------------

    if fx.empty and APP_DB.exists():

        con = sqlite3.connect(
            str(APP_DB)
        )

        try:

            fx = pd.read_sql_query(
                """
                SELECT
                    date,
                    instrument,
                    value,
                    source
                FROM market_data
                WHERE source = ?
                ORDER BY date
                """,
                con,
                params=(SOURCE,)
            )

        except Exception:

            fx = pd.DataFrame(
                columns=[
                    "date",
                    "instrument",
                    "value",
                    "source"
                ]
            )

        finally:
            con.close()

    # -------------------------------------------------
    # 4. Write only genuine CBK data.
    # -------------------------------------------------

    if not fx.empty or not tb.empty:

        write_data(
            fx,
            tb
        )

    return {
        "available": (
            not fx.empty
            or not tb.empty
        ),
        "fx_rows": int(
            len(fx)
        ),
        "treasury_bill_rows": int(
            len(tb)
        ),
        "fx_live": bool(
            live_fx
        ),
        "treasury_bills_live": bool(
            live_tb
        ),
        "mode": (
            "LIVE CBK"
            if live_fx or live_tb
            else "LOCAL CBK CACHE"
        ),
        "source": SOURCE,
        "updated": datetime.now().isoformat(
            timespec="seconds"
        )
    }


def status(
    db_path=None
):

    target = (
        Path(db_path)
        if db_path
        else APP_DB
    )

    try:

        con = sqlite3.connect(
            str(target)
        )

        fx_count = con.execute(
            """
            SELECT COUNT(*)
            FROM market_data
            WHERE source = ?
            """,
            (SOURCE,)
        ).fetchone()[0]

        tb_count = con.execute(
            """
            SELECT COUNT(*)
            FROM treasury_bills
            WHERE source = ?
            """,
            (SOURCE,)
        ).fetchone()[0]

        latest_fx = con.execute(
            """
            SELECT MAX(date)
            FROM market_data
            WHERE source = ?
            """,
            (SOURCE,)
        ).fetchone()[0]

        latest_tb = con.execute(
            """
            SELECT MAX(date)
            FROM treasury_bills
            WHERE source = ?
            """,
            (SOURCE,)
        ).fetchone()[0]

        con.close()

        return {
            "available": (
                fx_count > 0
                or tb_count > 0
            ),
            "fx_rows": fx_count,
            "treasury_bill_rows": tb_count,
            "latest_fx": latest_fx,
            "latest_treasury_bill": latest_tb,
            "source": SOURCE
        }

    except Exception as e:

        return {
            "available": False,
            "fx_rows": 0,
            "treasury_bill_rows": 0,
            "source": SOURCE,
            "error": str(e)
        }


if __name__ == "__main__":

    print("=" * 70)
    print("KENYA FINANCIAL ANALYTICS")
    print("CBK DATA ENGINE")
    print("=" * 70)

    print("\nAttempting official CBK refresh...")

    result = refresh(
        APP_DB,
        force=True
    )

    print("\nRESULT")
    print("-" * 70)

    for key, value in result.items():
        print(
            f"{key}: {value}"
        )

    print("\nDATABASE STATUS")
    print("-" * 70)

    print(
        status(APP_DB)
    )

    print("\nCBK DATA ENGINE COMPLETE")
    print("=" * 70)
