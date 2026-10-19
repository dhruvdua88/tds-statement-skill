#!/usr/bin/env python3
"""PAN checks beyond the format: the no-PAN rate floor and the TRACES status column."""

from __future__ import annotations

import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import intake  # noqa: E402
import lint  # noqa: E402
from model import Statement  # noqa: E402

FIX = ROOT / "tests" / "fixtures"


def codes_for(st):
    return {i.code for i in lint.model_issues(st) if i.level == lint.WARN}


class TestNoPanRate(unittest.TestCase):
    def st(self):
        return Statement.load(FIX / "example_140.json")

    def test_placeholder_at_the_normal_rate_is_flagged(self):
        st = self.st()
        st.deductees[2].pan = "PANNOTAVBL"          # 1027 at 10%
        self.assertIn("NO_PAN_RATE", codes_for(st))

    def test_placeholder_at_twenty_percent_is_not(self):
        st = self.st()
        row = st.deductees[2]
        row.pan, row.tds = "PANNOTAVBL", Decimal("20000.00")   # 20% of 100000
        st.challans[1].tax += Decimal("10000.00")
        st.challans[1].total += Decimal("10000.00")
        self.assertNotIn("NO_PAN_RATE", codes_for(st))

    def test_goods_purchase_floor_is_five_percent(self):
        st = self.st()
        row = st.deductees[1]                      # 1031, 30000 on 3 crore = 0.1%
        row.pan = "PANNOTAVBL"
        self.assertIn("NO_PAN_RATE", codes_for(st))
        row.amount_paid = Decimal("600000.00")      # 30000 is exactly 5%
        self.assertNotIn("NO_PAN_RATE", codes_for(st))

    def test_blank_pan_is_flagged_too(self):
        st = self.st()
        st.deductees[3].pan = ""
        self.assertIn("NO_PAN_RATE", codes_for(st))


class TestTracesStatus(unittest.TestCase):
    def test_inoperative_pan_at_the_normal_rate_is_flagged(self):
        st = Statement.load(FIX / "example_140.json")
        st.deductees[0].pan_status_traces = "inoperative"
        self.assertIn("PAN_INOPERATIVE", codes_for(st))
        st.deductees[0].pan_status_traces = "valid"
        self.assertNotIn("PAN_INOPERATIVE", codes_for(st))

    def test_status_survives_the_document(self):
        st = Statement.load(FIX / "example_140.json")
        st.deductees[0].pan_status_traces = "invalid"
        again = Statement.from_dict(st.to_dict())
        self.assertEqual(again.deductees[0].pan_status_traces, "invalid")
        self.assertNotIn("pan_status_traces", st.deductees[1].to_dict())

    def test_intake_reads_the_column_when_present(self):
        from openpyxl import Workbook
        path = Path(tempfile.mkdtemp()) / "src.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.title = "Deductee"
        ws.append(["Deductee Name", "PAN", "PAN Status from TRACES", "Nature of Payment",
                   "Amount Paid", "TDS", "Rate", "Date", "Challan No"])
        ws.append(["ONE", "AAECS1234K", "Inoperative", "Contractor", "100000", "1000", "1%", "31/07/2026", "1"])
        ws.append(["TWO", "AABFE5678L", "Valid", "Contractor", "100000", "1000", "1%", "31/07/2026", "1"])
        ws.append(["THREE", "AAGFM9012N", "", "Contractor", "100000", "1000", "1%", "31/07/2026", "1"])
        wb.save(path)
        st, _ = intake.intake([str(path)], form="140", financial_year="2026-27", quarter="Q2")
        self.assertEqual([r.pan_status_traces for r in st.deductees], ["inoperative", "valid", ""])
        self.assertEqual([r.pan for r in st.deductees], ["AAECS1234K", "AABFE5678L", "AAGFM9012N"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
