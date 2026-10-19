"""Correction statements (Form 140): only the records that changed, in the C3 or C5 shape.

The record layout is the department's correction file format, "Form Number
140-26Q - Q1 to Q4_04082026_correction.xlsx" (version 1.2, published on the
Protean e-TDS correction download page; sheet ``File Format_R``). It carries the
same four records as the regular statement, 18/72/30/45 fields, but each field
has a separate remark per correction type, and most of the work is knowing
which fields a type fills and which it must leave blank. The sets below are
read off the C3 and C5 columns of that workbook.

Two types are written, which between them cover the common corrections:

* **C3**, deductee and challan details. A deductee record is either added
  (mode "A", serial continuing after the last one filed) or updated (mode "U",
  keeping its filed serial, with the filed PAN and tax repeated in the
  verification fields 7, 26 and 42). Moving a row to another challan is an
  update under that challan's record. A challan whose own figures changed is
  written with the challan updation indicator (CD 7) set to 1.
* **C5**, PAN update only, chosen automatically when the PAN is the only thing
  that changed.

What is deliberately not here:

* C1 and C2 with the batch updation indicator set (deductor details). A change
  to the deductor or the responsible person is refused rather than half-written.
* C9 (adding a challan), which the format allows only for government deductors.
* Deleting a deductee, which the format does not allow at all.
* Reading the TRACES consolidated (``.tds``) file. Its layout for the new forms
  is not published; the correction format refers to it ("field no. 6 of
  consolidated file") but no workbook describes it, so it cannot be read without
  guessing. The starting point is the statement document as it was filed, which
  is what the remarks call "the regular or last correction statement".
* The consolidated file hash (FH 18). The utility requires it on a correction
  (T-FV-1037) and the workbook gives no remark for it, so it is taken from
  ``correction.consolidated_hash`` exactly as supplied. While it is blank the
  file is a draft.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import layout140
from model import ModelError, Statement, date8, money_str

FORMAT_FILE = "Form Number 140-26Q - Q1 to Q4_04082026_correction.xlsx"
FORMAT_VERSION = "1.2"
WIDTHS = {"FH": 18, "BH": 72, "CD": 30, "DD": 45}

# Fields each type writes, per record, with the batch updation indicator at 0.
# Read off the C3 and C5 remark columns: a field outside these sets is "No
# value should be specified" for that type, or applies only when the batch
# updation indicator is 1, which this module never sets.
BH_WRITES = {
    "C3": {3, 4, 5, 6, 7, 8, 9, 12, 13, 16, 17, 18, 19, 26, 32, 47, 59, 69},
    "C5": {3, 4, 5, 6, 8, 9, 12, 16, 17, 18, 19, 26, 32, 59, 69},
}
# CD 8-11 and 23 are written only when the challan updation indicator is 1.
CD_WRITES = {
    "C3": {3, 4, 5, 6, 7, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 24, 25},
    "C5": {3, 4, 5, 6, 13, 14, 16, 18, 20},
}
CD_WRITES_WHEN_UPDATED = {8, 9, 10, 11, 23}
# DD 7, 26 and 42 are the verification values, written for mode "U" only.
DD_WRITES = {
    "C3": {3, 4, 5, 6, 8, 9, 15, 18, 19, 20, 22, 23, 24, 25, 27, 28, 31, 32, 33},
    "C5": {3, 4, 5, 8, 26, 42},
}
DD_VERIFY_WHEN_UPDATED = {7, 26, 42}

CHALLAN_KEYS = ("bsr_code", "challan_date", "challan_serial", "tax", "surcharge", "cess",
                "interest", "fee", "penalty", "total", "minor_head", "nature")
ROW_IGNORED = ("remarks", "source_ref")


class CorrectionError(ModelError):
    pass


def _row_key(row) -> dict:
    out = row.to_dict()
    for k in ROW_IGNORED:
        out.pop(k, None)
    return out


def _challan_key(ch) -> dict:
    d = ch.to_dict()
    return {k: d[k] for k in CHALLAN_KEYS}


def _serials(st: Statement) -> tuple[dict[int, int], dict[int, int]]:
    """Filed numbering: list index of a row -> its DD serial, challan no -> CD serial.

    The regular builder writes challans in order and each challan's rows in
    list order, numbering the rows across the statement, so that is the
    numbering the filed statement carries.
    """
    row_serial, cd_serial = {}, {}
    serial = 0
    for idx, ch in enumerate(st.challans, 1):
        cd_serial[ch.no] = idx
        for i, r in enumerate(st.deductees):
            if r.challan_no == ch.no:
                serial += 1
                row_serial[i] = serial
    return row_serial, cd_serial


def diff(original: Statement, corrected: Statement) -> dict:
    """What changed, or a plain refusal when the change is not one this module writes."""
    if original.form != "140" or corrected.form != "140":
        raise CorrectionError(f"Form {corrected.form} correction layout not yet added")
    for key in ("financial_year", "quarter"):
        if getattr(original, key) != getattr(corrected, key):
            raise CorrectionError(f"{key} cannot change in a correction; it is a verification key")
    if original.tan != corrected.tan:
        raise CorrectionError("the TAN cannot change in a correction")
    for part in ("deductor", "responsible_person"):
        if original.to_dict()[part] != corrected.to_dict()[part]:
            raise CorrectionError(
                f"{part.replace('_', ' ')} details changed; that is a C1/C2 correction with the "
                "batch updation indicator set, which this tool does not write yet")
    if len(corrected.challans) > len(original.challans):
        raise CorrectionError("a challan was added; that is a C9 correction, allowed only for "
                              "government deductors, and not written by this tool")
    if len(corrected.challans) < len(original.challans):
        raise CorrectionError("a challan was removed; a filed challan cannot be deleted")
    if len(corrected.deductees) < len(original.deductees):
        raise CorrectionError("a deductee row was removed; the format does not allow deleting a "
                              "deductee - update it instead")

    challans_changed = [i for i, (a, b) in enumerate(zip(original.challans, corrected.challans))
                        if _challan_key(a) != _challan_key(b)]
    for i in challans_changed:
        if original.challans[i].no != corrected.challans[i].no:
            raise CorrectionError("challan numbers must stay in their filed order")
    updated, pan_only = [], True
    for i, (a, b) in enumerate(zip(original.deductees, corrected.deductees)):
        ka, kb = _row_key(a), _row_key(b)
        if ka != kb:
            updated.append(i)
            if {k for k in ka if ka[k] != kb.get(k)} != {"pan"}:
                pan_only = False
            if a.reason_code == "C" and (b.reason_code != "C" or a.tds != b.tds):
                raise CorrectionError(
                    f"row {i + 1} ({a.name}) carries flag C; the format does not allow its flag "
                    "or its tax to be updated")
    added = list(range(len(original.deductees), len(corrected.deductees)))
    if not (updated or added or challans_changed):
        raise CorrectionError("nothing changed between the two documents")
    ctype = "C5" if pan_only and updated and not added and not challans_changed else "C3"
    return {"type": ctype, "updated": updated, "added": added, "challans": challans_changed}


def _line(rec: dict, width: int, n: int, where: str) -> str:
    rec = dict(rec)
    rec[1] = str(n)
    fields = []
    for i in range(1, width + 1):
        val = rec.get(i, "")
        val = "" if val is None else str(val)
        if "^" in val:
            raise CorrectionError(f"{where} field {i}: value contains the delimiter: {val!r}")
        fields.append(val)
    return "^".join(fields)


def build(original: Statement, corrected: Statement, ctype: str | None = None) -> dict:
    change = diff(original, corrected)
    ctype = ctype or change["type"]
    if ctype not in ("C3", "C5"):
        raise CorrectionError(f"correction type {ctype} is not written by this tool (C3 or C5 only)")
    if ctype == "C5" and (change["added"] or change["challans"]):
        raise CorrectionError("C5 is a PAN update only; this change needs C3")
    corr = corrected.correction or {}
    prn = str(corr.get("original_token", "") or "")
    if not prn:
        raise CorrectionError("correction.original_token (the PRN of the regular statement) is required")
    previous = str(corr.get("previous_token", "") or prn)
    conso_hash = str(corr.get("consolidated_hash", "") or "")

    row_serial, cd_serial = _serials(original)
    last_serial = max(row_serial.values(), default=0)
    octx = layout140.Context(original)
    filed_dd = {i: layout140.build_dd(octx, original.deductees[i], s, cd_serial[original.deductees[i].challan_no])
                for i, s in row_serial.items()}

    # Every DD record to write, grouped under the challan it now belongs to.
    by_challan: dict[int, list[tuple[str, int, int]]] = {}
    for i in change["updated"]:
        if i not in row_serial:
            raise CorrectionError(f"row {i + 1} was not on any challan in the filed statement")
        by_challan.setdefault(corrected.deductees[i].challan_no, []).append(("U", i, row_serial[i]))
    for n, i in enumerate(change["added"], 1):
        by_challan.setdefault(corrected.deductees[i].challan_no, []).append(("A", i, last_serial + n))
    for idx in change["challans"]:
        by_challan.setdefault(corrected.challans[idx].no, [])

    ch_by_no = {c.no: c for c in corrected.challans}
    och_by_no = {c.no: c for c in original.challans}
    unknown = [no for no in by_challan if no not in ch_by_no]
    if unknown:
        raise CorrectionError(f"rows point at challan {unknown[0]}, which is not in the statement")
    changed_nos = {corrected.challans[i].no for i in change["challans"]}

    ded = corrected.deductor
    rp = corrected.responsible_person
    addr = ded.get("address")
    creation = str(corr.get("file_creation_date", "") or "") or date.today().strftime("%d%m%Y")
    lines: list[str] = []

    fh = {2: "FH", 3: "NS1", 4: "C", 5: creation, 6: "1", 7: "D", 8: corrected.tan, 9: "1",
          10: corrected.meta.get("utility_name") or "TDS Statement 1.0", 18: conso_hash}
    lines.append(_line(fh, WIDTHS["FH"], 1, "FH"))

    cd_order = sorted(by_challan, key=lambda no: cd_serial[no])
    cd_records, dd_count = [], 0
    for no in cd_order:
        ch, och, cds = ch_by_no[no], och_by_no[no], cd_serial[no]
        updated_ch = no in changed_nos
        dds = []
        add_dep = add_ded = Decimal("0.00")
        for mode, i, serial in sorted(by_challan[no], key=lambda t: t[2]):
            row = corrected.deductees[i]
            total = money_str(row.total_tds)
            rec = {2: "DD", 3: "1", 4: str(serial), 5: str(cds), 6: mode, 7: "",
                   8: row.pan, 9: row.name, 15: row.section, 18: row.deposited,
                   19: date8(row.payment_date) if row.payment_date else "",
                   20: money_str(row.amount_paid),
                   22: money_str(row.cash_withdrawal_1cr) if row.cash_withdrawal_1cr else "",
                   23: money_str(row.cash_withdrawal_3cr) if row.cash_withdrawal_3cr else "",
                   # The correction remarks require field 24 to equal field 25.
                   24: total, 25: total,
                   27: date8(row.deduction_date) if row.deduction_date and row.tds else "",
                   28: layout140._rate(row.rate), 31: row.form121, 32: row.reason_code,
                   33: row.certificate_no}
            keep = set(DD_WRITES[ctype])
            if mode == "U":
                filed = filed_dd[i]
                rec[7] = filed[layout140.DD_FIELDS["pan"]]
                rec[26] = filed[layout140.DD_FIELDS["tds"]]
                rec[42] = filed[layout140.DD_FIELDS["total_tds"]]
                if ctype == "C3":
                    keep |= DD_VERIFY_WHEN_UPDATED
                add_dep += row.total_tds - Decimal(rec[42] or "0")
                add_ded += row.total_tds - Decimal(rec[26] or "0")
            else:
                add_dep += row.total_tds
                add_ded += row.total_tds
            dds.append({k: v for k, v in rec.items() if k == 2 or k in keep})
        dd_count += len(dds)
        cd = {2: "CD", 3: "1", 4: str(cds), 5: str(len(dds)), 6: och.nil_challan,
              7: "1" if updated_ch else "0",
              8: money_str(ch.all_tax), 9: money_str(ch.interest), 10: money_str(ch.fee),
              11: money_str(ch.penalty), 12: money_str(ch.total),
              13: "" if och.nil_challan == "Y" else (ch.nature or "C"),
              14: och.bsr_code, 15: ch.bsr_code if updated_ch else och.bsr_code,
              16: och.challan_serial, 17: ch.challan_serial if updated_ch else och.challan_serial,
              18: date8(och.challan_date) if och.challan_date else "",
              19: date8(ch.challan_date if updated_ch else och.challan_date) if ch.challan_date else "",
              20: money_str(och.total), 21: money_str(add_dep), 22: money_str(add_ded),
              23: ch.minor_head, 24: money_str(ch.interest), 25: money_str(ch.penalty)}
        keep = set(CD_WRITES[ctype]) | (CD_WRITES_WHEN_UPDATED if updated_ch and ctype == "C3" else set())
        cd_records.append(({k: v for k, v in cd.items() if k == 2 or k in keep}, ch, dds))

    for _, ch, _ in cd_records:
        if any(v != v.to_integral_value() for v in (ch.all_tax, ch.interest, ch.fee, ch.penalty, ch.total)):
            raise CorrectionError(f"challan {ch.challan_serial}: the format allows no fractional "
                                  "portion on a challan record")

    batch_total = sum((ch.total for _, ch, _ in cd_records), Decimal("0.00"))
    bh = {2: "BH", 3: "1", 4: str(len(cd_records)), 5: "140", 6: ctype, 7: "0", 8: prn, 9: previous,
          12: original.tan, 13: corrected.tan, 16: corrected.assessment_year,
          17: corrected.tax_year, 18: corrected.quarter.upper(),
          19: str(ded.get("name", "") or ""), 26: str(getattr(addr, "state_code", "") or ""),
          32: str(ded.get("category", "") or ""), 47: money_str(batch_total),
          59: str(rp.get("pan", "") or ""), 69: str(ded.get("gstin", "") or "")}
    lines.append(_line({k: v for k, v in bh.items() if k == 2 or k in BH_WRITES[ctype]},
                       WIDTHS["BH"], 2, "BH"))
    for cd, ch, dds in cd_records:
        lines.append(_line(cd, WIDTHS["CD"], len(lines) + 1, f"CD {ch.challan_serial}"))
        for dd in dds:
            lines.append(_line(dd, WIDTHS["DD"], len(lines) + 1, f"DD {dd.get(4)}"))

    pending = []
    if not conso_hash:
        pending.append("correction.consolidated_hash (FH 18): the utility requires it on a "
                       "correction (T-FV-1037); it comes with the TRACES consolidated file")
    return {"type": ctype, "lines": lines, "pending": pending,
            "updated_rows": [i + 1 for i in change["updated"]],
            "added_rows": [i + 1 for i in change["added"]],
            "challans_updated": [i + 1 for i in change["challans"]],
            "records": {"CD": len(cd_records), "DD": dd_count}}


def write(original: Statement, corrected: Statement, out_dir: str | Path,
          ctype: str | None = None) -> dict:
    result = build(original, corrected, ctype)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    blob = ("\r\n".join(result["lines"]) + "\r\n").encode("ascii", errors="strict")
    q = (corrected.quarter or "Q0").upper()[:2]
    tail = (corrected.tan or "")[-2:] or "XX"
    short = "".join(c for c in f"C140{q}{tail}" if c.isalnum())[:8] + ".txt"
    name = "DRAFT_PENDING_HASH.txt" if result["pending"] else short
    (out / name).write_bytes(blob)
    if name != short:
        (out / short).write_bytes(blob)
    manifest = {
        "form": "140", "correction_type": result["type"], "format": FORMAT_FILE,
        "status": "DRAFT" if result["pending"] else "READY",
        "pending": result["pending"], "file": name, "short_name_copy": short,
        "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest(),
        "records": dict(result["records"], lines=len(result["lines"])),
        "updated_rows": result["updated_rows"], "added_rows": result["added_rows"],
        "challans_updated": result["challans_updated"],
    }
    (out / "correction_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
