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
        self.bills = []
        for tenor, rate in [(91, 0.087), (182, 0.088), (364, 0.090)]:
            self.bills.extend([
                {"auction_date": date(2026, 11, 23), "tenor_days": tenor, "accepted_rate": rate,
                 "price": None, "amount_offered": 10000000000, "amount_accepted": 9000000000,
                 "issue_number": f"2709/{tenor}", "source": "Central Bank of Kenya",
                 "source_url": "https://www.centralbank.go.ke/"},
                {"auction_date": date(2026, 11, 16), "tenor_days": tenor, "accepted_rate": rate - 0.001,
                 "price": None, "amount_offered": 10000000000, "amount_accepted": 8000000000,
                 "issue_number": f"2708/{tenor}", "source": "Central Bank of Kenya",
                 "source_url": "https://www.centralbank.go.ke/"},
            ])
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
            self.assertIn("Key Findings", workbook_xml)
            self.assertIn("FX Analytics", workbook_xml)
            self.assertIn("Treasury Analysis", workbook_xml)
            self.assertIn("Data Dictionary", workbook_xml)
            shared_strings = archive.read("xl/sharedStrings.xml").decode("utf-8")
            core_properties = archive.read("docProps/core.xml").decode("utf-8")
            self.assertIn("KENYA FINANCIAL ANALYTICS", shared_strings)
            self.assertIn("Market Research Report", core_properties)
            self.assertIn("FOREIGN-EXCHANGE PERFORMANCE", shared_strings)
            self.assertIn("TREASURY-BILL AUCTION", shared_strings)
            self.assertIn("KEY FINDINGS", shared_strings)
            self.assertIn("DATA DICTIONARY", shared_strings)
            self.assertIn("at least 20 daily changes", shared_strings)
            chart_files = [name for name in archive.namelist() if name.startswith("xl/charts/chart") and name.endswith(".xml")]
            self.assertGreaterEqual(len(chart_files), 2)
            styles_xml = archive.read("xl/styles.xml").decode("utf-8")
            self.assertIn("087F8C", styles_xml)
            self.assertIn("356BB3", styles_xml)
            self.assertIn("D5A43B", styles_xml)
            self.assertIn("numFmt", styles_xml)

    def test_report_includes_all_historical_rows_in_history_sheets(self):
        output = build_workbook(self.fx, self.bills, self.refresh)
        with zipfile.ZipFile(io.BytesIO(output)) as archive:
            shared_strings = archive.read("xl/sharedStrings.xml").decode("utf-8")
            bills_xml = archive.read("xl/worksheets/sheet4.xml").decode("utf-8")
            self.assertIn("USD/KES", shared_strings)
            self.assertIn("GBP/KES", shared_strings)
            self.assertIn("EUR/KES", shared_strings)
            self.assertIn("2709/91", shared_strings)
            self.assertIn("2709/182", shared_strings)
            self.assertIn("2709/364", shared_strings)
            self.assertGreater(bills_xml.count("<row"), 6)


if __name__ == "__main__":
    unittest.main()
