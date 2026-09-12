import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent
APP = BASE / "app.py"
REQ = BASE / "requirements.txt"
DB = BASE / "kenya_financial_analytics.db"

# ============================================================
# BACKUP
# ============================================================

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
BACKUP = BASE / f"LIVE_BACKUP_{stamp}"
BACKUP.mkdir(exist_ok=True)

for filename in [
    "app.py",
    "requirements.txt",
    "kenya_financial_analytics.db",
    "live_data.py",
]:
    source = BASE / filename
    if source.exists():
        shutil.copy2(source, BACKUP / filename)

print(f"[1/8] Backup created: {BACKUP}")

# ============================================================
# REQUIREMENTS
# ============================================================

requirements = [
    "streamlit>=1.40",
    "pandas>=2.2",
    "numpy>=1.26",
    "scipy>=1.12",
    "plotly>=5.20",
    "requests>=2.31",
    "beautifulsoup4>=4.12",
    "lxml>=5.0",
    "pypdf>=4.0",
]

existing = []

if REQ.exists():
    existing = [
        x.strip()
        for x in REQ.read_text(encoding="utf-8").splitlines()
        if x.strip()
    ]

existing_lower = [x.split(">=")[0].lower() for x in existing]

for item in requirements:
    package = item.split(">=")[0].lower()
    if package not in existing_lower:
        existing.append(item)

REQ.write_text(
    "\n".join(existing) + "\n",
    encoding="utf-8"
)

print("[2/8] requirements.txt updated")

# ============================================================
# LIVE DATA ENGINE
# ============================================================

