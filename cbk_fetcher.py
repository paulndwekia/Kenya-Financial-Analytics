"""
KENYA FINANCIAL ANALYTICS
CBK TREASURY BILL DATA ENGINE
"""

import re
from datetime import datetime

import requests


# ============================================================
# CBK OFFICIAL TREASURY BILL PAGE
# ============================================================

CBK_URLS = [
    "https://www.centralbank.go.ke/bills-bonds/treasury-bills/",
    "https://www.centralbank.go.ke/securities/treasury-bills/",
]


# ============================================================
# DOWNLOAD CBK PAGE
# ============================================================

def download_cbk_page():

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/142.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }

    for url in CBK_URLS:

        try:

            print(f"Trying CBK: {url}")

            response = requests.get(
                url,
                headers=headers,
                timeout=20,
                allow_redirects=True,
            )

            print(
                f"HTTP Status: {response.status_code}"
            )

            if response.status_code == 200:

                print(
                    "CBK page downloaded successfully."
                )

                return response.text

        except requests.RequestException as error:

            print(
                f"Connection failed: {error}"
            )

    return None


# ============================================================
# CLEAN HTML
# ============================================================

def clean_html(html):

    if not html:
        return ""

    html = re.sub(
        r"<script.*?</script>",
        " ",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    html = re.sub(
        r"<style.*?</style>",
        " ",
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    html = re.sub(
        r"<[^>]+>",
        " ",
        html,
    )

    html = html.replace(
        "&nbsp;",
        " ",
    )

    html = html.replace(
        "&amp;",
        "&",
    )

    html = re.sub(
        r"\s+",
        " ",
        html,
    )

    return html.strip()


# ============================================================
# FIND TREASURY BILL RATE
# ============================================================

def find_rate(text, tenor):

    if not text:
        return None

    # Search around the tenor
    pattern = (
        rf"{tenor}\s*[- ]?\s*DAY"
        rf".{{0,1200}}?"
        rf"(\d+\.\d{{2,4}})\s*%"
    )

    match = re.search(
        pattern,
        text,
        flags=re.IGNORECASE,
    )

    if match:

        try:

            percentage = float(
                match.group(1)
            )

            # Prevent accidentally interpreting
            # an unrelated large number as a rate.
            if 0 < percentage < 100:

                return percentage / 100

        except ValueError:

            pass

    return None


# ============================================================
# FETCH TREASURY BILL RATES
# ============================================================

def fetch_treasury_bill_rates():

    html = download_cbk_page()

    if html is None:

        return None

    text = clean_html(html)

    rates = {}

    for tenor in [91, 182, 364]:

        rate = find_rate(
            text,
            tenor,
        )

        if rate is not None:

            rates[tenor] = rate

    if not rates:

        return None

    return rates


# ============================================================
# COMPLETE MARKET DATA
# ============================================================

def get_cbk_market_data():

    rates = fetch_treasury_bill_rates()

    timestamp = datetime.now().isoformat(
        timespec="seconds"
    )

    if rates is None:

        return {
            "success": False,
            "source": "Central Bank of Kenya",
            "retrieved_at": timestamp,
            "rates": {},
        }

    return {
        "success": True,
        "source": "Central Bank of Kenya",
        "retrieved_at": timestamp,
        "rates": rates,
    }


# ============================================================
# DISPLAY
# ============================================================

def display_data(data):

    print()
    print("=" * 65)
    print("KENYA FINANCIAL ANALYTICS")
    print("CBK TREASURY BILL DATA")
    print("=" * 65)

    print()
    print(
        f"Source: {data['source']}"
    )

    print(
        f"Retrieved: {data['retrieved_at']}"
    )

    print()

    for tenor in [91, 182, 364]:

        rate = data["rates"].get(
            tenor
        )

        if rate is None:

            print(
                f"{tenor}-Day T-Bill : NOT FOUND"
            )

        else:

            print(
                f"{tenor}-Day T-Bill : "
                f"{rate * 100:.4f}%"
            )

    print()
    print("=" * 65)


# ============================================================
# MAIN TEST
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 65)
    print("CBK LIVE MARKET DATA TEST")
    print("=" * 65)

    print()
    print("Connecting to official CBK...")
    print()

    data = get_cbk_market_data()

    if data["success"]:

        print()
        print("SUCCESS!")
        print("CBK MARKET DATA RETRIEVED.")

        display_data(data)

        print()
        print(
            "CBK DATA ENGINE WORKING"
        )

    else:

        print()
        print(
            "CBK DATA COULD NOT BE RETRIEVED."
        )

        print(
            "No fake market data was inserted."
        )

    print()