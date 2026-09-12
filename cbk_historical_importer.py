
"""
KENYA FINANCIAL ANALYTICS
CBK HISTORICAL PDF IMPORTER

Automatically processes official CBK Treasury Bill
auction-result PDFs.

Extracts:
    - Auction date
    - Issue numbers
    - 91-day market weighted average rate
    - 182-day market weighted average rate
    - 364-day market weighted average rate

Stores results in:
    kenya_market.db

IMPORTANT:
Only data actually found inside the PDF is imported.
No historical market data is invented.
"""

import re
import sys
from pathlib import Path

from historical_data import (
    initialize_database,
    add_unique_rate,
    get_all_data,
)


# ============================================================
# FOLDERS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

PDF_FOLDER = BASE_DIR / "cbk_historical_pdfs"


# ============================================================
# CHECK PDF LIBRARY
# ============================================================

try:
    from pypdf import PdfReader

except ImportError:

    print()
    print("pypdf is not installed.")
    print()
    print("Install it with:")
    print("python -m pip install pypdf")
    print()

    sys.exit(1)


# ============================================================
# CREATE PDF FOLDER
# ============================================================

def create_pdf_folder():

    PDF_FOLDER.mkdir(
        exist_ok=True
    )


# ============================================================
# EXTRACT PDF TEXT
# ============================================================

def extract_pdf_text(pdf_file):

    reader = PdfReader(
        str(pdf_file)
    )

    pages = []

    for page in reader.pages:

        try:

            text = page.extract_text()

            if text:
                pages.append(text)

        except Exception:

            continue

    return "\n".join(pages)


# ============================================================
# NORMALIZE TEXT
# ============================================================

