import io
import json
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
            SELECT observation_date, instrument, rate, source, source_url, imported_at
            FROM fx_observations
            ORDER BY observation_date, instrument
            LIMIT 2000
            """
        ).fetchall()
        bills = conn.execute(
            """
            SELECT auction_date, tenor_days, accepted_rate, price,
                   amount_offered, amount_accepted, issue_number,
                   source, source_url, imported_at
            FROM treasury_bill_observations
            ORDER BY auction_date, tenor_days
            LIMIT 2000
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
        rows = by_pair[pair]
        levels = [float(row["rate"]) for row in rows]
        daily_returns = [
            levels[i] / levels[i - 1] - 1
            for i in range(1, len(levels)) if levels[i - 1]
        ]
        fx_stats.append({
            "pair": pair,
            "first_date": as_date(rows[0]["observation_date"]) if rows else None,
            "latest_date": as_date(rows[-1]["observation_date"]) if rows else None,
            "latest": levels[-1] if levels else None,
            "change": levels[-1] / levels[0] - 1 if len(levels) > 1 and levels[0] else None,
            "volatility": sample_std(daily_returns) * (252 ** 0.5) if len(daily_returns) > 1 else None,
            "drawdown": max_drawdown(levels) if levels else None,
            "observations": len(rows),
        })

    latest_fx_date = max((row["latest_date"] for row in fx_stats if row["latest_date"]), default=None)
    latest_bill_date = max((as_date(row["auction_date"]) for row in bills), default=None)
    latest_bills = [
        row for row in bills
        if latest_bill_date and as_date(row["auction_date"]) == latest_bill_date
    ]
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
    bill_sheet.write_row(0, 0, bill_headers, history_header)
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
        ("Model limitations", "FX risk and return statistics are sample-based. Treasury bill model prices exclude settlement timing, tax, transaction costs and other investor-specific terms. Verify the original CBK publication before relying on a value."),
        ("Use", "For education, financial research and analysis. This workbook is not investment, legal, tax or accounting advice."),
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
