
"""
============================================================
CBK AUTOMATIC TREASURY BILL IMPORTER
============================================================

Downloads official CBK Treasury Bill auction-result PDFs,
extracts the Market Weighted Average Interest Rate for:

    91 days
    182 days
    364 days

and stores the results in:

    kenya_market.db

Only official CBK publications are accepted.
Duplicate records are ignored.
No artificial/fake market data is generated.
============================================================
"""

import re
import sqlite3
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader


BASE_DIR = Path(__file__).resolve().parent

DATABASE = BASE_DIR / "kenya_market.db"

DOWNLOAD_DIR = BASE_DIR / "cbk_downloads"

DOWNLOAD_DIR.mkdir(
    exist_ok=True
)

CBK_URL = (
    "https://www.centralbank.go.ke/"
    "bills-bonds/treasury-bills/"
)

HEADERS = {
    "User-Agent":
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "Chrome/140 Safari/537.36"
}


# ============================================================
# DATABASE
# ============================================================

def ensure_database():

    connection = sqlite3.connect(
        DATABASE
    )

    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS treasury_bill_rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            auction_date TEXT NOT NULL,
            tenor_days INTEGER NOT NULL,
            rate REAL NOT NULL,
            issue_number TEXT,
            source TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(auction_date, tenor_days)
        )
    """)

    connection.commit()

    connection.close()


def insert_record(
    auction_date,
    tenor,
    rate,
    issue_number=""
):

    if rate > 1:

        rate /= 100

    connection = sqlite3.connect(
        DATABASE
    )

    cursor = connection.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO treasury_bill_rates
        (
            auction_date,
            tenor_days,
            rate,
            issue_number,
            source,
            created_at
        )
        VALUES (
            ?, ?, ?, ?, 'CBK Automatic Import',
            datetime('now')
        )
    """, (
        auction_date,
        tenor,
        rate,
        issue_number
    ))

    added = cursor.rowcount > 0

    connection.commit()

    connection.close()

    return added


# ============================================================
# DOWNLOAD CBK PAGE
# ============================================================

def get_cbk_page():

    print()
    print(
        "Connecting to official CBK Treasury Bill page..."
    )

    response = requests.get(
        CBK_URL,
        headers=HEADERS,
        timeout=30,
        allow_redirects=True
    )

    response.raise_for_status()

    print(
        f"CBK page loaded: HTTP {response.status_code}"
    )

    return response.text


# ============================================================
# FIND RESULT PDF LINKS
# ============================================================

def find_pdf_links(html):

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    links = []

    for anchor in soup.find_all(
        "a",
        href=True
    ):

        href = anchor["href"]

        title = (
            anchor.get_text(
                " ",
                strip=True
            )
            .lower()
        )

        href_lower = href.lower()

        if (
            ".pdf" in href_lower
            or "result" in href_lower
        ):

            url = urljoin(
                CBK_URL,
                href
            )

            if (
                "centralbank.go.ke"
                in url
            ):

                links.append(
                    (
                        url,
                        title
                    )
                )

    # Remove duplicates

    unique = {}

    for url, title in links:

        unique[url] = title

    return [
        (url, title)
        for url, title
        in unique.items()
    ]


# ============================================================
# DOWNLOAD PDF
# ============================================================

def download_pdf(
    url
):

    filename = (
        url
        .split("/")[-1]
        .split("?")[0]
    )

    if not filename.lower().endswith(
        ".pdf"
    ):

        filename += ".pdf"

    path = (
        DOWNLOAD_DIR
        / filename
    )

    if path.exists():

        return path

    print()
    print(
        "Downloading:"
    )

    print(
        url
    )

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=45,
        allow_redirects=True
    )

    response.raise_for_status()

    path.write_bytes(
        response.content
    )

    return path


# ============================================================
# EXTRACT PDF TEXT
# ============================================================

def extract_text(
    pdf_path
):

    reader = PdfReader(
        str(pdf_path)
    )

    pages = []

    for page in reader.pages:

        try:

            text = page.extract_text()

            if text:

                pages.append(
                    text
                )

        except Exception:

            continue

    return "\n".join(
        pages
    )


# ============================================================
# NORMALIZE PDF TEXT
# ============================================================

