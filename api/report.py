import io
import json
import math
import os
from datetime import date, datetime, time, timezone
from http.server import BaseHTTPRequestHandler

import psycopg
import xlsxwriter
from psycopg.rows import dict_row


NAVY = "#102A43"
TEAL = "#087F8C"
BLUE = "#356BB3"
GOLD = "#D5A43B"
RED = "#C45151"
GREEN = "#16835D"
INK = "#243B53"
MUTED = "#627D98"
PALE = "#F3F6F9"
PALE_BLUE = "#EAF1F8"
PALE_TEAL = "#E7F3F3"
PALE_GOLD = "#FBF5E8"
WHITE = "#FFFFFF"


def sample_std(values):
    if len(values) < 2:
        return 0.0
    avg = sum(values) / len(values)
    return (sum((x - avg) ** 2 for x in values) / (len(values) - 1)) ** 0.5


def max_drawdown(levels):
    peak = None
    worst = 0.0
    for value in levels:
        peak = value if peak is None else max(peak, value)
        if peak:
            worst = min(worst, value / peak - 1)
    return worst


def median(values):
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def historical_tail_metrics(daily_changes):
    """Nearest-rank 5th percentile and average worst 5% of observed daily quote changes.

    These are available only with at least 20 observations. They describe the
    FX quote sample, not portfolio VaR or an investor's expected loss.
    """
    if len(daily_changes) < 20:
        return None, None
    ordered = sorted(float(value) for value in daily_changes)
    tail_count = max(1, math.ceil(len(ordered) * 0.05))
    tail = ordered[:tail_count]
    return ordered[tail_count - 1], sum(tail) / len(tail)


def as_date(value):
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def load_report_data():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured.")
    with psycopg.connect(database_url, connect_timeout=8, row_factory=dict_row) as conn:
        fx = conn.execute(
            """
            WITH ranked_fx AS (
                SELECT observation_date, instrument, rate, source, source_url, imported_at,
                       ROW_NUMBER() OVER (
                           PARTITION BY instrument
                           ORDER BY observation_date DESC
                       ) AS row_number
                FROM fx_observations
                WHERE instrument IN ('USD/KES', 'GBP/KES', 'EUR/KES')
            )
            SELECT observation_date, instrument, rate, source, source_url, imported_at
            FROM ranked_fx
            WHERE row_number <= 2000
            ORDER BY observation_date, instrument
            """
        ).fetchall()
        bills = conn.execute(
            """
            WITH ranked_bills AS (
                SELECT auction_date, tenor_days, accepted_rate, price,
                       amount_offered, amount_accepted, issue_number,
                       source, source_url, imported_at,
                       ROW_NUMBER() OVER (
                           PARTITION BY tenor_days
                           ORDER BY auction_date DESC
                       ) AS row_number
                FROM treasury_bill_observations
                WHERE tenor_days IN (91, 182, 364)
            )
            SELECT auction_date, tenor_days, accepted_rate, price,
                   amount_offered, amount_accepted, issue_number,
                   source, source_url, imported_at
            FROM ranked_bills
            WHERE row_number <= 2000
            ORDER BY auction_date, tenor_days
            """
        ).fetchall()
        refreshes = conn.execute(
            """
            SELECT source, status, started_at, completed_at,
                   fx_rows_upserted, bill_rows_upserted, details
            FROM data_refresh_runs
            ORDER BY started_at DESC
            LIMIT 1
            """
        ).fetchone()
    return fx, bills, refreshes


