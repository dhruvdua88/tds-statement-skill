"""Reference tables from the official file-format workbook (Annexures 1-7).

These are not opinions; they are transcribed from the department's own
spreadsheet, because a single wrong state code or section code produces a
statement that looks fine and is rejected at upload. The tables live in
``assets/annexures.json`` so they can be regenerated when Protean publishes a
new format version, and ``scripts/extract_annexures.py`` builds that file from
the official workbook.

If the JSON is missing, the fallback below keeps the common cases working and
marks the tables as incomplete so the linter can say so rather than silently
passing a wrong code.
"""

from __future__ import annotations

import json
from pathlib import Path

ASSET = Path(__file__).resolve().parent.parent / "assets" / "annexures.json"

# Fallback only. Populated with the codes that appear in almost every statement.
_FALLBACK = {
    "state_codes": {
        "01": "Andhra Pradesh", "02": "Assam", "03": "Bihar", "04": "Chandigarh",
        "05": "Chhattisgarh", "06": "Dadra & Nagar Haveli", "07": "Daman & Diu",
        "08": "Delhi", "09": "Goa", "10": "Gujarat", "11": "Haryana",
        "12": "Himachal Pradesh", "13": "Jammu & Kashmir", "14": "Jharkhand",
        "15": "Karnataka", "16": "Kerala", "17": "Lakshadweep", "18": "Madhya Pradesh",
        "19": "Maharashtra", "20": "Manipur", "21": "Meghalaya", "22": "Mizoram",
        "23": "Nagaland", "24": "Odisha", "25": "Puducherry", "26": "Punjab",
        "27": "Rajasthan", "28": "Sikkim", "29": "Tamil Nadu", "30": "Tripura",
        "31": "Uttar Pradesh", "32": "West Bengal", "33": "Andaman & Nicobar Islands",
        "34": "Arunachal Pradesh", "35": "Uttarakhand", "36": "Telangana",
    },
    "sections": {
        "1002": {"description": "Salary", "rate_pct": None, "form": "138"},
        "1006": {"description": "Commission or brokerage", "rate_pct": 2, "form": "140"},
        "1009": {"description": "Rent", "rate_pct": 10, "form": "140"},
        "1023": {"description": "Contractor - individual/HUF", "rate_pct": 1, "form": "140"},
        "1024": {"description": "Contractor - other than individual/HUF", "rate_pct": 2, "form": "140"},
        "1026": {"description": "Technical services / royalty", "rate_pct": 2, "form": "140"},
        "1027": {"description": "Professional services", "rate_pct": 10, "form": "140"},
        "1031": {"description": "Purchase of goods", "rate_pct": 0.1, "form": "140"},
    },
    "minor_heads": {"200": "TDS/TCS payable", "400": "TDS/TCS regular assessment"},
    "deductor_categories": {
        "A": "Association of persons", "B": "Body of individuals",
        "C": "Company (other than government)", "F": "Firm / LLP", "G": "Government",
        "H": "Hindu undivided family", "J": "Artificial juridical person",
        "K": "Company", "L": "Local authority", "P": "Individual", "T": "Trust",
    },
    "reason_codes": {"Y": "Valid PAN", "C": "PAN not available", "N": "PAN not applied for"},
}


def _load() -> tuple[dict, bool]:
    if ASSET.exists():
        try:
            data = json.loads(ASSET.read_text(encoding="utf-8"))
            merged = dict(_FALLBACK)
            merged.update({k: v for k, v in data.items() if v})
            return merged, True
        except json.JSONDecodeError:
            pass
    return _FALLBACK, False


DATA, COMPLETE = _load()

STATE_CODES: dict[str, str] = DATA["state_codes"]
SECTIONS: dict[str, dict] = DATA["sections"]
MINOR_HEADS: dict[str, str] = DATA["minor_heads"]
DEDUCTOR_CATEGORIES: dict[str, str] = DATA["deductor_categories"]
REASON_CODES: dict[str, str] = DATA["reason_codes"]
ANNEXURES = DATA.get("annexures", {})

TABLES_COMPLETE = COMPLETE


def section_label(code: str) -> str:
    return SECTIONS.get(code, {}).get("description", f"unknown section {code}")


def state_name(code: str) -> str:
    return STATE_CODES.get(code, "")


def sections_for_form(form: str) -> dict[str, dict]:
    """Salary statements only use 1002; the non-salary form uses the rest."""
    if form == "138":
        return {k: v for k, v in SECTIONS.items() if v.get("form") in (None, "138")}
    return {k: v for k, v in SECTIONS.items() if v.get("form") != "138"}
