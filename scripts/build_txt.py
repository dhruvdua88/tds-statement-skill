"""Write a statement TXT in the prescribed caret-delimited layout.

The record writer is deliberately dumb: it asks a layout module for a dict of
field-number -> value, fills the line number, and joins with carets. All the
knowledge about which field means what lives in ``layout140.py`` /
``layout138.py``, which is also where the department's remarks are quoted.

Two rules the writer enforces because the utility is unforgiving about them:

* every record carries its own line number, sequential from 1, including the
  last one;
* the file ends in CRLF, is pure ASCII, and has no BOM. A BOM or a bare LF is
  the most common silent rejection and it is invisible in a text editor.

It also enforces the arithmetic contract before writing anything: the DD rows
under a challan must add up to that challan's tax, because the utility's
challan matching will reject the file otherwise and the error message it gives
does not tell you which challan drifted.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from model import Statement, date8, money_str


class BuildError(RuntimeError):
    pass


def load_layout(form: str):
    if form == "140":
        import layout140 as mod
        return mod
    if form == "138":
        import layout138 as mod
        return mod
    raise BuildError(f"unsupported form {form!r} (expected '140' or '138')")


def build_records(st: Statement, layout) -> list[str]:
    lines: list[str] = []

    def add(rec: dict, width: int, where: str) -> None:
        n = len(lines) + 1
        rec = dict(rec)
        rec[1] = str(n)
        missing = [k for k in rec if not isinstance(k, int) or k < 1 or k > width]
        if missing:
            raise BuildError(f"{where}: field numbers outside 1..{width}: {missing}")
        fields = []
        for i in range(1, width + 1):
            val = rec.get(i, "")
            if val is None:
                val = ""
            if not isinstance(val, str):
                val = str(val)
            if "^" in val:
                raise BuildError(f"{where} field {i}: value contains the delimiter: {val!r}")
            fields.append(val)
        lines.append("^".join(fields))

    ctx = layout.Context(st)

    add(layout.build_fh(ctx), layout.WIDTHS["FH"], "FH")

    # Refuse to build a statement whose DD rows do not settle its challans.
    alloc = st.allocation()
    for row in alloc:
        if row["allocated"] != row["challan_tax"]:
            raise BuildError(
                f"challan {row['serial']} ({row['date']}): deductee rows total "
                f"{row['allocated']} against challan tax {row['challan_tax']} "
                f"(difference {row['remaining']}). Fix the allocation before building."
            )

    add(layout.build_bh(ctx), layout.WIDTHS["BH"], "BH")

    serial = 0
    for idx, ch in enumerate(st.challans, 1):
        rows = [r for r in st.deductees if r.challan_no == ch.no]
        add(layout.build_cd(ctx, ch, rows, idx), layout.WIDTHS["CD"], f"CD {ch.challan_serial}")
        for row in rows:
            serial += 1
            add(
                layout.build_dd(ctx, row, serial, idx),
                layout.WIDTHS["DD"],
                f"DD {serial} ({row.name})",
            )

    return lines


def render(st: Statement, layout) -> bytes:
    lines = build_records(st, layout)
    blob = ("\r\n".join(lines) + "\r\n").encode("ascii", errors="strict")
    return blob


def short_name(st: Statement, fallback: str = "TDSSTMT") -> str:
    """The utility rejects input names longer than 12 characters including .txt.

    A caller can pin the name in ``meta.short_name`` (useful for reproducing a
    previously filed file); otherwise build something both legal and
    recognisable: form + quarter + a tail of the TAN.
    """
    pinned = str(st.meta.get("short_name", "") or "")
    if pinned:
        name = Path(pinned).name
        if len(name) > 12:
            raise BuildError(f"meta.short_name {name!r} is {len(name)} characters; the limit is 12")
        return name
    form = st.form
    q = (st.quarter or "Q0").upper()[:2]
    tail = (st.tan or "")[-3:] or "XXX"
    name = f"{form}{q}{tail}"
    name = "".join(c for c in name if c.isalnum())[:8]
    return f"{name or fallback}.txt"


def output_name(st: Statement) -> str:
    """Draft files are named so nobody uploads one by accident."""
    if st.is_draft:
        return "DRAFT_PENDING_HEADER.txt"
    return short_name(st)


def write(st: Statement, out_dir: str | Path, layout=None) -> dict:
    layout = layout or load_layout(st.form)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    blob = render(st, layout)

    primary_name = output_name(st)
    primary = out / primary_name
    primary.write_bytes(blob)

    short = out / short_name(st)
    if short.name != primary.name:
        short.write_bytes(blob)

    lines = blob.decode("ascii").split("\r\n")
    if lines and lines[-1] == "":
        lines.pop()
    counts = {"FH": 0, "BH": 0, "CD": 0, "DD": 0}
    for line in lines:
        parts = line.split("^")
        if len(parts) > 1 and parts[1] in counts:
            counts[parts[1]] += 1

    totals = st.totals
    manifest = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "form": st.form,
        "file_type": layout.FILE_TYPE,
        "tan": st.tan,
        "period": f"{st.financial_year} {st.quarter}",
        "status": "DRAFT" if st.is_draft else "READY",
        "draft_reason": st.draft_reason,
        "file": primary.name,
        "short_name_copy": short.name,
        "bytes": len(blob),
        "sha256": hashlib.sha256(blob).hexdigest(),
        "records": dict(counts, lines=len(lines)),
        "totals": {
            "tax": str(totals["tax"]), "surcharge": str(totals["surcharge"]),
            "cess": str(totals["cess"]), "interest": str(totals["interest"]),
            "fee": str(totals["fee"]), "penalty": str(totals["penalty"]),
            "deposit": str(totals["deposit"]),
            "deductee_tds": str(totals["deductee_tds"]),
            "variance": str(totals["variance"]),
        },
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
