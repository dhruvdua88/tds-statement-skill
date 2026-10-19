"""Data contract for a TDS/TCS quarterly statement.

Everything in this pipeline reads and writes one JSON document. The TXT
builder, the linter, the Excel working paper and the packaging step all work
off this file, so the JSON is the single source of truth for a filing.

Why a separate contract instead of going straight from the client's sheet to
the TXT: the department's file format has no room for commentary. Almost all
of the real work in a TDS filing is deciding what each row means, which
challan it belongs to, and what to do with the rows that do not fit. Carrying
those decisions in a reviewable document means a reviewer can approve the
statement without reading Python, and a correction three months later starts
from the same record.

Money is held as Decimal, never float. Dates are held as ISO-like
``DD-MM-YYYY`` strings so they cannot be silently re-ordered by a spreadsheet,
and are converted to ``DDMMYYYY`` only when a record is written.

Run ``python3 scripts/tds.py schema`` for the full annotated schema.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

SCHEMA_ID = "tds-statement/1"

PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
TAN_RE = re.compile(r"^[A-Z]{4}[0-9]{5}[A-Z]$")
GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z]$")
DATE_RE = re.compile(r"^(\d{2})-(\d{2})-(\d{4})$")

# Deductee code is the 4th character of the PAN (Annexure 4).
PAN_4TH = {
    "A": "A",  # Association of persons
    "B": "B",  # Body of individuals
    "C": "C",  # Company
    "F": "F",  # Firm / LLP
    "G": "G",  # Government
    "H": "H",  # Hindu undivided family
    "J": "J",  # Artificial juridical person
    "L": "L",  # Local authority
    "P": "P",  # Individual
    "T": "T",  # Trust
}

# Deductor category (Annexure 4).
DEDUCTOR_CATEGORIES = {
    "A": "Association of persons",
    "B": "Body of individuals",
    "C": "Company (other than government)",
    "F": "Firm / LLP",
    "G": "Government",
    "H": "Hindu undivided family",
    "J": "Artificial juridical person",
    "K": "Company (deductor category K)",
    "L": "Local authority",
    "P": "Individual",
    "T": "Trust",
}


class ModelError(ValueError):
    """Raised when the document cannot be used at all."""


def d(value, what: str = "amount") -> Decimal:
    """Parse a money value strictly. Blank is zero; anything unparseable is an error.

    Silently coercing a bad amount to zero is the single easiest way to file a
    wrong statement, so this refuses instead.
    """
    if value is None or value == "":
        return Decimal("0.00")
    if isinstance(value, Decimal):
        return value.quantize(Decimal("0.01"))
    try:
        return Decimal(str(value).replace(",", "").replace("₹", "").strip()).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as exc:
        raise ModelError(f"{what}: cannot read {value!r} as an amount") from exc


def norm_date(value, what: str = "date") -> str:
    """Normalise to DD-MM-YYYY. Accepts date/datetime, ddmmyyyy, yyyy-mm-dd, dd/mm/yyyy."""
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        return value.strftime("%d-%m-%Y")
    if isinstance(value, date):
        return value.strftime("%d-%m-%Y")
    s = str(value).strip()
    if DATE_RE.match(s):
        return s
    iso = re.match(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$", s)
    if iso:
        y, m, dd = iso.groups()
        return f"{int(dd):02d}-{int(m):02d}-{y}"
    digits = re.sub(r"\D", "", s)
    if len(digits) == 8:
        # Try ddmmyyyy first, then yyyymmdd when the first four digits look like a year.
        if 1900 <= int(digits[:4]) <= 2100 and int(digits[2:4]) <= 12 and int(digits[4:6]) <= 31:
            return f"{digits[6:8]}-{digits[4:6]}-{digits[:4]}"
        if int(digits[2:4]) <= 12 and int(digits[0:2]) <= 31:
            return f"{digits[0:2]}-{digits[2:4]}-{digits[4:8]}"
    raise ModelError(f"{what}: cannot read {value!r} as a date (expected DD-MM-YYYY)")


def date8(value: str) -> str:
    """DD-MM-YYYY -> DDMMYYYY for the file records."""
    m = DATE_RE.match(value or "")
    if not m:
        raise ModelError(f"not a DD-MM-YYYY date: {value!r}")
    return m.group(1) + m.group(2) + m.group(3)


def parse_date8(value: str) -> date:
    return datetime.strptime(value, "%d%m%Y").date()


def money_str(value) -> str:
    return f"{d(value):.2f}"


@dataclass
class Address:
    line1: str = ""
    line2: str = ""
    line3: str = ""
    line4: str = ""
    line5: str = ""
    state_code: str = ""
    pin: str = ""
    country: str = "INDIA"

    @classmethod
    def from_dict(cls, raw: dict | None) -> "Address":
        raw = raw or {}
        return cls(
            line1=str(raw.get("line1", "") or ""),
            line2=str(raw.get("line2", "") or ""),
            line3=str(raw.get("line3", "") or ""),
            line4=str(raw.get("line4", "") or ""),
            line5=str(raw.get("line5", "") or ""),
            state_code=str(raw.get("state_code", "") or ""),
            pin=str(raw.get("pin", "") or ""),
            country=str(raw.get("country", "INDIA") or "INDIA"),
        )

    def to_dict(self) -> dict:
        return {
            "line1": self.line1, "line2": self.line2, "line3": self.line3,
            "line4": self.line4, "line5": self.line5,
            "state_code": self.state_code, "pin": self.pin, "country": self.country,
        }


@dataclass
class Challan:
    no: int
    bsr_code: str
    challan_date: str
    challan_serial: str
    tax: Decimal
    surcharge: Decimal = Decimal("0.00")
    cess: Decimal = Decimal("0.00")
    interest: Decimal = Decimal("0.00")
    fee: Decimal = Decimal("0.00")
    penalty: Decimal = Decimal("0.00")
    total: Decimal = Decimal("0.00")
    minor_head: str = "200"
    nature: str = "C"
    tds_section: str = ""
    remarks: str = ""

    @property
    def all_tax(self) -> Decimal:
        return self.tax + self.surcharge + self.cess

    @classmethod
    def from_dict(cls, raw: dict) -> "Challan":
        total = raw.get("total")
        ch = cls(
            no=int(raw["no"]),
            bsr_code=str(raw.get("bsr_code", "")),
            challan_date=norm_date(raw.get("challan_date"), "challan date"),
            challan_serial=str(raw.get("challan_serial", "")),
            tax=d(raw.get("tax"), "challan tax"),
            surcharge=d(raw.get("surcharge"), "challan surcharge"),
            cess=d(raw.get("cess"), "challan cess"),
            interest=d(raw.get("interest"), "challan interest"),
            fee=d(raw.get("fee"), "challan fee"),
            penalty=d(raw.get("penalty"), "challan penalty"),
            minor_head=str(raw.get("minor_head", "200") or "200"),
            nature=str(raw.get("nature", "C") or "C"),
            tds_section=str(raw.get("tds_section", "") or ""),
            remarks=str(raw.get("remarks", "") or ""),
        )
        computed = ch.all_tax + ch.interest + ch.fee + ch.penalty
        ch.total = d(total, "challan total") if total not in (None, "") else computed
        return ch

    def to_dict(self) -> dict:
        return {
            "no": self.no, "bsr_code": self.bsr_code,
            "challan_date": self.challan_date, "challan_serial": self.challan_serial,
            "minor_head": self.minor_head, "nature": self.nature,
            "tax": money_str(self.tax), "surcharge": money_str(self.surcharge),
            "cess": money_str(self.cess), "interest": money_str(self.interest),
            "fee": money_str(self.fee), "penalty": money_str(self.penalty),
            "total": money_str(self.total), "tds_section": self.tds_section,
            "remarks": self.remarks,
        }


@dataclass
class Deductee:
    challan_no: int
    pan: str
    name: str
    section: str
    payment_date: str
    deduction_date: str
    amount_paid: Decimal
    tds: Decimal
    rate: str = ""
    surcharge: Decimal = Decimal("0.00")
    cess: Decimal = Decimal("0.00")
    pan_status: str = "Y"
    certificate_no: str = ""
    remarks: str = ""
    source_ref: str = ""
    # Salary-only fields, kept optional so one model serves both forms.
    salary_income: Decimal | None = None
    total_income: Decimal | None = None
    net_tax: Decimal | None = None

    @property
    def total_tds(self) -> Decimal:
        return self.tds + self.surcharge + self.cess

    @property
    def deductee_code(self) -> str:
        ch = (self.pan or "")[3:4].upper()
        return PAN_4TH.get(ch, "")

    @classmethod
    def from_dict(cls, raw: dict) -> "Deductee":
        row = cls(
            challan_no=int(raw["challan_no"]),
            pan=str(raw.get("pan", "") or "").strip().upper(),
            name=str(raw.get("name", "") or "").strip(),
            section=str(raw.get("section", "") or "").strip(),
            payment_date=norm_date(raw.get("payment_date"), "payment date"),
            deduction_date=norm_date(raw.get("deduction_date"), "deduction date"),
            amount_paid=d(raw.get("amount_paid"), "amount paid"),
            tds=d(raw.get("tds"), "tds"),
            rate=str(raw.get("rate", "") or ""),
            surcharge=d(raw.get("surcharge"), "deductee surcharge"),
            cess=d(raw.get("cess"), "deductee cess"),
            pan_status=str(raw.get("pan_status", "Y") or "Y").strip().upper(),
            certificate_no=str(raw.get("certificate_no", "") or ""),
            remarks=str(raw.get("remarks", "") or ""),
            source_ref=str(raw.get("source_ref", "") or ""),
        )
        for key in ("salary_income", "total_income", "net_tax"):
            if raw.get(key) not in (None, ""):
                setattr(row, key, d(raw[key], key))
        return row

    def to_dict(self) -> dict:
        out = {
            "challan_no": self.challan_no, "pan": self.pan, "name": self.name,
            "section": self.section, "payment_date": self.payment_date,
            "deduction_date": self.deduction_date,
            "amount_paid": money_str(self.amount_paid), "tds": money_str(self.tds),
            "surcharge": money_str(self.surcharge), "cess": money_str(self.cess),
            "rate": self.rate, "pan_status": self.pan_status,
            "certificate_no": self.certificate_no, "remarks": self.remarks,
            "source_ref": self.source_ref,
        }
        for key in ("salary_income", "total_income", "net_tax"):
            val = getattr(self, key)
            if val is not None:
                out[key] = money_str(val)
        return out


@dataclass
class Statement:
    form: str = "140"
    upload_type: str = "R"
    financial_year: str = ""
    quarter: str = ""
    deductor: dict = field(default_factory=dict)
    responsible_person: dict = field(default_factory=dict)
    challans: list[Challan] = field(default_factory=list)
    deductees: list[Deductee] = field(default_factory=list)
    flags: list[dict] = field(default_factory=list)
    pending: list[dict] = field(default_factory=list)
    meta: dict = field(default_factory=dict)
    correction: dict = field(default_factory=dict)

    # ---- derived ----------------------------------------------------------
    @property
    def tan(self) -> str:
        return str(self.deductor.get("tan", "") or "")

    @property
    def tax_year(self) -> str:
        """2026-27 -> 202627."""
        fy = self.financial_year or ""
        if not re.match(r"^\d{4}-\d{2}$", fy):
            return ""
        start, end = fy.split("-")
        return f"{start}{end}"

    @property
    def assessment_year(self) -> str:
        """Financial year 2026-27 -> assessment year 202728.

        The assessment year is the year after the financial year. The previous
        version of this derived it from the tax year, which is one digit out:
        tax year 202627 means 2026-27, so the assessment year is 2027-28.
        """
        fy = self.financial_year or ""
        if not re.match(r"^\d{4}-\d{2}$", fy):
            return ""
        start, end = fy.split("-")
        try:
            return f"{int(start) + 1}{int(end) + 1}"
        except ValueError:
            return ""

    @property
    def totals(self) -> dict:
        tax = sum((c.tax for c in self.challans), Decimal("0.00"))
        surcharge = sum((c.surcharge for c in self.challans), Decimal("0.00"))
        cess = sum((c.cess for c in self.challans), Decimal("0.00"))
        interest = sum((c.interest for c in self.challans), Decimal("0.00"))
        fee = sum((c.fee for c in self.challans), Decimal("0.00"))
        penalty = sum((c.penalty for c in self.challans), Decimal("0.00"))
        deposit = sum((c.total for c in self.challans), Decimal("0.00"))
        dd_tds = sum((r.total_tds for r in self.deductees), Decimal("0.00"))
        return {
            "tax": tax, "surcharge": surcharge, "cess": cess, "interest": interest,
            "fee": fee, "penalty": penalty, "deposit": deposit,
            "deductee_tds": dd_tds, "variance": deposit - dd_tds,
            "challans": len(self.challans), "rows": len(self.deductees),
        }

    def allocation(self) -> list[dict]:
        """Per-challan allocation with the remaining balance, which is the check
        that catches almost every real reconciliation failure."""
        out = []
        for ch in self.challans:
            rows = [r for r in self.deductees if r.challan_no == ch.no]
            allocated = sum((r.tds for r in rows), Decimal("0.00"))
            out.append({
                "no": ch.no, "serial": ch.challan_serial, "date": ch.challan_date,
                "deposited": ch.total, "challan_tax": ch.tax,
                "allocated": allocated, "remaining": ch.tax - allocated,
                "rows": len(rows),
            })
        return out

    # ---- io ---------------------------------------------------------------
    @classmethod
    def from_dict(cls, raw: dict) -> "Statement":
        if raw.get("schema") not in (None, SCHEMA_ID):
            raise ModelError(f"unexpected schema {raw.get('schema')!r}")
        st = cls(
            form=str(raw.get("form", "140")),
            upload_type=str(raw.get("upload_type", "R") or "R"),
            financial_year=str(raw.get("financial_year", "") or ""),
            quarter=str(raw.get("quarter", "") or ""),
            deductor=dict(raw.get("deductor", {}) or {}),
            responsible_person=dict(raw.get("responsible_person", {}) or {}),
            flags=list(raw.get("flags", []) or []),
            pending=list(raw.get("pending", []) or []),
            meta=dict(raw.get("meta", {}) or {}),
            correction=dict(raw.get("correction", {}) or {}),
        )
        st.deductor["address"] = Address.from_dict(st.deductor.get("address"))
        st.responsible_person["address"] = Address.from_dict(st.responsible_person.get("address"))
        st.challans = [Challan.from_dict(c) for c in raw.get("challans", [])]
        st.deductees = [Deductee.from_dict(r) for r in raw.get("deductees", [])]
        return st

    def to_dict(self) -> dict:
        deductor = dict(self.deductor)
        deductor["address"] = (deductor.get("address") or Address()).to_dict()
        rp = dict(self.responsible_person)
        rp["address"] = (rp.get("address") or Address()).to_dict()
        return {
            "schema": SCHEMA_ID,
            "form": self.form,
            "upload_type": self.upload_type,
            "financial_year": self.financial_year,
            "quarter": self.quarter,
            "correction": self.correction,
            "deductor": deductor,
            "responsible_person": rp,
            "challans": [c.to_dict() for c in self.challans],
            "deductees": [r.to_dict() for r in self.deductees],
            "flags": self.flags,
            "pending": self.pending,
            "meta": self.meta,
        }

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "Statement":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    # ---- readiness --------------------------------------------------------
    @property
    def blocking_pending(self) -> list[dict]:
        return [p for p in self.pending if p.get("blocking", True)]

    @property
    def is_draft(self) -> bool:
        return bool(self.blocking_pending)

    @property
    def draft_reason(self) -> str:
        items = self.blocking_pending
        if not items:
            return ""
        return "; ".join(str(i.get("field", "")) for i in items)


SCHEMA_HELP = """\
tds-statement/1 - one JSON document per filing

form                 "140" (resident non-salary) or "138" (salary)
upload_type          "R" original/regular, "C" correction
financial_year       "2026-27"   -> tax_year 202627, assessment_year 202728
quarter              "Q1".."Q4"
correction           {"original_token": "...", "correction_type": "..."} when upload_type is C

deductor             tan, pan, name, category (Annexure 4), address{},
                     email, std_code, phone, gstin
responsible_person   name, designation, pan, address{}, email, phone

challans[]           no, bsr_code, challan_date, challan_serial, tax,
                     surcharge, cess, interest, fee, penalty, total,
                     minor_head, nature, tds_section
deductees[]          challan_no, pan, name, section, payment_date,
                     deduction_date, amount_paid, tds, surcharge, cess,
                     rate, pan_status, certificate_no, remarks, source_ref
                     salary form only: salary_income, total_income, net_tax

flags[]              {"level": "warn|error", "code": "...", "message": "...", "rows": [...]}
pending[]            {"field": "...", "why": "...", "owner": "client|us", "blocking": true}

Dates are DD-MM-YYYY. Amounts are strings or numbers, normalised to 2 dp.
"""
