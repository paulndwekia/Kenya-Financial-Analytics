import io
import json
import os
import re
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from urllib.parse import urljoin

import psycopg
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
from psycopg.rows import dict_row

CBK_FOREX_URL = "https://www.centralbank.go.ke/forex/"
CBK_TBILLS_URL = "https://www.centralbank.go.ke/bills-bonds/treasury-bills/"
SOURCE = "Central Bank of Kenya"
HEADERS = {
    "User-Agent": "KenyaFinancialAnalytics/2.0 (market-data research; contact via project repository)",
    "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
}


def get(url, accept=None):
    headers = dict(HEADERS)
    if accept:
        headers["Accept"] = accept
    response = requests.get(url, headers=headers, timeout=(8, 25), allow_redirects=True)
    response.raise_for_status()
    return response


def parse_date(value):
    value = str(value or "").strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d-%b-%y", "%d-%b-%Y", "%d %b %Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def parse_rate(value):
    try:
        number = float(str(value).replace(",", "").replace("%", "").strip())
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def fetch_fx():
    response = get(CBK_FOREX_URL)
    soup = BeautifulSoup(response.text, "html.parser")
    currency_map = {
        "US DOLLAR": "USD/KES",
        "STG POUND": "GBP/KES",
        "EURO": "EUR/KES",
    }
    observations = {}
    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in tr.find_all(["th", "td"])]
            if len(cells) < 3:
                continue
            date = parse_date(cells[0])
            currency = re.sub(r"\s+", " ", cells[1].upper()).strip()
            instrument = currency_map.get(currency)
            rate = parse_rate(cells[2])
            if date and instrument and rate and 80 < rate < 250:
                observations[(date.isoformat(), instrument)] = {
                    "date": date.isoformat(),
                    "instrument": instrument,
                    "rate": rate,
                    "source": SOURCE,
                    "source_url": CBK_FOREX_URL,
                }

    if observations:
        return list(observations.values())

    # Fallback to the CBK daily rates page; only use its explicitly posted date.
    current_url = "https://www.centralbank.go.ke/new-rates/"
    page = get(current_url)
    text = BeautifulSoup(page.text, "html.parser").get_text("\n", strip=True)
    posted = re.search(r"Posted\s+On\s*:?\s*(\d{1,2}-\d{1,2}-\d{4})", text, re.I)
    posted_date = parse_date(posted.group(1)) if posted else None
    if not posted_date:
        raise RuntimeError("The CBK daily FX page did not provide a usable posted date.")
    patterns = {
        "USD/KES": r"US\s+DOLLAR\s*[|:]\s*([0-9]+(?:\.[0-9]+)?)",
        "GBP/KES": r"STG\s+POUND\s*[|:]\s*([0-9]+(?:\.[0-9]+)?)",
        "EUR/KES": r"EURO\s*[|:]\s*([0-9]+(?:\.[0-9]+)?)",
    }
    fallback = []
    for instrument, pattern in patterns.items():
        match = re.search(pattern, text, re.I)
        if not match:
            raise RuntimeError("CBK daily rate missing for " + instrument)
        rate = parse_rate(match.group(1))
        if not rate or not 80 < rate < 250:
            raise RuntimeError("CBK daily rate failed validation for " + instrument)
        fallback.append({
            "date": posted_date.isoformat(),
            "instrument": instrument,
            "rate": rate,
            "source": SOURCE,
            "source_url": current_url,
        })
    return fallback


def extract_auction_date(text):
    for pattern in (
        r"DATED\s+(\d{1,2})[-/](\d{1,2})[-/](\d{4})",
        r"DATED\s+(\d{1,2})\s+(\d{1,2})\s+(\d{4})",
    ):
        match = re.search(pattern, text, re.I)
        if match:
            day, month, year = match.groups()
            try:
                return datetime(int(year), int(month), int(day)).date()
            except ValueError:
                pass
    return None


def extract_issue_numbers(text):
    match = re.search(
        r"ISSUES?\s+(\d{3,4}/091).*?(\d{3,4}/182).*?(\d{3,4}/364)",
        text, re.I
    )
    if not match:
        return {91: None, 182: None, 364: None}
    return {91: match.group(1), 182: match.group(2), 364: match.group(3)}


def extract_weighted_rates(text):
    clean = re.sub(r"\s+", " ", text.replace("\xa0", " "))
    marker = re.search(r"Market\s+Weighted\s+Average\s+Interest\s+Rate", clean, re.I)
    if not marker:
        return {}
    section = clean[marker.start():marker.start() + 700]
    values = re.findall(r"(\d{1,2}\.\d{3,6})\s*%", section)
    if len(values) < 3:
        return {}
    parsed = [float(value) / 100.0 for value in values[:3]]
    if any(not 0 <= rate <= 0.30 for rate in parsed):
        return {}
    return {91: parsed[0], 182: parsed[1], 364: parsed[2]}


