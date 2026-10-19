"""Turn whatever the client sent into a statement document.

Nobody sends a clean table. What arrives is a monthly sheet with merged
headers, a total row in the middle, amounts formatted as text, a section column
that says "Professional Fees - Sec 393(1) Tbl 6(iii).D(b)" instead of a code,
and challans either in a column or in a separate tab. This module reads that,
maps it onto the statement fields, and says plainly what it could not map.

The design rule is that intake never guesses silently. Every row it takes gets
a source reference back to the cell it came from, every inference is recorded,
and anything it cannot map is listed with the row number so a person can look
at that row. A statement with three flagged rows is useful. A statement that
quietly dropped three rows is a filing risk.

Confidence scoring is intentionally simple: each field has a list of header
synonyms; a column scores by how many synonyms it matches and how specific the
match is. Ambiguity is reported rather than resolved by preference order.
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from model import Address, Challan, Deductee, Statement, check_form, d, norm_date

# ---------------------------------------------------------------------------
# Header vocabulary. Order matters only for readability; scoring is by match.
# ---------------------------------------------------------------------------
SYNONYMS: dict[str, list[str]] = {
    "name": ["deductee", "deductee name", "name of deductee", "party", "party name",
             "vendor", "vendor name", "payee", "payee name", "beneficiary", "name"],
    "pan": ["pan", "pan no", "pan number", "deductee pan", "pan of deductee", "party pan"],
    "section": ["section", "nature", "nature of payment", "section code", "tds section",
                "section under which", "payment code", "description"],
    "amount": ["amount", "amount paid", "gross", "gross amount", "taxable value",
               "invoice value", "payment", "paid", "bill amount", "base amount"],
    "tds": ["tds", "tax", "tds amount", "tax deducted", "tds deducted", "deduction",
            "tds rs", "tax amount", "amount deducted"],
    "rate": ["rate", "tds rate", "rate %", "rate of tds", "percentage"],
    "payment_date": ["payment date", "date of payment", "paid on", "invoice date",
                     "bill date", "date", "credit date", "date of credit"],
    "deduction_date": ["deduction date", "date of deduction", "tds date", "deducted on"],
    "challan": ["challan", "challan no", "challan number", "challan serial",
                "bank challan", "challan sr", "cin", "challan ref"],
    "bsr": ["bsr", "bsr code", "bsr no"],
    "challan_date": ["challan date", "date of deposit", "deposit date", "paid date"],
    "challan_tax": ["challan amount", "amount deposited", "deposit amount", "challan tax"],
    "month": ["month", "period", "month/year", "tds month"],
    "remarks": ["remark", "remarks", "comment", "comments", "note", "notes"],
}

# Section text -> 4-digit return section code. Longest phrase first so that
# "professional" does not win over "professional fees - technical".
SECTION_HINTS: list[tuple[str, str]] = [
    ("purchase of goods", "1031"), ("goods", "1031"), ("194q", "1031"),
    ("professional", "1027"), ("profession", "1027"), ("194j(a)", "1027"),
    ("technical", "1026"), ("royalty", "1026"), ("194j(b)", "1026"),
    ("commission", "1006"), ("brokerage", "1006"), ("194h", "1006"),
    ("rent", "1009"), ("194i", "1009"),
    ("contractor", "1023"), ("contract", "1023"), ("194c", "1023"),
    ("salary", "1002"), ("192", "1002"),
]

DATE_HEADER_RE = re.compile(
    r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s\-/,]*(\d{2,4})", re.I)

TOTAL_WORDS = {"total", "grand total", "totals", "sum", "sub total", "subtotal"}


@dataclass
class Column:
    index: int
    header: str
    field: str = ""
    score: float = 0.0

    def as_dict(self) -> dict:
        return {"index": self.index, "header": self.header, "field": self.field, "score": round(self.score, 2)}


@dataclass
class SheetReport:
    sheet: str
    header_row: int
    columns: list[Column] = field(default_factory=list)
    rows_read: int = 0
    rows_kept: int = 0
    rows_skipped: list[dict] = field(default_factory=list)
    month_context: str = ""

    def as_dict(self) -> dict:
        return {
            "sheet": self.sheet, "header_row": self.header_row,
            "columns": [c.as_dict() for c in self.columns],
            "rows_read": self.rows_read, "rows_kept": self.rows_kept,
            "rows_skipped": self.rows_skipped, "month_context": self.month_context,
        }


def normalise(text) -> str:
    s = str(text or "").lower()
    s = re.sub(r"[^a-z0-9%/\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def match_field(header: str) -> tuple[str, float]:
    """Best field for a header, with a score. Exact synonym beats a substring."""
    h = normalise(header)
    if not h:
        return "", 0.0
    best, best_score = "", 0.0
    for fld, syns in SYNONYMS.items():
        for syn in syns:
            if h == syn:
                score = 3.0
            elif h.startswith(syn + " ") or h.endswith(" " + syn):
                score = 2.2
            elif syn in h:
                score = 1.5
            else:
                continue
            # longer synonyms are more specific
            score += min(len(syn) / 40.0, 0.6)
            if score > best_score:
                best, best_score = fld, score
    return best, best_score


# ---------------------------------------------------------------------------
# Reading sources
# ---------------------------------------------------------------------------
def read_tables(path: str | Path) -> dict[str, list[list]]:
    """Return {sheet_name: rows} for xlsx/xlsm/csv/tsv. Values are raw cells."""
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix in (".xlsx", ".xlsm", ".xltx"):
        from openpyxl import load_workbook
        wb = load_workbook(p, read_only=True, data_only=True)
        tables = {}
        for ws in wb.worksheets:
            rows = [list(r) for r in ws.iter_rows(values_only=True)]
            tables[ws.title] = rows
        wb.close()
        return tables
    if suffix in (".csv", ".tsv", ".txt"):
        delim = "\t" if suffix in (".tsv", ".txt") else ","
        with p.open(newline="", encoding="utf-8-sig", errors="replace") as fh:
            sample = fh.read(4096)
            fh.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
                delim = dialect.delimiter
            except Exception:
                pass
            return {p.stem: [list(r) for r in csv.reader(fh, delimiter=delim)]}
    raise ValueError(f"unsupported source type {suffix!r} (use xlsx, xlsm, csv or tsv)")


def find_header(rows: list[list], limit: int = 40) -> tuple[int, int]:
    """Best (row_index, score) for a header row. Skips title and blank rows."""
    best_i, best_score = -1, 0.0
    for i, row in enumerate(rows[:limit]):
        cells = [c for c in row if str(c or "").strip()]
        if len(cells) < 3:
            continue
        score = 0.0
        for c in cells:
            fld, sc = match_field(c)
            if fld:
                score += sc
        # a header row has several recognisable labels and little numeric content
        numeric = sum(1 for c in cells if isinstance(c, (int, float)))
        score -= numeric * 0.5
        if score > best_score:
            best_i, best_score = i, score
    return best_i, best_score


def month_context(rows: list[list], header_row: int) -> str:
    """Pick up a 'July 2026' style marker from the rows above the header."""
    for row in reversed(rows[: max(header_row, 0)]):
        for cell in row:
            if isinstance(cell, datetime):
                return cell.strftime("%B %Y")
            if isinstance(cell, str):
                m = DATE_HEADER_RE.search(cell)
                if m and len(cell) < 40 and not re.search(r"\d{1,2}[/-]\d{1,2}", cell):
                    return cell.strip()
    return ""


def cell_date(value) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, datetime):
        return value.strftime("%d-%m-%Y")
    if isinstance(value, date):
        return value.strftime("%d-%m-%Y")
    return norm_date(value)


def cell_money(value) -> Decimal:
    if value in (None, ""):
        return Decimal("0.00")
    if isinstance(value, (int, float, Decimal)):
        return d(value)
    s = str(value).strip()
    # Tally style: "1,23,456.00 Dr" / "₹ 45,000" / "(45,000)" negative
    neg = s.startswith("(") and s.endswith(")")
    s = re.sub(r"[₹,\s]|dr\b|cr\b", "", s, flags=re.I)
    s = s.strip("()")
    if not s:
        return Decimal("0.00")
    try:
        v = Decimal(s)
    except InvalidOperation:
        return Decimal("0.00")
    return (-v if neg else v).quantize(Decimal("0.01"))


def cell_section(value) -> str:
    s = str(value or "").strip()
    if re.fullmatch(r"\d{4}", s):
        return s
    low = s.lower()
    for needle, code in SECTION_HINTS:
        if needle in low:
            return code
    m = re.search(r"\b(1\d{3})\b", s)
    return m.group(1) if m else ""


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------
def extract_rows(rows: list[list], header_row: int, columns: list[Column],
                 sheet: str, month_ctx: str) -> tuple[list[dict], list[dict], int]:
    by_field = {c.field: c.index for c in columns if c.field}
    out, skipped = [], []
    read = 0
    blank_run = 0
    for offset, row in enumerate(rows[header_row + 1:], start=header_row + 2):
        read += 1
        cells = [c for c in row if str(c or "").strip()]
        if not cells:
            blank_run += 1
            if blank_run >= 5:
                break
            continue
        blank_run = 0
        first = normalise(row[0] if row else "")
        if first in TOTAL_WORDS or any(t == first for t in TOTAL_WORDS):
            continue

        def get(fld):
            idx = by_field.get(fld)
            return row[idx] if idx is not None and idx < len(row) else None

        name = str(get("name") or "").strip()
        pan = re.sub(r"[^A-Za-z0-9]", "", str(get("pan") or "")).upper()
        amount = cell_money(get("amount"))
        tds = cell_money(get("tds"))

        if not name and not pan:
            if amount or tds:
                skipped.append({"row": offset, "reason": "amount without a deductee name or PAN",
                                "preview": [str(c) for c in row[:8] if c not in (None, "")]})
            continue
        if not pan:
            skipped.append({"row": offset, "reason": "no PAN in the row", "preview": [name]})
        if not amount and not tds:
            skipped.append({"row": offset, "reason": "row has no amount and no TDS", "preview": [name]})
            continue

        rec = {
            "source_ref": f"{sheet}!{offset}",
            "name": name,
            "pan": pan,
            "section": cell_section(get("section")),
            "amount_paid": str(amount),
            "tds": str(tds),
            "rate": str(get("rate") or "").strip(),
            "payment_date": cell_date(get("payment_date")),
            "deduction_date": cell_date(get("deduction_date")),
            "challan_serial": str(get("challan") or "").strip(),
            "remarks": str(get("remarks") or "").strip(),
            "month_context": month_ctx,
        }
        if not rec["payment_date"]:
            rec["payment_date"] = cell_date(get("month")) or ""
        if not rec["deduction_date"]:
            rec["deduction_date"] = rec["payment_date"]
        out.append(rec)
    return out, skipped, read


IDENTITY_LABELS = {
    "tan": ["tan", "tan no", "tan of deductor"],
    "pan": ["pan", "pan of deductor", "deductor pan"],
    "gstin": ["gstin", "gst no", "gstin of deductor"],
    "phone": ["phone", "telephone", "mobile", "contact no", "contact number"],
    "email": ["email", "e-mail", "email id"],
    "name": ["deductor", "deductor name", "name of deductor", "company name", "name of the company"],
    "designation": ["designation"],
    "rp_name": ["person responsible", "responsible person", "name of the person responsible"],
}


def _clean_ident(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip(" :-\t")


def scan_identity(tables: dict[str, list[list]], header_rows: dict[str, int] | None = None) -> tuple[dict, list[str]]:
    """Find the deductor's own details in the source, if they are there at all.

    Title blocks often carry the TAN and the company name even when nobody
    filled a header field. Reading them saves a round trip with the client; not
    finding them is equally important, because then the statement is a draft and
    the pipeline says which values it is waiting for.

    Only the rows above the table header are searched for a company name or a
    phone number. A deductee list is full of company names and phone numbers,
    and taking one of those as the deductor is worse than finding nothing.
    """
    header_rows = header_rows or {}
    found: dict[str, str] = {}
    notes: list[str] = []
    tan_re = re.compile(r"\b[A-Z]{4}[0-9]{5}[A-Z]\b")
    pan_re = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
    gstin_re = re.compile(r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z]\b")
    email_re = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
    company_re = re.compile(r"\b(private limited|pvt\.? ltd|limited|llp)\b", re.I)

    for sheet, rows in tables.items():
        head = header_rows.get(sheet, 25)
        preamble = rows[:head] if head > 0 else rows[:1]
        for row in preamble:
            cells = [_clean_ident(c) for c in row if str(c or "").strip()]
            for i, cell in enumerate(cells):
                following = cells[i + 1] if i + 1 < len(cells) else ""
                low = normalise(cell)
                for key, labels in IDENTITY_LABELS.items():
                    if key in found:
                        continue
                    if any(low == lab or low.startswith(lab) for lab in labels) and following:
                        candidate = following
                        if key == "tan" and not tan_re.fullmatch(candidate.upper()):
                            continue
                        if key == "pan" and not pan_re.fullmatch(candidate.upper()):
                            continue
                        found[key] = candidate
                        notes.append(f"{sheet}: {key} read as {candidate!r}")
            joined = " ".join(cells)
            if "tan" not in found:
                m = tan_re.search(joined.upper())
                if m:
                    found["tan"] = m.group(0)
                    notes.append(f"{sheet}: TAN found in a title row")
            if "gstin" not in found:
                m = gstin_re.search(joined.upper())
                if m:
                    found["gstin"] = m.group(0)
                    notes.append(f"{sheet}: GSTIN found in a title row")
            if "email" not in found:
                m = email_re.search(joined)
                if m:
                    found["email"] = m.group(0)
            if "phone" not in found:
                m = re.search(r"\b(?:\+91[\s-]?)?([6-9]\d{9})\b", joined)
                if m:
                    found["phone"] = m.group(1)
            if "name" not in found:
                for cell in cells:
                    if company_re.search(cell) and len(cell) < 80 and not pan_re.search(cell.upper()):
                        found["name"] = cell
                        notes.append(f"{sheet}: name read as {cell!r}")
                        break
    return found, notes


def looks_like_challan_sheet(rows: list[list]) -> bool:
    idx, score = find_header(rows, limit=25)
    if idx < 0:
        return False
    fields = {match_field(c)[0] for c in rows[idx] if c not in (None, "")}
    return {"bsr", "challan", "challan_tax"} <= fields or (
        "challan" in fields and "challan_date" in fields and "challan_tax" in fields
    )


def extract_challans(rows: list[list], header_row: int, columns: list[Column]) -> list[dict]:
    by_field = {c.field: c.index for c in columns if c.field}
    out = []
    for offset, row in enumerate(rows[header_row + 1:], start=header_row + 2):
        if not any(str(c or "").strip() for c in row):
            continue

        def get(fld):
            idx = by_field.get(fld)
            return row[idx] if idx is not None and idx < len(row) else None

        serial = re.sub(r"\D", "", str(get("challan") or ""))
        tax = cell_money(get("challan_tax"))
        if not serial or not tax:
            continue
        out.append({
            "challan_serial": serial,
            "bsr_code": re.sub(r"\D", "", str(get("bsr") or "")),
            "challan_date": cell_date(get("challan_date")),
            "tax": str(tax),
            "source_ref": f"row {offset}",
        })
    return out


# ---------------------------------------------------------------------------
# Mapping report
# ---------------------------------------------------------------------------
def write_mapping_report(path: str | Path, sheets: list[SheetReport], challans: list[dict],
                         pending: list[dict], unmapped: dict[str, list[str]]) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    head_font = Font(bold=True, color="FFFFFF")
    head_fill = PatternFill("solid", fgColor="1F3864")
    warn_fill = PatternFill("solid", fgColor="FFF2CC")

    ws = wb.active
    ws.title = "Read me"
    lines = [
        ("What this is", "The intake step read your source files and mapped them onto the statement fields."),
        ("How to use it", "Check the Mapping tab column by column, then the Skipped rows tab. Every skipped row is a row that is NOT in the statement."),
        ("Colour", "Yellow means the intake was not confident, or a value needs a human decision."),
        ("Next step", "Fix the mapping with --map field=header, or correct the source, then run intake again."),
    ]
    for i, (k, v) in enumerate(lines, start=1):
        ws.cell(row=i, column=1, value=k).font = Font(bold=True)
        ws.cell(row=i, column=2, value=v)
    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 110

    ws = wb.create_sheet("Mapping")
    headers = ["Sheet", "Header row", "Column", "Header text", "Mapped to", "Score", "Note"]
    ws.append(headers)
    for c in ws[1]:
        c.font, c.fill = head_font, head_fill
    for rep in sheets:
        for col in rep.columns:
            note = ""
            if not col.field:
                note = "not used"
            elif col.score < 2.0:
                note = "low confidence - check"
            ws.append([rep.sheet, rep.header_row, get_column_letter(col.index + 1),
                       col.header, col.field or "", col.score, note])
            if note.startswith("low"):
                for c in ws[ws.max_row]:
                    c.fill = warn_fill
    for i, w in enumerate([22, 10, 8, 42, 18, 7, 26], start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"

    ws = wb.create_sheet("Skipped rows")
    ws.append(["Sheet", "Row", "Reason", "Preview"])
    for c in ws[1]:
        c.font, c.fill = head_font, head_fill
    for rep in sheets:
        for sk in rep.rows_skipped:
            ws.append([rep.sheet, sk["row"], sk["reason"], " | ".join(sk.get("preview", []))])
            for c in ws[ws.max_row]:
                c.fill = warn_fill
    for i, w in enumerate([22, 8, 46, 70], start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws = wb.create_sheet("Challans found")
    ws.append(["Serial", "BSR", "Date", "Tax", "Source"])
    for c in ws[1]:
        c.font, c.fill = head_font, head_fill
    for ch in challans:
        ws.append([ch["challan_serial"], ch["bsr_code"], ch["challan_date"], ch["tax"], ch.get("source_ref", "")])
    for i, w in enumerate([16, 14, 14, 16, 14], start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws = wb.create_sheet("Unmapped columns")
    ws.append(["Sheet", "Header"])
    for c in ws[1]:
        c.font, c.fill = head_font, head_fill
    for sheet, hdrs in unmapped.items():
        for h in hdrs:
            ws.append([sheet, h])
    ws.column_dimensions["A"].width = 24
    ws.column_dimensions["B"].width = 50

    ws = wb.create_sheet("Pending")
    ws.append(["Field", "Why", "Owner", "Blocking"])
    for c in ws[1]:
        c.font, c.fill = head_font, head_fill
    for p in pending:
        ws.append([p.get("field"), p.get("why"), p.get("owner", ""), p.get("blocking", True)])

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def intake(sources: list[str], form: str = "140", financial_year: str = "",
           quarter: str = "", overrides: dict[str, str] | None = None,
           report: str | None = None) -> tuple[Statement, dict]:
    check_form(form)
    overrides = overrides or {}
    st = Statement(form=form, financial_year=financial_year, quarter=quarter)
    sheets: list[SheetReport] = []
    all_rows: list[dict] = []
    challan_rows: list[dict] = []
    unmapped: dict[str, list[str]] = {}
    all_tables: dict[str, list[list]] = {}
    header_rows: dict[str, int] = {}

    for src in sources:
        tables = read_tables(src)
        all_tables.update(tables)
        for name, rows in tables.items():
            if not rows:
                continue
            hdr, score = find_header(rows)
            if hdr < 0 or score < 2.0:
                continue
            header_rows[name] = hdr
            columns = []
            for i, cell in enumerate(rows[hdr]):
                fld, sc = match_field(cell)
                if str(cell or "").strip() in overrides:
                    fld, sc = overrides[str(cell).strip()], 3.0
                columns.append(Column(i, str(cell or "").strip(), fld, sc))
            rep = SheetReport(name, hdr, columns, month_context=month_context(rows, hdr))

            if looks_like_challan_sheet(rows):
                challan_rows.extend(extract_challans(rows, hdr, columns))
                sheets.append(rep)
                continue

            recs, skipped, read = extract_rows(rows, hdr, columns, name, rep.month_context)
            rep.rows_read, rep.rows_kept, rep.rows_skipped = read, len(recs), skipped
            all_rows.extend(recs)
            unmapped[name] = [c.header for c in columns if c.header and not c.field]
            sheets.append(rep)

    # ---- challans --------------------------------------------------------
    by_serial = {}
    for ch in challan_rows:
        ch.setdefault("no", len(by_serial) + 1)
        by_serial[ch["challan_serial"]] = ch

    if not by_serial:
        # Derive challans from the rows themselves: distinct challan serials,
        # with the tax taken as the sum of the rows linked to each.
        derived: dict[str, Decimal] = {}
        for r in all_rows:
            key = r["challan_serial"] or ""
            derived[key] = derived.get(key, Decimal("0.00")) + d(r["tds"])
        for i, (serial, tax) in enumerate(sorted(derived.items()), start=1):
            by_serial[serial] = {
                "no": i, "challan_serial": serial, "bsr_code": "", "challan_date": "",
                "tax": str(tax), "source_ref": "derived from deductible rows",
            }

    for serial, ch in by_serial.items():
        st.challans.append(Challan.from_dict({
            "no": ch["no"], "bsr_code": ch.get("bsr_code", ""),
            "challan_date": ch.get("challan_date", ""), "challan_serial": serial,
            "tax": ch.get("tax", "0"), "interest": ch.get("interest", "0"),
            "total": ch.get("total") or None,
        }))

    ch_by_serial = {c.challan_serial: c for c in st.challans}
    for rec in all_rows:
        ch = ch_by_serial.get(rec["challan_serial"])
        row = Deductee.from_dict({
            "challan_no": ch.no if ch else 0,
            "pan": rec["pan"], "name": rec["name"], "section": rec["section"],
            "payment_date": rec["payment_date"], "deduction_date": rec["deduction_date"],
            "amount_paid": rec["amount_paid"], "tds": rec["tds"], "rate": rec["rate"],
            "remarks": rec["remarks"], "source_ref": rec["source_ref"],
        })
        st.deductees.append(row)

    # rows with no challan match are a blocking pending item, not a silent drop
    orphans = [r for r in st.deductees if r.challan_no == 0]
    pending = []
    if orphans:
        pending.append({
            "field": "challan allocation",
            "why": f"{len(orphans)} deductee rows are not linked to a challan",
            "owner": "us", "blocking": True,
        })

    # The salary statement carries only the four salary codes of its Annexure 2.
    # Anything else is a mapping mistake; 1002 (employees other than Government
    # employees) is by far the usual one, so the row is set to it and says so.
    if form == "138":
        from codes import SALARY_SECTIONS
        for row in st.deductees:
            if row.section not in SALARY_SECTIONS:
                row.section = "1002"
                row.rate = ""
                row.remarks = (row.remarks + " section forced to 1002 for the salary form").strip()

    # ---- deductor identity ------------------------------------------------
    found, notes = scan_identity(all_tables, header_rows)
    ded = st.deductor
    for key in ("tan", "pan", "name", "gstin", "email", "phone"):
        if found.get(key) and not ded.get(key):
            ded[key] = found[key]
    rp = st.responsible_person
    if found.get("rp_name"):
        rp["name"] = found["rp_name"]
    if found.get("designation"):
        rp["designation"] = found["designation"]

    # Everything the statement needs but the source did not provide becomes a
    # named, blocking pending item. This is what makes the file a draft.
    missing = [
        ("deductor.tan", "TAN of the deductor", "client"),
        ("deductor.pan", "PAN of the deductor", "client"),
        ("deductor.name", "legal name of the deductor", "client"),
        ("deductor.phone", "deductor contact number", "client"),
        ("responsible_person.name", "name of the person responsible", "client"),
        ("responsible_person.pan", "PAN of the person responsible", "client"),
        ("responsible_person.phone", "contact number of the person responsible", "client"),
        ("deductor.address", "address to print in the statement", "client"),
        ("responsible_person.address", "address of the person responsible", "client"),
    ]
    for path, label, owner in missing:
        node = st
        parts = path.split(".")
        for part in parts[:-1]:
            node = getattr(node, part)
        value = node.get(parts[-1]) if isinstance(node, dict) else None
        if not value:
            pending.append({"field": path, "why": label, "owner": owner, "blocking": True})

    st.deductor = ded
    st.responsible_person = rp
    st.pending = pending
    st.flags = [{"level": "info", "code": "INTAKE",
                 "message": f"{len(st.deductees)} deductee rows and {len(st.challans)} challans read "
                            f"from {len(sources)} file(s)",
                 "rows": []}]
    for note in notes:
        st.flags.append({"level": "info", "code": "INTAKE_IDENTITY", "message": note, "rows": []})

    summary = {
        "sources": sources,
        "sheets": [s.as_dict() for s in sheets],
        "deductees": len(st.deductees),
        "challans": len(st.challans),
        "skipped": sum(len(s.rows_skipped) for s in sheets),
        "unmapped": unmapped,
        "pending": pending,
    }
    if report:
        write_mapping_report(report, sheets, list(by_serial.values()), pending, unmapped)
    return st, summary
