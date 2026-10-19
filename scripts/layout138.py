"""Form 138 (salary) record layout.

Every field number below is stated once, in the ``*_FIELDS`` maps, so a format
change is a one-line edit rather than a hunt through the builder. The numbers
are taken from the official file-format workbook for Form 138 - 24Q, Q1 to Q3,
published 22-Jul-2026 (the published file is named version 1.2 while the sheet's
own title still says 1.1, the same mismatch the Form 140 workbook has), sheet
``File Format_R``. The DD map was cross-checked against the department's own
accepted sample ``138RQ1_sample.txt`` and the record widths against both
workbooks.

Four differences from Form 140 drive the code:

* there is no rate field. DD field 28 is "Remarks 11 (for future use)", declared
  not applicable, and the utility scopes the rate rule to forms 140, 143 and 144
  (T-FV-4093), so nothing is written there;
* the two tax figures on a deductee row are one figure. DD field 24 ("Total Tax
  Deducted") and field 25 ("Total Tax Deposited") each carry tax, surcharge and
  cess merged, because the workbook's remarks require the two fields to be
  equal. Legacy Form 24Q spread the same money over fields 14, 15 and 16;
* DD field 29 ("Date of deposit") carries the date of the challan the row is
  paid under, in ddmmyyyy, the same value as CD field 19: T-FV-6489 requires the
  two to be equal. The workbook types field 29 as DECIMAL size 7, which is a
  workbook defect rather than an invitation to write a number, and the
  department's own sample writes a date;
* the cash-withdrawal fields are gone. DD fields 22 and 23 are "Remarks 9" and
  "Remarks 10" on this form, declared not applicable, and T-FV-6434 and
  T-FV-6436 reject a value there on a 138.

CD fields 21 and 22 are the sums of the two DD tax columns. Since those columns
hold the same figure on this form, both challan fields end up as the sum of the
rows' merged tax, which is also what ``lint.txt_issues`` demands of the written
file.

Quarter 4 is deliberately not implemented. A Q4 statement must also carry the
salary-detail records of Annexure II and their children, and the department has
not published the Form 138 Q4 workbook: the Q1 to Q3 workbook in hand says so on
its face, and ``layout_24q_q4.json`` in the research tree is the legacy,
pre-2025-Act 24Q table that cannot be mapped without guessing. Rather than write
a Q4 file the utility will reject, ``Context`` refuses a Q4 build and says why,
citing T-FV-2133. The same reasoning is written up in
``references/form-138-layout.md``.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from build_txt import BuildError
from model import Statement, date8, money_str

FORMAT_VERSION = "1.2"
FORM = "138"
FILE_TYPE = "SL1"
FORM_LABEL = "138"

WIDTHS = {"FH": 18, "BH": 72, "CD": 30, "DD": 45}

# ---------------------------------------------------------------------------
# Field numbers
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

# BH field numbers are the same as Form 140's throughout; only the wording of
# the remarks differs. Fields 48, 49 and 50 are declared not applicable on this
# form (the salary-detail count belongs to Q4), so they are not mapped and stay
# blank.
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
    "section": 15,
    "deposited": 18,
    "payment_date": 19,
    "amount_paid": 20,
    "tds": 24,
    "total_tds": 25,
    "deduction_date": 27,
    "deposit_date": 29,
    "reason_code": 32,
    "certificate_no": 33,
}

# The remarks below are the department's, shortened. Where a remark imposes a
# rule, the rule is in lint.py as well; this is the explanation a reviewer reads.
FIELD_NOTES = {
    ("FH", 3): "File type: 'SL1' for Form 138. The utility rejects an SL1 file whose batch header does not say 138 (T-FV-2100).",
    ("FH", 4): "Upload type: 'R' for a regular statement, 'C' for a correction.",
    ("FH", 5): "File creation date, DDMMYYYY.",
    ("FH", 10): "Name of the software that produced the file.",
    ("BH", 5): "Form number; must be 138, and must agree with the SL1 file type.",
    ("BH", 16): "Assessment year, e.g. 202728 for tax year 2026-27. Never less than 202728.",
    ("BH", 17): "Tax year, e.g. 202627 for tax year 2026-27.",
    ("BH", 18): "Quarter: Q1, Q2 or Q3. Q4 is not written by this builder (see the module docstring).",
    ("BH", 47): "Batch total of the deposit amounts; equals the sum of CD field 12. Paisa must be 00.",
    ("BH", 52): "'Y' only if a regular statement for this form was already filed for an earlier period.",
    ("BH", 54): "State code per Annexure 5. Required only for the State Government deductor types (S, E, H, N); for every other type it must be blank.",
    ("BH", 57): "Ministry code per Annexure 3. Required for Central Government types (A, D, G).",
    ("BH", 58): "Ministry name in words, required only when the ministry code is 99 (Other).",
    ("BH", 68): "AIN of the PAO/TO/CDDO, required only for a government deductor paying by book adjustment.",
    ("CD", 6): "'N' always, except on a nil statement where nothing was deposited, when it is 'Y'.",
    ("CD", 8): "Income tax component of the deposit. The format allows no fractional portion here.",
    ("CD", 12): "Total deposited. Equals fields 8+9+10+11, must have no fractional portion, and must be at least the tax, interest, other and fee allocated to this challan.",
    ("CD", 13): "'C' when the tax went through a bank challan, 'B' for a book adjustment. Blank on a nil statement.",
    ("CD", 21): "Sum of the deposit column of the underlying deductee rows (DD field 25), which on this form is also the deducted figure. Decimal, so paise are allowed.",
    ("CD", 22): "Sum of the deducted column of the same rows (DD field 24); the workbook requires this to equal field 21.",
    ("CD", 24): "Interest allocation: the interest on this challan (field 9). Integer values only.",
    ("CD", 25): "Other allocation: the penalty/other amount on this challan (field 11), not the fee. Integer values only, so it is written with .00.",
    ("DD", 4): "Deductee serial number. Runs across the whole statement 1..n and must strictly increase (T-FV-4125).",
    ("DD", 5): "Challan reference: the challan's serial number within the batch.",
    ("DD", 6): "'O', the only value the format allows.",
    ("DD", 8): "Employee PAN. A text placeholder is allowed in place of a real PAN - PANAPPLIED, PANINVALID or PANNOTAVBL.",
    ("DD", 15): "Section code from Annexure 2's salary rows. This toolkit writes 1002 (employee other than a Government employee); 1001, 1003 and 1032 are also valid on the form but intake does not produce them yet.",
    ("DD", 18): "'Y' or 'N': has the tax deducted on this row been deposited?",
    ("DD", 19): "Date paid or credited. Must fall inside the quarter and financial year of the statement.",
    ("DD", 24): "Total tax deducted: tax, surcharge and cess as one figure, because the workbook requires this field to equal field 25.",
    ("DD", 25): "Total tax deposited; the workbook requires it to equal field 24, so the same figure is written in both.",
    ("DD", 27): "Date of deduction. Required when the tax deducted is more than zero, and never earlier than the first day of the quarter.",
    ("DD", 29): "Date of deposit, ddmmyyyy. T-FV-6489 requires it to equal the challan's date (CD field 19), so that is what is written; the workbook's DECIMAL type here is a defect.",
    ("DD", 32): "Reason flag from Annexure 6; blank when none applies. On this form only A and C are valid (T-FV-6444).",
    ("DD", 33): "Certificate number under section 395(1), 10 or 15 alphanumeric characters. Required when field 32 is 'A'.",
}


class Context:
    """Everything a record needs that is not in the row itself."""

    def __init__(self, st: Statement, file_creation_date: str | None = None,
                 utility_name: str | None = None):
        self.st = st
        # Quarter 4 also needs the salary-detail (Annexure II) records, and the
        # department has not published the Form 138 Q4 file format: the workbook
        # in hand covers Q1 to Q3 and says so on its face. Writing a Q4 file
        # without the SD records trips T-FV-2133, so the build stops here with an
        # explanation instead of producing a file the utility will reject.
        if (st.quarter or "").strip().upper() == "Q4":
            raise BuildError(
                "Form 138 Q4: the quarter also needs the salary-detail (Annexure II) "
                "records, and the department has not published the Form 138 Q4 file "
                "format (the workbook in hand covers Q1 to Q3 only; T-FV-2133 makes an "
                "SD record mandatory in Q4). This builder refuses Q4 rather than write "
                "a file the utility will reject."
            )
        # Reproducibility matters: a statement rebuilt from the same document must
        # produce the same bytes, so the creation date can be pinned in the document.
        self.file_creation_date = (
            file_creation_date
            or str(st.meta.get("file_creation_date", "") or "")
            or date.today().strftime("%d%m%Y")
        )
        self.utility_name = utility_name or st.meta.get("utility_name") or "TDS Statement 1.0"

    @property
    def batch_number(self) -> str:
        return "1"


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
    merged_tds = sum((r.total_tds for r in rows), Decimal("0.00"))
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
        # Both sums are the same figure: on this form DD fields 24 and 25 carry
        # the merged tax, so the deducted and deposited columns agree by design.
        CD_FIELDS["total_deductee_tax"]: money_str(merged_tds),
        CD_FIELDS["deductee_tax"]: money_str(merged_tds),
        CD_FIELDS["minor_head"]: ch.minor_head,
        CD_FIELDS["interest_allocation"]: money_str(ch.interest),
        # Field 11 only. The official remark says to repeat field 11 here, and
        # the fee (field 10) is checked separately in the deposit test, so
        # adding it in as well would count it twice.
        CD_FIELDS["other_allocation"]: money_str(ch.penalty),
    }


def build_dd(ctx: Context, row, serial: int, challan_index: int) -> dict:
    # DD field 29 carries the challan's own date (CD field 19): T-FV-6489
    # requires the two to be equal, by value, as dates.
    challan = next((c for c in ctx.st.challans if c.no == row.challan_no), None)
    deposit_date = date8(challan.challan_date) if challan and challan.challan_date else ""
    merged_tds = money_str(row.total_tds)
    return {
        DD_FIELDS["record_type"]: "DD",
        DD_FIELDS["batch_number"]: ctx.batch_number,
        DD_FIELDS["deductee_serial"]: str(serial),
        DD_FIELDS["challan_no"]: str(challan_index),
        DD_FIELDS["record_status"]: "O",
        DD_FIELDS["pan"]: row.pan,
        DD_FIELDS["name"]: row.name,
        DD_FIELDS["section"]: row.section,
        DD_FIELDS["deposited"]: row.deposited,
        DD_FIELDS["payment_date"]: date8(row.payment_date) if row.payment_date else "",
        DD_FIELDS["amount_paid"]: money_str(row.amount_paid),
        # Fields 24 and 25 both carry tax + surcharge + cess: the workbook's
        # remarks require the two to be equal, and legacy 24Q's three separate
        # money fields (14, 15, 16) map onto this one figure.
        DD_FIELDS["tds"]: merged_tds,
        DD_FIELDS["total_tds"]: merged_tds,
        DD_FIELDS["deduction_date"]: date8(row.deduction_date) if row.deduction_date else "",
        DD_FIELDS["deposit_date"]: deposit_date,
        DD_FIELDS["reason_code"]: row.reason_code,
        DD_FIELDS["certificate_no"]: row.certificate_no,
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
