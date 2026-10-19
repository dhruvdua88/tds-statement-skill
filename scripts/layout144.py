"""Form 144 (payments to non-residents) record layout.

Form 144 is the quarterly statement of the tax deducted on payments other than
salary made to non-residents, the form that replaced the old 27Q. Its record
shape is Form 140's: an 18-field file header, a 72-field batch header, a
30-field challan record and a 45-field deductee record, in the same order and
with the same field numbers. What changes is inside the records. Ten fields that
are "Not applicable" fillers on Form 140 carry real values here, and the section
codes come from a different Annexure 2.

Every field number below is stated once, in the ``*_FIELDS`` maps, so a format
change is a one-line edit rather than a hunt through the builder. The numbers
are taken from the official file-format workbook of the version named in
``FORMAT_VERSION`` and were confirmed against the department's own sample
statement, ``144RQ1_sample.txt`` (see ``references/form-144-layout.md``).

Three things about Form 144 catch people out, and all three are rules rather
than opinions:

* the challan record allows no fractional portion in fields 8 to 12, exactly as
  on Form 140, so the money actually deposited has to be whole rupees. Paise are
  allowed on a deductee row, where fields 20, 24 and 25 are decimal;
* the deductee record needs six figures for which the statement document has no
  field: the deductee's status, whether it has opted out of the taxation regime
  under section 202(1), the nature of the remittance, the country it is remitted
  to, whether the amount is grossed up, and whether the rate follows the Act or
  a treaty. They travel in ``meta.non_resident``, keyed by the deductee's PAN,
  and a value the document does not carry is written blank rather than guessed
  at - a wrong 'N' under grossing up is a wrong statement;
* Form 144's own Annexure 2 (code 1004 and codes 1039 to 1067) is not Form 140's
  (code 1004, 1005 to 1038 and 1058 to 1067). The two overlap only at 1004 and
  1058 to 1067. The 144 table is in ``assets/annexures_144.json``, written by
  ``extract_annexures.py --form144`` from the workbook, and lint checks a 144
  statement against it.

The official remarks, where they impose a rule, are quoted on the field they
belong to, in the same style as ``layout140.py``.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from model import ModelError, Statement, date8, money_str

FORMAT_VERSION = "1.2"
FORM = "144"
FILE_TYPE = "NS1"
FORM_LABEL = "144"

WIDTHS = {"FH": 18, "BH": 72, "CD": 30, "DD": 45}

# ---------------------------------------------------------------------------
# Field numbers
#
# FH, BH and CD below are field for field the same as Form 140's, which
# ``tests/test_layout144.py`` pins so a change to one form's shape cannot drift
# quietly away from the other's. The DD map is Form 144's own.
# ---------------------------------------------------------------------------
FH_FIELDS = {
    "line_no": 1,
    "record_type": 2,
    "file_type": 3,
    "upload_type": 4,
    "file_creation_date": 5,
    "file_sequence_no": 6,
    "uploader_type": 7,
    "tan": 8,
    "total_batches": 9,
    "utility_name": 10,
}

BH_FIELDS = {
    "line_no": 1,
    "record_type": 2,
    "batch_number": 3,
    "num_challans": 4,
    "form_number": 5,
    "token_previous": 9,
    "tan": 13,
    "pan_deductor": 15,
    "assessment_year": 16,
    "tax_year": 17,
    "period": 18,
    "name_deductor": 19,
    "addr_country": 20,
    "addr1": 21,
    "addr2": 22,
    "addr3": 23,
    "addr4": 24,
    "addr5": 25,
    "state_code": 26,
    "pin": 27,
    "deductor_email": 28,
    "deductor_country_code": 29,
    "deductor_phone": 30,
    "deductor_category": 32,
    "rp_name": 33,
    "rp_designation": 34,
    "rp_addr1": 35,
    "rp_addr2": 36,
    "rp_addr3": 37,
    "rp_addr4": 38,
    "rp_addr5": 39,
    "rp_state_code": 40,
    "rp_pin": 41,
    "rp_email": 42,
    "rp_country": 43,
    "rp_country_code": 44,
    "rp_phone": 45,
    "batch_total": 47,
    "regular_earlier": 52,
    "state_name": 54,
    "ministry_code": 57,
    "ministry_name": 58,
    "rp_pan": 59,
    "ain": 68,
    "gstin": 69,
}

CD_FIELDS = {
    "line_no": 1,
    "record_type": 2,
    "batch_number": 3,
    "challan_no": 4,
    "num_deductees": 5,
    "nil_challan": 6,
    "tax": 8,
    "interest": 9,
    "fee": 10,
    "penalty": 11,
    "total": 12,
    "challan_mode": 13,
    "bsr_code": 15,
    "challan_serial": 17,
    "challan_date": 19,
    "total_deductee_tax": 21,
    "deductee_tax": 22,
    "minor_head": 23,
    "interest_allocation": 24,
    "other_allocation": 25,
}

DD_FIELDS = {
    "line_no": 1,
    "record_type": 2,
    "batch_number": 3,
    "deductee_serial": 4,
    "challan_no": 5,
    "record_status": 6,
    "pan": 8,
    "name": 9,
    "status": 12,
    "opting_out": 14,
    "section": 15,
    "nature_of_remittance": 16,
    "country_code": 17,
    "deposited": 18,
    "payment_date": 19,
    "amount_paid": 20,
    "grossed_up": 21,
    "cash_1cr": 22,
    "cash_3cr": 23,
    "tds": 24,
    "total_tds": 25,
    "deduction_date": 27,
    "rate": 28,
    "rate_basis": 30,
    "form15ca": 31,
    "reason_code": 32,
    "certificate_no": 33,
    "address_abroad": 37,
    "email": 38,
    "phone": 39,
    "tin": 41,
}

# Where the ten Form 144-only figures in the deductee record come from. The
# model is shared with Form 140 and has no field for any of them, so they are
# read from ``meta.non_resident``, an object keyed by the deductee's PAN in
# capitals. The first six are marked mandatory in the workbook; the last four
# are mandatory only in the no-PAN cases described on fields 37 to 39 and 41.
NON_RESIDENT_KEYS = {
    "status": 12,
    "opting_out": 14,
    "nature_of_remittance": 16,
    "country_code": 17,
    "grossed_up": 21,
    "rate_basis": 30,
    "address_abroad": 37,
    "email": 38,
    "phone": 39,
    "tin": 41,
}
NON_RESIDENT_MANDATORY = (
    "status",
    "opting_out",
    "nature_of_remittance",
    "country_code",
    "grossed_up",
    "rate_basis",
)

# The remarks below are the department's, shortened. Where a remark imposes a
# rule, the rule is in lint.py as well where the form is shared with Form 140;
# the Form 144-only rules are enforced by the utility (see the FVU codes named
# in references/form-144-layout.md), because the annexures they need are 144's
# own and are not in assets/annexures.json yet.
FIELD_NOTES = {
    ("FH", 4): "Upload type: 'R' for a regular statement, 'C' for a correction.",
    ("FH", 5): "File creation date, DDMMYYYY.",
    ("FH", 10): "Name of the software that produced the file.",
    ("BH", 16): "Assessment year. The Form 144 workbook still shows the older 2008-09 example; the rule is that the assessment year is the year after the financial year, so tax year 2026-27 takes 202728.",
    ("BH", 17): "Tax year, e.g. 202627 for tax year 2026-27.",
    ("BH", 18): "Quarter: Q1, Q2, Q3 or Q4.",
    ("BH", 47): "Batch total of the deposit amounts; equals the sum of CD field 12. Paisa must be 00.",
    ("BH", 52): "'Y' only if a regular statement for this form was already filed for an earlier period.",
    ("BH", 54): "State code per Annexure 5. Required only for the State Government deductor types (S, E, H, N); for every other type it must be blank.",
    ("BH", 57): "Ministry code per Annexure 3. Required for Central Government types (A, D, G).",
    ("BH", 58): "Ministry name in words, required only when the ministry code is 99 (Other).",
    ("BH", 68): "AIN of the PAO/TO/CDDO, required only for a government deductor paying by book adjustment.",
    ("CD", 6): "'N' always, except on a nil statement where nothing was deposited, when it is 'Y'.",
    ("CD", 8): "Income tax component of the deposit. The format allows no fractional portion here.",
    ("CD", 12): "Total deposited. Equals fields 8+9+10+11, must have no fractional portion, and must be at least the tax, interest, other and fee allocated to this challan.",
    ("CD", 13): "'C' when the tax went through a bank challan, 'B' for a transfer voucher. Required when any deductee on the challan uses section 1059 or 1061, and blank on a nil statement.",
    ("CD", 21): "Deposit per the deductee rows: the sum of DD field 25 over the rows charged to this challan.",
    ("CD", 22): "Deduction per the deductee rows: the sum of DD field 24 over the rows charged to this challan.",
    ("CD", 24): "Interest allocation: the interest on this challan (field 9). Integer values only.",
    ("CD", 25): "Other allocation: the penalty or other amount on this challan (field 11), not the fee. Integer values only, so it is written with .00.",
    ("DD", 4): "Deductee serial number. Runs across the whole statement 1..n, and the utility requires each row to be higher than the one before it (T-FV-4125).",
    ("DD", 5): "Challan reference: the serial number of the challan record this row is charged to, the same number as CD field 4.",
    ("DD", 6): "'O', the only value the format allows.",
    ("DD", 8): "Deductee PAN. A text placeholder is allowed in place of a real PAN - PANAPPLIED, PANINVALID or PANNOTAVBL - except on section 1059 or 1061 rows, where the tax was paid before the winnings were released and a real PAN is required.",
    ("DD", 12): "Status of the deductee as per Annexure 8: 1 company, 2 individual, 3 HUF, 4 AOP, 5 AOP of companies only, 6 co-operative society, 7 firm, 8 body of individuals, 9 artificial juridical person, 10 others. Mandatory on every row.",
    ("DD", 14): "Whether the deductee is opting out of the taxation regime under section 202(1). The workbook says only 'Value should be Y/N (Yes or No)'. What section 202(1) covers could not be established from the material available here, so the value is written from the document as given and no meaning is read into it.",
    ("DD", 15): "Section code as per Annexure 2. Form 144's Annexure 2 is its own list (code 1004 and codes 1039 to 1067), which overlaps Form 140's only at 1004 and 1058 to 1067.",
    ("DD", 16): "Nature of remittance as per Annexure 9: 27 interest, 16 and 73 dividend, 21 and 74 fees for technical services, 49 and 75 royalty, 66 to 72 capital gains, 28 investment income, 99 other income. The workbook says: 'Mandatory to mention values for sections present under Annexure 9. For all other sections, no value should be specified.'",
    ("DD", 17): "Country to which the remittance is made, the three-digit code from Annexure 10. Mandatory on every row (T-FV-6425).",
    ("DD", 18): "'Y' or 'N': has the tax deducted on this row been deposited? The department's own sample leaves it blank although the workbook marks it mandatory; this toolkit writes it.",
    ("DD", 19): "Date paid or credited. The remark requires it to fall inside the quarter and the financial year the statement covers.",
    ("DD", 21): "Whether the amount paid or credited is grossed up as per section 393(10), that is, whether the deductor bore the tax. Y or N; mandatory on every row (T-FV-6429).",
    ("DD", 24): "Tax deducted on this row. Two decimals are allowed here, unlike on the challan record. Zero when the section is 1059 or 1061.",
    ("DD", 25): "Tax deposited for this row: the tax in field 24 plus any surcharge and cess. The workbook's remark on this field is a copy of the CD field 25 remark and speaks of the fee allocation, which cannot apply to a deductee row; the resolution is Form 140's, where field 25 carries the row's own deposited tax.",
    ("DD", 27): "Date of deduction. Required when the tax deducted is more than zero, and never earlier than the first day of the quarter.",
    ("DD", 28): "Rate of deduction, four decimals ('10.0000'). Mandatory on Form 144 (T-FV-4093); zero when nothing was deducted.",
    ("DD", 30): "Whether the rate follows the Income-tax Act, 2025 ('A') or a double taxation agreement ('B').",
    ("DD", 31): "Unique acknowledgement number of the corresponding Form 15CA, 26 characters. The field name is Form 144's; the remark on it still speaks of Form No. 121, the Form 140 field this one replaced. It is written from the row's form121 attribute because the document model is shared between the two forms.",
    ("DD", 32): "Reason flag from Form 144's Annexure 6. On this form nearly every section code accepts A (a lower or nil deduction certificate under section 395(1) or 395(2)) and C (deduction at a higher rate under section 397(2) for want of a PAN), with G, H, I, N, O, Y and Z reserved for particular codes. Blank when none applies.",
    ("DD", 33): "Certificate number under section 395(1) or 395(2). Required when field 32 is 'A' (T-FV-6454); 10 or 15 alphanumeric characters.",
    ("DD", 37): "Address of the deductee in its country of residence. The workbook makes it mandatory only when the rate is below 20%, the reason flag is 'C', the deductee's PAN is a placeholder, and the nature of remittance is 16, 27, 49, 21, 52 or 31. A value given when the nature of remittance is not one of those is rejected (T-FV-4342); the workbook names no other list.",
    ("DD", 38): "Email of the deductee abroad, 75 characters, checked for @ and . with a character either side, at least one . after the @, and no '^' or space. Mandatory under the same conditions as field 37, and rejected for any other nature of remittance (T-FV-4340).",
    ("DD", 39): "Contact number of the deductee abroad, digits only, up to 15. The first two sentences of the remark are the deductor's contact number copied from the batch header and do not apply here; the mandatory conditions are those of field 37, and a value is rejected for any other nature of remittance (T-FV-4341).",
    ("DD", 41): "Tax Identification Number of the deductee, or a unique number by which the deductee is identified by the government of the country it claims residence in, 25 characters. Mandatory under the same conditions as fields 37 to 39 (T-FV-4337, T-FV-4338, T-FV-4343). The remark points at 'field no. 36' and 'Annexure 8', which are slips for field 16 and Annexure 9.",
}


class Context:
    """Everything a record needs that is not in the row itself."""

    def __init__(self, st: Statement, file_creation_date: str | None = None,
                 utility_name: str | None = None):
        self.st = st
        # Reproducibility matters: a statement rebuilt from the same document must
        # produce the same bytes, so the creation date can be pinned in the document.
        self.file_creation_date = (
            file_creation_date
            or str(st.meta.get("file_creation_date", "") or "")
            or date.today().strftime("%d%m%Y")
        )
        self.utility_name = utility_name or st.meta.get("utility_name") or "TDS Statement 1.0"
        self.non_resident = _non_resident_index(st)

    @property
    def batch_number(self) -> str:
        return "1"


def _non_resident_index(st: Statement) -> dict[str, dict]:
    """Read ``meta.non_resident``, keyed by deductee PAN.

    A malformed block is refused rather than ignored: silently dropping a
    country code or a status would produce a file that looks complete and is
    rejected at upload, which is the failure this whole toolkit exists to
    prevent.
    """
    raw = st.meta.get("non_resident")
    if raw in (None, ""):
        return {}
    if not isinstance(raw, dict):
        raise ModelError(
            "meta.non_resident must be an object keyed by deductee PAN; got "
            f"{type(raw).__name__}"
        )
    out: dict[str, dict] = {}
    for pan, block in raw.items():
        if not isinstance(block, dict):
            raise ModelError(
                f"meta.non_resident[{pan!r}] must be an object of Form 144 fields; got "
                f"{type(block).__name__}"
            )
        known = [k for k in block if k not in NON_RESIDENT_KEYS]
        if known:
            raise ModelError(
                f"meta.non_resident[{pan!r}] has keys that are not Form 144 fields: "
                f"{', '.join(sorted(known))}"
            )
        out[str(pan).strip().upper()] = dict(block)
    return out


def _extra(ctx: Context, row, key: str) -> str:
    """One Form 144-only figure, or blank when the document does not carry it.

    Nothing is defaulted. The model defaults a few of its own fields (the
    deposit indicator, for one), but a missing grossing-up answer or a missing
    nature of remittance has to surface as a blank field for the utility to
    report, not as a plausible-looking guess.
    """
    block = ctx.non_resident.get((row.pan or "").strip().upper())
    if not block:
        return ""
    value = block.get(key)
    if value in (None, ""):
        return ""
    return str(value).strip()


def _flag(value: str) -> str:
    """A one-character Y/N or A/B field, written as the form wants it."""
    return (value or "").strip().upper()[:1]


def _rate(value: str) -> str:
    """Rates are written with four decimals; the utility compares them as text."""
    if value in (None, ""):
        return ""
    s = str(value).strip().replace("%", "")
    try:
        return f"{Decimal(s):.4f}"
    except Exception:
        return str(value)


def build_fh(ctx: Context) -> dict:
    st = ctx.st
    return {
        FH_FIELDS["record_type"]: "FH",
        FH_FIELDS["file_type"]: FILE_TYPE,
        FH_FIELDS["upload_type"]: st.upload_type,
        FH_FIELDS["file_creation_date"]: ctx.file_creation_date,
        FH_FIELDS["file_sequence_no"]: "1",
        FH_FIELDS["uploader_type"]: str(st.meta.get("uploader_type", "D") or "D"),
        FH_FIELDS["tan"]: st.tan,
        FH_FIELDS["total_batches"]: "1",
        FH_FIELDS["utility_name"]: ctx.utility_name,
    }


def build_bh(ctx: Context) -> dict:
    st = ctx.st
    ded = st.deductor
    rp = st.responsible_person
    addr = ded.get("address")
    raddr = rp.get("address")
    batch_total = sum((c.total for c in st.challans), Decimal("0.00"))
    return {
        BH_FIELDS["record_type"]: "BH",
        BH_FIELDS["batch_number"]: ctx.batch_number,
        BH_FIELDS["num_challans"]: str(len(st.challans)),
        BH_FIELDS["form_number"]: FORM_LABEL,
        BH_FIELDS["tan"]: st.tan,
        BH_FIELDS["pan_deductor"]: str(ded.get("pan", "") or ""),
        BH_FIELDS["assessment_year"]: st.assessment_year,
        BH_FIELDS["tax_year"]: st.tax_year,
        BH_FIELDS["period"]: st.quarter.upper(),
        BH_FIELDS["name_deductor"]: str(ded.get("name", "") or ""),
        BH_FIELDS["addr_country"]: str(getattr(addr, "country", "") or ""),
        BH_FIELDS["addr1"]: str(getattr(addr, "line1", "") or ""),
        BH_FIELDS["addr2"]: str(getattr(addr, "line2", "") or ""),
        BH_FIELDS["addr3"]: str(getattr(addr, "line3", "") or ""),
        BH_FIELDS["addr4"]: str(getattr(addr, "line4", "") or ""),
        BH_FIELDS["addr5"]: str(getattr(addr, "line5", "") or ""),
        BH_FIELDS["state_code"]: str(getattr(addr, "state_code", "") or ""),
        BH_FIELDS["pin"]: str(getattr(addr, "pin", "") or ""),
        BH_FIELDS["deductor_email"]: str(ded.get("email", "") or ""),
        BH_FIELDS["deductor_country_code"]: str(ded.get("country_code", "") or ""),
        BH_FIELDS["deductor_phone"]: str(ded.get("phone", "") or ""),
        BH_FIELDS["deductor_category"]: str(ded.get("category", "") or ""),
        BH_FIELDS["rp_name"]: str(rp.get("name", "") or ""),
        BH_FIELDS["rp_designation"]: str(rp.get("designation", "") or ""),
        BH_FIELDS["rp_addr1"]: str(getattr(raddr, "line1", "") or ""),
        BH_FIELDS["rp_addr2"]: str(getattr(raddr, "line2", "") or ""),
        BH_FIELDS["rp_addr3"]: str(getattr(raddr, "line3", "") or ""),
        BH_FIELDS["rp_addr4"]: str(getattr(raddr, "line4", "") or ""),
        BH_FIELDS["rp_addr5"]: str(getattr(raddr, "line5", "") or ""),
        BH_FIELDS["rp_state_code"]: str(getattr(raddr, "state_code", "") or ""),
        BH_FIELDS["rp_pin"]: str(getattr(raddr, "pin", "") or ""),
        BH_FIELDS["rp_email"]: str(rp.get("email", "") or ""),
        BH_FIELDS["rp_country"]: str(getattr(raddr, "country", "") or ""),
        BH_FIELDS["rp_country_code"]: str(rp.get("country_code", "") or ""),
        BH_FIELDS["rp_phone"]: str(rp.get("phone", "") or ""),
        BH_FIELDS["batch_total"]: money_str(batch_total),
        BH_FIELDS["regular_earlier"]: str(ded.get("regular_earlier", "N") or "N").upper()[:1],
        BH_FIELDS["token_previous"]: str(ded.get("token_previous", "") or ""),
        BH_FIELDS["state_name"]: str(ded.get("state_name", "") or ""),
        BH_FIELDS["ministry_code"]: str(ded.get("ministry_code", "") or ""),
        BH_FIELDS["ministry_name"]: str(ded.get("ministry_name", "") or ""),
        BH_FIELDS["rp_pan"]: str(rp.get("pan", "") or ""),
        BH_FIELDS["ain"]: str(ded.get("ain", "") or ""),
        BH_FIELDS["gstin"]: str(ded.get("gstin", "") or ""),
    }


def build_cd(ctx: Context, ch, rows, index: int) -> dict:
    total_tds = sum((r.total_tds for r in rows), Decimal("0.00"))
    tds = sum((r.tds for r in rows), Decimal("0.00"))
    nil = "Y" if str(getattr(ch, "nil_challan", "N") or "N").upper()[:1] == "Y" else "N"
    mode = "" if nil == "Y" else (ch.nature or "C")
    return {
        CD_FIELDS["record_type"]: "CD",
        CD_FIELDS["batch_number"]: ctx.batch_number,
        CD_FIELDS["challan_no"]: str(index),
        CD_FIELDS["num_deductees"]: str(len(rows)),
        CD_FIELDS["nil_challan"]: nil,
        CD_FIELDS["tax"]: money_str(ch.all_tax),
        CD_FIELDS["interest"]: money_str(ch.interest),
        CD_FIELDS["fee"]: money_str(ch.fee),
        CD_FIELDS["penalty"]: money_str(ch.penalty),
        CD_FIELDS["total"]: money_str(ch.total),
        CD_FIELDS["challan_mode"]: mode,
        CD_FIELDS["bsr_code"]: ch.bsr_code,
        CD_FIELDS["challan_serial"]: ch.challan_serial,
        CD_FIELDS["challan_date"]: date8(ch.challan_date) if ch.challan_date else "",
        CD_FIELDS["total_deductee_tax"]: money_str(total_tds),
        CD_FIELDS["deductee_tax"]: money_str(tds),
        CD_FIELDS["minor_head"]: ch.minor_head,
        CD_FIELDS["interest_allocation"]: money_str(ch.interest),
        # Field 11 only. The official remark says to repeat field 11 here, and
        # the fee (field 10) is checked separately in the deposit test, so
        # adding it in as well would count it twice.
        CD_FIELDS["other_allocation"]: money_str(ch.penalty),
    }


def build_dd(ctx: Context, row, serial: int, challan_index: int) -> dict:
    return {
        DD_FIELDS["record_type"]: "DD",
        DD_FIELDS["batch_number"]: ctx.batch_number,
        DD_FIELDS["deductee_serial"]: str(serial),
        DD_FIELDS["challan_no"]: str(challan_index),
        DD_FIELDS["record_status"]: "O",
        DD_FIELDS["pan"]: row.pan,
        DD_FIELDS["name"]: row.name,
        DD_FIELDS["status"]: _extra(ctx, row, "status"),
        DD_FIELDS["opting_out"]: _flag(_extra(ctx, row, "opting_out")),
        DD_FIELDS["section"]: row.section,
        DD_FIELDS["nature_of_remittance"]: _extra(ctx, row, "nature_of_remittance"),
        DD_FIELDS["country_code"]: _extra(ctx, row, "country_code"),
        DD_FIELDS["deposited"]: row.deposited,
        DD_FIELDS["payment_date"]: date8(row.payment_date) if row.payment_date else "",
        DD_FIELDS["amount_paid"]: money_str(row.amount_paid),
        DD_FIELDS["grossed_up"]: _flag(_extra(ctx, row, "grossed_up")),
        DD_FIELDS["cash_1cr"]: money_str(row.cash_withdrawal_1cr) if row.cash_withdrawal_1cr else "",
        DD_FIELDS["cash_3cr"]: money_str(row.cash_withdrawal_3cr) if row.cash_withdrawal_3cr else "",
        DD_FIELDS["tds"]: money_str(row.tds),
        DD_FIELDS["total_tds"]: money_str(row.total_tds),
        DD_FIELDS["deduction_date"]: date8(row.deduction_date) if row.deduction_date else "",
        DD_FIELDS["rate"]: _rate(row.rate),
        DD_FIELDS["rate_basis"]: _flag(_extra(ctx, row, "rate_basis")),
        DD_FIELDS["form15ca"]: row.form121,
        DD_FIELDS["reason_code"]: row.reason_code,
        DD_FIELDS["certificate_no"]: row.certificate_no,
        DD_FIELDS["address_abroad"]: _extra(ctx, row, "address_abroad"),
        DD_FIELDS["email"]: _extra(ctx, row, "email"),
        DD_FIELDS["phone"]: _extra(ctx, row, "phone"),
        DD_FIELDS["tin"]: _extra(ctx, row, "tin"),
    }


def field_table(record: str) -> list[dict]:
    """For documentation and the ``fields`` command."""
    maps = {"FH": FH_FIELDS, "BH": BH_FIELDS, "CD": CD_FIELDS, "DD": DD_FIELDS}
    out = []
    for name, no in sorted(maps[record].items(), key=lambda kv: kv[1]):
        if name in ("line_no", "record_type"):
            continue
        out.append({"field": no, "name": name, "note": FIELD_NOTES.get((record, no), "")})
    return out
