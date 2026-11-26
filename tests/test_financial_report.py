import io
import unittest
import zipfile
from datetime import date, datetime, timezone

from api.report import build_workbook


class FinancialReportTests(unittest.TestCase):
    def setUp(self):
        self.fx = []
        for pair, start, end in [
            ("USD/KES", 129.5, 130.0),
            ("GBP/KES", 169.0, 170.0),
            ("EUR/KES", 141.0, 142.0),
        ]:
            self.fx.extend([
                {"observation_date": date(2026, 11, 24), "instrument": pair, "rate": start,
                 "source": "Central Bank of Kenya", "source_url": "https://www.centralbank.go.ke/new-rates/"},
                {"observation_date": date(2026, 11, 25), "instrument": pair, "rate": end,
                 "source": "Central Bank of Kenya", "source_url": "https://www.centralbank.go.ke/new-rates/"},
            ])
        self.bills = [
            {"auction_date": date(2026, 11, 23), "tenor_days": tenor, "accepted_rate": rate,
             "price": None, "amount_offered": 10000000000, "amount_accepted": 9000000000,
             "issue_number": f"2709/{tenor}", "source": "Central Bank of Kenya",
             "source_url": "https://www.centralbank.go.ke/"},
            {"auction_date": date(2026, 11, 16), "tenor_days": tenor, "accepted_rate": rate - 0.001,
             "price": None, "amount_offered": 10000000000, "amount_accepted": 8000000000,
             "issue_number": f"2708/{tenor}", "source": "Central Bank of Kenya",
             "source_url": "https://www.centralbank.go.ke/"},
        ]
        self.refresh = {
            "source": "CBK scheduled refresh",
            "status": "success",
            "completed_at": datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc),
            "started_at": datetime(2026, 11, 26, 11, 59, tzinfo=timezone.utc),
            "fx_rows_upserted": 3,
            "bill_rows_upserted": 3,
            "details": {},
        }

    def test_report_is_a_valid_xlsx_with_distinct_sheets_and_charts(self):
        output = build_workbook(self.fx, self.bills, self.refresh)
        self.assertTrue(output.startswith(b"PK"))
        with zipfile.ZipFile(io.BytesIO(output)) as archive:
            self.assertIsNone(archive.testzip())
            workbook_xml = archive.read("xl/workbook.xml").decode("utf-8")
            self.assertIn("Executive Summary", workbook_xml)
            self.assertIn("FX History", workbook_xml)
            self.assertIn("Treasury Bills", workbook_xml)
            self.assertIn("Methodology", workbook_xml)
            chart_files = [name for name in archive.namelist() if name.startswith("xl/charts/chart") and name.endswith(".xml")]
            self.assertGreaterEqual(len(chart_files), 2)

    def test_report_includes_all_historical_rows_in_history_sheets(self):
        output = build_workbook(self.fx, self.bills, self.refresh)
        with zipfile.ZipFile(io.BytesIO(output)) as archive:
            fx_xml = archive.read("xl/worksheets/sheet2.xml").decode("utf-8")
            bills_xml = archive.read("xl/worksheets/sheet3.xml").decode("utf-8")
            self.assertIn("USD/KES", fx_xml)
            self.assertIn("GBP/KES", fx_xml)
            self.assertIn("EUR/KES", fx_xml)
            self.assertIn("2709", bills_xml)
            self.assertIn("182", bills_xml)


if __name__ == "__main__":
    unittest.main()
