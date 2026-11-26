import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler

import psycopg
from psycopg.rows import dict_row


def load_market_data():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured for this deployment.")

    with psycopg.connect(database_url, connect_timeout=8, row_factory=dict_row) as conn:
        fx_rows = conn.execute(
            """
            SELECT observation_date, instrument, rate, source, source_url, imported_at
            FROM fx_observations
            WHERE instrument IN ('USD/KES', 'GBP/KES', 'EUR/KES')
            ORDER BY observation_date ASC, instrument ASC
            LIMIT 2000
            """
        ).fetchall()
        bill_rows = conn.execute(
            """
            SELECT auction_date, tenor_days, accepted_rate, price,
                   amount_offered, amount_accepted, issue_number,
                   source, source_url, imported_at
            FROM treasury_bill_observations
            WHERE tenor_days IN (91, 182, 364)
            ORDER BY auction_date ASC, tenor_days ASC
            LIMIT 2000
            """
        ).fetchall()
        refresh = conn.execute(
            """
            SELECT source, status, started_at, completed_at,
                   fx_rows_upserted, bill_rows_upserted, details
            FROM data_refresh_runs
            ORDER BY started_at DESC
            LIMIT 1
            """
        ).fetchone()

    fx = [
        {
            "date": row["observation_date"].isoformat(),
            "instrument": row["instrument"],
            "value": float(row["rate"]),
            "source": row["source"],
            "source_url": row["source_url"],
            "imported_at": row["imported_at"].isoformat() if row["imported_at"] else None,
        }
        for row in fx_rows
    ]
    bills = [
        {
            "date": row["auction_date"].isoformat(),
            "tenor_days": int(row["tenor_days"]),
            "rate": float(row["accepted_rate"]),
            "price": float(row["price"]) if row["price"] is not None else None,
            "amount_offered": float(row["amount_offered"]) if row["amount_offered"] is not None else None,
            "amount_accepted": float(row["amount_accepted"]) if row["amount_accepted"] is not None else None,
            "issue_number": row["issue_number"],
            "source": row["source"],
            "source_url": row["source_url"],
            "imported_at": row["imported_at"].isoformat() if row["imported_at"] else None,
        }
        for row in bill_rows
    ]
    last_refresh = None
    if refresh:
        last_refresh = {
            "source": refresh["source"],
            "status": refresh["status"],
            "started_at": refresh["started_at"].isoformat() if refresh["started_at"] else None,
            "completed_at": refresh["completed_at"].isoformat() if refresh["completed_at"] else None,
            "fx_rows_upserted": int(refresh["fx_rows_upserted"]),
            "bill_rows_upserted": int(refresh["bill_rows_upserted"]),
            "details": refresh["details"],
        }

    latest_fx = max((row["date"] for row in fx), default=None)
    latest_bill = max((row["date"] for row in bills), default=None)
    retrieved_at = datetime.now(timezone.utc).isoformat()
    return {
        "ok": bool(fx or bills),
        "fx": fx,
        "bills": bills,
        "source": "Central Bank of Kenya",
        "retrieved_at": retrieved_at,
        "health": {
            "database": "Neon Postgres",
            "database_connected": True,
            "fx_rows": len(fx),
            "bills_rows": len(bills),
            "latest_fx_observation": latest_fx,
            "latest_bill_observation": latest_bill,
            "last_refresh": last_refresh,
            "warnings": [],
        },
    }


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?")[0] != "/api/market":
            self.send_error(404)
            return
        try:
            payload = json.dumps(load_market_data(), separators=(",", ":")).encode("utf-8")
            self.send_response(200)
        except Exception as exc:
            payload = json.dumps({
                "ok": False,
                "error": "The market data service could not reach its database.",
                "fx": [],
                "bills": [],
                "source": "Central Bank of Kenya",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "health": {
                    "database": "Neon Postgres",
                    "database_connected": False,
                    "fx_rows": 0,
                    "bills_rows": 0,
                    "warnings": [str(exc)[:180]],
                },
            }).encode("utf-8")
            self.send_response(503)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "s-maxage=60, stale-while-revalidate=300")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(payload)