def normalize(
    text
):

    text = text.replace(
        "\xa0",
        " "
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text


# ============================================================
# EXTRACT AUCTION DATE
# ============================================================

def extract_date(
    text
):

    patterns = [

        r"DATED\s+(\d{2})[-/](\d{2})[-/](\d{4})",

        r"DATED\s+(\d{2})\s+(\d{2})\s+(\d{4})",

        r"DATED\s+(\d{1,2})[-/](\d{1,2})[-/](\d{4})"

    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            day = match.group(1)
            month = match.group(2)
            year = match.group(3)

            return (
                f"{year}-"
                f"{int(month):02d}-"
                f"{int(day):02d}"
            )

    return None


# ============================================================
# EXTRACT ISSUE NUMBERS
# ============================================================

def extract_issues(
    text
):

    pattern = (
        r"ISSUES?\s+"
        r"(\d{3,4}/091)"
        r".*?"
        r"(\d{3,4}/182)"
        r".*?"
        r"(\d{3,4}/364)"
    )

    match = re.search(
        pattern,
        text,
        re.IGNORECASE
    )

    if not match:

        return {
            91: "",
            182: "",
            364: ""
        }

    return {
        91: match.group(1),
        182: match.group(2),
        364: match.group(3)
    }


# ============================================================
# EXTRACT WEIGHTED AVERAGE RATES
# ============================================================

def extract_rates(
    text
):

    clean = normalize(
        text
    )

    # The CBK PDFs normally contain:
    #
    # Market Weighted Average Interest Rate
    # 8.xxxx%  9.xxxx%  9.xxxx%
    #
    # We first locate the phrase and then inspect
    # the following section.

    marker = (
        "Market Weighted Average Interest Rate"
    )

    position = clean.lower().find(
        marker.lower()
    )

    if position == -1:

        return {}

    section = clean[
        position:
        position + 500
    ]

    numbers = re.findall(
        r"(\d{1,2}\.\d{3,6})\s*%",
        section
    )

    if len(numbers) < 3:

        return {}

    return {
        91: float(numbers[0]),
        182: float(numbers[1]),
        364: float(numbers[2])
    }


# ============================================================
# PROCESS PDF
# ============================================================

def process_pdf(
    pdf_path,
    url=""
):

    print()
    print(
        "-" * 65
    )

    print(
        f"Processing: {pdf_path.name}"
    )

    text = extract_text(
        pdf_path
    )

    if not text.strip():

        print(
            "Could not extract text."
        )

        return 0

    auction_date = extract_date(
        text
    )

    if not auction_date:

        print(
            "Auction date not detected."
        )

        return 0

    rates = extract_rates(
        text
    )

    if len(rates) < 3:

        print(
            "Could not safely extract all "
            "three CBK rates."
        )

        return 0

    issues = extract_issues(
        text
    )

    added = 0

    for tenor in (
        91,
        182,
        364
    ):

        rate = rates.get(
            tenor
        )

        if rate is None:
            continue

        if insert_record(
            auction_date,
            tenor,
            rate,
            issues.get(
                tenor,
                ""
            )
        ):

            print(
                f"ADDED {tenor}-day: "
                f"{rate:.4f}%"
            )

            added += 1

        else:

            print(
                f"DUPLICATE {tenor}-day: "
                f"{rate:.4f}%"
            )

    return added


# ============================================================
# MAIN IMPORT PROCESS
# ============================================================

def run():

    ensure_database()

    print()
    print("=" * 70)
    print("KENYA FINANCIAL ANALYTICS")
    print("CBK AUTOMATIC TREASURY BILL IMPORTER")
    print("=" * 70)

    try:

        html = get_cbk_page()

    except Exception as error:

        print()
        print(
            "CBK CONNECTION FAILED"
        )

        print(
            str(error)
        )

        print()
        print(
            "The existing database has NOT been modified."
        )

        return

    links = find_pdf_links(
        html
    )

    if not links:

        print()
        print(
            "No CBK result PDFs were discovered."
        )

        return

    print()
    print(
        f"CBK result links discovered: "
        f"{len(links)}"
    )

    # Process the most recent results first.
    # Limit the first automatic run so that
    # the project does not hammer the CBK website.

    links = links[:20]

    total_added = 0
    processed = 0

    for url, title in links:

        try:

            pdf = download_pdf(
                url
            )

            added = process_pdf(
                pdf,
                url
            )

            total_added += added

            processed += 1

            time.sleep(
                0.5
            )

        except Exception as error:

            print()
            print(
                "FAILED:"
            )

            print(
                url
            )

            print(
                str(error)
            )

    print()
    print("=" * 70)
    print("CBK IMPORT COMPLETE")
    print("=" * 70)

    print(
        f"PDFs processed: {processed}"
    )

    print(
        f"New observations added: "
        f"{total_added}"
    )

    print(
        f"Database: {DATABASE}"
    )

    print(
        f"Downloaded PDFs: {DOWNLOAD_DIR}"
    )

    print("=" * 70)


if __name__ == "__main__":

    run()
