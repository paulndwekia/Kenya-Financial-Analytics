from http.server import BaseHTTPRequestHandler
from pathlib import Path
import json
import sqlite3
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
APP_DB = ROOT / "kenya_financial_analytics.db"
MARKET_DB = ROOT / "kenya_market.db"

def table_columns(con, table):
    return {row[1] for row in con.execute(f"PRAGMA table_info({table})").fetchall()}

def rows_from(path, table, select_sql, where_sql, order_sql):
    if not path.exists():
        return []
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
    con.row_factory = sqlite3.Row
    try:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if table not in tables:
            return []
        cols = table_columns(con, table)
        if not cols:
            return []
        date_col = "trade_date" if table == "market_data" and "trade_date" in cols else ("auction_date" if "auction_date" in cols else ("date" if "date" in cols else None))
        if table == "market_data":
            instrument = "instrument" if "instrument" in cols else "''"
            price = "COALESCE(price, value)" if {"price", "value"}.issubset(cols) else ("price" if "price" in cols else ("value" if "value" in cols else "NULL"))
            source = "source" if "source" in cols else "'Central Bank of Kenya'"
            date_expr = f"COALESCE(NULLIF(trade_date,''), date)" if {"trade_date", "date"}.issubset(cols) else (date_col or "NULL")
            sql = f"SELECT DISTINCT {date_expr} AS date, {instrument} AS instrument, {price} AS value, {source} AS source FROM {table} WHERE {instrument} IN ('USD/KES','GBP/KES','EUR/KES') AND {price} IS NOT NULL ORDER BY date ASC LIMIT 2000"
        else:
            tenor = "tenor_days" if "tenor_days" in cols else "NULL"
            rate_parts = [c for c in ("accepted_rate", "rate", "value") if c in cols]
            rate = "COALESCE(" + ", ".join(rate_parts) + ")" if len(rate_parts) > 1 else (rate_parts[0] if rate_parts else "NULL")
            source = "source" if "source" in cols else "'Central Bank of Kenya'"
            date_expr = f"COALESCE(NULLIF(auction_date,''), date)" if {"auction_date", "date"}.issubset(cols) else (date_col or "NULL")
            sql = f"SELECT DISTINCT {date_expr} AS date, {tenor} AS tenor_days, {rate} AS rate, {source} AS source FROM {table} WHERE {tenor} IN (91,182,364) AND {rate} IS NOT NULL ORDER BY date ASC, tenor_days ASC LIMIT 2000"
        return [dict(row) for row in con.execute(sql).fetchall()]
    finally:
        con.close()

def get_market_data():
    warnings = []
    try:
        fx = rows_from(APP_DB, "market_data", None, None, None)
    except Exception as exc:
        fx = []
        warnings.append("FX data store: " + str(exc)[:160])

    app_bills = []
    market_bills = []
    try:
        app_bills = rows_from(APP_DB, "treasury_bills", None, None, None)
    except Exception as exc:
        warnings.append("Treasury bill application store: " + str(exc)[:160])
    try:
        market_bills = rows_from(MARKET_DB, "treasury_bill_rates", None, None, None)
    except Exception as exc:
        warnings.append("CBK market history store: " + str(exc)[:160])

    # Merge retained CBK bill stores and deduplicate by auction date and tenor.
    unique_bills = {}
    for item in app_bills + market_bills:
        key = (str(item.get("date") or ""), int(item.get("tenor_days") or 0))
        if key[0] and key[1] in (91, 182, 364):
            unique_bills[key] = item
    bills = sorted(unique_bills.values(), key=lambda item: (item["date"], int(item["tenor_days"])))

    latest_fx_date = max((str(item.get("date") or "") for item in fx), default=None)
    latest_bill_date = max((str(item.get("date") or "") for item in bills), default=None)
    return {
        "ok": bool(fx or bills),
        "fx": fx,
        "bills": bills,
        "source": "Central Bank of Kenya",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "health": {
            "fx_rows": len(fx),
            "bills_rows": len(bills),
            "latest_fx_observation": latest_fx_date,
            "latest_bill_observation": latest_bill_date,
            "database": "read-only bundled SQLite snapshot",
            "warnings": warnings
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
            payload = json.dumps({"ok": False, "error": str(exc)[:200], "fx": [], "bills": [], "health": {"fx_rows": 0, "bills_rows": 0, "warnings": []}}).encode("utf-8")
            self.send_response(500)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "s-maxage=300, stale-while-revalidate=900")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(payload)