def fetch_tbill_results():
    page = get(CBK_TBILLS_URL)
    soup = BeautifulSoup(page.text, "html.parser")
    urls = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        label = anchor.get_text(" ", strip=True).lower()
        url = urljoin(CBK_TBILLS_URL, href)
        lower = url.lower()
        if ("centralbank.go.ke" in lower and ".pdf" in lower
                and ("result" in lower or "result" in label)):
            urls.append(url)
    # Newest results are normally listed first on the official CBK page.
    urls = list(dict.fromkeys(urls))[:25]
    if not urls:
        raise RuntimeError("No official CBK Treasury bill auction-result PDFs were found.")

    records = {}
    failures = []
    for url in urls:
        try:
            response = get(url, "application/pdf,*/*;q=0.8")
            content = response.content
            if len(content) > 25 * 1024 * 1024 or not content.startswith(b"%PDF"):
                raise RuntimeError("Link did not return a valid, reasonably sized PDF.")
            reader = PdfReader(io.BytesIO(content))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
            if not text.strip():
                raise RuntimeError("PDF text could not be extracted.")
            auction_date = extract_auction_date(text)
            rates = extract_weighted_rates(text)
            if not auction_date or len(rates) != 3:
                raise RuntimeError("Auction date or all three weighted average rates were not present.")
            issues = extract_issue_numbers(text)
            for tenor, rate in rates.items():
                key = (auction_date.isoformat(), tenor)
                records[key] = {
                    "date": auction_date.isoformat(),
                    "tenor_days": tenor,
                    "rate": rate,
                    "price": 100.0 / (1.0 + rate * tenor / 365.0),
                    "issue_number": issues.get(tenor),
                    "source": SOURCE,
                    "source_url": url,
                }
        except Exception as exc:
            failures.append({"url": url, "error": str(exc)[:150]})
    if not records:
        raise RuntimeError("No usable Treasury bill auction data could be extracted from the latest CBK PDFs.")
    return list(records.values()), failures


def write_observations(fx, bills, fx_error=None, bill_error=None):
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured.")
    with psycopg.connect(database_url, connect_timeout=8, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            for row in fx:
                cur.execute(
                    """
                    INSERT INTO fx_observations
                        (observation_date, instrument, rate, source, source_url)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (observation_date, instrument) DO UPDATE SET
                        rate = EXCLUDED.rate,
                        source = EXCLUDED.source,
                        source_url = EXCLUDED.source_url,
                        imported_at = now()
                    """,
                    (row["date"], row["instrument"], row["rate"], row["source"], row["source_url"]),
                )
            for row in bills:
                cur.execute(
                    """
                    INSERT INTO treasury_bill_observations
                        (auction_date, tenor_days, accepted_rate, price, issue_number, source, source_url)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (auction_date, tenor_days) DO UPDATE SET
                        accepted_rate = EXCLUDED.accepted_rate,
                        price = EXCLUDED.price,
                        issue_number = EXCLUDED.issue_number,
                        source = EXCLUDED.source,
                        source_url = EXCLUDED.source_url,
                        imported_at = now()
                    """,
                    (row["date"], row["tenor_days"], row["rate"], row.get("price"),
                     row.get("issue_number"), row["source"], row["source_url"]),
                )
            status = "success" if fx and bills else "partial"
            details = {
                "fx_error": fx_error,
                "treasury_bill_error": bill_error,
                "fx_latest_date": max((row["date"] for row in fx), default=None),
                "bill_latest_date": max((row["date"] for row in bills), default=None),
            }
            cur.execute(
                """
                INSERT INTO data_refresh_runs
                    (source, status, completed_at, fx_rows_upserted, bill_rows_upserted, details)
                VALUES (%s, %s, now(), %s, %s, %s)
                """,
                (SOURCE, status, len(fx), len(bills), json.dumps(details)),
            )
    return {"fx_rows": len(fx), "bill_rows": len(bills), "status": status}


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?")[0] != "/api/refresh":
            self.send_error(404)
            return
        expected = os.environ.get("CRON_SECRET")
        supplied = self.headers.get("Authorization", "")
        if not expected or supplied != "Bearer " + expected:
            self.send_error(401)
            return
        fx, bills = [], []
        fx_error, bill_error = None, None
        try:
            fx = fetch_fx()
        except Exception as exc:
            fx_error = str(exc)[:200]
        try:
            bills, bill_failures = fetch_tbill_results()
            if bill_failures:
                bill_error = "Some CBK PDFs could not be processed: " + str(len(bill_failures))
        except Exception as exc:
            bill_error = str(exc)[:200]
        try:
            result = write_observations(fx, bills, fx_error, bill_error)
            status = 200 if result["status"] == "success" else 207
            payload = {"ok": result["status"] == "success", **result,
                       "fx_error": fx_error, "treasury_bill_error": bill_error}
        except Exception as exc:
            status = 500
            payload = {"ok": False, "error": str(exc)[:200]}
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)
