"""A local, guided web page for the pipeline, for people who do not use a terminal.

    python3 scripts/tds.py ui            # opens http://127.0.0.1:<port>/ in the browser

Standard library only. The server binds 127.0.0.1 and nothing else, so the page
cannot be reached from another machine, and it never uploads anything anywhere:
"upload" here means handing a file from the browser to this local process.
Every run works in its own temporary folder, and each step's outputs can be
downloaded from the page.

The page is ``assets/ui.html``. It talks to the handlers below with JSON; files
travel base64-encoded inside the JSON so no multipart parser is needed. Every
handler answers either a result or ``{"error": "<one plain line>"}``, worded by
``tds.plain_error``, never a traceback.

The FVU step is optional and needs Java and the official utility. The page
shows "validated" only when the utility has written a .fvu file.
"""

from __future__ import annotations

import base64
import json
import shutil
import tempfile
import threading
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAGE = HERE.parent / "assets" / "ui.html"
MAX_BODY = 60 * 1024 * 1024
HOST = "127.0.0.1"


class UIError(ValueError):
    pass


class Workspace:
    def __init__(self, root: Path | None = None):
        self.root = Path(root or tempfile.mkdtemp(prefix="tds-ui-"))
        self.lock = threading.Lock()

    def new_job(self) -> Path:
        job = self.root / uuid.uuid4().hex[:12]
        job.mkdir(parents=True)
        return job

    def job(self, job_id: str) -> Path:
        job_id = str(job_id or "")
        if not job_id.isalnum():
            raise UIError("unknown job; start again from step 1")
        path = self.root / job_id
        if not path.is_dir():
            raise UIError("unknown job; start again from step 1")
        return path


def _save_upload(folder: Path, upload: dict | None, what: str) -> Path:
    if not upload or not upload.get("data"):
        raise UIError(f"choose the {what} first")
    name = Path(str(upload.get("name") or "upload")).name or "upload"
    target = folder / name
    try:
        target.write_bytes(base64.b64decode(upload["data"], validate=True))
    except (ValueError, TypeError) as exc:
        raise UIError(f"the {what} could not be read from the browser") from exc
    return target


def _files(job: Path, *names: str) -> list[dict]:
    out = []
    for name in names:
        p = job / name
        if p.is_file():
            out.append({"name": p.name, "url": f"/files/{job.name}/{p.relative_to(job).as_posix()}",
                        "bytes": p.stat().st_size})
    return out


def _issues(st) -> dict:
    import lint
    issues = [i.as_dict() for i in lint.model_issues(st)]
    order = {"error": 0, "warn": 1, "info": 2}
    issues.sort(key=lambda i: order.get(i["level"], 9))
    return {
        "blockers": [i for i in issues if i["level"] == "error"],
        "warnings": [i for i in issues if i["level"] == "warn"],
        "notes": [i for i in issues if i["level"] == "info"],
        "all": issues,
    }


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------
def step_intake(ws: Workspace, body: dict) -> dict:
    import intake

    job = ws.new_job()
    src = _save_upload(job, body.get("source"), "source Excel or CSV file")
    st, summary = intake.intake([str(src)], form=str(body.get("form") or "140"),
                                financial_year=str(body.get("fy") or ""),
                                quarter=str(body.get("quarter") or ""),
                                report=str(job / "mapping.xlsx"))
    st.save(job / "statement.json")
    return {"job": job.name, "deductees": summary["deductees"], "challans": summary["challans"],
            "skipped": summary["skipped"], "pending": st.pending, "issues": _issues(st),
            "files": _files(job, "statement.json", "mapping.xlsx")}


def step_statement(ws: Workspace, body: dict) -> dict:
    """Replace the statement with an edited copy (header details filled in, rows fixed)."""
    from model import Statement

    job = ws.job(body.get("job"))
    path = _save_upload(job, body.get("statement"), "edited statement.json")
    st = Statement.load(path)
    st.save(job / "statement.json")
    if path.name != "statement.json":
        path.unlink()
    return {"job": job.name, "pending": st.pending, "issues": _issues(st),
            "files": _files(job, "statement.json", "mapping.xlsx")}


