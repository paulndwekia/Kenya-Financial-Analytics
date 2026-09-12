from pathlib import Path
import sqlite3
import subprocess
import sys
import json
import re
import os
from datetime import datetime, timedelta

import pandas as pd
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader


BASE = Path(__file__).resolve().parent

APP_DB = BASE / "kenya_financial_analytics.db"
CBK_DB = BASE / "kenya_market.db"

STATUS_FILE = BASE / "cbk_auto_update_status.json"
LOG_FILE = BASE / "cbk_auto_update.log"
DOWNLOAD_DIR = BASE / "cbk_fx_bulletins"

CBK_BULLETIN_INDEX = (
    "https://www.centralbank.go.ke/releases/weekly-bulletin/"
)

SOURCE = "Central Bank of Kenya"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/142.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
}

DOWNLOAD_DIR.mkdir(
    exist_ok=True
)


# =========================================================
# LOGGING
# =========================================================

def log(message):

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    line = f"[{timestamp}] {message}"

    print(line)

    with LOG_FILE.open(
        "a",
        encoding="utf-8"
    ) as f:

        f.write(line + "\n")


def save_status(
    status,
    details=None
):

    payload = {
        "status": status,
        "last_attempt": datetime.now().isoformat(
            timespec="seconds"
        ),
        "details": details or {}
    }

    STATUS_FILE.write_text(
        json.dumps(
            payload,
            indent=2
        ),
        encoding="utf-8"
    )


# =========================================================
# DOWNLOAD CBK BULLETIN INDEX
# =========================================================

def get_bulletin_index():

    response = requests.get(
        CBK_BULLETIN_INDEX,
        headers=HEADERS,
        timeout=60,
        allow_redirects=True
    )

    response.raise_for_status()

    if len(response.text) < 1000:

        raise RuntimeError(
            "CBK weekly bulletin page returned unusable HTML."
        )

    return response.text


# =========================================================
# DISCOVER BULLETIN PDF LINKS
# =========================================================

def parse_date_from_text(text):

    if not text:
        return None

    patterns = [
        r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})",

        r"(\d{1,2})[- ]"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"[- ,]+(\d{4})",

        r"(\d{1,2})"
        r"(?:-| )"
        r"(January|February|March|April|May|June|July|August|"
        r"September|October|November|December)"
        r"(?:-| |,)+"
        r"(\d{4})"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if not match:
            continue

        groups = match.groups()

        try:

            if len(groups) == 3:

                a, b, c = groups

                if str(b).isdigit():

                    return datetime(
                        int(c),
                        int(b),
                        int(a)
                    )

                month = datetime.strptime(
                    str(b)[:3],
                    "%b"
                ).month

                return datetime(
                    int(c),
                    month,
                    int(a)
                )

        except Exception:
            pass

    return None


def discover_bulletins():

    html = get_bulletin_index()

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    found = []

    for anchor in soup.find_all(
        "a",
        href=True
    ):

        href = anchor.get(
            "href",
            ""
        ).strip()

        label = anchor.get_text(
            " ",
            strip=True
        )

        href_lower = href.lower()

        if ".pdf" not in href_lower:

            continue

        url = requests.compat.urljoin(
            CBK_BULLETIN_INDEX,
            href
        )

        combined = (
            f"{label} {href}"
        )

        date = parse_date_from_text(
            combined
        )

        found.append({
            "date": date,
            "url": url,
            "label": label
        })

    # Remove duplicates.
    unique = {}

    for item in found:

        unique[item["url"]] = item

    found = list(
        unique.values()
    )

    # Sort dated bulletins first.
    found.sort(
        key=lambda x: (
            x["date"] is not None,
            x["date"] or datetime.min
        ),
        reverse=True
    )

    return found


# =========================================================
# DOWNLOAD BULLETIN
# =========================================================

