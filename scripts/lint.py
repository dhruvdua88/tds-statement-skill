"""Pre-flight checks. A pass here means "ready for the official FVU", nothing more.

The checks are grouped by how expensive the failure is:

  error   the utility will reject the file, or the filing would be wrong
  warn    the statement is usable but something needs a human eye
  info    recorded for the workpaper

Two classes of check earn their keep in practice. The allocation check (do the
deductee rows under a challan add up to the challan?) catches more real
failures than everything else combined, because a filing is usually built from
two sources that were never reconciled. The duplicate check catches the other
big one: the same invoice entered twice in a client's sheet, often in
consecutive months, which inflates the deposit and is very hard to spot by eye.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import re

import codes
from model import DATE_RE, GSTIN_RE, PAN_RE, TAN_RE, Statement

ERROR, WARN, INFO = "error", "warn", "info"


class Issue:
    __slots__ = ("level", "code", "message", "ref")

    def __init__(self, level: str, code: str, message: str, ref: str = ""):
        self.level, self.code, self.message, self.ref = level, code, message, ref

    def as_dict(self) -> dict:
        return {"level": self.level, "code": self.code, "message": self.message, "ref": self.ref}

    def __str__(self) -> str:
        ref = f" [{self.ref}]" if self.ref else ""
        return f"{self.level.upper():5} {self.code:22}{ref} {self.message}"


def _quarter_window(fy: str, quarter: str) -> tuple[str, str]:
    """Return the qurter window as sortable ISO dates (YYYYMMDD).

    Comparing DD-MM-YYYY strings as text silently gives the wrong answer, which
    is how a row from the wrong quarter slips through, so everything is
    compared as ISO.
    """
    start_year = int(fy[:4])
    q = {"Q1": (4, 6), "Q2": (7, 9), "Q3": (10, 12), "Q4": (1, 3)}.get(quarter.upper())
    if not q:
        return "", ""
    m1, m2 = q
    y1 = start_year if m1 >= 4 else start_year + 1
    y2 = start_year if m2 >= 4 else start_year + 1
    last = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30, 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}[m2]
    return f"{y1}{m1:02d}01", f"{y2}{m2:02d}{last}"


def _iso(value: str) -> str:
    """DD-MM-YYYY -> YYYYMMDD, or '' when it is not a date."""
    if not value or not re.match(r"^\d{2}-\d{2}-\d{4}$", value):
        return ""
    return value[6:10] + value[3:5] + value[0:2]


def model_issues(st: Statement) -> list[Issue]:
    out: list[Issue] = []
    add = lambda lvl, code, msg, ref="": out.append(Issue(lvl, code, msg, ref))

    # ---- statement level -------------------------------------------------
    if st.form not in ("140", "138"):
        add(ERROR, "FORM", f"unsupported form {st.form!r}")
    if st.upload_type not in ("R", "C"):
        add(ERROR, "UPLOAD_TYPE", f"upload type must be R or C, got {st.upload_type!r}")
    if st.upload_type == "C" and not st.correction.get("original_token"):
        add(ERROR, "CORRECTION", "correction statement needs correction.original_token")
    if not st.financial_year:
        add(ERROR, "FY", "financial_year is required")
    if st.quarter.upper() not in ("Q1", "Q2", "Q3", "Q4"):
        add(ERROR, "QUARTER", f"quarter must be Q1..Q4, got {st.quarter!r}")
    lo, hi = _quarter_window(st.financial_year, st.quarter)

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
        add(ERROR, "DEDUCTOR_CATEGORY", f"unknown deductor category {cat!r}")
    addr = ded.get("address")
    if addr is not None:
        sc = str(getattr(addr, "state_code", "") or "")
        if sc and sc not in codes.STATE_CODES:
            add(ERROR, "STATE_CODE", f"deductor state code {sc!r} is not in Annexure 1")
        pin = str(getattr(addr, "pin", "") or "")
        if pin and not (pin.isdigit() and len(pin) == 6):
            add(ERROR, "PIN", f"deductor PIN {pin!r} must be 6 digits")
        if not str(getattr(addr, "country", "INDIA") or "INDIA").strip():
            add(WARN, "COUNTRY", "deductor country is blank; INDIA is the usual value")
    gstin = str(ded.get("gstin", "") or "")
    if gstin and not GSTIN_RE.match(gstin):
        add(WARN, "GSTIN", f"GSTIN {gstin!r} does not match the 15-character pattern")

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
    elif not (phone.isdigit() and 6 <= len(phone) <= 12):
        add(WARN, "DEDUCTOR_PHONE", f"deductor phone {phone!r} does not look like a number")
    rphone = str(rp.get("phone", "") or "")
    if not rphone:
        add(ERROR, "RP_PHONE", "responsible person phone is blank (the utility will reject the file)")

    # ---- challans --------------------------------------------------------
    if not st.challans:
        add(ERROR, "CHALLANS", "no challans in the statement")
    seen_serial = {}
    for ch in st.challans:
        ref = f"challan {ch.challan_serial or ch.no}"
        if ch.nature != "C":
            add(WARN, "CHALLAN_NATURE", f"challan nature is {ch.nature!r}; C (bank challan) is usual", ref)
        bsr = ch.bsr_code
        if not (bsr.isdigit() and len(bsr) == 7):
            add(ERROR, "BSR", f"BSR code {bsr!r} must be 7 digits", ref)
        if ch.minor_head not in codes.MINOR_HEADS:
            add(WARN, "MINOR_HEAD", f"minor head {ch.minor_head!r} is not in Annexure 7", ref)
        dt = _iso(ch.challan_date)
        if not dt:
            add(ERROR, "CHALLAN_DATE", f"challan date {ch.challan_date!r} is not DD-MM-YYYY", ref)
        elif lo and not (lo <= dt <= hi):
            # A challan may be paid after the quarter closes; that is normal and not an error.
            add(INFO, "CHALLAN_OUT_OF_QUARTER",
                f"challan date {ch.challan_date} is outside the quarter", ref)
        key = (ch.bsr_code, ch.challan_date, ch.challan_serial)
        if key in seen_serial:
            add(ERROR, "CHALLAN_DUPLICATE", f"same BSR/date/serial as challan {seen_serial[key]}", ref)
        seen_serial[key] = ch.challan_serial or ch.no
        if not ch.challan_serial.strip():
            add(ERROR, "CHALLAN_SERIAL", "challan serial is blank", ref)
        if ch.total != ch.tax + ch.surcharge + ch.cess + ch.interest + ch.fee + ch.penalty:
            add(ERROR, "CHALLAN_TOTAL", "challan total does not equal the sum of its parts", ref)
        if ch.tax <= 0:
            add(WARN, "CHALLAN_TAX", "challan tax is zero or negative", ref)

    # ---- deductees -------------------------------------------------------
    by_no = {ch.no: ch for ch in st.challans}
    seen_rows = {}
    for i, row in enumerate(st.deductees, 1):
        ref = row.source_ref or f"row {i} ({row.name})"
        if row.challan_no not in by_no:
            add(ERROR, "CHALLAN_LINK", f"row points at challan {row.challan_no}, which is not in the statement", ref)
        if not PAN_RE.match(row.pan or ""):
            add(ERROR, "DEDUCTEE_PAN", f"PAN {row.pan!r} is not in the form AAAAA9999A", ref)
        elif not row.deductee_code:
            add(WARN, "DEDUCTEE_CODE",
                f"PAN {row.pan} has an unusual 4th character, so no deductee code can be derived", ref)
        if not row.name.strip():
            add(ERROR, "DEDUCTEE_NAME", "deductee name is blank", ref)
        if len(row.name) > 75:
            add(WARN, "DEDUCTEE_NAME_LEN", f"name is {len(row.name)} characters; long names get truncated by portals", ref)
        if row.section not in codes.SECTIONS:
            add(ERROR, "SECTION", f"section code {row.section!r} is not in Annexure 2", ref)
        if row.pan_status not in codes.REASON_CODES:
            add(ERROR, "REASON_CODE", f"deductee status {row.pan_status!r} is not in Annexure 6", ref)
        for label, val in (("payment date", row.payment_date), ("deduction date", row.deduction_date)):
            if not val:
                add(ERROR, "DATE_BLANK", f"{label} is blank", ref)
            elif not DATE_RE.match(val):
                add(ERROR, "DATE_FORM", f"{label} {val!r} is not DD-MM-YYYY", ref)
            else:
                iso = _iso(val)
                if lo and not (lo <= iso <= hi):
                    add(WARN, "DATE_OUT_OF_QUARTER", f"{label} {val} is outside {lo[6:8]}-{lo[4:6]}-{lo[:4]}"
                                                    f" to {hi[6:8]}-{hi[4:6]}-{hi[:4]}", ref)
        if row.deduction_date and row.payment_date and row.deduction_date < row.payment_date:
            add(INFO, "DEDUCTION_BEFORE_PAYMENT",
                f"deduction date {row.deduction_date} precedes payment date {row.payment_date}", ref)
        if row.amount_paid <= 0:
            add(WARN, "AMOUNT", "amount paid is zero or negative", ref)
        if row.tds < 0:
            add(WARN, "NEGATIVE_TDS", "negative tax; confirm this is a genuine reversal", ref)

        # rate sanity: a deviation is legitimate but always worth a look
        if codes.SECTIONS.get(row.section, {}).get("rate_pct") and row.amount_paid > 0:
            expected = (row.amount_paid * Decimal(str(codes.SECTIONS[row.section]["rate_pct"])) / Decimal(100)).quantize(Decimal("1"))
            actual = row.tds.quantize(Decimal("1"))
            if abs(expected - actual) > 1:
                add(WARN, "RATE_DEVIATION",
                    f"section {row.section} implies about {expected} on {row.amount_paid} "
                    f"but {actual} was deducted (difference {actual - expected})", ref)

        # duplicate suspicion: same PAN, amount and tax within the same statement
        dkey = (row.pan, str(row.amount_paid), str(row.tds))
        if row.pan and dkey in seen_rows:
            add(WARN, "POSSIBLE_DUPLICATE",
                f"same PAN, amount and tax as {seen_rows[dkey]}", ref)
        seen_rows[dkey] = ref

    # ---- allocation ------------------------------------------------------
    for row in st.allocation():
        ref = f"challan {row['serial']} ({row['date']})"
        if row["allocated"] != row["challan_tax"]:
            level = ERROR
            add(level, "ALLOCATION",
                f"deductee rows total {row['allocated']} against challan tax {row['challan_tax']} "
                f"(difference {row['remaining']})", ref)
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

    # interleaving and global DD serial
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

    # arithmetic tie-out
    cd_tax = {}
    for line in lines:
        parts = line.split("^")
        if len(parts) > 1 and parts[1] == "CD":
            cd_tax[parts[3]] = Decimal(parts[7] or "0")
    dd_sum: dict[str, Decimal] = {}
    open_cd = None
    for line in lines:
        parts = line.split("^")
        if len(parts) > 1 and parts[1] == "CD":
            open_cd = parts[3]
        elif len(parts) > 1 and parts[1] == "DD" and open_cd:
            dd_sum[open_cd] = dd_sum.get(open_cd, Decimal("0")) + Decimal(parts[23] or "0")
    for cd, tax in cd_tax.items():
        got = dd_sum.get(cd, Decimal("0"))
        if got != tax:
            add(ERROR, "TXT_ALLOCATION", f"CD {cd}: challan tax {tax} but DD tax totals {got}")

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