def step_lint(ws: Workspace, body: dict) -> dict:
    from model import Statement

    job = ws.job(body.get("job"))
    st = Statement.load(job / "statement.json")
    return {"job": job.name, "pending": st.pending, "issues": _issues(st)}


def step_build(ws: Workspace, body: dict) -> dict:
    import build_txt
    from model import Statement

    job = ws.job(body.get("job"))
    st = Statement.load(job / "statement.json")
    out = job / "build"
    if out.exists():
        shutil.rmtree(out)
    manifest = build_txt.write(st, out)
    names = sorted({manifest["file"], manifest["short_name_copy"], "manifest.json"})
    return {"job": job.name, "status": manifest["status"], "draft_reason": manifest["draft_reason"],
            "records": manifest["records"], "totals": manifest["totals"],
            "files": _files(job, *[f"build/{n}" for n in names])}


def step_excel(ws: Workspace, body: dict) -> dict:
    import excel
    import interest
    from model import Statement

    job = ws.job(body.get("job"))
    st = Statement.load(job / "statement.json")
    recon_result = None
    if body.get("ledger") and body["ledger"].get("data"):
        import recon
        ledger = _save_upload(job, body["ledger"], "ledger export")
        recon_result = recon.reconcile(
            st, recon.read_ledger(ledger, str(body.get("credit_sign") or "negative")),
            str(body.get("ledger_kind") or "tds"))
    filed_on = str(body.get("filed_on") or "")
    issues = _issues(st)["all"]
    (job / "issues.json").write_text(json.dumps(issues, indent=2) + "\n")
    excel.build(st, job / "working.xlsx", issues=issues, filed_on=filed_on, recon_result=recon_result)
    w = interest.compute(st, filed_on)
    out = {"job": job.name, "files": _files(job, "working.xlsx"),
           "interest": {k: str(w[k]) for k in ("interest", "interest_paid", "interest_short", "fee",
                                               "fee_paid", "fee_short", "days_late", "statement_due",
                                               "filed_on")}}
    if recon_result:
        out["recon"] = [{"section": r["section"], "books": str(r["books"]), "statement": str(r["statement"]),
                         "challans": "" if r["challans"] is None else str(r["challans"]),
                         "differs": r in recon_result["differences"]} for r in recon_result["rows"]]
        out["recon_unmapped"] = len(recon_result["unmapped"])
    return out


def step_correct(ws: Workspace, body: dict) -> dict:
    import correct
    from model import Statement

    job = ws.job(body.get("job"))
    if body.get("conso") and body["conso"].get("data"):
        raise UIError("the TRACES consolidated file cannot be read: its layout for Forms 138, 140 and "
                      "144 is not published. Upload a corrected copy of statement.json instead, and "
                      "type the consolidated file hash from TRACES in the box")
    path = _save_upload(job, body.get("corrected"), "corrected statement.json")
    corrected = Statement.load(path)
    corr = dict(corrected.correction or {})
    for key in ("original_token", "previous_token", "consolidated_hash"):
        if body.get(key):
            corr[key] = str(body[key]).strip()
    corrected.correction = corr
    corrected.upload_type = "C"
    out = job / "correction"
    if out.exists():
        shutil.rmtree(out)
    manifest = correct.write(Statement.load(job / "statement.json"), corrected, out)
    names = sorted({manifest["file"], manifest["short_name_copy"], "correction_manifest.json"})
    return {"job": job.name, "type": manifest["correction_type"], "status": manifest["status"],
            "pending": manifest["pending"], "records": manifest["records"],
            "updated_rows": manifest["updated_rows"], "added_rows": manifest["added_rows"],
            "files": _files(job, *[f"correction/{n}" for n in names])}


def step_check_env(ws: Workspace, body: dict) -> dict:
    import fvu

    out = {}
    try:
        out["java"] = fvu.find_java(None)
    except Exception as exc:  # noqa: BLE001 - reported, not raised: this step is optional
        out["java_missing"] = str(exc)
    try:
        out["jar"] = fvu.find_jar(None)
    except Exception as exc:  # noqa: BLE001
        out["jar_missing"] = str(exc)
    out["ready"] = "java" in out and "jar" in out
    return out