def download_bulletin(
    item,
    index
):

    response = requests.get(
        item["url"],
        headers={
            **HEADERS,
            "Accept": "application/pdf,*/*"
        },
        timeout=60,
        allow_redirects=True
    )

    response.raise_for_status()

    content = response.content

    if not content.startswith(
        b"%PDF"
    ):

        raise RuntimeError(
            "CBK link did not return a PDF."
        )

    filename = (
        f"weekly_bulletin_"
        f"{item['date'].strftime('%Y%m%d') if item['date'] else index}.pdf"
    )

    path = (
        DOWNLOAD_DIR
        /
        filename
    )

    path.write_bytes(
        content
    )

    return path


# =========================================================
# EXTRACT TEXT
# =========================================================

def extract_pdf_text(path):

    reader = PdfReader(
        str(path)
    )

    pages = []

    for page in reader.pages:

        text = page.extract_text()

        if text:

            pages.append(
                text
            )

    return "\n".join(
        pages
    )


# =========================================================
# EXTRACT TABLE 1 FX OBSERVATIONS
# =========================================================

def extract_fx_rows(text):

    text = text.replace(
        "\xa0",
        " "
    )

    text = text.replace(
        "\r",
        "\n"
    )

    # -----------------------------------------------------
    # Match rows such as:
    #
    # 28-Aug-26 129.46 175.83 150.75
    #
    # The summary rows such as "Sep 4-10" do not match.
    # -----------------------------------------------------

    pattern = re.compile(
        r"(?P<date>"
        r"\d{1,2}-"
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"-\d{2}"
        r")"
        r"\s+"
        r"(?P<usd>\d{2,3}\.\d+)"
        r"\s+"
        r"(?P<gbp>\d{2,3}\.\d+)"
        r"\s+"
        r"(?P<eur>\d{2,3}\.\d+)",
        flags=re.IGNORECASE
    )

    rows = []

    for match in pattern.finditer(
        text
    ):

        raw_date = match.group(
            "date"
        )

        parsed = pd.to_datetime(
            raw_date,
            format="%d-%b-%y",
            errors="coerce"
        )

        if pd.isna(parsed):

            continue

        usd = float(
            match.group("usd")
        )

        gbp = float(
            match.group("gbp")
        )

        eur = float(
            match.group("eur")
        )

        # Conservative sanity checks.
        if not (
            80 < usd < 200
            and
            100 < gbp < 250
            and
            100 < eur < 200
        ):

            continue

        date_text = parsed.strftime(
            "%Y-%m-%d"
        )

        rows.extend([
            {
                "date": date_text,
                "instrument": "USD/KES",
                "value": usd,
                "source": SOURCE
            },
            {
                "date": date_text,
                "instrument": "GBP/KES",
                "value": gbp,
                "source": SOURCE
            },
            {
                "date": date_text,
                "instrument": "EUR/KES",
                "value": eur,
                "source": SOURCE
            }
        ])

    return rows


# =========================================================
# DATABASE
# =========================================================

def ensure_app_db():

    con = sqlite3.connect(
        APP_DB
    )

    con.execute("""
        CREATE TABLE IF NOT EXISTS market_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date TEXT,
            instrument TEXT,
            price REAL,
            yield REAL,
            volume REAL,
            source TEXT
        )
    """)

    columns = {
        row[1]
        for row in con.execute(
            "PRAGMA table_info(market_data)"
        ).fetchall()
    }

    if "date" not in columns:

        con.execute(
            "ALTER TABLE market_data ADD COLUMN date TEXT"
        )

    if "value" not in columns:

        con.execute(
            "ALTER TABLE market_data ADD COLUMN value REAL"
        )

    con.commit()

    con.close()


