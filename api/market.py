from http.server import BaseHTTPRequestHandler
from pathlib import Path
import json
import sqlite3
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
APP_DB = ROOT / "kenya_financial_analytics.db"
MARKET_DB = ROOT / "kenya_market.db"

def rows_from(path, sql, params=()):
    if not path.exists():
        return []
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
    con.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in con.execute(sql, params).fetchall()]
    finally:
        con.close()

def get_market_data():
    fx, bills = [], []
    errors = []
    try:
        fx = rows_from(APP_DB, """
            SELECT COALESCE(NULLIF(trade_date,''), date) AS date,
                   instrument,
                   COALESCE(price, value) AS value,
                   COALESCE(source, 'Central Bank of Kenya') AS source
            FROM market_data
            WHERE instrument IN ('USD/KES','GBP/KES','EUR/KES')
              AND COALESCE(NULLIF(trade_date,''), date) IS NOT NULL
              AND COALESCE(price, value) IS NOT NULL
            ORDER BY date ASC
        """)
    except Exception as exc:
        errors.append("FX store: " + str(exc)[:180])
    try:
        bills = rows_from(APP_DB, """
            SELECT COALESCE(NULLIF(auction_date,''), date) AS date,
                   tenor_days,
                   COALESCE(accepted_rate, rate, value) AS rate,
                   COALESCE(source, 'Central Bank of Kenya') AS source
            FROM treasury_bills
            WHERE tenor_days IN (91,182,364)
              AND COALESCE(accepted_rate, rate, value) IS NOT NULL
            ORDER BY date ASC, tenor_days ASC
        """)
    except Exception as exc:
        errors.append("Treasury bill store: " + str(exc)[:180])
    if not bills:
        try:
            bills = rows_from(MARKET_DB, """
                SELECT auction_date AS date, tenor_days, rate,
                       COALESCE(source, 'Central Bank of Kenya') AS source
                FROM treasury_bill_rates
                WHERE tenor_days IN (91,182,364) AND rate IS NOT NULL
                ORDER BY auction_date ASC, tenor_days ASC
            """)
        except Exception as exc:
            errors.append("CBK market store: " + str(exc)[:180])
    fx_rows = len(fx)
    bill_rows = len(bills)
    return {
        "ok": bool(fx_rows or bill_rows),
        "fx": fx,
        "bills": bills,
        "source": "Central Bank of Kenya",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "health": {
            "fx_rows": fx_rows,
            "bills_rows": bill_rows,
            "database": "read-only bundled SQLite snapshot",
            "warnings": errors
        }
    }

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?")[0] not in ("/api/market", "/"):
            self.send_error(404)
            return
        try:
            payload = json.dumps(get_market_data(), default=str).encode("utf-8")
            self.send_response(200)
        except Exception as exc:
            payload = json.dumps({"ok": False, "error": str(exc)[:200], "fx": [], "bills": [], "health": {"fx_rows": 0, "bills_rows": 0}}).encode("utf-8")
            self.send_response(500)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "s-maxage=300, stale-while-revalidate=900")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(payload)