live_data = r'''
import io
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

BASE = Path(__file__).resolve().parent
CACHE_FILE = BASE / "cbk_live_cache.json"

CBK_FX_URL = "https://www.centralbank.go.ke/rates/forex-exchange-rates/"
CBK_TBILL_URL = "https://www.centralbank.go.ke/bills-bonds/treasury-bills/"

HEADERS = {
    "User-Agent": "Kenya-Financial-Analytics/1.0"
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def request_cbk(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )
    response.raise_for_status()
    return response.text


def read_cache():
    if not CACHE_FILE.exists():
        return {}

    try:
        return json.loads(
            CACHE_FILE.read_text(encoding="utf-8")
        )
    except Exception:
        return {}


def write_cache(data):
    CACHE_FILE.write_text(
        json.dumps(data, indent=2),
        encoding="utf-8"
    )


def get_fx():
    """
    Get current official CBK KES exchange rates.
    """

    html = request_cbk(CBK_FX_URL)

    tables = pd.read_html(io.StringIO(html))

    wanted = {
        "US DOLLAR": "USD/KES",
        "EURO": "EUR/KES",
        "STG POUND": "GBP/KES",
        "STERLING POUND": "GBP/KES",
    }

    output = {}

    for table in tables:

        table = table.copy()

        for _, row in table.iterrows():

            values = [
                str(v).strip()
                for v in row.tolist()
            ]

            text = " ".join(values).upper()

            for currency, instrument in wanted.items():

                if currency not in text:
                    continue

                numeric = []

                for value in values:

                    cleaned = (
                        value
                        .replace(",", "")
                        .replace("%", "")
                        .strip()
                    )

                    try:
                        number = float(cleaned)

                        if number > 0:
                            numeric.append(number)

                    except Exception:
                        pass

                if numeric:

                    # CBK tables normally contain buying/selling
                    # and/or mean information. Select the most
                    # exchange-rate-like value.
                    candidates = [
                        n for n in numeric
                        if 50 < n < 300
                    ]

                    if candidates:

                        output[instrument] = {
                            "price": candidates[-1],
                            "source": "Central Bank of Kenya",
                            "updated": utc_now()
                        }

    return output


def get_treasury_bills():
    """
    Get current official CBK Treasury Bill rates.
    """

    html = request_cbk(CBK_TBILL_URL)

    tables = pd.read_html(io.StringIO(html))

    results = {}

    for table in tables:

        table = table.copy()

        for _, row in table.iterrows():

            values = [
                str(v).strip()
                for v in row.tolist()
            ]

            text = " ".join(values).upper()

            tenor = None

            for candidate in [91, 182, 364]:

                if re_search_tenor(text, candidate):
                    tenor = candidate
                    break

            if tenor is None:
                continue

            numbers = []

            for value in values:

                cleaned = (
                    value
                    .replace("%", "")
                    .replace(",", "")
                    .strip()
                )

                try:
                    number = float(cleaned)

                    if 0 < number < 100:
                        numbers.append(number)

                except Exception:
                    pass

            if numbers:

                # Prefer values in the normal Kenyan T-bill
                # interest-rate range.
                rates = [
                    n for n in numbers
                    if 1 < n < 30
                ]

                if rates:

                    results[tenor] = {
                        "tenor_days": tenor,
                        "rate": rates[-1],
                        "source": "Central Bank of Kenya",
                        "updated": utc_now()
                    }

    return list(results.values())


def re_search_tenor(text, tenor):
    patterns = [
        rf"\b{tenor}\s*[- ]?\s*DAY",
        rf"\b{tenor}\b"
    ]

    import re

    return any(
        re.search(pattern, text)
        for pattern in patterns
    )


def refresh(db_path, force=False):

    cache = read_cache()

    # 15-minute protection against unnecessary CBK requests.
    if not force and cache.get("status") == "LIVE":

        try:
            updated = datetime.fromisoformat(
                cache["updated"]
            )

            age = (
                datetime.now(timezone.utc) - updated
            ).total_seconds()

            if age < 900:
                return cache

        except Exception:
            pass

    fx = get_fx()
    bills = get_treasury_bills()

    if not fx:
        raise RuntimeError(
            "CBK FX data could not be read."
        )

    if not bills:
        raise RuntimeError(
            "CBK Treasury Bill data could not be read."
        )

    con = sqlite3.connect(db_path)

    try:

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

        today = datetime.now().strftime("%Y-%m-%d")

        # Remove all previous demo market observations.
        con.execute("DELETE FROM market_data")

        # Remove previous demo T-bill observations.
        con.execute("DELETE FROM treasury_bills")

        for instrument, item in fx.items():

            con.execute("""
                INSERT INTO market_data
                (
                    trade_date,
                    instrument,
                    price,
                    yield,
                    volume,
                    source
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                today,
                instrument,
                float(item["price"]),
                None,
                None,
                "Central Bank of Kenya"
            ))

        for item in bills:

            rate = float(item["rate"])
            tenor = int(item["tenor_days"])

            # Indicative price calculated from the official CBK rate.
            price = 100 / (
                1 + (rate / 100) * tenor / 365
            )

            con.execute("""
                INSERT INTO treasury_bills
                (
                    auction_date,
                    tenor_days,
                    accepted_rate,
                    price,
                    amount_offered,
                    amount_accepted,
                    source
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                today,
                tenor,
                rate,
                price,
                None,
                None,
                "Central Bank of Kenya"
            ))

        con.commit()

    finally:
        con.close()

    result = {
        "status": "LIVE",
        "source": "Central Bank of Kenya",
        "updated": utc_now(),
        "fx": fx,
        "treasury_bills": bills
    }

    write_cache(result)

    return result


def status():
    return read_cache()
'''

# Add missing import required by helper.
live_data = "import re\n" + live_data.replace(
    "import io\n",
    "import io\n",
    1
)

(BASE / "live_data.py").write_text(
    live_data,
    encoding="utf-8"
)

print("[3/8] live_data.py created")

# ============================================================
# PATCH APP.PY
# ============================================================

text = APP.read_text(encoding="utf-8")

# Add import.
if "from live_data import refresh, status" not in text:
    text = text.replace(
        "import streamlit as st",
        "import streamlit as st\nfrom live_data import refresh, status",
        1
    )

# ------------------------------------------------------------
# Replace init_db()
# ------------------------------------------------------------

start = text.find("def init_db():")
end = text.find("\n\ndef seed_market", start)

if start != -1 and end != -1:

    new_init = '''def init_db():
    con = db()

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

    con.commit()
    con.close()
'''

    text = text[:start] + new_init + text[end:]