def save_fx_history(rows):

    if not rows:

        return {
            "added": 0,
            "updated": 0
        }

    df = pd.DataFrame(
        rows
    )

    df = df.drop_duplicates(
        subset=[
            "date",
            "instrument"
        ],
        keep="last"
    )

    df["date"] = pd.to_datetime(
        df["date"]
    ).dt.strftime(
        "%Y-%m-%d"
    )

    df["value"] = pd.to_numeric(
        df["value"]
    )

    ensure_app_db()

    con = sqlite3.connect(
        APP_DB
    )

    added = 0
    updated = 0

    try:

        for _, row in df.iterrows():

            date = row["date"]
            instrument = row[
                "instrument"
            ]
            value = float(
                row["value"]
            )

            existing = con.execute("""
                SELECT id
                FROM market_data
                WHERE trade_date = ?
                  AND instrument = ?
                  AND source = ?
                LIMIT 1
            """, (
                date,
                instrument,
                SOURCE
            )).fetchone()

            if existing:

                con.execute("""
                    UPDATE market_data
                    SET
                        price = ?,
                        date = ?,
                        value = ?
                    WHERE id = ?
                """, (
                    value,
                    date,
                    value,
                    existing[0]
                ))

                updated += 1

            else:

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
                    VALUES (
                        ?, ?, ?, NULL, NULL, ?, ?, ?
                    )
                """, (
                    date,
                    instrument,
                    value,
                    SOURCE,
                    date,
                    value
                ))

                added += 1

        con.commit()

    finally:

        con.close()

    return {
        "added": added,
        "updated": updated
    }


# =========================================================
# GET LATEST N BULLETINS
# =========================================================

def update_fx_from_bulletins():

    bulletins = discover_bulletins()

    if not bulletins:

        raise RuntimeError(
            "No CBK weekly bulletin PDFs were discovered."
        )

    # We only need the newest few bulletins on each run.
    # Overlap ensures that a temporary missed bulletin
    # doesn't create a permanent gap.
    recent = bulletins[:4]

    log(
        f"CBK bulletins discovered: {len(bulletins)}"
    )

    log(
        f"Processing newest {len(recent)} bulletins."
    )

    rows = []

    processed = 0

    for index, item in enumerate(
        recent,
        start=1
    ):

        try:

            label = item["label"] or item["url"]

            log(
                f"FX bulletin {index}: {label}"
            )

            path = download_bulletin(
                item,
                index
            )

            pdf_text = extract_pdf_text(
                path
            )

            extracted = extract_fx_rows(
                pdf_text
            )

            log(
                f"  Extracted {len(extracted)} observations."
            )

            rows.extend(
                extracted
            )

            processed += 1

        except Exception as error:

            log(
                f"  Bulletin skipped: {error}"
            )

    if not rows:

        raise RuntimeError(
            "No daily FX observations were extracted "
            "from the latest CBK bulletins."
        )

    result = save_fx_history(
        rows
    )

    return {
        "bulletins_processed": processed,
        "observations_seen": len(rows),
        "added": result["added"],
        "updated": result["updated"]
    }


# =========================================================
# EXISTING T-BILL IMPORTER
# =========================================================

def run_tbill_importer():

    script = BASE / "cbk_auto_importer.py"

    if not script.exists():

        log(
            "Treasury Bill importer not found."
        )

        return False

    log(
        "Running official CBK Treasury Bill importer..."
    )

    try:

        python_exe = (
            BASE
            / ".venv"
            / "Scripts"
            / "python.exe"
        )

        result = subprocess.run(
            [
                str(python_exe),
                str(script)
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180
        )

        if result.returncode != 0:

            log(
                "Treasury Bill importer returned an error."
            )

            if result.stderr:

                log(
                    result.stderr[-3000:]
                )

            return False

        if result.stdout:

            for line in result.stdout.splitlines()[-20:]:

                if line.strip():

                    log(
                        "  " + line
                    )

        return True

    except Exception as error:

        log(
            f"Treasury Bill importer failed: {error}"
        )

        return False


# =========================================================
# SYNC TREASURY BILLS
# =========================================================

def sync_treasury_bills():

    if not CBK_DB.exists():

        log(
            "kenya_market.db not found."
        )

        return 0

    source = sqlite3.connect(
        CBK_DB
    )

    try:

        exists = source.execute("""
            SELECT COUNT(*)
            FROM sqlite_master
            WHERE type='table'
              AND name='treasury_bill_rates'
        """).fetchone()[0]

        if not exists:

            return 0

        rows = source.execute("""
            SELECT
                auction_date,
                tenor_days,
                rate
            FROM treasury_bill_rates
            WHERE tenor_days IN (91,182,364)
        """).fetchall()

    finally:

        source.close()

    if not rows:

        return 0

    con = sqlite3.connect(
        APP_DB
    )

    try:

        # Ensure table exists.
        con.execute("""
            CREATE TABLE IF NOT EXISTS treasury_bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                auction_date TEXT,
                tenor_days INTEGER,
                accepted_rate REAL,
                price REAL,
                amount_offered REAL,
                amount_accepted REAL,
                source TEXT
            )
        """)

        synced = 0

        for auction_date, tenor, rate in rows:

            if not auction_date or rate is None:
                continue

            rate = float(rate)

            if rate > 1:
                rate /= 100.0

            price = (
                100.0
                /
                (
                    1.0
                    +
                    rate * int(tenor) / 365.0
                )
            )

            existing = con.execute("""
                SELECT id
                FROM treasury_bills
                WHERE auction_date = ?
                  AND tenor_days = ?
                  AND source = ?
                LIMIT 1
            """, (
                auction_date,
                int(tenor),
                SOURCE
            )).fetchone()

            if existing:

                con.execute("""
                    UPDATE treasury_bills
                    SET
                        accepted_rate = ?,
                        price = ?
                    WHERE id = ?
                """, (
                    rate,
                    price,
                    existing[0]
                ))

            else:

                con.execute("""
                    INSERT INTO treasury_bills
                    (
                        auction_date,
                        tenor_days,
                        accepted_rate,
                        price,
                        source
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    auction_date,
                    int(tenor),
                    rate,
                    price,
                    SOURCE
                ))

            synced += 1

        con.commit()

    finally:

        con.close()

    return synced


