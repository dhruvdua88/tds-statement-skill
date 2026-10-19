"""Reference tables from the official file-format workbook (Annexures 1-7).

These are not opinions. Every code below comes from the department's own
spreadsheet in ``assets/annexures.json``, which ``scripts/extract_annexures.py``
builds from the official workbook. Hand-typing a state or section code from
memory is how a statement ends up looking right and being rejected at upload:
the state codes in the first draft of this file were all shifted (Delhi was 08
instead of 09, Haryana 11 instead of 12) and the deductor categories were a
different scheme altogether.

If the JSON is missing, the loader falls back to the handful of values that are
independently verifiable and sets ``TABLES_COMPLETE`` false. The linter then
reports an unknown code as a warning rather than an error, because without the
tables a code it does not recognise may still be correct.
"""

from __future__ import annotations

import json
from pathlib import Path

ASSET = Path(__file__).resolve().parent.parent / "assets" / "annexures.json"

# Sections that may only appear on a salary statement: Annexure 2 of the Form
# 138 workbook (22-Jul-2026) lists exactly these four. None of them is in Annexure
# 2 of Form 140, so a non-salary statement carrying one is wrong.
SALARY_SECTIONS = {"1001", "1002", "1003", "1032"}

# Sections the official remarks single out: the tax was paid before release, so
# the deductee PAN may not be a placeholder, the tax columns must be zero and
# the rate must be zero.
NO_PAN_DEFAULT_SECTIONS = {"1059", "1034", "1038", "1061"}

# Cash-withdrawal sections. See FIELD_NOTES in layout140: the workbook's remarks
# for DD fields 22 and 23 name sections 1065 and 1064, which is the reverse of
# the field names. Rare enough that it is flagged rather than resolved.
CASH_WITHDRAWAL_SECTIONS = {"1064", "1065"}

# Indicative rates, used only to raise "this looks off" warnings on the
# workpaper. The rate is set by the Act and the Finance Act for the year, not by
# the file format, so treat these as a prompt to look, never as authority.
INDICATIVE_RATES = {
    "1004": 10.0, "1006": 2.0, "1008": 10.0, "1009": 10.0,
    "1019": 10.0, "1021": 10.0, "1023": 1.0, "1024": 2.0,
    "1026": 2.0, "1027": 10.0, "1028": 10.0, "1029": 10.0,
    "1031": 0.1, "1033": 2.0, "1035": 2.0, "1058": 2.0,
    "1059": 30.0, "1060": 5.0, "1061": 30.0, "1062": 2.0,
    "1063": 2.0, "1064": 2.0, "1065": 5.0,
}

# Fallback only, and only for values that cannot be misread: the three minor
# heads, the official deductor categories, and the reason flags. State and
# section codes are intentionally absent - a plausible wrong code is worse than
# a loud "table missing".
_FALLBACK = {
    "state_codes": {},
    "sections": {},
    "minor_heads": {
        "100": "Advance Tax",
        "200": "TDS payable by taxpayer",
        "400": "TDS regular assessment (Raised by I. T, Dept.)",
    },
    "deductor_categories": {
        "A": "Central Government",
        "B": "Body of Individuals",
        "D": "Statutory body (Central Govt.)",
        "E": "Statutory body (State Govt.)",
        "F": "Firm",
        "G": "Autonomous body (Central Govt.)",
        "H": "Autonomous body (State Govt.)",
        "J": "Artificial Juridical Person",
        "K": "Company",
        "L": "Local Authority (Central Govt.)",
        "M": "Branch / Division of Company",
        "N": "Local Authority (State Govt.)",
        "P": "Association of Person (AOP)",
        "Q": "Individual/HUF",
        "S": "State Government",
        "T": "Association of Person (Trust)",
    },
    "reason_codes": {},
}


def _load() -> tuple[dict, list[str]]:
    data: dict = {}
    if ASSET.exists():
        try:
            data = json.loads(ASSET.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return dict(_FALLBACK), [f"{ASSET.name} is not valid JSON: {exc}"]

    merged = {k: dict(v) for k, v in _FALLBACK.items()}
    for key in ("state_codes", "sections", "minor_heads", "deductor_categories", "reason_codes"):
        if data.get(key):
            merged[key] = data[key]
    merged["annexures"] = data.get("annexures", {})
    merged["source"] = data.get("source", {})

    missing = [k for k in ("state_codes", "sections", "reason_codes") if not merged.get(k)]
    return merged, missing


DATA, MISSING_TABLES = _load()

STATE_CODES: dict[str, str] = DATA["state_codes"]
SECTIONS: dict[str, dict] = DATA["sections"]
MINOR_HEADS: dict[str, str] = DATA["minor_heads"]
DEDUCTOR_CATEGORIES: dict[str, str] = DATA["deductor_categories"]
REASON_CODES: dict[str, str] = DATA["reason_codes"]
ANNEXURES: dict = DATA.get("annexures", {})
MINISTRY_CODES: dict[str, str] = ANNEXURES.get("ministry_codes", {})
REASON_CODE_DETAIL: dict = ANNEXURES.get("reason_code_detail", {})
SOURCE: dict = DATA.get("source", {})

TABLES_COMPLETE = not MISSING_TABLES

# Form 144 has its own Annexure 2 (code 1004 and codes 1039 to 1067), extracted
# from the Form 144 workbook by ``extract_annexures.py --form144``.
ASSET_144 = ASSET.parent / "annexures_144.json"
SECTIONS_144: dict[str, dict] = (
    json.loads(ASSET_144.read_text(encoding="utf-8")).get("sections", {})
    if ASSET_144.exists() else {}
)


def section_label(code: str) -> str:
    meta = SECTIONS.get(code) or SECTIONS_144.get(code)
    return meta["description"] if meta else f"unknown section code {code}"


def section_reference(code: str) -> str:
    meta = SECTIONS.get(code)
    return meta.get("section", "") if meta else ""


def state_name(code: str) -> str:
    return STATE_CODES.get(code, "")


def state_code(name: str) -> str:
    wanted = (name or "").strip().upper()
    for code, label in STATE_CODES.items():
        if label.upper() == wanted:
            return code
    return ""


def sections_for_form(form: str) -> dict[str, dict]:
    """Form 138 is salary only; Form 144 has its own table; Form 140 uses the rest."""
    if form == "138":
        return {k: v for k, v in SECTIONS.items() if k in SALARY_SECTIONS}
    if form == "144":
        return SECTIONS_144
    return {k: v for k, v in SECTIONS.items() if k not in SALARY_SECTIONS}


def indicative_rate(code: str) -> float | None:
    return INDICATIVE_RATES.get(code)