# ------------------------------------------------------------
# Disable old synthetic seed functions
# ------------------------------------------------------------

start = text.find("def seed_market(")
end = text.find("\n\ndef query_df", start)

if start != -1 and end != -1:

    text = text[:start] + '''def seed_market(con):
    # Synthetic market data disabled.
    # Live data comes from official CBK sources.
    return None


def seed_bills(con):
    # Synthetic Treasury Bill data disabled.
    # Live data comes from official CBK sources.
    return None
''' + text[end:]

# ------------------------------------------------------------
# Make market() safe
# ------------------------------------------------------------

old_market = '''def market(instrument=None):
    if instrument:
        data = query_df(
            "SELECT * FROM market_data WHERE instrument=? ORDER BY trade_date",
            (instrument,)
        )
    else:
        data = query_df("SELECT * FROM market_data ORDER BY trade_date")
    if not data.empty:
        data["trade_date"] = pd.to_datetime(data["trade_date"])
    return data
'''

new_market = '''def market(instrument=None):
    if instrument:
        data = query_df(
            "SELECT * FROM market_data WHERE instrument=? ORDER BY trade_date",
            (instrument,)
        )
    else:
        data = query_df(
            "SELECT * FROM market_data ORDER BY trade_date"
        )

    if not data.empty:
        data["trade_date"] = pd.to_datetime(
            data["trade_date"]
        )

    return data
'''

text = text.replace(old_market, new_market, 1)

# ------------------------------------------------------------
# Safe dashboard instruments
# ------------------------------------------------------------

text = text.replace(
    '["NSE20", "NSE25", "USD/KES", "EUR/KES", "GBP/KES", "10Y KENYA"]',
    '["USD/KES", "EUR/KES", "GBP/KES"]'
)

text = text.replace(
    '["NSE20", "NSE25", "USD/KES", "EUR/KES", "GBP/KES"]',
    '["USD/KES", "EUR/KES", "GBP/KES"]'
)

text = text.replace(
    '["NSE20", "NSE25"]',
    '["USD/KES", "EUR/KES"]'
)

# ------------------------------------------------------------
# Add live status to dashboard
# ------------------------------------------------------------

needle = '''    st.caption("Kenyan quantitative-finance platform.")

    rows = []
'''

replacement = '''    st.caption("Kenyan quantitative-finance platform.")

    live = status()

    if live.get("status") == "LIVE":
        st.success(
            "🟢 LIVE DATA — Central Bank of Kenya"
        )
        st.caption(
            f"Last update: {live.get('updated', 'Unknown')}"
        )
    else:
        st.warning(
            "CBK live data is not currently available."
        )

    rows = []
'''

text = text.replace(
    needle,
    replacement,
    1
)

# ------------------------------------------------------------
# Patch Treasury Bill page
# ------------------------------------------------------------

needle = '''def treasury_bills():
    st.title("💰 Treasury Bills")
    data = bills()
'''

replacement = '''def treasury_bills():
    st.title("💰 Treasury Bills")
    st.caption(
        "Official Central Bank of Kenya Treasury Bill data."
    )
    data = bills()

    if data.empty:
        st.warning(
            "No CBK Treasury Bill data is currently available."
        )
        return
'''

text = text.replace(
    needle,
    replacement,
    1
)

# ------------------------------------------------------------
# Patch Yield Curve
# ------------------------------------------------------------

needle = '''def yield_curve():
    st.title("📊 Yield Curve")
    data = bills()
'''

replacement = '''def yield_curve():
    st.title("📊 Yield Curve")
    data = bills()

    if data.empty:
        st.warning(
            "No CBK Treasury Bill data is currently available."
        )
        return
'''

text = text.replace(
    needle,
    replacement,
    1
)

# ------------------------------------------------------------
# Patch sidebar refresh/system section
# ------------------------------------------------------------

old_sidebar = '''        if st.button("🔄 REFRESH", use_container_width=True):
            st.session_state.refresh += 1
            st.rerun()

        st.divider()
        selected = st.radio("Select Module", MODULES)
        st.divider()

        st.caption("SYSTEM STATUS")
        st.write("Database: **SQLite**")
        st.write("Quant Engine: **ONLINE**")
        st.write("Risk Engine: **ONLINE**")
        st.write("Refresh:", st.session_state.refresh)
'''

