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


def checklist(st: Statement, fvu_result: dict | None, files: dict) -> str:
    ok_fvu = bool(fvu_result and fvu_result.get("status") == "PASS")
    header = "READY TO UPLOAD" if ok_fvu and not st.is_draft else "NOT READY - DO NOT UPLOAD"
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
        status = (fvu_result or {}).get("status", "not run")
        lines.append(f"- [ ] The FVU has NOT produced a `.fvu` (status: {status}). Do not upload yet.")
        lines.append("- [ ] Resolve the reasons above, re-run the utility, and rebuild this folder.")
    lines += [
        "",
        "## After the upload",
        "",
        "- [ ] Save the provisional receipt, the token number and the date.",
        "- [ ] Check the statement status on TRACES once the portal has processed it.",
        "- [ ] Confirm the deductee count and the tax on Form 27A agree with the acknowledgement.",
        "- [ ] File the acknowledgement with the working paper.",
    ]
    if st.is_draft:
        lines += ["", "## Still outstanding from the client", ""]
        for p in st.blocking_pending:
            lines.append(f"- {p.get('field')}: {p.get('why')}")
    return "\n".join(lines) + "\n"


def assemble(statement_path, out_dir, txt_dir: str = "", fvu_result: str = "",
             working_paper: str = "") -> dict:
    st = Statement.load(statement_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}
    fvu = json.loads(Path(fvu_result).read_text()) if fvu_result else None
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

    (out / "Form_27A.md").write_text(form_27a(st, manifest))
    (out / "UPLOAD_CHECKLIST.md").write_text(checklist(st, fvu, files))

    summary = {
        "prepared": datetime.now().isoformat(timespec="seconds"),
        "form": st.form, "tan": st.tan, "period": f"{st.financial_year} {st.quarter}",
        "status": (fvu or {}).get("status", "FVU_NOT_RUN") if not st.is_draft else "DRAFT_PENDING",
        "ready_to_upload": bool(fvu and fvu.get("status") == "PASS") and not st.is_draft,
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
        "  3. the .fvu file             the only file that is uploaded (when the run passed)",
        "  4. the .txt file             the statement behind the .fvu; keep it with the acknowledgement",
        "  5. the workbook              the working paper, challan allocation and flags",
        "  6. package_manifest.json     checksums and the utility result",
        "",
    ]
    if st.is_draft:
        readme += ["Outstanding from the client", ""]
        for p in st.blocking_pending:
            readme.append(f"  - {p.get('field')}: {p.get('why')}")
        readme.append("")
    readme.append("Do not upload anything unless UPLOAD_CHECKLIST.md says READY TO UPLOAD.")
    (out / "README.txt").write_text("\n".join(readme) + "\n")

    return summary