def step_fvu(ws: Workspace, body: dict) -> dict:
    import fvu

    job = ws.job(body.get("job"))
    manifest = json.loads((job / "build" / "manifest.json").read_text())
    csi = _save_upload(job, body.get("csi"), "Challan Status Inquiry (.csi) file")
    result = fvu.run(job / "build" / manifest["short_name_copy"], job / "fvu_out", csi=str(csi))
    (job / "fvu_result.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    validated = result.get("status") == "PASS" and bool(result.get("fvu")) and Path(result["fvu"]).exists()
    return {"job": job.name, "status": result.get("status"), "validated": validated,
            "summary": fvu.summarise(result), "files": _files(job, "fvu_result.json")}


def step_package(ws: Workspace, body: dict) -> dict:
    import package

    job = ws.job(body.get("job"))
    if not (job / "build" / "manifest.json").exists():
        raise UIError("build the TXT (step 3) before packaging")
    out = job / "deliverables"
    if out.exists():
        shutil.rmtree(out)
    fvu_result = job / "fvu_result.json"
    issues = json.loads((job / "issues.json").read_text()) if (job / "issues.json").exists() else None
    summary = package.assemble(
        job / "statement.json", out_dir=out, txt_dir=str(job / "build"),
        fvu_result=str(fvu_result) if fvu_result.exists() else "",
        working_paper=str(job / "working.xlsx") if (job / "working.xlsx").exists() else "",
        issues=issues)
    shutil.make_archive(str(job / "deliverables"), "zip", out)
    return {"job": job.name, "ready": summary["ready_to_upload"], "status": summary["status"],
            "blockers": summary["blockers"], "files": _files(job, "deliverables.zip")}


STEPS = {
    "intake": step_intake, "statement": step_statement, "lint": step_lint, "build": step_build,
    "excel": step_excel, "correct": step_correct, "check-env": step_check_env, "fvu": step_fvu,
    "package": step_package,
}


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
def make_handler(ws: Workspace):
    class Handler(BaseHTTPRequestHandler):
        server_version = "tds-ui"

        def log_message(self, fmt, *args):  # keep the terminal quiet
            pass

        def _send(self, code: int, body: bytes, ctype: str, extra: dict | None = None):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, payload: dict):
            self._send(code, json.dumps(payload, default=str).encode(), "application/json")

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                return self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
            if self.path.startswith("/files/"):
                parts = self.path.split("/", 3)
                try:
                    job = ws.job(parts[2])
                    target = (job / parts[3]).resolve()
                    if job.resolve() not in target.parents or not target.is_file():
                        raise UIError("no such file")
                except (UIError, IndexError):
                    return self._json(404, {"error": "no such file"})
                return self._send(200, target.read_bytes(), "application/octet-stream",
                                  {"Content-Disposition": f'attachment; filename="{target.name}"'})
            return self._json(404, {"error": "not found"})

        def do_POST(self):
            import tds

            name = self.path.removeprefix("/api/")
            step = STEPS.get(name)
            if not self.path.startswith("/api/") or not step:
                return self._json(404, {"error": "not found"})
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                return self._json(413, {"error": "that file is too large for this page (60 MB limit)"})
            try:
                body = json.loads(self.rfile.read(length) or b"{}")
                with ws.lock:
                    return self._json(200, step(ws, body))
            except Exception as exc:  # noqa: BLE001 - the page shows one plain line
                return self._json(200, {"error": tds.plain_error(exc)})

    return Handler


def make_server(port: int = 0, root: Path | None = None) -> tuple[ThreadingHTTPServer, Workspace]:
    ws = Workspace(root)
    server = ThreadingHTTPServer((HOST, port), make_handler(ws))
    return server, ws


def serve(port: int = 0, open_browser: bool = True) -> int:
    server, ws = make_server(port)
    url = f"http://{HOST}:{server.server_address[1]}/"
    print(f"TDS statement page: {url}")
    print(f"working folder:     {ws.root}")
    print("Press Ctrl+C to stop.")
    if open_browser:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        server.server_close()
    return 0