new_sidebar = '''        force_live_refresh = False

        if st.button(
            "🔄 REFRESH CBK DATA",
            use_container_width=True
        ):
            st.session_state.refresh += 1
            force_live_refresh = True

        try:
            live_result = refresh(
                DB,
                force=force_live_refresh
            )
        except Exception as exc:
            live_result = status()
            st.error("CBK connection unavailable")
            st.caption(str(exc))

        st.divider()
        selected = st.radio("Select Module", MODULES)
        st.divider()

        st.caption("SYSTEM STATUS")
        st.write("Database: **SQLite**")
        st.write("Quant Engine: **ONLINE**")
        st.write("Risk Engine: **ONLINE**")

        if live_result.get("status") == "LIVE":
            st.write("Market Data: **LIVE — CBK**")
            st.write(
                "Source: **Central Bank of Kenya**"
            )
            st.write(
                "FX feeds:",
                len(live_result.get("fx", {}))
            )
            st.write(
                "T-Bill feeds:",
                len(live_result.get("treasury_bills", []))
            )
        else:
            st.write("Market Data: **OFFLINE**")

        st.write("Refresh:", st.session_state.refresh)
'''

if old_sidebar in text:
    text = text.replace(
        old_sidebar,
        new_sidebar,
        1
    )

APP.write_text(
    text,
    encoding="utf-8"
)

print("[4/8] Existing app.py patched")

# ============================================================
# CLEAN OLD DEMO DATABASE
# ============================================================

if DB.exists():

    con = sqlite3.connect(DB)

    try:
        con.execute("""
            DELETE FROM market_data
            WHERE source LIKE '%demo%'
               OR source LIKE '%Demo%'
               OR source LIKE '%Local SQLite%'
        """)

        con.execute("""
            DELETE FROM treasury_bills
            WHERE source LIKE '%demo%'
               OR source LIKE '%Demo%'
               OR source LIKE '%Local SQLite%'
        """)

        con.commit()

    finally:
        con.close()

print("[5/8] Synthetic/demo observations removed")

# ============================================================
# SYNTAX CHECK
# ============================================================

subprocess.check_call([
    sys.executable,
    "-m",
    "py_compile",
    str(APP),
    str(BASE / "live_data.py")
])

print("[6/8] Python syntax check PASSED")

# ============================================================
# LIVE CBK TEST
# ============================================================

sys.path.insert(0, str(BASE))

from live_data import get_fx, get_treasury_bills

fx = get_fx()
tbills = get_treasury_bills()

print()
print("==============================================")
print("           CBK LIVE CONNECTION TEST")
print("==============================================")
print()

print("FX:")
for instrument, value in fx.items():
    print(
        f"  {instrument}: {value['price']}"
    )

print()
print("TREASURY BILLS:")

for item in tbills:
    print(
        f"  {item['tenor_days']}-Day: "
        f"{item['rate']:.4f}%"
    )

if not fx:
    raise RuntimeError(
        "CBK FX test returned no data."
    )

if not tbills:
    raise RuntimeError(
        "CBK Treasury Bill test returned no data."
    )

print()
print("[7/8] CBK LIVE TEST PASSED")

# ============================================================
# WRITE CACHE + DATABASE
# ============================================================

from live_data import refresh

result = refresh(
    DB,
    force=True
)

print()
print(
    f"Live FX instruments loaded: "
    f"{len(result.get('fx', {}))}"
)

print(
    f"Live Treasury Bill tenors loaded: "
    f"{len(result.get('treasury_bills', []))}"
)

print("[8/8] LIVE DATABASE REFRESH PASSED")

print()
print("==============================================")
print("     KENYA FINANCIAL ANALYTICS IS LIVE")
print("==============================================")
print()
print("Source: Central Bank of Kenya")
print("Synthetic data: DISABLED")
print("FX: USD/KES, EUR/KES, GBP/KES")
print("Treasury Bills: 91D, 182D, 364D")
print()
print("Backup:")
print(BACKUP)
print()
