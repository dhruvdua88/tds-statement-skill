#!/usr/bin/env python3
"""Build the test fixtures: a synthetic statement document and a messy source sheet.

The 140 fixture mirrors the shape of a real quarterly statement (three bank
challans, rows spread across two sections) but every identifier is invented.
It is deliberately small so a reader can check the built TXT by eye.

The messy source workbook is the more useful fixture. It reproduces what
clients actually send: a title row, a month block, a header row with awkward
wording, amounts stored as text with a trailing 'Dr', a section written as a
sentence rather than a code, a total row halfway down, and the challans on a
second tab. If intake handles this, it will handle most real sources.

Run: python3 tests/make_fixtures.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

FIX = ROOT / "tests" / "fixtures"

CHALLANS = [
    {"no": 1, "bsr_code": "0180002", "challan_serial": "90001", "challan_date": "07-08-2026",
     "tax": "45000.00", "interest": "0.00", "total": "45000.00"},
    {"no": 2, "bsr_code": "0180002", "challan_serial": "90002", "challan_date": "07-09-2026",
     "tax": "12000.00", "interest": "0.00", "total": "12000.00"},
    {"no": 3, "bsr_code": "0180002", "challan_serial": "90003", "challan_date": "07-10-2026",
     "tax": "31500.00", "interest": "15.00", "total": "31515.00"},
]

ROWS = [
    # challan, name, pan, section, amount, tds, rate, payment, deduction
    (1, "SAMPLE INFRA PROJECTS PRIVATE LIMITED", "AAECS1234K", "1023", "1500000.00", "15000.00", "1.0000", "31-07-2026", "31-07-2026"),
    (1, "EXAMPLE TRADERS", "AABFE5678L", "1031", "30000000.00", "30000.00", "0.1000", "31-07-2026", "31-07-2026"),
    (2, "MEENAKSHI CONSULTING LLP", "AAGFM9012N", "1027", "100000.00", "10000.00", "10.0000", "31-08-2026", "31-08-2026"),
    (2, "DEMO CARRIERS", "AAHPD3456M", "1023", "200000.00", "2000.00", "1.0000", "31-08-2026", "31-08-2026"),
    (3, "MEENAKSHI CONSULTING LLP", "AAGFM9012N", "1027", "150000.00", "15000.00", "10.0000", "30-09-2026", "30-09-2026"),
    (3, "SAMPLE INFRA PROJECTS PRIVATE LIMITED", "AAECS1234K", "1023", "1650000.00", "16500.00", "1.0000", "30-09-2026", "30-09-2026"),
]


def statement_140() -> dict:
    return {
        "schema": "tds-statement/1",
        "form": "140",
        "upload_type": "R",
        "financial_year": "2026-27",
        "quarter": "Q2",
        "meta": {
            "prepared_by": "Dhruv Dua & Co.",
            "utility_name": "TDS Statement Skill 1.0",
            "file_creation_date": "19102026",
            "short_name": "EX140Q2.txt",
            "note": "Synthetic fixture. Every identifier here is invented.",
        },
        "deductor": {
            "tan": "AAAA12345A",
            "pan": "AAACA1234A",
            "name": "SAMPLE WORKS PRIVATE LIMITED",
            "category": "K",
            "regular_earlier": "N",
            "email": "accounts@example.in",
            "country_code": "91",
            "phone": "9810000000",
            "gstin": "",
            "address": {
                "line1": "PLOT 1, INDUSTRIAL AREA", "line2": "", "line3": "PHASE II",
                "line4": "SONEPAT", "line5": "HARYANA", "state_code": "11",
                "pin": "131001", "country": "INDIA",
            },
        },
        "responsible_person": {
            "name": "A DIRECTOR", "designation": "DIRECTOR", "pan": "AAAPA1234A",
            "email": "director@example.in", "country_code": "91", "phone": "9810000001",
            "address": {
                "line1": "PLOT 1, INDUSTRIAL AREA", "line2": "", "line3": "PHASE II",
                "line4": "SONEPAT", "line5": "HARYANA", "state_code": "11",
                "pin": "131001", "country": "INDIA",
            },
        },
        "challans": CHALLANS,
        "deductees": [
            {
                "challan_no": c, "name": n, "pan": p, "section": s,
                "amount_paid": a, "tds": t, "rate": r,
                "payment_date": pay, "deduction_date": ded,
                "pan_status": "Y", "source_ref": f"fixture row {i + 1}",
            }
            for i, (c, n, p, s, a, t, r, pay, ded) in enumerate(ROWS)
        ],
        "flags": [],
        "pending": [],
    }


MESSY_ROWS = [
    ["TDS WORKING - JULY TO SEPTEMBER 2026"],
    ["Deductee Name", "PAN", "Nature of Payment", "Amount Paid", "TDS", "Rate", "Date", "Challan No"],
    ["SAMPLE INFRA PROJECTS PRIVATE LIMITED", "AAECS1234K", "Contractor - 194C", "15,00,000.00 Dr", "15000", "1%", "31/07/2026", "90001"],
    ["EXAMPLE TRADERS", "AABFE5678L", "Purchase of Goods u/s 194Q", "3,00,00,000", "30000", "0.10%", "31/07/2026", "90001"],
    ["Total", "", "", "3,15,00,000", "45000", "", "", ""],
    ["MEENAKSHI CONSULTING LLP", "AAGFM9012N", "Professional Fees - Sec 393(1) Tbl 6(iii).D(b)", "1,00,000", "10000", "10%", "31/08/2026", "90002"],
    ["DEMO CARRIERS", "AAHPD3456M", "Contractor - 194C", "2,00,000", "2000", "1%", "31/08/2026", "90002"],
    ["MEENAKSHI CONSULTING LLP", "AAGFM9012N", "Professional Fees", "1,50,000", "15000", "10%", "30/09/2026", "90003"],
    ["SAMPLE INFRA PROJECTS PRIVATE LIMITED", "AAECS1234K", "Contractor - 194C", "16,50,000", "16500", "1%", "30/09/2026", "90003"],
]

MESSY_CHALLANS = [
    ["Bank Challan Details"],
    ["Challan No", "BSR Code", "Challan Date", "Amount Deposited"],
    ["90001", "0180002", "07/08/2026", "45000"],
    ["90002", "0180002", "07/09/2026", "12000"],
    ["90003", "0180002", "07/10/2026", "31500"],
]


def messy_workbook(path: Path) -> None:
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Deductee"
    for row in MESSY_ROWS:
        ws.append(row)
    ch = wb.create_sheet("Challans")
    for row in MESSY_CHALLANS:
        ch.append(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def main() -> int:
    FIX.mkdir(parents=True, exist_ok=True)
    (FIX / "example_140.json").write_text(json.dumps(statement_140(), indent=2) + "\n")
    print(f"wrote {FIX / 'example_140.json'}")
    messy_workbook(FIX / "messy_source.xlsx")
    print(f"wrote {FIX / 'messy_source.xlsx'}")

    try:
        import layout138  # noqa: F401
        (FIX / "example_138.json").write_text(json.dumps(statement_138(), indent=2) + "\n")
        print(f"wrote {FIX / 'example_138.json'}")
    except ImportError:
        print("layout138 not present yet, skipped the salary fixture")
    return 0


def statement_138() -> dict:
    """Salary statement fixture. Only 1002 rows, no rate is quoted."""
    base = statement_140()
    base["form"] = "138"
    base["meta"]["short_name"] = "EX138Q2.txt"
    rows = [
        ("A WORKER", "AAKPA1234A", "500000.00", "0.00"),
        ("B EMPLOYEE", "AALPB5678B", "820000.00", "12000.00"),
        ("C MANAGER", "AAMPC9012C", "1400000.00", "96000.00"),
    ]
    base["challans"] = [
        {"no": 1, "bsr_code": "0180002", "challan_serial": "90010",
         "challan_date": "07-09-2026", "tax": "108000.00", "interest": "0.00", "total": "108000.00"},
    ]
    base["deductees"] = [
        {
            "challan_no": 1, "name": n, "pan": p, "section": "1002",
            "amount_paid": amt, "tds": tds, "rate": "",
            "payment_date": "31-08-2026", "deduction_date": "31-08-2026",
            "pan_status": "Y", "source_ref": f"salary fixture row {i + 1}",
        }
        for i, (n, p, amt, tds) in enumerate(rows)
    ]
    return base


if __name__ == "__main__":
    raise SystemExit(main())