# =========================================================
# MAIN
# =========================================================

def run():

    log("=" * 70)
    log("KENYA FINANCIAL ANALYTICS - CBK AUTOMATIC UPDATE")
    log("=" * 70)

    details = {}

    # -----------------------------------------------------
    # FX HISTORY
    # -----------------------------------------------------

    try:

        fx_result = update_fx_from_bulletins()

        details.update({
            "fx_source": "CBK Weekly Bulletins",
            **{
                f"fx_{key}": value
                for key, value in fx_result.items()
            }
        })

        log(
            f"FX update complete: "
            f"{fx_result}"
        )

        fx_ok = True

    except Exception as error:

        details["fx_error"] = str(error)

        log(
            f"FX update failed: {error}"
        )

        fx_ok = False

    # -----------------------------------------------------
    # TREASURY BILLS
    # -----------------------------------------------------

    tb_import_ok = run_tbill_importer()

    details[
        "tbill_importer"
    ] = tb_import_ok

    try:

        synced = sync_treasury_bills()

        details[
            "tbill_synced"
        ] = synced

        log(
            f"Treasury Bill synchronization: "
            f"{synced} records."
        )

        tb_ok = (
            tb_import_ok
            or
            synced > 0
        )

    except Exception as error:

        details[
            "tbill_error"
        ] = str(error)

        log(
            f"Treasury Bill sync failed: {error}"
        )

        tb_ok = tb_import_ok

    # -----------------------------------------------------
    # FINAL STATUS
    # -----------------------------------------------------

    if fx_ok or tb_ok:

        save_status(
            "SUCCESS",
            details
        )

        log(
            "AUTOMATIC CBK UPDATE FINISHED SUCCESSFULLY."
        )

    else:

        save_status(
            "FAILED",
            details
        )

        log(
            "AUTOMATIC CBK UPDATE FAILED."
        )


if __name__ == "__main__":
    run()
