"""Assemble the filing folder: everything a person needs at upload time, in one place.

The point of this step is that the upload is done by someone who may not have
built the statement. The folder therefore carries the file to upload, the
figures that go on Form 27A, exactly what the utility said, and a checklist
that states plainly whether the package is ready or still waiting on something.

Nothing here ever claims a pass it cannot prove. A package without a ``.fvu``
is marked NOT READY in the first line of its own README, because the one
mistake that matters is uploading an unvalidated statement.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

import queries
from model import Statement


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def form_27a(st: Statement, manifest: dict | None) -> str:
    t = st.totals
    ded = st.deductor
    rp = st.responsible_person
    return f"""# Form 27A figures

Print or reproduce these on Form 27A. They must agree with the statement that
is uploaded; the portal compares them.

| Field | Value |
|---|---|
| Name of the deductor | {ded.get('name', '')} |
| TAN | {st.tan} |
| PAN | {ded.get('pan', '')} |
| Financial year | {st.financial_year} |
| Quarter / period | {st.quarter} |
| Form | {st.form} |
| Type of statement | {'Original' if st.upload_type == 'R' else 'Correction'} |
| Total number of deductee records | {t['rows']} |
| Total number of challans | {t['challans']} |
| Total tax deducted and paid (Rs) | {t['tax']} |
| Total surcharge (Rs) | {t['surcharge']} |
| Total cess (Rs) | {t['cess']} |
| Total interest (Rs) | {t['interest']} |
| Total fee and penalty (Rs) | {t['fee'] + t['penalty']} |
| Total amount deposited (Rs) | {t['deposit']} |
| Name of the person responsible | {rp.get('name', '')} |
| Designation | {rp.get('designation', '')} |
| PAN of the person responsible | {rp.get('pan', '')} |
| Contact | {rp.get('phone', '')} |{'  ' + str(manifest.get('sha256', '')) if manifest else ''}
"""


def checklist(st: Statement, fvu_result: dict | None, files: dict,
              qblockers: list[dict] | None = None) -> str:
    qblockers = qblockers or []
    ok_fvu = bool(fvu_result and fvu_result.get("status") == "PASS")
    header = "READY TO UPLOAD" if ok_fvu and not qblockers else "NOT READY - DO NOT UPLOAD"
    lines = [
        f"# Upload checklist - {header}",
        "",
        f"Statement: Form {st.form}, {st.financial_year} {st.quarter}, TAN {st.tan}",
        "",
        "## Before you start",
        "",
        "- [ ] The deductor's TRACES registration is active and the TAN details match the statement.",
        "- [ ] You are logged in as the deductor (or their representative) on the e-filing portal.",
        "- [ ] The Challan Status Inquiry (CSI) for this TAN and quarter has been downloaded.",
        "- [ ] The due date has been checked. A late statement attracts a fee for every day of delay.",
        "",
        "## The file",
        "",
    ]
    if ok_fvu:
        lines.append(f"- [ ] Upload `{Path(files['fvu']).name}` on the portal's TDS statement upload screen.")
        lines.append("- [ ] Keep the original `.txt` with the acknowledgement; the portal may ask for it if the upload is queried.")
    else:
        lines.append("- [ ] The FVU has NOT produced a `.fvu`. Do not upload yet.")
        lines.append("- [ ] Work through the blockers below, fix the statement, and rebuild this folder.")
    lines += [
        "",
        "## After the upload",
        "",
        "- [ ] Save the provisional receipt, the token number and the date.",
        "- [ ] Check the statement status on TRACES once the portal has processed it.",
        "- [ ] Confirm the deductee count and the tax on Form 27A agree with the acknowledgement.",
        "- [ ] File the acknowledgement with the working paper.",
    ]
    if qblockers:
        lines += ["", "## Blockers stopping the .fvu", ""]
        for q in qblockers:
            owner = f" _({q['owner']})_" if q.get("owner") else ""
            lines.append(f"- **{q['id']}  {q['reference']}** - {q['issue']}{owner}")
        lines += ["", "The same list is in the workbook's *Queries & Blockers* tab and in the "
                      f"`Queries_{st.form}_{st.quarter or 'Q0'}.xlsx` file beside this checklist."]
    return "\n".join(lines) + "\n"


def assemble(statement_path, out_dir, txt_dir: str = "", fvu_result: str = "",
             working_paper: str = "", issues: list[dict] | None = None) -> dict:
    st = Statement.load(statement_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}
    fvu = json.loads(Path(fvu_result).read_text()) if fvu_result else None
    if issues is None:
        # Recompute the pre-flight findings so the package's blocker list cannot
        # drift from the one the workbook was built with.
        try:
            import lint
            issues = [i.as_dict() for i in lint.model_issues(st)]
        except Exception:
            issues = []
    qrows = queries.build(st, issues, fvu)
    qblockers = queries.blockers(qrows)
    manifest = None
    if txt_dir and (Path(txt_dir) / "manifest.json").exists():
        manifest = json.loads((Path(txt_dir) / "manifest.json").read_text())

    # the statement itself
    if txt_dir:
        src = Path(txt_dir)
        for name in {manifest.get("file") if manifest else None, manifest.get("short_name_copy") if manifest else None}:
            if name and (src / name).exists():
                shutil.copy2(src / name, out / name)
                files["txt" if name.endswith(".txt") and "DRAFT" in name else "txt_short"] = str(out / name)
    if manifest:
        (out / "build_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    if fvu and fvu.get("fvu") and Path(fvu["fvu"]).exists():
        shutil.copy2(fvu["fvu"], out / Path(fvu["fvu"]).name)
        files["fvu"] = str(out / Path(fvu["fvu"]).name)
    if fvu and fvu.get("err") and Path(fvu["err"]).exists():
        shutil.copy2(fvu["err"], out / Path(fvu["err"]).name)
        files["err"] = str(out / Path(fvu["err"]).name)
    if fvu and fvu.get("html") and Path(fvu["html"]).exists():
        shutil.copy2(fvu["html"], out / Path(fvu["html"]).name)

    if working_paper and Path(working_paper).exists():
        shutil.copy2(working_paper, out / Path(working_paper).name)
        files["working_paper"] = str(out / Path(working_paper).name)

    # The query list on its own: one workbook for the client, one note that can
    # be pasted into an e-mail. It is the same list the workbook's Queries tab
    # shows, so the two can never disagree.
    q_xlsx, q_md = queries.write_sidecar(st, out, issues, fvu)
    files["queries_xlsx"] = str(q_xlsx)
    files["queries_md"] = str(q_md)

    (out / "Form_27A.md").write_text(form_27a(st, manifest))
    (out / "UPLOAD_CHECKLIST.md").write_text(checklist(st, fvu, files, qblockers))

    summary = {
        "prepared": datetime.now().isoformat(timespec="seconds"),
        "form": st.form, "tan": st.tan, "period": f"{st.financial_year} {st.quarter}",
        "status": "DRAFT_PENDING" if st.is_draft else queries.fvu_status_label(fvu),
        "ready_to_upload": not qblockers and bool(fvu and fvu.get("status") == "PASS"),
        "blockers": [{"id": q["id"], "reference": q["reference"], "issue": q["issue"]}
                     for q in qblockers],
        "queries": queries.counts(qrows),
        "totals": {k: str(v) for k, v in st.totals.items()},
        "files": {k: Path(v).name for k, v in files.items()},
        "checksums": {Path(v).name: sha256(Path(v)) for v in files.values()},
    }
    (out / "package_manifest.json").write_text(json.dumps(summary, indent=2) + "\n")

    who = str(st.deductor.get("name", "") or "").strip() or "(deductor name not supplied yet)"
    readme = [
        f"{who} - TDS statement {st.form}, {st.financial_year} {st.quarter}",
        f"Prepared {datetime.now().strftime('%d-%b-%Y')}. TAN {st.tan or '(not supplied yet)'}.",
        f"Status: {'READY TO UPLOAD' if summary['ready_to_upload'] else 'NOT READY'}",
        "",
        "Files",
        "  1. UPLOAD_CHECKLIST.md       what to do, in order",
        "  2. Form_27A.md               the control totals for Form 27A",
        "  3. the .fvu file             the only file that is uploaded (present only when the run passed)",
        "  4. the .txt file             the statement behind the .fvu; keep it with the acknowledgement",
        "  5. the workbook              the working paper, challan allocation and flags",
        f"  6. {Path(q_xlsx).name:<24} the query list on its own, for the client",
        f"  7. {Path(q_md).name:<24} the same list as a note",
        "  8. package_manifest.json     checksums and the utility result",
        "",
    ]
    if qblockers:
        readme += ["Blockers stopping the .fvu", ""]
        for q in qblockers:
            readme.append(f"  - {q['id']}  {q['reference']}: {q['issue']}")
        readme.append("")
    readme.append("Do not upload anything unless UPLOAD_CHECKLIST.md says READY TO UPLOAD.")
    (out / "README.txt").write_text("\n".join(readme) + "\n")

    return summary