def build_workbook(fx, bills, refresh):
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    workbook.set_properties({
        "title": "Kenya Financial Analytics — Market Research Report",
        "subject": "Central Bank of Kenya foreign exchange and Treasury bill observations",
        "author": "Kenya Financial Analytics",
        "company": "Kenya Financial Analytics",
        "category": "Market Research",
        "keywords": "Kenya, CBK, foreign exchange, Treasury bills, market research",
        "comments": "Generated from the application's stored CBK market observations.",
    })
    workbook.set_calc_mode("auto")

    fmt = {}
    fmt["title"] = workbook.add_format({
        "bold": True, "font_name": "Aptos Display", "font_size": 22,
        "font_color": WHITE, "bg_color": NAVY, "valign": "vcenter",
    })
    fmt["subtitle"] = workbook.add_format({
        "font_name": "Aptos", "font_size": 10, "font_color": "#D7E3ED",
        "bg_color": NAVY, "valign": "vcenter",
    })
    fmt["section"] = workbook.add_format({
        "bold": True, "font_name": "Aptos", "font_size": 11,
        "font_color": WHITE, "bg_color": TEAL, "valign": "vcenter",
    })
    fmt["kpi_label"] = workbook.add_format({
        "bold": True, "font_size": 9, "font_color": MUTED,
        "bg_color": PALE, "align": "center", "valign": "vcenter",
        "bottom": 0,
    })
    fmt["kpi_value"] = workbook.add_format({
        "bold": True, "font_name": "Aptos Display", "font_size": 19,
        "font_color": NAVY, "bg_color": PALE, "align": "center",
        "valign": "vcenter", "num_format": '#,##0;[Red](#,##0);-',
    })
    fmt["kpi_date"] = workbook.add_format({
        "font_size": 9, "font_color": MUTED, "bg_color": PALE,
        "align": "center", "valign": "vcenter",
    })
    fmt["meta_label"] = workbook.add_format({"bold": True, "font_color": MUTED, "font_size": 9})
    fmt["meta_value"] = workbook.add_format({"font_color": INK, "font_size": 9})
    fmt["body"] = workbook.add_format({"font_color": INK, "font_size": 9, "valign": "vcenter"})
    fmt["body_wrap"] = workbook.add_format({"font_color": INK, "font_size": 9, "text_wrap": True, "valign": "top"})
    fmt["date"] = workbook.add_format({"font_color": INK, "font_size": 9, "num_format": "dd-mmm-yyyy"})
    fmt["num"] = workbook.add_format({"font_color": INK, "font_size": 9, "num_format": '#,##0.0000;[Red](#,##0.0000);-'})
    fmt["integer"] = workbook.add_format({"font_color": INK, "font_size": 9, "num_format": '#,##0;[Red](#,##0);-'})
    fmt["kes"] = workbook.add_format({"font_color": INK, "font_size": 9, "num_format": '"KES " #,##0.00;[Red]("KES " #,##0.00);-'})
    fmt["pct"] = workbook.add_format({"font_color": INK, "font_size": 9, "num_format": '0.00%;[Red](0.00%);-'})
    fmt["yield"] = workbook.add_format({"font_color": INK, "font_size": 9, "num_format": '0.0000%;[Red](0.0000%);-'})
    fmt["hyperlink"] = workbook.add_format({"font_color": BLUE, "underline": True, "font_size": 9})
    fmt["note"] = workbook.add_format({
        "font_color": MUTED, "font_size": 9, "text_wrap": True,
        "bg_color": PALE_BLUE, "valign": "top",
    })
    fmt["good"] = workbook.add_format({"font_color": GREEN, "bg_color": "#E8F5EE", "num_format": '0.00%;[Red](0.00%);-'})
    fmt["bad"] = workbook.add_format({"font_color": RED, "bg_color": "#FCEBEC", "num_format": '0.00%;[Red](0.00%);-'})
    fmt["small"] = workbook.add_format({"font_color": MUTED, "font_size": 8, "text_wrap": True, "valign": "top"})

    pairs = ("USD/KES", "GBP/KES", "EUR/KES")
    by_pair = {
        pair: [row for row in fx if row["instrument"] == pair]
        for pair in pairs
    }
    fx_stats = []
    for pair in pairs:
        rows = sorted(by_pair[pair], key=lambda row: as_date(row["observation_date"]))
        levels = [float(row["rate"]) for row in rows]
        daily_changes = []
        for index in range(1, len(rows)):
            previous = levels[index - 1]
            if previous:
                daily_changes.append({
                    "date": as_date(rows[index]["observation_date"]),
                    "value": levels[index] / previous - 1,
                })
        daily_returns = [item["value"] for item in daily_changes]
        lower_tail, average_worst_tail = historical_tail_metrics(daily_returns)
        best_day = max(daily_changes, key=lambda item: item["value"]) if daily_changes else None
        worst_day = min(daily_changes, key=lambda item: item["value"]) if daily_changes else None
        fx_stats.append({
            "pair": pair,
            "first_date": as_date(rows[0]["observation_date"]) if rows else None,
            "latest_date": as_date(rows[-1]["observation_date"]) if rows else None,
            "latest": levels[-1] if levels else None,
            "change": levels[-1] / levels[0] - 1 if len(levels) > 1 and levels[0] else None,
            "mean_daily_change": sum(daily_returns) / len(daily_returns) if daily_returns else None,
            "volatility": sample_std(daily_returns) * (252 ** 0.5) if len(daily_returns) > 1 else None,
            "drawdown": max_drawdown(levels) if levels else None,
            "best_daily_change": best_day["value"] if best_day else None,
            "best_daily_date": best_day["date"] if best_day else None,
            "worst_daily_change": worst_day["value"] if worst_day else None,
            "worst_daily_date": worst_day["date"] if worst_day else None,
            "lower_tail_5pct": lower_tail,
            "average_worst_5pct": average_worst_tail,
            "daily_observations": len(daily_returns),
            "observations": len(rows),
        })

    latest_fx_date = max((row["latest_date"] for row in fx_stats if row["latest_date"]), default=None)
    latest_bill_date = max((as_date(row["auction_date"]) for row in bills), default=None)
    latest_bills = [
        row for row in bills
        if latest_bill_date and as_date(row["auction_date"]) == latest_bill_date
    ]

    tenor_stats = []
    for tenor in (91, 182, 364):
        rows = sorted(
            [row for row in bills if int(row["tenor_days"]) == tenor],
            key=lambda row: as_date(row["auction_date"]),
        )
        yields = [float(row["accepted_rate"]) for row in rows]
        latest = rows[-1] if rows else None
        previous = rows[-2] if len(rows) > 1 else None
        amount_rows = [
            row for row in rows
            if row["amount_offered"] is not None
            and row["amount_accepted"] is not None
            and float(row["amount_offered"]) > 0
        ]
        total_offered = sum(float(row["amount_offered"]) for row in amount_rows)
        total_accepted = sum(float(row["amount_accepted"]) for row in amount_rows)
        latest_price = None
        if latest:
            latest_rate = float(latest["accepted_rate"])
            latest_price = (
                float(latest["price"])
                if latest["price"] is not None
                else 100 / (1 + latest_rate * tenor / 365)
            )
        tenor_stats.append({
            "tenor": tenor,
            "observations": len(rows),
            "first_date": as_date(rows[0]["auction_date"]) if rows else None,
            "latest_date": as_date(latest["auction_date"]) if latest else None,
            "latest_yield": float(latest["accepted_rate"]) if latest else None,
            "previous_yield": float(previous["accepted_rate"]) if previous else None,
            "change_vs_previous": (
                float(latest["accepted_rate"]) - float(previous["accepted_rate"])
                if latest and previous else None
            ),
            "mean_yield": sum(yields) / len(yields) if yields else None,
            "median_yield": median(yields),
            "minimum_yield": min(yields) if yields else None,
            "maximum_yield": max(yields) if yields else None,
            "latest_price": latest_price,
            "latest_issue": latest["issue_number"] if latest else None,
            "total_offered": total_offered if amount_rows else None,
            "total_accepted": total_accepted if amount_rows else None,
            "accepted_offered_ratio": total_accepted / total_offered if total_offered else None,
        })

    latest_curve = {
        int(row["tenor_days"]): float(row["accepted_rate"])
        for row in latest_bills
    }
    curve_spread = (
        latest_curve[364] - latest_curve[91]
        if 91 in latest_curve and 364 in latest_curve else None
    )
    if curve_spread is None:
        curve_reading = "Not available: both 91-day and 364-day observations are required on the same auction date."
    elif curve_spread > 0.0000001:
        curve_reading = "Upward slope: the 364-day accepted yield is above the 91-day yield."
    elif curve_spread < -0.0000001:
        curve_reading = "Downward slope: the 364-day accepted yield is below the 91-day yield."
    else:
        curve_reading = "Approximately flat: the 91-day and 364-day accepted yields are very close."
    retrieved_at = datetime.now(timezone.utc).replace(tzinfo=None)
    status = (refresh or {}).get("status", "No import recorded")
    source = (refresh or {}).get("source", "Not recorded")
    last_import = (refresh or {}).get("completed_at")
    if last_import:
        if getattr(last_import, "tzinfo", None):
            last_import = last_import.astimezone(timezone.utc).replace(tzinfo=None)

    # Executive Summary
    summary = workbook.add_worksheet("Executive Summary")
    summary.hide_gridlines(2)
    summary.set_tab_color(TEAL)
    summary.set_zoom(90)
    summary.set_column("A:A", 15)
    summary.set_column("B:B", 14)
    summary.set_column("C:C", 14)
    summary.set_column("D:D", 14)
    summary.set_column("E:E", 14)
    summary.set_column("F:F", 14)
    summary.set_column("G:G", 16)
    summary.set_column("H:H", 18)
    summary.set_column("I:I", 3)
    summary.set_column("J:Q", 12)
    summary.set_row(0, 28)
    summary.set_row(1, 16)
    summary.merge_range("A1:H1", "KENYA FINANCIAL ANALYTICS", fmt["title"])
    summary.merge_range("A2:H2", "MARKET RESEARCH REPORT  /  KENYAN MARKETS  /  CBK SOURCE DATA", fmt["subtitle"])
    summary.merge_range("A3:H3", "Market report generated " + retrieved_at.strftime("%d %B %Y, %H:%M UTC"), fmt["small"])

    def kpi(label, value, note, first_col, last_col, number_format=None):
        summary.merge_range(4, first_col, 4, last_col, label.upper(), fmt["kpi_label"])
        value_format = fmt["kpi_value"]
        if number_format:
            value_format = workbook.add_format({
                "bold": True, "font_name": "Aptos Display", "font_size": 19,
                "font_color": NAVY, "bg_color": PALE, "align": "center",
                "valign": "vcenter", "num_format": number_format,
            })
        summary.merge_range(5, first_col, 6, last_col, value if value is not None else "—", value_format)
        summary.merge_range(7, first_col, 7, last_col, note, fmt["kpi_date"])

    summary.set_row(4, 18)
    summary.set_row(5, 23)
    summary.set_row(6, 14)
    summary.set_row(7, 20)
    kpi("FX observations", len(fx), "Three tracked KES currency pairs", 0, 1)
    kpi("Treasury bill records", len(bills), "91 / 182 / 364-day CBK auctions", 2, 3)
    kpi("Latest FX date", latest_fx_date.strftime("%d %b %Y") if latest_fx_date else "—", "Most recent stored CBK FX date", 4, 5)
    kpi("Latest auction date", latest_bill_date.strftime("%d %b %Y") if latest_bill_date else "—", "Most recent stored Treasury auction", 6, 7)

    summary.merge_range("A10:H10", "FOREIGN EXCHANGE PERFORMANCE", fmt["section"])
    fx_headers = ["Pair", "First date", "Latest date", "Latest rate (KES / unit)", "Cumulative change", "Annualised volatility", "Max drawdown", "Observations"]
    for col, header in enumerate(fx_headers):
        summary.write(10, col, header, workbook.add_format({
            "bold": True, "font_color": WHITE, "bg_color": NAVY,
            "font_size": 9, "text_wrap": True, "valign": "vcenter",
            "bottom": 1, "bottom_color": TEAL,
        }))
    for idx, stat in enumerate(fx_stats, start=11):
        summary.write(idx, 0, stat["pair"], fmt["body"])
        summary.write_datetime(idx, 1, datetime.combine(stat["first_date"], time.min), fmt["date"]) if stat["first_date"] else summary.write(idx, 1, "—", fmt["body"])
        summary.write_datetime(idx, 2, datetime.combine(stat["latest_date"], time.min), fmt["date"]) if stat["latest_date"] else summary.write(idx, 2, "—", fmt["body"])
        summary.write_number(idx, 3, stat["latest"], fmt["num"]) if stat["latest"] is not None else summary.write(idx, 3, "—", fmt["body"])
        summary.write_number(idx, 4, stat["change"], fmt["pct"]) if stat["change"] is not None else summary.write(idx, 4, "—", fmt["body"])
        summary.write_number(idx, 5, stat["volatility"], fmt["pct"]) if stat["volatility"] is not None else summary.write(idx, 5, "—", fmt["body"])
        summary.write_number(idx, 6, stat["drawdown"], fmt["pct"]) if stat["drawdown"] is not None else summary.write(idx, 6, "—", fmt["body"])
        summary.write_number(idx, 7, stat["observations"], fmt["integer"])
    summary.conditional_format("E12:G14", {"type": "3_color_scale", "min_color": "#E8F5EE", "mid_color": "#FFF4D6", "max_color": "#FCEBEC"})

    summary.merge_range("A17:H17", "LATEST TREASURY BILL AUCTION", fmt["section"])
    tbill_headers = ["Tenor", "Auction date", "Accepted yield", "Price / KES 100*", "Issue number", "Amount offered (KES)", "Amount accepted (KES)", "Source"]
    for col, header in enumerate(tbill_headers):
        summary.write(17, col, header, workbook.add_format({
            "bold": True, "font_color": WHITE, "bg_color": NAVY,
            "font_size": 9, "text_wrap": True, "valign": "vcenter",
        }))
    for idx, row in enumerate(sorted(latest_bills, key=lambda x: x["tenor_days"]), start=18):
        auction_date = as_date(row["auction_date"])
        rate = float(row["accepted_rate"])
        price = float(row["price"]) if row["price"] is not None else 100 / (1 + rate * int(row["tenor_days"]) / 365)
        summary.write_number(idx, 0, int(row["tenor_days"]), fmt["integer"])
        summary.write_datetime(idx, 1, datetime.combine(auction_date, time.min), fmt["date"])
        summary.write_number(idx, 2, rate, fmt["yield"])
        summary.write_number(idx, 3, price, fmt["num"])
        summary.write(idx, 4, row["issue_number"] or "—", fmt["body"])
        if row["amount_offered"] is not None:
            summary.write_number(idx, 5, float(row["amount_offered"]), fmt["kes"])
        else:
            summary.write(idx, 5, "—", fmt["body"])
        if row["amount_accepted"] is not None:
            summary.write_number(idx, 6, float(row["amount_accepted"]), fmt["kes"])
        else:
            summary.write(idx, 6, "—", fmt["body"])
        summary.write(idx, 7, row["source"], fmt["body"])
    summary.merge_range("A23:H23", "* Price per KES 100 is taken from the stored CBK result where available; otherwise it is calculated as 100 ÷ (1 + accepted yield × tenor / 365). It is a model comparison, not a dealer quote.", fmt["note"])
    summary.set_row(22, 34)
    summary.merge_range("A25:H25", "DATA PROVENANCE & CONTROL", fmt["section"])
    summary.write("A26", "Stored source", fmt["meta_label"])
    summary.merge_range("B26:D26", "Central Bank of Kenya official market publications", fmt["meta_value"])
    summary.write("E26", "Last import status", fmt["meta_label"])
    summary.merge_range("F26:H26", str(status).upper(), fmt["meta_value"])
    summary.write("A27", "Import source", fmt["meta_label"])
    summary.merge_range("B27:D27", str(source), fmt["meta_value"])
    summary.write("E27", "Last completed import (UTC)", fmt["meta_label"])
    summary.merge_range("F27:H27", last_import.strftime("%d %b %Y %H:%M") if last_import else "Not yet recorded", fmt["meta_value"])
    summary.merge_range("A29:H30", "Interpretation: KES per foreign-currency unit is the quote convention. A rise in a pair's rate means more shillings per unit of foreign currency. FX cumulative change and volatility describe the stored sample only; neither is a forecast. Missing dates are not filled.", fmt["note"])
    summary.set_row(28, 28)
    summary.set_row(29, 18)

    # Hidden aligned series used by charts, with missing observations left blank.
    chart_data = workbook.add_worksheet("Chart Data")
    chart_data.hide()
    chart_data.write_row(0, 0, ["Observation date", *pairs])
    all_fx_dates = sorted({as_date(row["observation_date"]) for row in fx})
    fx_lookup = {(as_date(row["observation_date"]), row["instrument"]): float(row["rate"]) for row in fx}
    for row_idx, observation_date in enumerate(all_fx_dates, start=1):
        chart_data.write_datetime(row_idx, 0, datetime.combine(observation_date, time.min))
        for col_idx, pair in enumerate(pairs, start=1):
            value = fx_lookup.get((observation_date, pair))
            if value is not None:
                chart_data.write_number(row_idx, col_idx, value)
    chart_data.write_row(0, 5, ["Auction date", "91-day", "182-day", "364-day"])
    all_bill_dates = sorted({as_date(row["auction_date"]) for row in bills})
    bill_lookup = {(as_date(row["auction_date"]), int(row["tenor_days"])): float(row["accepted_rate"]) for row in bills}
    for row_idx, auction_date in enumerate(all_bill_dates, start=1):
        chart_data.write_datetime(row_idx, 5, datetime.combine(auction_date, time.min))
        for col_idx, tenor_value in enumerate((91, 182, 364), start=6):
            value = bill_lookup.get((auction_date, tenor_value))
            if value is not None:
                chart_data.write_number(row_idx, col_idx, value)


    fx_chart = workbook.add_chart({"type": "line"})
    for idx, pair in enumerate(pairs):
        rows = by_pair[pair]
        if not rows:
            continue
        fx_chart.add_series({
            "name": pair,
            "categories": ["Chart Data", 1, 0, len(all_fx_dates), 0],
            "values": ["Chart Data", 1, idx + 1, len(all_fx_dates), idx + 1],
            "line": {"color": [TEAL, BLUE, GOLD][idx], "width": 2.0},
            "marker": {"type": "none"},
        })
    fx_chart.show_hidden_data()
    fx_chart.show_blanks_as("gap")
    fx_chart.set_title({"name": "KES exchange-rate history"})
    fx_chart.set_x_axis({"name": "CBK observation date", "date_axis": True, "num_format": "mmm-yy", "line": {"color": "#AAB7C4"}})
    fx_chart.set_y_axis({"name": "KES per unit", "num_format": "#,##0.00", "major_gridlines": {"visible": True, "line": {"color": "#E5EBF0"}}})
    fx_chart.set_legend({"position": "bottom"})
    fx_chart.set_chartarea({"border": {"none": True}, "fill": {"color": WHITE}})
    fx_chart.set_plotarea({"border": {"none": True}, "fill": {"color": WHITE}})
    fx_chart.set_size({"width": 640, "height": 300})
    if fx:
        summary.insert_chart("J4", fx_chart, {"x_offset": 6, "y_offset": 3})

    bill_chart = workbook.add_chart({"type": "line"})
    for idx, tenor_value in enumerate((91, 182, 364), start=1):
        rows = [row for row in bills if int(row["tenor_days"]) == tenor_value]
        if not rows:
            continue
        bill_chart.add_series({
            "name": f"{tenor_value}-day",
            "categories": ["Chart Data", 1, 5, len(all_bill_dates), 5],
            "values": ["Chart Data", 1, idx + 5, len(all_bill_dates), idx + 5],
            "line": {"color": [TEAL, BLUE, GOLD][idx - 1], "width": 2.0},
            "marker": {"type": "circle", "size": 3},
            "gap": True,
        })
    bill_chart.show_hidden_data()
    bill_chart.show_blanks_as("gap")
    bill_chart.set_title({"name": "Treasury bill auction yields"})
    bill_chart.set_x_axis({"name": "Auction date", "date_axis": True, "num_format": "mmm-yy"})
    bill_chart.set_y_axis({"name": "Accepted yield", "num_format": "0.00%", "major_gridlines": {"visible": True, "line": {"color": "#E5EBF0"}}})
    bill_chart.set_legend({"position": "bottom"})
    bill_chart.set_chartarea({"border": {"none": True}, "fill": {"color": WHITE}})
    bill_chart.set_plotarea({"border": {"none": True}, "fill": {"color": WHITE}})
    bill_chart.set_size({"width": 640, "height": 300})
    if bills:
        summary.insert_chart("J21", bill_chart, {"x_offset": 6, "y_offset": 3})


    # Detailed FX analytics, with the quote convention and sample limitations visible.
    analysis_header = workbook.add_format({
        "bold": True, "font_color": WHITE, "bg_color": NAVY,
        "font_size": 9, "text_wrap": True, "valign": "vcenter",
        "bottom": 2, "bottom_color": TEAL,
    })
    analysis_title = workbook.add_format({
        "bold": True, "font_name": "Aptos Display", "font_size": 18,
        "font_color": WHITE, "bg_color": NAVY, "valign": "vcenter",
    })
    analysis_note = workbook.add_format({
        "font_color": MUTED, "font_size": 9, "text_wrap": True,
        "bg_color": PALE_BLUE, "valign": "top",
    })
    analysis_text = workbook.add_format({
        "font_color": INK, "font_size": 9, "text_wrap": True, "valign": "top",
    })
    analysis_label = workbook.add_format({
        "bold": True, "font_color": MUTED, "font_size": 9,
        "text_wrap": True, "valign": "top",
    })
    analysis_percent = workbook.add_format({
        "font_color": INK, "font_size": 9,
        "num_format": "0.00%;[Red](0.00%);-",
    })
    analysis_yield = workbook.add_format({
        "font_color": INK, "font_size": 9,
        "num_format": "0.0000%;[Red](0.0000%);-",
    })
    analysis_number = workbook.add_format({
        "font_color": INK, "font_size": 9,
        "num_format": '#,##0.0000;[Red](#,##0.0000);-',
    })
    analysis_integer = workbook.add_format({
        "font_color": INK, "font_size": 9,
        "num_format": '#,##0;[Red](#,##0);-',
    })
    analysis_money = workbook.add_format({
        "font_color": INK, "font_size": 9,
        "num_format": '"KES " #,##0.00;[Red]("KES " #,##0.00);-',
    })

    fx_analytics = workbook.add_worksheet("FX Analytics")
    fx_analytics.hide_gridlines(2)
    fx_analytics.set_tab_color(BLUE)
    fx_analytics.freeze_panes(3, 0)
    fx_analytics.set_landscape()
    fx_analytics.fit_to_pages(1, 0)
    fx_analytics.set_column("A:A", 14)
    fx_analytics.set_column("B:C", 14)
    fx_analytics.set_column("D:D", 19)
    fx_analytics.set_column("E:I", 19)
    fx_analytics.set_column("J:J", 15)
    fx_analytics.set_column("K:K", 19)
    fx_analytics.set_column("L:L", 15)
    fx_analytics.set_column("M:N", 23)
    fx_analytics.set_column("O:P", 15)
    fx_analytics.merge_range("A1:P1", "FOREIGN-EXCHANGE PERFORMANCE & RISK ANALYSIS", analysis_title)
    fx_analytics.merge_range(
        "A2:P2",
        "All changes use the stored KES-per-foreign-currency-unit quote. Pair histories can have different start and end dates; comparisons are descriptive, not forecasts.",
        analysis_note,
    )
    fx_headers = [
        "Currency pair", "First observation", "Latest observation",
        "Latest quote (KES / unit)", "Cumulative quote change",
        "Mean daily quote change", "Annualised historical volatility",
        "Maximum drawdown in quote level", "Best daily quote change", "Best day",
        "Worst daily quote change", "Worst day",
        "5th percentile daily quote change",
        "Average of worst 5% daily changes",
        "Daily changes", "Rate observations",
    ]
    fx_analytics.write_row(2, 0, fx_headers, analysis_header)
    for row_index, stat in enumerate(fx_stats, start=3):
        fx_analytics.write(row_index, 0, stat["pair"], fmt["body"])
        for column, key in ((1, "first_date"), (2, "latest_date")):
            value = stat[key]
            if value:
                fx_analytics.write_datetime(row_index, column, datetime.combine(value, time.min), fmt["date"])
            else:
                fx_analytics.write(row_index, column, "—", fmt["body"])
        for column, key, number_format in (
            (3, "latest", analysis_number),
            (4, "change", analysis_percent),
            (5, "mean_daily_change", analysis_percent),
            (6, "volatility", analysis_percent),
            (7, "drawdown", analysis_percent),
            (8, "best_daily_change", analysis_percent),
            (10, "worst_daily_change", analysis_percent),
            (12, "lower_tail_5pct", analysis_percent),
            (13, "average_worst_5pct", analysis_percent),
        ):
            value = stat[key]
            if value is None:
                fx_analytics.write(row_index, column, "—", fmt["body"])
            else:
                fx_analytics.write_number(row_index, column, value, number_format)
        for column, key in ((9, "best_daily_date"), (11, "worst_daily_date")):
            value = stat[key]
            fx_analytics.write(row_index, column, value.strftime("%d-%b-%Y") if value else "—", fmt["body"])
        fx_analytics.write_number(row_index, 14, stat["daily_observations"], fmt["integer"])
        fx_analytics.write_number(row_index, 15, stat["observations"], fmt["integer"])
    if fx_stats:
        fx_analytics.autofilter(2, 0, 2 + len(fx_stats), len(fx_headers) - 1)
    fx_analytics.merge_range(
        6, 0, 7, 15,
        "Lower-tail note: the 5th percentile and average-worst-5% fields are calculated only when a pair has at least 20 daily changes. They describe the quote series only; they are not portfolio Value at Risk, expected shortfall, or an investor's loss estimate. Annualised volatility uses sample standard deviation of daily percentage changes multiplied by √252.",
        analysis_note,
    )
    fx_analytics.set_row(6, 30)
    fx_analytics.set_row(7, 30)

    treasury_analysis = workbook.add_worksheet("Treasury Analysis")
    treasury_analysis.hide_gridlines(2)
    treasury_analysis.set_tab_color(GOLD)
    treasury_analysis.freeze_panes(3, 0)
    treasury_analysis.set_landscape()
    treasury_analysis.fit_to_pages(1, 0)
    treasury_analysis.set_column("A:A", 13)
    treasury_analysis.set_column("B:B", 15)
    treasury_analysis.set_column("C:D", 15)
    treasury_analysis.set_column("E:J", 19)
    treasury_analysis.set_column("K:K", 20)
    treasury_analysis.set_column("L:M", 23)
    treasury_analysis.set_column("N:N", 21)
    treasury_analysis.merge_range("A1:N1", "TREASURY-BILL AUCTION & YIELD ANALYSIS", analysis_title)
    treasury_analysis.merge_range(
        "A2:N2",
        "Tenor histories are kept separate. Change versus the preceding stored observation is not necessarily a week-on-week change.",
        analysis_note,
    )
    treasury_headers = [
        "Tenor (days)", "Auction records", "First auction", "Latest auction",
        "Latest accepted yield", "Change vs preceding stored auction",
        "Mean accepted yield", "Median accepted yield",
        "Lowest accepted yield", "Highest accepted yield",
        "Latest price per KES 100*", "Total offered (KES)",
        "Total accepted (KES)", "Aggregate accepted / offered",
    ]
    treasury_analysis.write_row(2, 0, treasury_headers, analysis_header)
    for row_index, stat in enumerate(tenor_stats, start=3):
        treasury_analysis.write_number(row_index, 0, stat["tenor"], fmt["integer"])
        treasury_analysis.write_number(row_index, 1, stat["observations"], fmt["integer"])
        for column, key in ((2, "first_date"), (3, "latest_date")):
            value = stat[key]
            if value:
                treasury_analysis.write_datetime(row_index, column, datetime.combine(value, time.min), fmt["date"])
            else:
                treasury_analysis.write(row_index, column, "—", fmt["body"])
        for column, key, number_format in (
            (4, "latest_yield", analysis_yield),
            (5, "change_vs_previous", analysis_yield),
            (6, "mean_yield", analysis_yield),
            (7, "median_yield", analysis_yield),
            (8, "minimum_yield", analysis_yield),
            (9, "maximum_yield", analysis_yield),
            (10, "latest_price", analysis_number),
            (11, "total_offered", analysis_money),
            (12, "total_accepted", analysis_money),
            (13, "accepted_offered_ratio", analysis_percent),
        ):
            value = stat[key]
            treasury_analysis.write_number(row_index, column, value, number_format) if value is not None else treasury_analysis.write(row_index, column, "—", fmt["body"])
    if tenor_stats:
        treasury_analysis.autofilter(2, 0, 2 + len(tenor_stats), len(treasury_headers) - 1)
    treasury_analysis.merge_range(
        8, 0, 9, 13,
        "* A price is shown from the CBK record when available; otherwise it is estimated as 100 ÷ (1 + accepted yield × tenor days / 365). Aggregate accepted/offered is the sum of accepted amounts divided by the sum of offered amounts where both are recorded. Neither is a dealer price or a standalone measure of investor demand.",
        analysis_note,
    )
    treasury_analysis.set_row(8, 30)
    treasury_analysis.set_row(9, 30)
    treasury_analysis.merge_range("A12:N12", "LATEST MATCHED AUCTION CURVE", fmt["section"])
    treasury_analysis.write("A13", "Latest auction date", fmt["meta_label"])
    treasury_analysis.merge_range("B13:D13", latest_bill_date.strftime("%d %b %Y") if latest_bill_date else "No auction data", fmt["meta_value"])
    treasury_analysis.write("E13", "364-day less 91-day", fmt["meta_label"])
    if curve_spread is None:
        treasury_analysis.merge_range("F13:G13", "—", fmt["body"])
    else:
        treasury_analysis.merge_range("F13:G13", curve_spread, analysis_yield)
    treasury_analysis.merge_range("H13:N13", curve_reading, analysis_note)
    treasury_analysis.merge_range(
        "A15:N16",
        "The matched curve uses 91-day and 364-day accepted yields from the same auction date only. It is a snapshot of the short end, not a forecast of future policy rates, secondary-market yields or long-term bond prices.",
        analysis_note,
    )
    treasury_analysis.set_row(14, 25)
    treasury_analysis.set_row(15, 25)

    key_findings = workbook.add_worksheet("Key Findings")
    key_findings.hide_gridlines(2)
    key_findings.set_tab_color(TEAL)
    key_findings.set_column("A:A", 25)
    key_findings.set_column("B:B", 75)
    key_findings.set_column("C:C", 65)
    key_findings.merge_range("A1:C1", "KEY FINDINGS & INTERPRETATION", analysis_title)
    key_findings.merge_range(
        "A2:C2",
        "Findings describe the observations stored when this workbook was requested. They are not forecasts or investment recommendations.",
        analysis_note,
    )
    key_findings.write_row(2, 0, ["Area", "Observed finding", "How to read it"], analysis_header)
    comparable_fx = [stat for stat in fx_stats if stat["change"] is not None]
    largest_quote_change = max(comparable_fx, key=lambda stat: stat["change"]) if comparable_fx else None
    smallest_quote_change = min(comparable_fx, key=lambda stat: stat["change"]) if comparable_fx else None
    highest_volatility = max(
        [stat for stat in fx_stats if stat["volatility"] is not None],
        key=lambda stat: stat["volatility"],
        default=None,
    )
    tail_ready = [stat for stat in fx_stats if stat["lower_tail_5pct"] is not None]
    ratios = [stat["accepted_offered_ratio"] for stat in tenor_stats if stat["accepted_offered_ratio"] is not None]
    findings = [
        (
            "Coverage",
            f"{len(fx)} FX observations across {sum(bool(stat['observations']) for stat in fx_stats)} tracked currency pairs; {len(bills)} Treasury-bill auction observations across {sum(bool(stat['observations']) for stat in tenor_stats)} tracked tenors.",
            "The coverage dates are stated separately for each series. A missing pair or tenor is not filled with an estimate.",
        ),
        (
            "FX lower-tail sample",
            f"{len(tail_ready)} of {len(fx_stats)} currency pairs have at least 20 daily changes for the lower-tail statistics.",
            "The 5th-percentile and average-worst-5% figures are descriptive quote-series measures, not portfolio VaR or investor-level expected shortfall.",
        ),
        (
            "Treasury-bill curve",
            curve_reading,
            "The 91-day and 364-day comparison is made only when both observations share the same latest auction date.",
        ),
    ]
    if largest_quote_change:
        findings.insert(1, (
            "FX quote movement",
            f"{largest_quote_change['pair']} recorded the largest cumulative quote change in its stored window ({largest_quote_change['change']:.2%}).",
            "A rising KES-per-unit quote means more shillings are required for one unit of foreign currency. Pair windows can differ, so the ranking is descriptive rather than a perfectly matched comparison.",
        ))
    if smallest_quote_change:
        findings.insert(2, (
            "FX relative movement",
            f"{smallest_quote_change['pair']} recorded the smallest cumulative quote change in its stored window ({smallest_quote_change['change']:.2%}).",
            "A falling KES-per-unit quote means fewer shillings are required for one unit of foreign currency.",
        ))
    if highest_volatility:
        findings.append((
            "FX historical variability",
            f"{highest_volatility['pair']} had the highest annualised sample volatility among the tracked pairs ({highest_volatility['volatility']:.2%}).",
            "Volatility is backward-looking sample standard deviation of daily quote changes multiplied by √252. It is not a forecast.",
        ))
    if ratios:
        findings.append((
            "Auction amounts",
            f"Aggregate accepted/offered amounts are available for {len(ratios)} tenors; the simple average of those tenor-level ratios is {sum(ratios) / len(ratios):.2%}.",
            "Each tenor ratio is sum of accepted amounts divided by sum of offered amounts where both are published. It is not a bid-cover or investor-demand measure.",
        ))
    else:
        findings.append((
            "Auction amounts",
            "An aggregate accepted/offered ratio is not available from the stored sample.",
            "Both offered and accepted amounts are required. Missing amounts are left missing.",
        ))
    fx_age = (retrieved_at.date() - latest_fx_date).days if latest_fx_date else None
    bill_age = (retrieved_at.date() - latest_bill_date).days if latest_bill_date else None
    findings.extend([
        (
            "Data refresh",
            f"Latest FX observation age: {fx_age} calendar days; latest Treasury-bill auction age: {bill_age} calendar days. Last recorded refresh status: {str(status).upper()}.",
            "The date of a market observation is different from the retrieval time. A successful database connection does not imply all source series were refreshed at once.",
        ),
        (
            "Scope boundary",
            "This workbook analyses stored CBK FX and Treasury-bill observations.",
            "It does not include user-specific portfolio positions, bond calculator inputs, option positions or backtest settings because those inputs are not persisted in the shared market database.",
        ),
        (
            "Decision-use limitation",
            "The workbook does not issue buy/sell instructions or forward market forecasts.",
            "Verify the source publication and account for taxes, transaction costs, settlement terms and personal circumstances before using any figure.",
        ),
    ])
    for row_index, (area, finding, interpretation) in enumerate(findings, start=3):
        key_findings.write(row_index, 0, area, analysis_label)
        key_findings.write(row_index, 1, finding, analysis_text)
        key_findings.write(row_index, 2, interpretation, analysis_text)
        key_findings.set_row(row_index, 52 if max(len(finding), len(interpretation)) > 150 else 38)
    key_findings.freeze_panes(3, 0)
    key_findings.set_landscape()
    key_findings.fit_to_pages(1, 0)

    dictionary = workbook.add_worksheet("Data Dictionary")
    dictionary.hide_gridlines(2)
    dictionary.set_tab_color(MUTED)
    dictionary.set_column("A:A", 30)
    dictionary.set_column("B:B", 70)
    dictionary.set_column("C:C", 65)
    dictionary.merge_range("A1:C1", "DATA DICTIONARY & MEASURE DEFINITIONS", analysis_title)
    dictionary.merge_range(
        "A2:C2",
        "Definitions apply to this report's stored CBK data. Percentages are stored as decimals and displayed as percentages.",
        analysis_note,
    )
    dictionary.write_row(2, 0, ["Field or measure", "Definition", "Interpretation / caution"], analysis_header)
    definitions = [
        ("FX observation", "A stored CBK exchange-rate quote for one currency pair on an observation date.", "KES per one unit of foreign currency; not a bid/ask trading quote."),
        ("Daily FX quote change", "Current observation divided by the previous stored observation for the same pair, minus one.", "Missing dates are not interpolated and the prior observation need not be the previous calendar day."),
        ("Cumulative FX quote change", "Latest stored quote divided by the first stored quote in the pair history, minus one.", "Coverage windows can differ across pairs."),
        ("Annualised historical volatility", "Sample standard deviation of daily percentage quote changes multiplied by √252.", "Backward-looking; not a forecast or guaranteed risk interval."),
        ("Maximum drawdown in quote level", "Largest decline from a previous peak in the observed KES-per-unit quote level.", "Not a portfolio drawdown or realised investor loss."),
        ("5th-percentile daily quote change", "Nearest-rank 5th percentile of daily quote changes; displayed only with at least 20 daily observations.", "A lower-tail quote statistic, not portfolio Value at Risk."),
        ("Average worst 5% daily changes", "Arithmetic mean of the lowest 5% of daily quote changes, using at least 20 daily observations.", "Not a position-level expected shortfall or investor P&L."),
        ("Accepted Treasury-bill yield", "CBK market-weighted average accepted auction yield stored as a decimal annual rate.", "Auction yield, not a secondary-market yield or a guaranteed reinvestment rate."),
        ("Price per KES 100", "Stored CBK price where supplied; otherwise 100 divided by (1 + accepted yield × tenor days / 365).", "A calculated price is a model comparison, not a dealer quote or settlement price."),
        ("Aggregate accepted / offered", "Sum of accepted amounts divided by sum of offered amounts where both figures are recorded.", "Describes published auction amounts; not a measure of bids or investor demand."),
        ("Percentage-point change", "Difference between two percentage rates, expressed in percentage points.", "For example, 9.0% minus 8.5% is 0.5 percentage points, or 50 basis points."),
        ("Source URL", "Direct link saved with the imported observation when one is available.", "Open the original CBK publication to confirm context and later corrections."),
    ]
    for row_index, (term, definition, caution) in enumerate(definitions, start=3):
        dictionary.write(row_index, 0, term, analysis_label)
        dictionary.write(row_index, 1, definition, analysis_text)
        dictionary.write(row_index, 2, caution, analysis_text)
        dictionary.set_row(row_index, 40 if max(len(definition), len(caution)) > 115 else 30)

    # Source-level FX history
    fx_sheet = workbook.add_worksheet("FX History")
    fx_sheet.hide_gridlines(2)
    fx_sheet.set_tab_color(BLUE)
    fx_sheet.freeze_panes(1, 0)
    fx_sheet.set_zoom(90)
    fx_sheet.set_column("A:A", 15)
    fx_sheet.set_column("B:B", 14)
    fx_sheet.set_column("C:D", 18)
    fx_sheet.set_column("E:E", 28)
    fx_sheet.set_column("F:F", 55)
    fx_sheet.set_default_row(16)
    fx_headers = ["Observation date", "Currency pair", "Rate (KES / unit)", "Daily change", "Published source", "Source URL"]
    history_header = workbook.add_format({
        "bold": True, "font_color": WHITE, "bg_color": NAVY,
        "font_size": 9, "text_wrap": True, "valign": "vcenter",
        "bottom": 2, "bottom_color": TEAL,
    })
    fx_sheet.write_row(0, 0, fx_headers, history_header)
    previous = {}
    for row_idx, row in enumerate(fx, start=1):
        pair = row["instrument"]
        rate = float(row["rate"])
        prev = previous.get(pair)
        daily = rate / prev - 1 if prev else None
        previous[pair] = rate
        fx_sheet.write_datetime(row_idx, 0, datetime.combine(as_date(row["observation_date"]), time.min), fmt["date"])
        fx_sheet.write(row_idx, 1, pair, fmt["body"])
        fx_sheet.write_number(row_idx, 2, rate, fmt["num"])
        if daily is None:
            fx_sheet.write(row_idx, 3, "—", fmt["body"])
        else:
            fx_sheet.write_number(row_idx, 3, daily, fmt["pct"])
        fx_sheet.write(row_idx, 4, row["source"] or "Central Bank of Kenya", fmt["body_wrap"])
        if row["source_url"]:
            fx_sheet.write_url(row_idx, 5, row["source_url"], fmt["hyperlink"], string="Open CBK source")
        else:
            fx_sheet.write(row_idx, 5, "—", fmt["body"])
    if fx:
        fx_sheet.conditional_format(1, 0, len(fx), len(fx_headers) - 1, {
            "type": "formula", "criteria": "=MOD(ROW(),2)=0",
            "format": workbook.add_format({"bg_color": "#F6F9FB"}),
        })
        fx_sheet.conditional_format(1, 3, len(fx), 3, {"type": "3_color_scale", "min_color": "#FCEBEC", "mid_color": "#FFF4D6", "max_color": "#E8F5EE"})
        fx_sheet.autofilter(0, 0, len(fx), len(fx_headers) - 1)
    fx_sheet.repeat_rows(0)
    fx_sheet.set_landscape()
    fx_sheet.fit_to_pages(1, 0)

    # Treasury bill auction history
    bill_sheet = workbook.add_worksheet("Treasury Bills")
    bill_sheet.hide_gridlines(2)
    bill_sheet.set_tab_color(GOLD)
    bill_sheet.freeze_panes(1, 0)
    bill_sheet.set_zoom(90)
    bill_widths = [15, 12, 18, 18, 17, 22, 22, 28, 55]
    for col, width in enumerate(bill_widths):
        bill_sheet.set_column(col, col, width)
    bill_headers = ["Auction date", "Tenor (days)", "Accepted yield", "Price / KES 100*", "Issue number", "Amount offered (KES)", "Amount accepted (KES)", "Published source", "Source URL"]
    bill_header = workbook.add_format({
        "bold": True, "font_color": NAVY, "bg_color": GOLD,
        "font_size": 9, "text_wrap": True, "valign": "vcenter",
        "bottom": 2, "bottom_color": NAVY,
    })
    bill_sheet.write_row(0, 0, bill_headers, bill_header)
    for row_idx, row in enumerate(bills, start=1):
        auction_date = as_date(row["auction_date"])
        rate = float(row["accepted_rate"])
        tenor_value = int(row["tenor_days"])
        calculated_price = float(row["price"]) if row["price"] is not None else 100 / (1 + rate * tenor_value / 365)
        bill_sheet.write_datetime(row_idx, 0, datetime.combine(auction_date, time.min), fmt["date"])
        bill_sheet.write_number(row_idx, 1, tenor_value, fmt["integer"])
        bill_sheet.write_number(row_idx, 2, rate, fmt["yield"])
        bill_sheet.write_number(row_idx, 3, calculated_price, fmt["num"])
        bill_sheet.write(row_idx, 4, row["issue_number"] or "—", fmt["body"])
        if row["amount_offered"] is not None:
            bill_sheet.write_number(row_idx, 5, float(row["amount_offered"]), fmt["kes"])
        else:
            bill_sheet.write(row_idx, 5, "—", fmt["body"])
        if row["amount_accepted"] is not None:
            bill_sheet.write_number(row_idx, 6, float(row["amount_accepted"]), fmt["kes"])
        else:
            bill_sheet.write(row_idx, 6, "—", fmt["body"])
        bill_sheet.write(row_idx, 7, row["source"] or "Central Bank of Kenya", fmt["body_wrap"])
        if row["source_url"]:
            bill_sheet.write_url(row_idx, 8, row["source_url"], fmt["hyperlink"], string="Open CBK source")
        else:
            bill_sheet.write(row_idx, 8, "—", fmt["body"])
    if bills:
        bill_sheet.conditional_format(1, 0, len(bills), len(bill_headers) - 1, {
            "type": "formula", "criteria": "=MOD(ROW(),2)=0",
            "format": workbook.add_format({"bg_color": "#F6F9FB"}),
        })
        bill_sheet.conditional_format(1, 2, len(bills), 2, {"type": "3_color_scale", "min_color": "#E8F5EE", "mid_color": "#FFF4D6", "max_color": "#FCEBEC"})
        bill_sheet.autofilter(0, 0, len(bills), len(bill_headers) - 1)
    bill_sheet.repeat_rows(0)
    bill_sheet.set_landscape()
    bill_sheet.fit_to_pages(1, 0)

    # Methodology and limitations
    method = workbook.add_worksheet("Methodology")
    method.hide_gridlines(2)
    method.set_tab_color(MUTED)
    method.set_column("A:A", 29)
    method.set_column("B:B", 100)
    method.set_row(0, 28)
    method.merge_range("A1:B1", "METHODOLOGY & REPORTING NOTES", fmt["title"])
    methodology = [
        ("Source", "Market observations are stored from Central Bank of Kenya official publications. Each history row carries a publisher label and, when available, a direct source URL."),
        ("FX quote convention", "Rates are shown as Kenyan shillings per one unit of foreign currency (KES / unit). An increase in the quoted rate means more KES are needed to buy one unit of that foreign currency."),
        ("Daily FX change", "Current observation divided by the previous stored observation for the same currency pair, minus one. No synthetic observations are inserted for dates with no publication."),
        ("Cumulative FX change", "Latest stored rate divided by the first stored rate in that pair's available dataset, minus one. Pair windows may differ."),
        ("Annualised FX volatility", "Sample standard deviation of the stored daily percentage changes, multiplied by the square root of 252. It is historical realised volatility, not a forecast."),
        ("Maximum drawdown", "Largest decline from a previous peak in the stored KES-per-unit rate level. It is not a portfolio drawdown unless the series is used as that portfolio's value proxy."),
        ("Treasury-bill yield", "Market-weighted average accepted yield stored as a decimal and displayed as an annual percentage. Auction dates and tenors are not combined across different dates in the latest-curve summary."),
        ("Price per KES 100", "Where not already stored from the official result, the report calculates 100 / (1 + accepted yield × tenor days / 365). The result is a transparent model estimate, not a dealer's quote or settlement price."),
        ("Missing values", "Blank, missing, or unavailable records are shown as em dashes. The report does not interpolate missing auction outcomes or forward-fill missing FX observations."),
        ("Refresh status", "The report shows the latest recorded data-refresh status. A successful database connection does not mean that every CBK publication has been refreshed on the same day."),
        ("Lower-tail quote changes", "The 5th percentile and average worst 5% daily quote changes are shown only after at least 20 daily observations. They describe the FX quote series, not an investor's portfolio Value at Risk or expected shortfall."),
        ("Auction change", "Change versus the preceding stored auction compares the latest tenor-specific observation with the previous stored observation for that tenor. The elapsed calendar period may vary."),
        ("Auction amount ratio", "Aggregate accepted/offered equals total accepted divided by total offered over rows where both fields are present. It describes published auction amounts; it is not an investor-demand or bid-cover estimate."),
        ("Data scope", "The workbook covers stored CBK FX and Treasury-bill observations. User-entered bond valuations, option positions, portfolio allocations and backtest settings are not persisted in the shared market database and are not included."),
        ("Model limitations", "FX statistics are sample-based. Treasury-bill model prices exclude settlement timing, taxes, transaction costs and investor-specific terms. Calculated measures must not be confused with directly published observations."),
        ("Use", "For education, financial research and analysis. This workbook is not investment, legal, tax or accounting advice. It does not issue a buy/sell instruction or forward market forecast."),
    ]
    for idx, (label, description) in enumerate(methodology, start=2):
        method.write(idx, 0, label, fmt["meta_label"])
        method.write(idx, 1, description, fmt["body_wrap"])
        method.set_row(idx, 34 if len(description) > 145 else 25)

    # Workbook front sheet and print-friendly settings
    summary.set_landscape()
    summary.fit_to_pages(1, 1)
    summary.set_margins(0.25, 0.25, 0.45, 0.45)
    summary.set_header("&CKenya Financial Analytics")
    summary.set_footer("&LConfidential research output&CPage &P of &N&RSource: Central Bank of Kenya")
    summary.activate()
    workbook.close()
    return output.getvalue()


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?")[0] != "/api/report":
            self.send_error(404)
            return
        try:
            fx, bills, refresh = load_report_data()
            payload = build_workbook(fx, bills, refresh)
            filename = "Kenya_Financial_Analytics_Market_Report.xlsx"
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            self.send_header("Content-Disposition", 'attachment; filename="' + filename + '"')
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "private, no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
        except Exception:
            payload = json.dumps({
                "ok": False,
                "error": "The formatted market report could not be generated. The market database may be unavailable.",
            }).encode("utf-8")
            self.send_response(503)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(payload)
