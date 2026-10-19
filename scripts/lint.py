"""Pre-flight checks. A pass here means "ready for the official FVU", nothing more.

The checks are grouped by how expensive the failure is:

  error   the utility will reject the file, or the filing would be wrong
  warn    the statement is usable but something needs a human eye
  info    recorded for the workpaper

The rules come from the remarks on the fields in the department's file-format
workbook, quoted on the field in ``layout140.py`` and enforced here. A few earn
their keep more than the rest:

* the allocation check - do the deductee rows charged to a challan come to more
  than was deposited against it? Over-allocation is rejected; a challan paid at
  a round figure with the odd rupees unallocated is not, and is reported as a
  note rather than an error.
* the whole-rupee check on the challan record. Fields 8 to 12 are declared
  integer; "1000.50" is rejected and "1000.00" accepted. This is invisible in a
  spreadsheet, where both look like money.
* the duplicate check: the same invoice entered twice, often in consecutive
  months, which inflates the deposit and is very hard to spot by eye.

Where a code cannot be checked because the reference tables are missing, the
finding is downgraded to a warning: an unrecognised code may well be correct.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import NamedTuple
import re

import codes
from model import (
    DATE_RE,
    GSTIN_RE,
    PAN_PLACEHOLDERS,
    PAN_RE,
    TAN_RE,
    Statement,
)

ERROR, WARN, INFO = "error", "warn", "info"

# Deductor categories that must carry a state name (BH field 54).
STATE_NAME_CATEGORIES = {"S", "E", "H", "N"}
# Deductor categories that must carry a ministry code (BH field 57).
MINISTRY_REQUIRED_CATEGORIES = {"A", "D", "G"}
# Deductor categories that may carry a ministry code at all.
MINISTRY_ALLOWED_CATEGORIES = MINISTRY_REQUIRED_CATEGORIES | {"E", "H"}
# Deductor categories for which the AIN matters on a book-adjustment deposit.
AIN_CATEGORIES = {"A", "S"}

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Issue:
    __slots__ = ("level", "code", "message", "ref")

    def __init__(self, level: str, code: str, message: str, ref: str = ""):
        self.level, self.code, self.message, self.ref = level, code, message, ref

    def as_dict(self) -> dict:
        return {"level": self.level, "code": self.code, "message": self.message, "ref": self.ref}

    def __str__(self) -> str:
        ref = f" [{self.ref}]" if self.ref else ""
        return f"{self.level.upper():5} {self.code:22}{ref} {self.message}"


class Quarter(NamedTuple):
    lo: str  # first day, YYYYMMDD, for comparisons
    hi: str  # last day, YYYYMMDD
    first: str  # first day, DD-MM-YYYY, for messages and rules
    last: str  # last day, DD-MM-YYYY


def _quarter_window(fy: str, quarter: str) -> Quarter | None:
    """The window a quarter covers, as sortable ISO dates.

    Comparing DD-MM-YYYY strings as text silently gives the wrong answer, which
    is how a row from the wrong quarter slips through, so everything is
    compared as ISO. The DD-MM-YYYY forms are kept for the rules that have to
    state a date, such as a nil challan taking the last day of the quarter.
    """
    if not re.match(r"^\d{4}-\d{2}$", fy or ""):
        return None
    start_year = int(fy[:4])
    q = {"Q1": (4, 6), "Q2": (7, 9), "Q3": (10, 12), "Q4": (1, 3)}.get((quarter or "").upper())
    if not q:
        return None
    m1, m2 = q
    y1 = start_year if m1 >= 4 else start_year + 1
    y2 = start_year if m2 >= 4 else start_year + 1
    last_day = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
                7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}[m2]
    return Quarter(
        lo=f"{y1}{m1:02d}01", hi=f"{y2}{m2:02d}{last_day:02d}",
        first=f"01-{m1:02d}-{y1}", last=f"{last_day:02d}-{m2:02d}-{y2}",
    )


def _iso(value: str) -> str:
    """DD-MM-YYYY -> YYYYMMDD, or '' when it is not a date."""
    if not value or not re.match(r"^\d{2}-\d{2}-\d{4}$", value):
        return ""
    return value[6:10] + value[3:5] + value[0:2]


def _has_paise(value: Decimal) -> bool:
    return value != value.to_integral_value()


def _rate_decimal(value: str) -> Decimal | None:
    try:
        return Decimal(str(value).strip().replace("%", ""))
    except (InvalidOperation, ValueError, AttributeError):
        return None


def model_issues(st: Statement) -> list[Issue]:
    out: list[Issue] = []
    add = lambda lvl, code, msg, ref="": out.append(Issue(lvl, code, msg, ref))
    unknown = WARN if not codes.TABLES_COMPLETE else ERROR

    if not codes.TABLES_COMPLETE:
        add(WARN, "TABLES", "reference tables are incomplete (" + ", ".join(codes.MISSING_TABLES)
            + "); run scripts/extract_annexures.py before relying on these checks")

    # ---- statement level -------------------------------------------------
    if st.form not in ("140", "138"):
        add(ERROR, "FORM", f"unsupported form {st.form!r}")
    if st.upload_type not in ("R", "C"):
        add(ERROR, "UPLOAD_TYPE", f"upload type must be R or C, got {st.upload_type!r}")
    if st.upload_type == "C" and not st.correction.get("original_token"):
        add(ERROR, "CORRECTION", "correction statement needs correction.original_token")
    if not st.financial_year:
        add(ERROR, "FY", "financial_year is required")
    q = _quarter_window(st.financial_year, st.quarter)
    if q is None:
        add(ERROR, "QUARTER", f"quarter must be Q1..Q4 with a financial year like 2026-27, got "
                              f"{st.quarter!r} {st.financial_year!r}")

    # ---- deductor / responsible person -----------------------------------
    ded = st.deductor
    if not TAN_RE.match(st.tan or ""):
        add(ERROR, "TAN", f"deductor TAN {st.tan!r} is not in the form AAAX99999X")
    pan = str(ded.get("pan", "") or "")
    if not PAN_RE.match(pan):
        add(ERROR, "DEDUCTOR_PAN", f"deductor PAN {pan!r} is not in the form AAAAA9999A")
    if not str(ded.get("name", "") or "").strip():
        add(ERROR, "DEDUCTOR_NAME", "deductor name is blank")
    cat = str(ded.get("category", "") or "").upper()
    if cat and cat not in codes.DEDUCTOR_CATEGORIES:
        add(unknown, "DEDUCTOR_CATEGORY", f"unknown deductor category {cat!r}")
    addr = ded.get("address")
    if addr is not None:
        sc = str(getattr(addr, "state_code", "") or "")
        if sc and sc not in codes.STATE_CODES:
            add(unknown, "STATE_CODE", f"deductor state code {sc!r} is not in Annexure 1")
        pin = str(getattr(addr, "pin", "") or "")
        if pin and not (pin.isdigit() and len(pin) == 6):
            add(ERROR, "PIN", f"deductor PIN {pin!r} must be 6 digits")
        if not str(getattr(addr, "country", "INDIA") or "INDIA").strip():
            add(WARN, "COUNTRY", "deductor country is blank; INDIA is the usual value")
    email = str(ded.get("email", "") or "")
    if email and not _EMAIL_RE.match(email):
        add(WARN, "EMAIL_FORM", f"deductor email {email!r} does not look like an address")
    gstin = str(ded.get("gstin", "") or "")
    if gstin and not GSTIN_RE.match(gstin):
        add(WARN, "GSTIN", f"GSTIN {gstin!r} does not match the 15-character pattern")

    # BH field 54: only the four State-Government categories carry a state name.
    state_name = str(ded.get("state_name", "") or "")
    if cat in STATE_NAME_CATEGORIES and not state_name:
        add(ERROR, "STATE_NAME", f"BH field 54 (state code) is required for deductor category {cat}")
    elif state_name and cat and cat not in STATE_NAME_CATEGORIES:
        add(ERROR, "STATE_NAME", f"BH field 54 must be blank for deductor category {cat}")
    elif state_name and not (state_name.isdigit() and len(state_name) == 2):
        add(ERROR, "STATE_NAME", f"state code {state_name!r} must be a two-digit code from Annexure 5")
    elif state_name and state_name not in codes.STATE_CODES:
        add(unknown, "STATE_NAME", f"state code {state_name!r} is not in Annexure 5")

    # BH fields 57 and 58: the ministry code.
    ministry = str(ded.get("ministry_code", "") or "")
    ministry_name = str(ded.get("ministry_name", "") or "")
    if cat in MINISTRY_REQUIRED_CATEGORIES and not ministry:
        add(ERROR, "MINISTRY_CODE", f"BH field 57 (ministry code) is required for deductor category {cat}")
    elif ministry and cat and cat not in MINISTRY_ALLOWED_CATEGORIES:
        add(ERROR, "MINISTRY_CODE", f"BH field 57 must be blank for deductor category {cat}")
    elif ministry and codes.MINISTRY_CODES and ministry not in codes.MINISTRY_CODES:
        add(unknown, "MINISTRY_CODE", f"ministry code {ministry!r} is not in Annexure 3")
    if ministry == "99" and not ministry_name.strip():
        add(ERROR, "MINISTRY_NAME", "BH field 58 (ministry name in words) is required when the code is 99")
    if ministry_name and ministry and ministry != "99":
        add(WARN, "MINISTRY_NAME", "BH field 58 is only expected when the ministry code is 99")

    regular_earlier = str(ded.get("regular_earlier", "N") or "N").upper()[:1]
    token_previous = str(ded.get("token_previous", "") or "")
    if regular_earlier not in ("Y", "N"):
        add(ERROR, "REGULAR_EARLIER", f"BH field 52 must be Y or N, got {regular_earlier!r}")
    if st.upload_type == "C" and regular_earlier != "Y":
        add(WARN, "REGULAR_EARLIER", "a correction normally follows an earlier regular statement (BH field 52 = 'Y')")
    if regular_earlier == "Y" and not token_previous and st.upload_type == "C":
        add(WARN, "TOKEN_PREVIOUS", "BH field 9 (token of the earlier regular statement) is blank")
    if token_previous and regular_earlier != "Y":
        add(WARN, "TOKEN_PREVIOUS", "BH field 9 is set but BH field 52 says no earlier statement")
    if token_previous and not token_previous.isdigit():
        add(ERROR, "TOKEN_PREVIOUS", f"BH field 9 {token_previous!r} must be numeric")

    rp = st.responsible_person
    rpan = str(rp.get("pan", "") or "")
    if not rpan:
        add(ERROR, "RP_PAN", "responsible person PAN is blank (the utility will reject the file)")
    elif not PAN_RE.match(rpan):
        add(ERROR, "RP_PAN", f"responsible person PAN {rpan!r} is not in the form AAAAA9999A")
    if not str(rp.get("name", "") or "").strip():
        add(ERROR, "RP_NAME", "responsible person name is blank")
    phone = str(ded.get("phone", "") or "")
    if not phone:
        add(ERROR, "DEDUCTOR_PHONE", "deductor phone is blank (the utility will reject the file)")
    elif not (phone.isdigit() and 6 <= len(phone) <= 15):
        add(WARN, "DEDUCTOR_PHONE", f"deductor phone {phone!r} does not look like a number")
    rphone = str(rp.get("phone", "") or "")
    if not rphone:
        add(ERROR, "RP_PHONE", "responsible person phone is blank (the utility will reject the file)")
    elif not (rphone.isdigit() and 6 <= len(rphone) <= 10):
        add(WARN, "RP_PHONE", f"responsible person phone {rphone!r} does not look like a number")
    rp_email = str(rp.get("email", "") or "")
    if rp_email and not _EMAIL_RE.match(rp_email):
        add(WARN, "EMAIL_FORM", f"responsible person email {rp_email!r} does not look like an address")

    # ---- challans --------------------------------------------------------
    if not st.challans:
        add(ERROR, "CHALLANS", "no challans in the statement")
    by_no = {ch.no: ch for ch in st.challans}
    seen_serial: dict = {}
    for ch in st.challans:
        ref = f"challan {ch.challan_serial or ch.no}"
        nil = (ch.nil_challan or "N").upper()[:1] == "Y"
        if ch.nature not in ("C", "B"):
            add(ERROR, "CHALLAN_NATURE", f"challan mode is {ch.nature!r}; the format allows C or B", ref)
        if nil:
            if ch.bsr_code or ch.challan_serial:
                add(WARN, "CHALLAN_NIL", "a nil challan carries no BSR code or challan number", ref)
            if q and ch.challan_date != q.last:
                add(WARN, "CHALLAN_NIL",
                    f"a nil challan takes the last day of the quarter ({q.last}), not {ch.challan_date}", ref)
        else:
            bsr = ch.bsr_code
            if not (bsr.isdigit() and len(bsr) == 7):
                add(ERROR, "BSR", f"BSR code {bsr!r} must be 7 digits", ref)
            if not ch.challan_serial.strip():
                add(ERROR, "CHALLAN_SERIAL", "challan serial is blank", ref)
            elif not (ch.challan_serial.isdigit() and len(ch.challan_serial) <= 5):
                add(WARN, "CHALLAN_SERIAL", f"challan serial {ch.challan_serial!r} is not up to 5 digits", ref)
        if ch.minor_head not in codes.MINOR_HEADS:
            add(unknown, "MINOR_HEAD", f"minor head {ch.minor_head!r} is not in Annexure 7", ref)
        dt = _iso(ch.challan_date)
        if not dt:
            add(ERROR, "CHALLAN_DATE", f"challan date {ch.challan_date!r} is not DD-MM-YYYY", ref)
        elif q and not (q.lo <= dt <= q.hi) and not nil:
            # A challan may be paid after the quarter closes; the format allows
            # any date from 1 April of the previous year, so this is a note.
            add(INFO, "CHALLAN_OUT_OF_QUARTER",
                f"challan date {ch.challan_date} is outside the quarter", ref)
        key = (ch.bsr_code, ch.challan_date, ch.challan_serial)
        if key in seen_serial:
            add(ERROR, "CHALLAN_DUPLICATE", f"same BSR/date/serial as challan {seen_serial[key]}", ref)
        seen_serial[key] = ch.challan_serial or ch.no
        if ch.total != ch.all_tax + ch.interest + ch.fee + ch.penalty:
            add(ERROR, "CHALLAN_TOTAL", "challan total does not equal fields 8+9+10+11", ref)
        fractional = [name for name, val in
                      (("8 income tax", ch.all_tax), ("9 interest", ch.interest),
                       ("10 fee", ch.fee), ("11 penalty", ch.penalty), ("12 total", ch.total))
                      if _has_paise(val)]
        if fractional:
            add(ERROR, "CHALLAN_FRACTIONAL",
                "no fractional portion is allowed on the challan record; fields with paise: "
                + ", ".join(fractional)
                + " (write the amount actually deposited, in whole rupees)", ref)
        if ch.tax <= 0 and not nil:
            add(WARN, "CHALLAN_TAX", "challan tax is zero or negative", ref)
        for label, val in (("interest", ch.interest), ("fee", ch.fee), ("penalty", ch.penalty)):
            if val < 0:
                add(ERROR, "CHALLAN_NEGATIVE", f"challan {label} is negative", ref)
        deposit = ch.total
        allocated = sum((r.total_tds for r in st.deductees if r.challan_no == ch.no), Decimal("0.00"))
        required = allocated + ch.interest + ch.penalty + (ch.fee if ch.nature == "C" else Decimal("0.00"))
        if deposit < required:
            add(ERROR, "CHALLAN_UNDERFUNDED",
                f"deposited {deposit} is less than the {required} that has to be accounted for "
                f"(deductee tax {allocated} + interest {ch.interest} + other {ch.penalty}"
                + (f" + fee {ch.fee}" if ch.nature == "C" else "") + ")", ref)

        rows = [r for r in st.deductees if r.challan_no == ch.no]
        # CD field 13: 'C' is required when any deductee uses one of the
        # sections whose tax is paid before the income is released.
        if any(r.section in codes.NO_PAN_DEFAULT_SECTIONS for r in rows) and ch.nature != "C":
            add(ERROR, "CHALLAN_MODE",
                "challan mode must be C when a deductee uses section 1059, 1034, 1038 or 1061", ref)
        # CD field 23: minor head 100 brings two date rules with it.
        if ch.minor_head == "100":
            if not any(r.section in codes.NO_PAN_DEFAULT_SECTIONS for r in rows):
                add(WARN, "MINOR_HEAD_100",
                    "minor head 100 applies to sections 1059/1034/1038/1061, but no such row is on "
                    "this challan", ref)
            if q and dt and not (q.lo <= dt <= q.hi):
                add(ERROR, "CHALLAN_MINOR100_DATE",
                    f"with minor head 100 the challan date {ch.challan_date} must fall inside the quarter", ref)
            for r in rows:
                pdt = _iso(r.payment_date)
                if dt and pdt and dt > pdt:
                    add(ERROR, "CHALLAN_MINOR100_DATE",
                        f"with minor head 100 the challan date {ch.challan_date} must be on or before the "
                        f"payment date {r.payment_date} on row {r.name}", ref)

    # ---- deductees -------------------------------------------------------
    seen_rows: dict = {}
    for i, row in enumerate(st.deductees, 1):
        ref = row.source_ref or f"row {i} ({row.name})"
        special = row.section in codes.NO_PAN_DEFAULT_SECTIONS
        if row.challan_no not in by_no:
            add(ERROR, "CHALLAN_LINK", f"row points at challan {row.challan_no}, which is not in the statement", ref)

        if row.pan_is_placeholder:
            if special:
                add(ERROR, "DEDUCTEE_PAN",
                    f"PAN placeholders are not allowed on section {row.section}; a real PAN is required", ref)
        elif not PAN_RE.match(row.pan or ""):
            add(ERROR, "DEDUCTEE_PAN", f"PAN {row.pan!r} is not in the form AAAAA9999A and is not one of "
                                       f"{', '.join(PAN_PLACEHOLDERS)}", ref)
        elif not row.deductee_code:
            add(WARN, "DEDUCTEE_CODE",
                f"PAN {row.pan} has an unusual 4th character, so no deductee code can be derived", ref)

        if not row.name.strip():
            add(ERROR, "DEDUCTEE_NAME", "deductee name is blank", ref)
        if len(row.name) > 75:
            add(WARN, "DEDUCTEE_NAME_LEN", f"name is {len(row.name)} characters; long names get truncated by portals", ref)

        if st.form == "138":
            if row.section not in codes.SALARY_SECTIONS:
                add(ERROR, "SECTION", f"a salary statement uses section 1002 only, got {row.section!r}", ref)
        elif row.section in codes.SALARY_SECTIONS:
            add(ERROR, "SECTION", "section 1002 is salary and does not belong on a non-salary statement", ref)
        elif row.section not in codes.SECTIONS:
            add(unknown, "SECTION", f"section code {row.section!r} is not in Annexure 2", ref)

        if row.reason_code and row.reason_code not in codes.REASON_CODES:
            add(unknown, "REASON_CODE", f"reason flag {row.reason_code!r} is not in Annexure 6", ref)
        if row.reason_code == "A":
            if not row.certificate_no:
                add(ERROR, "CERTIFICATE", "DD field 33 is required when the reason flag is A", ref)
            elif not re.fullmatch(r"[A-Za-z0-9]{10}|[A-Za-z0-9]{15}", row.certificate_no or ""):
                add(ERROR, "CERTIFICATE",
                    f"certificate number {row.certificate_no!r} must be 10 or 15 alphanumeric characters", ref)
        if row.form121 and len(row.form121) != 26:
            add(ERROR, "FORM121", f"DD field 31 is {len(row.form121)} characters; the format is 26", ref)

        if row.cash_withdrawal_1cr or row.cash_withdrawal_3cr:
            if row.section not in codes.CASH_WITHDRAWAL_SECTIONS:
                add(ERROR, "CASH_WITHDRAWAL",
                    f"cash-withdrawal amounts belong to sections 1064/1065, not {row.section}", ref)
        if row.section in codes.CASH_WITHDRAWAL_SECTIONS and not (row.cash_withdrawal_1cr or row.cash_withdrawal_3cr):
            add(WARN, "CASH_WITHDRAWAL",
                f"section {row.section} is a cash-withdrawal section but both amount fields are blank", ref)

        if row.deposited not in ("Y", "N"):
            add(ERROR, "DEPOSITED", f"DD field 18 must be Y or N, got {row.deposited!r}", ref)

        for label, val in (("payment date", row.payment_date), ("deduction date", row.deduction_date)):
            if val and not DATE_RE.match(val):
                add(ERROR, "DATE_FORM", f"{label} {val!r} is not DD-MM-YYYY", ref)

        # DD field 19 must fall inside the quarter; the remark is mandatory.
        iso = _iso(row.payment_date)
        if not row.payment_date:
            add(ERROR, "DATE_BLANK", "payment date is blank", ref)
        elif q and iso and not (q.lo <= iso <= q.hi):
            add(ERROR, "PAYMENT_DATE_QUARTER",
                f"payment date {row.payment_date} is outside the quarter {q.first} to {q.last}; "
                "the row belongs in the statement for the quarter it was paid in", ref)

        # DD field 27: required when tax was deducted, and never before the quarter.
        d_iso = _iso(row.deduction_date)
        if row.tds > 0 and not row.deduction_date:
            add(ERROR, "DEDUCTION_DATE", "deduction date is required when tax was deducted", ref)
        elif row.tds == 0 and row.deduction_date:
            add(INFO, "DEDUCTION_DATE", "deduction date is set although no tax was deducted", ref)
        elif d_iso and q:
            if d_iso < q.lo:
                add(ERROR, "DEDUCTION_DATE_QUARTER",
                    f"deduction date {row.deduction_date} is before the quarter starts ({q.first})", ref)
            elif d_iso > q.hi:
                add(WARN, "DEDUCTION_DATE_QUARTER",
                    f"deduction date {row.deduction_date} is after the quarter ends ({q.last})", ref)
        if row.deduction_date and row.payment_date and d_iso and iso and d_iso < iso:
            add(INFO, "DEDUCTION_BEFORE_PAYMENT",
                f"deduction date {row.deduction_date} precedes payment date {row.payment_date}", ref)

        if row.amount_paid <= 0:
            add(ERROR, "AMOUNT", "DD field 20 must be greater than 0.00", ref)
        if row.tds < 0:
            add(WARN, "NEGATIVE_TDS", "negative tax; confirm this is a genuine reversal", ref)

        # DD field 28: four decimals, zero when nothing was deducted.
        rate = _rate_decimal(row.rate)
        if rate is None:
            add(WARN, "RATE", f"rate {row.rate!r} is not numeric", ref)
        else:
            if row.tds == 0 and rate != 0:
                add(WARN, "RATE", f"rate is {row.rate} but no tax was deducted", ref)
            if row.tds > 0 and rate == 0:
                add(WARN, "RATE", "rate is zero but tax was deducted", ref)
            decimals = str(row.rate).strip().split(".")[1] if "." in str(row.rate) else ""
            if len(decimals) != 4:
                add(WARN, "RATE", f"rate {row.rate!r} should be written with four decimals, e.g. 2.0000", ref)
            if rate > 40:
                add(WARN, "RATE", f"rate {row.rate} looks too high", ref)

        # The four pre-release sections carry no tax at all on the statement.
        if special:
            if row.tds != 0 or (row.total_tds or Decimal("0")) != 0:
                add(ERROR, "SPECIAL_SECTION",
                    f"section {row.section} must show no tax deducted; found {row.tds}", ref)
            if rate is not None and rate != 0:
                add(ERROR, "SPECIAL_SECTION", f"section {row.section} must show a rate of zero", ref)

        expected = codes.indicative_rate(row.section)
        if expected and row.amount_paid > 0 and not special:
            expected_tax = (row.amount_paid * Decimal(str(expected)) / Decimal(100)).quantize(Decimal("1"))
            actual = row.tds.quantize(Decimal("1"))
            if abs(expected_tax - actual) > 1:
                add(WARN, "RATE_DEVIATION",
                    f"section {row.section} implies about {expected_tax} on {row.amount_paid} "
                    f"but {actual} was deducted (difference {actual - expected_tax})", ref)

        dkey = (row.pan, str(row.amount_paid), str(row.tds))
        if row.pan and dkey in seen_rows:
            add(WARN, "POSSIBLE_DUPLICATE", f"same PAN, amount and tax as {seen_rows[dkey]}", ref)
        seen_rows[dkey] = ref

    # ---- allocation ------------------------------------------------------
    for row in st.allocation():
        ref = f"challan {row['serial']} ({row['date']})"
        if row["over_by"] > 0:
            add(ERROR, "ALLOCATION",
                f"deductee rows total {row['allocated']} against challan tax {row['challan_tax']} "
                f"(over by {row['over_by']}); the utility rejects a challan that is asked to cover "
                "more tax than was deposited against it", ref)
        elif row["unallocated"] > 0:
            add(INFO, "ALLOCATION_EXCESS",
                f"{row['unallocated']} of the {row['challan_tax']} tax on this challan is not "
                "allocated to any deductee row; the format allows it, so confirm it is intentional", ref)
        if row["rows"] == 0:
            add(WARN, "CHALLAN_UNUSED", "no deductee rows against this challan", ref)

    # ---- pending ---------------------------------------------------------
    for p in st.blocking_pending:
        add(ERROR, "PENDING", f"awaiting {p.get('field')}: {p.get('why')}", str(p.get("owner", "")))

    return out


def txt_issues(path: str | Path, st: Statement, layout) -> list[Issue]:
    out: list[Issue] = []
    add = lambda lvl, code, msg, ref="": out.append(Issue(lvl, code, msg, ref))
    raw = Path(path).read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        add(ERROR, "BOM", "file starts with a UTF-8 BOM; the utility expects plain ASCII")
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        add(ERROR, "ENCODING", f"file is not ASCII: {exc}")
        return out
    if not raw.endswith(b"\r\n"):
        add(ERROR, "CRLF_END", "file must end with CRLF")
    if raw.replace(b"\r\n", b"").count(b"\n"):
        add(ERROR, "BARE_LF", "file contains a bare LF")
    if raw.replace(b"\r\n", b"").count(b"\r"):
        add(ERROR, "BARE_CR", "file contains a bare CR")

    lines = text.split("\r\n")
    if lines and lines[-1] == "":
        lines.pop()

    types = []
    for i, line in enumerate(lines, 1):
        parts = line.split("^")
        if len(parts) < 2:
            add(ERROR, "SHORT_RECORD", "fewer than two fields", f"line {i}")
            continue
        rt = parts[1]
        types.append(rt)
        if rt in layout.WIDTHS and len(parts) != layout.WIDTHS[rt]:
            add(ERROR, "WIDTH", f"{rt} has {len(parts)} fields, expected {layout.WIDTHS[rt]}", f"line {i}")
        if parts[0] != str(i):
            add(ERROR, "LINE_NO", f"line number is {parts[0]!r}", f"line {i}")

    if types[:2] != ["FH", "BH"]:
        add(ERROR, "HEAD", "the first two records must be FH and BH")
    if types.count("FH") != 1 or types.count("BH") != 1:
        add(ERROR, "HEAD_COUNT", f"expected exactly one FH and one BH, found {types.count('FH')} and {types.count('BH')}")

    # interleaving and the global DD serial
    serial = 0
    open_cd = None
    for i, line in enumerate(lines, 1):
        parts = line.split("^")
        rt = parts[1] if len(parts) > 1 else ""
        if rt == "CD":
            open_cd = parts[3] if len(parts) > 3 else None
        elif rt == "DD":
            if open_cd is None:
                add(ERROR, "DD_WITHOUT_CD", "a DD record appears before any CD record", f"line {i}")
            serial += 1
            if len(parts) > 3 and parts[3] != str(serial):
                add(ERROR, "DD_SERIAL",
                    f"DD field 4 is {parts[3]!r}; the utility requires the running serial {serial}", f"line {i}")
            if len(parts) > 4 and open_cd and parts[4] != open_cd:
                add(ERROR, "DD_CHALLAN_REF",
                    f"DD field 5 is {parts[4]!r} but the enclosing CD is {open_cd!r}", f"line {i}")

    if st.deductees and serial != len(st.deductees):
        add(ERROR, "DD_COUNT", f"file has {serial} DD records, the model has {len(st.deductees)}")

    # arithmetic tie-out, on the written bytes rather than the model
    challans: dict[str, dict] = {}
    open_cd = None
    dd_tax: dict[str, Decimal] = {}
    dd_deposited: dict[str, Decimal] = {}
    for line in lines:
        parts = line.split("^")
        if len(parts) < 2:
            continue
        if parts[1] == "CD":
            open_cd = parts[3]
            challans[open_cd] = {
                "tax": Decimal(parts[7] or "0"), "interest": Decimal(parts[8] or "0"),
                "fee": Decimal(parts[9] or "0"), "penalty": Decimal(parts[10] or "0"),
                "total": Decimal(parts[11] or "0"), "mode": parts[12],
                # field 21 = the deposit per the collectee annexure,
                # field 22 = the deduction per the deductor annexure.
                "reported_deposit": Decimal(parts[20] or "0"),
                "reported_deduction": Decimal(parts[21] or "0"),
                "interest_alloc": Decimal(parts[23] or "0"), "other_alloc": Decimal(parts[24] or "0"),
            }
        elif parts[1] == "DD" and open_cd:
            dd_tax[open_cd] = dd_tax.get(open_cd, Decimal("0")) + Decimal(parts[23] or "0")
            dd_deposited[open_cd] = dd_deposited.get(open_cd, Decimal("0")) + Decimal(parts[24] or "0")

    for cd, c in challans.items():
        if c["total"] != c["tax"] + c["interest"] + c["fee"] + c["penalty"]:
            add(ERROR, "TXT_CD_TOTAL", f"CD {cd}: field 12 is not fields 8+9+10+11", f"challan {cd}")
        deposited = dd_deposited.get(cd, Decimal("0"))
        deducted = dd_tax.get(cd, Decimal("0"))
        if c["reported_deposit"] != deposited:
            add(ERROR, "TXT_CD21", f"CD {cd}: field 21 is {c['reported_deposit']} but the DD rows deposit {deposited}",
                f"challan {cd}")
        if c["reported_deduction"] != deducted:
            add(ERROR, "TXT_CD22", f"CD {cd}: field 22 is {c['reported_deduction']} but the DD rows deduct {deducted}",
                f"challan {cd}")
        if c["interest_alloc"] != c["interest"]:
            add(ERROR, "TXT_CD24", f"CD {cd}: interest allocation is not the challan's interest", f"challan {cd}")
        if c["other_alloc"] != c["penalty"]:
            add(ERROR, "TXT_CD25", f"CD {cd}: other allocation is not the challan's penalty/other", f"challan {cd}")
        required = deposited + c["interest_alloc"] + c["other_alloc"]
        if c["mode"] == "C":
            required += c["fee"]
        if c["total"] < required:
            add(ERROR, "TXT_CD12",
                f"CD {cd}: field 12 is {c['total']}, less than the {required} it has to cover",
                f"challan {cd}")

    return out


def format_issues(issues: list[Issue], limit: int | None = None) -> str:
    order = {ERROR: 0, WARN: 1, INFO: 2}
    issues = sorted(issues, key=lambda i: (order.get(i.level, 9), i.code))
    shown = issues if limit is None else issues[:limit]
    lines = [str(i) for i in shown]
    errors = sum(1 for i in issues if i.level == ERROR)
    warns = sum(1 for i in issues if i.level == WARN)
    infos = sum(1 for i in issues if i.level == INFO)
    lines.append(f"-- {errors} error(s), {warns} warning(s), {infos} note(s)")
    if limit is not None and len(issues) > limit:
        lines.append(f"-- {len(issues) - limit} more not shown")
    return "\n".join(lines)


def counts(issues: list[Issue]) -> dict:
    return {
        "errors": sum(1 for i in issues if i.level == ERROR),
        "warnings": sum(1 for i in issues if i.level == WARN),
        "notes": sum(1 for i in issues if i.level == INFO),
    }