def normalize_text(text):

    if not text:
        return ""

    text = text.replace(
        "\xa0",
        " "
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# FIND AUCTION DATE
# ============================================================

def find_auction_date(text):

    patterns = [

        # DATED 15/06/2026
        r"DATED\s+(\d{2}/\d{2}/\d{4})",

        # DATED 15-06-2026
        r"DATED\s+(\d{2}-\d{2}-\d{4})",

        # DATED 15.06.2026
        r"DATED\s+(\d{2}\.\d{2}\.\d{4})",

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if match:

            raw = match.group(1)

            raw = raw.replace(
                ".",
                "/"
            ).replace(
                "-",
                "/"
            )

            day, month, year = (
                raw.split("/")
            )

            return (
                f"{year}-{month}-{day}"
            )

    return None


# ============================================================
# FIND ISSUE NUMBER
# ============================================================

def find_issue_number(
    text,
    tenor
):

    pattern = (
        rf"ISSUES?\s+"
        rf"([0-9]+)"
        rf"/{tenor}"
    )

    match = re.search(
        pattern,
        text,
        flags=re.IGNORECASE
    )

    if match:

        return (
            f"{match.group(1)}/{tenor}"
        )

    return None


# ============================================================
# EXTRACT MARKET WEIGHTED RATE
# ============================================================

def find_market_rate(
    text,
    tenor
):

    # The CBK PDF places the three tenor values
    # in the same "Market Weighted Average Interest Rate"
    # row. We first locate that row.

    patterns = [

        r"Market\s+Weighted\s+Average\s+Interest\s+Rate"
        r"(.*?)(?:Weighted\s+Average\s+Interest\s+Rate"
        r"\s+of\s+accepted\s+bids)",

        r"Market\s+Weighted\s+Average\s+Interest\s+Rate"
        r"(.*?)(?:Price\s+per\s+Kshs)",
    ]

    section = None

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if match:

            section = match.group(1)

            break

    if not section:

        return None

    # Extract percentage values.
    values = re.findall(
        r"(\d+(?:\.\d+)?)\s*%",
        section
    )

    if len(values) < 3:

        # Some PDF extraction layouts remove the %
        # symbol or insert spaces.
        values = re.findall(
            r"(\d+\.\d{2,4})",
            section
        )

    if len(values) < 3:

        return None

    # CBK ordering:
    # 91-day, 182-day, 364-day

    index = {
        91: 0,
        182: 1,
        364: 2,
    }[tenor]

    try:

        rate = float(
            values[index]
        )

    except (
        ValueError,
        IndexError
    ):

        return None

    # Handle PDF formatting such as:
    # 8 7665 instead of 8.7665

    if rate >= 100:

        return None

    return rate / 100


# ============================================================
# IMPORT ONE PDF
# ============================================================

def import_pdf(pdf_file):

    print()
    print(
        f"Processing: {pdf_file.name}"
    )

    text = extract_pdf_text(
        pdf_file
    )

    text = normalize_text(
        text
    )

    if not text:

        print(
            "  ERROR: Could not extract text."
        )

        return {
            "imported": 0,
            "rejected": 1,
        }

    auction_date = find_auction_date(
        text
    )

    if not auction_date:

        print(
            "  WARNING: Auction date not found."
        )

        return {
            "imported": 0,
            "rejected": 1,
        }

    print(
        f"  Auction date: {auction_date}"
    )

    imported = 0

    for tenor in [
        91,
        182,
        364
    ]:

        rate = find_market_rate(
            text,
            tenor
        )

        issue = find_issue_number(
            text,
            tenor
        )

        if rate is None:

            print(
                f"  {tenor}-day: rate not found"
            )

            continue

        print(
            f"  {tenor}-day: "
            f"{rate * 100:.4f}%"
        )

        added = add_unique_rate(
            auction_date=auction_date,
            tenor_days=tenor,
            rate=rate,
            issue_number=issue,
            source=(
                "Central Bank of Kenya - "
                "Official Auction Result"
            ),
        )

        if added:

            imported += 1

            print(
                "    -> IMPORTED"
            )

        else:

            print(
                "    -> DUPLICATE"
            )

    return {
        "imported": imported,
        "rejected": 0,
    }


# ============================================================
# IMPORT ALL PDFs
# ============================================================

def import_all_pdfs():

    create_pdf_folder()

    pdf_files = sorted(
        PDF_FOLDER.glob(
            "*.pdf"
        )
    )

    if not pdf_files:

        print()
        print(
            "No PDF files found."
        )

        print()
        print(
            f"Put official CBK PDFs here:"
        )

        print(
            PDF_FOLDER
        )

        return

    total_imported = 0
    total_rejected = 0

    print()
    print("=" * 70)
    print("CBK HISTORICAL PDF IMPORT")
    print("=" * 70)

    print(
        f"PDF files found: "
        f"{len(pdf_files)}"
    )

    for pdf_file in pdf_files:

        result = import_pdf(
            pdf_file
        )

        total_imported += (
            result["imported"]
        )

        total_rejected += (
            result["rejected"]
        )

    print()
    print("=" * 70)
    print("IMPORT SUMMARY")
    print("=" * 70)

    print(
        f"Records imported : "
        f"{total_imported}"
    )

    print(
        f"Files rejected   : "
        f"{total_rejected}"
    )

    print("=" * 70)


# ============================================================
# DATABASE SUMMARY
# ============================================================

def database_summary():

    rows = get_all_data()

    print()
    print("=" * 70)
    print("KENYA MARKET DATABASE")
    print("=" * 70)

    print(
        f"Total records: "
        f"{len(rows)}"
    )

    for tenor in [
        91,
        182,
        364
    ]:

        records = [
            row
            for row in rows
            if row[1] == tenor
        ]

        print(
            f"{tenor}-day records: "
            f"{len(records)}"
        )

    if rows:

        dates = [
            row[0]
            for row in rows
        ]

        print(
            f"Earliest date: "
            f"{min(dates)}"
        )

        print(
            f"Latest date: "
            f"{max(dates)}"
        )

    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

def main():

    initialize_database()

    create_pdf_folder()

    print()
    print("=" * 70)
    print("KENYA FINANCIAL ANALYTICS")
    print("CBK HISTORICAL PDF IMPORTER")
    print("=" * 70)

    print()
    print(
        f"PDF folder:"
    )

    print(
        PDF_FOLDER
    )

    import_all_pdfs()

    database_summary()

    print()
    print("=" * 70)
    print("CBK PDF IMPORTER READY")
    print("=" * 70)


if __name__ == "__main__":

    main()
