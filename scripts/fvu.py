"""Run the official Protean FVU and read back what it says.

The FVU is the only thing that actually validates a statement. Everything in
``lint.py`` is a pre-flight check; if the two disagree, the FVU is right.

Practical notes that cost real time to rediscover:

* The utility is a Java Swing application. On macOS it will not run from a
  plain shell on a headless session: it has to be started inside the logged-in
  GUI session, which means ``launchctl bootstrap gui/$UID`` with a throw-away
  LaunchAgent. On Linux, ``xvfb-run`` does the same job. This module tries a
  direct run first and falls back automatically.
* **It never exits.** It validates, writes its output files and then sits there
  with its window open. So the run cannot be a ``subprocess.run`` that waits for
  the process: it is started, watched for its output files, and then stopped.
  Waiting on the process would time out every time and throw away artefacts that
  were already correct.
* It refuses an input file name longer than 12 characters including ``.txt``,
  and a CSI name longer than 25 including ``.csi``.
* Validation always needs a CSI, and a real one. With no CSI the utility throws
  a NullPointerException; with a fabricated CSI whose TAN and TAN name are right
  but whose challan digests are not, it validates the file field by field and
  then fails the challan stage. The field-by-field result is still useful, and
  it is not a pass: only a ``.fvu`` file proves that.
* The ``.err`` file has seven caret-separated fields and is written only when
  something failed. No ``.err`` and no ``.fvu`` means it died before finishing,
  which is a different problem from a validation failure.
* **Outputs do not always land where you tell them to.** The utility derives its
  error/report path from the *jar* location, so on a failure the ``.err`` shows
  up beside the jar rather than in the output directory that was passed in. The
  watcher searches both, otherwise a finished run looks like a timeout.

The command line (verified against the 1.2 standalone package):

    java -jar <FVU>.jar <input.txt> <jar path> <out dir> 0 <format version> 0 <csi>
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

ERR_FIELDS = [
    "line_no", "record_type", "field_name", "challan_no",
    "deductee_no", "code", "message",
]

DEFAULT_FORMAT_VERSION = "1.2"

TXT_NAME_LIMIT = 12
CSI_NAME_LIMIT = 25

JAVA_CANDIDATES = [
    "/opt/homebrew/opt/openjdk/bin/java",
    "/usr/local/opt/openjdk/bin/java",
    "/opt/homebrew/opt/openjdk@21/bin/java",
    "/usr/lib/jvm/default-java/bin/java",
]

CODES_ASSET = Path(__file__).resolve().parent.parent / "assets" / "fvu_codes.json"


class FVUError(RuntimeError):
    pass


def _java_works(path: str) -> bool:
    """True only for a java that actually runs.

    macOS ships ``/usr/bin/java`` as a stub that is on PATH but has no runtime
    behind it, and it answers with "Unable to locate a Java Runtime". Picking
    that one produces a run that dies instantly and looks like a validation
    failure, so every candidate is tested before it is used.
    """
    try:
        out = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=30)
    except Exception:
        return False
    text = (out.stderr or "") + (out.stdout or "")
    if out.returncode != 0 or "Unable to locate a Java Runtime" in text:
        return False
    return "version" in text.lower()


def find_java(explicit: str | None = None) -> str:
    if explicit:
        if not Path(explicit).exists():
            raise FVUError(f"java not found at {explicit}")
        return explicit

    candidates: list[str] = []
    env = os.environ.get("TDS_JAVA")
    if env:
        candidates.append(env)
    home = os.environ.get("JAVA_HOME")
    if home:
        candidates.append(str(Path(home, "bin", "java")))
    if shutil.which("/usr/libexec/java_home"):
        out = subprocess.run(["/usr/libexec/java_home"], capture_output=True, text=True)
        if out.returncode == 0 and out.stdout.strip():
            candidates.append(str(Path(out.stdout.strip(), "bin", "java")))
    candidates.extend(JAVA_CANDIDATES)
    found = shutil.which("java")
    if found:
        candidates.append(found)

    for cand in candidates:
        if Path(cand).exists() and _java_works(cand):
            return cand
    raise FVUError(
        "No working Java runtime found"
        + (f" (tried {', '.join(candidates)})" if candidates else "")
        + ". Install a JDK (macOS: brew install openjdk) and set TDS_JAVA or JAVA_HOME, "
        "or pass --java."
    )


def find_jar(explicit: str | None = None) -> str:
    if explicit:
        p = Path(explicit)
        if not p.exists():
            raise FVUError(f"FVU jar not found at {explicit}")
        return str(p)
    env = os.environ.get("TDS_FVU_JAR")
    if env and Path(env).exists():
        return env
    roots = [
        Path.home() / ".tds-utils" / "fvu",
        Path.home() / ".tds-utils",
        Path("/opt/tds/fvu"),
    ]
    for root in roots:
        if not root.exists():
            continue
        hits = sorted(root.rglob("*.jar"))
        # Prefer the standalone FVU over the RPU, which ships a similarly named jar.
        hits = [h for h in hits if "FVU" in h.name.upper()] or hits
        if hits:
            return str(hits[-1])
    raise FVUError(
        "FVU jar not found. Run 'tds fetch-official' (downloads from the official "
        "Protean page) or point at your copy with --jar."
    )


def check_java_version(java: str) -> str:
    try:
        out = subprocess.run([java, "-version"], capture_output=True, text=True, timeout=30)
        return (out.stderr or out.stdout).strip().splitlines()[0] if (out.stderr or out.stdout) else ""
    except Exception as exc:  # pragma: no cover - environment dependent
        return f"could not run java: {exc}"


def command(java: str, jar: str, txt: Path, out_dir: Path, csi: Path | None,
            fmt: str = DEFAULT_FORMAT_VERSION, extra: list[str] | None = None) -> list[str]:
    cmd = [java, "-jar", jar, str(txt), jar, str(out_dir) + os.sep, "0", fmt, "0"]
    if csi is not None:
        cmd.append(str(csi))
    if extra:
        cmd.extend(extra)
    return cmd


def explain(code: str) -> str:
    """The FVU's own message for a validation code, when the table is on disk."""
    if not CODES_ASSET.exists():
        return ""
    try:
        table = json.loads(CODES_ASSET.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    return str(table.get(code, "") or "")


# ---------------------------------------------------------------------------
# Artefacts
# ---------------------------------------------------------------------------

def _search_dirs(out_dir: Path, extra_dirs: tuple[Path, ...] = ()) -> list[Path]:
    """Every directory the utility might write into, output directory first.

    The utility derives its error/report path from the **jar** location
    (``errorFileNameSAM``) instead of the output directory it is handed, so a run
    that only looks in ``out_dir`` never sees the ``.err`` it produced and times
    out on a run that actually finished. Both locations are searched.
    """
    seen: list[Path] = []
    for d in (out_dir, *extra_dirs):
        d = Path(d)
        if d not in seen:
            seen.append(d)
    return seen


def _artefacts(txt: Path, out_dir: Path, extra_dirs: tuple[Path, ...] = ()) -> dict:
    """The utility names outputs after the input stem, except for err.html.

    Outputs can land beside the jar as well as in the output directory, so both
    are searched; the exact-name match in the output directory wins first.
    """
    stem = txt.stem
    roots = _search_dirs(out_dir, extra_dirs)

    def pick(suffixes: tuple[str, ...]) -> Path | None:
        for root in roots:
            for s in suffixes:
                cand = root / f"{stem}{s}"
                if cand.exists():
                    return cand
        for root in roots:
            if not root.exists():
                continue
            hits = [p for p in root.iterdir() if p.suffix.lower() in suffixes and p.is_file()]
            if hits:
                return sorted(hits)[-1]
        return None

    err_html = None
    for root in roots:
        if not root.exists():
            continue
        hits = sorted(root.glob(f"{stem}*err*.html"))
        if hits:
            err_html = hits[-1]
            break
    return {
        "fvu": pick((".fvu",)),
        "err": pick((".err",)),
        "html": err_html,
        "statistics": pick(("_PAN_Statistics.html",)),
        "warnings": pick(("_Electronic_Statement_Warning_File.html",)),
    }


def _produced(txt: Path, out_dir: Path, extra_dirs: tuple[Path, ...] = ()) -> bool:
    arts = _artefacts(txt, out_dir, extra_dirs)
    return bool(arts["fvu"] or arts["err"])


def quarantine(txt: Path, out_dir: Path, extra_dirs: tuple[Path, ...] = ()) -> list[str]:
    """Move any previous run's output aside before starting a new one.

    Without this a stale ``.fvu`` from yesterday makes today's failed run look
    like a pass, which is the worst possible failure mode for this tool. The
    files are renamed rather than deleted so nothing is lost.
    """
    roots = _search_dirs(out_dir, extra_dirs)
    if not any(r.exists() for r in roots):
        return []
    stamp = time.strftime("%Y%m%d-%H%M%S")
    moved = []
    for art in _artefacts(txt, out_dir, extra_dirs).values():
        if art is None:
            continue
        target = art.with_name(f"{art.name}.previous-{stamp}")
        try:
            art.rename(target)
            moved.append(target.name)
        except OSError:
            pass
    return moved


# ---------------------------------------------------------------------------
# Starting and stopping the utility, per platform
# ---------------------------------------------------------------------------

def _start_process(cmd: list[str], cwd: Path, workspace: Path) -> dict:
    log = workspace / "run.log"
    fh = open(log, "w", encoding="utf-8")
    proc = subprocess.Popen(cmd, cwd=str(cwd), stdout=fh, stderr=subprocess.STDOUT,
                            text=True, start_new_session=True)
    return {"kind": "process", "proc": proc, "log_file": log, "handle": fh}


def _stop_process(handle: dict) -> None:
    proc = handle["proc"]
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
    try:
        handle["handle"].close()
    except Exception:
        pass


def _start_macos_gui(cmd: list[str], cwd: Path, workspace: Path) -> dict:
    """Start the utility inside the user's GUI session via a throw-away LaunchAgent.

    A plain ``java -jar`` from a shell on macOS throws HeadlessException, so the
    job has to be handed to launchd in the ``gui`` domain.
    """
    label = f"com.tdsstatement.fvu.{uuid.uuid4().hex[:8]}"
    exit_file = workspace / "exit.code"
    log_file = workspace / "run.log"
    wrapper = workspace / "run.sh"
    quoted = " ".join("'" + a.replace("'", "'\\''") + "'" for a in cmd)
    wrapper.write_text(f"#!/bin/sh\n{quoted} > '{log_file}' 2>&1\necho $? > '{exit_file}'\n")
    wrapper.chmod(0o755)
    plist = workspace / f"{label}.plist"
    plist.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0"><dict>\n'
        f'  <key>Label</key><string>{label}</string>\n'
        '  <key>ProgramArguments</key><array>\n'
        f'    <string>/bin/sh</string><string>{wrapper}</string>\n'
        '  </array>\n'
        f'  <key>WorkingDirectory</key><string>{cwd}</string>\n'
        '  <key>RunAtLoad</key><true/>\n'
        '</dict></plist>\n'
    )
    uid = os.getuid()
    boot = subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", str(plist)],
                          capture_output=True, text=True)
    if boot.returncode != 0:
        raise FVUError("launchctl bootstrap failed: "
                       + (boot.stderr.strip() or boot.stdout.strip())
                       + "  (a stale label gives 'bootstrap failed: 5')")
    return {"kind": "macos-gui", "label": label, "workspace": workspace,
            "log_file": log_file, "exit_file": exit_file}


def _stop_macos_gui(handle: dict) -> None:
    subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{handle['label']}"],
                   capture_output=True, text=True)


def _log_of(handle: dict) -> str:
    log_file = handle.get("log_file")
    text = log_file.read_text(encoding="utf-8", errors="replace") if log_file and log_file.exists() else ""
    if handle["kind"] == "macos-gui":
        text += f"\n[launchd run directory: {handle['workspace']}]"
    return text


def _wait_for_artefacts(txt: Path, out_dir: Path, deadline: float, handle: dict,
                       extra_dirs: tuple[Path, ...] = ()) -> str:
    """Watch for output files. The utility does not exit, so this is the only signal."""
    while time.time() < deadline:
        if _produced(txt, out_dir, extra_dirs):
            return "artefacts"
        if handle["kind"] == "macos-gui":
            if handle["exit_file"].exists():
                return "exited"
        elif handle["proc"].poll() is not None:
            return "exited"
        time.sleep(0.5)
    return "timeout"


def run(txt: str | Path, out_dir: str | Path, csi: str | Path | None = None,
        jar: str | None = None, java: str | None = None,
        fmt: str = DEFAULT_FORMAT_VERSION, timeout: int = 300,
        extra: list[str] | None = None, force_mode: str | None = None) -> dict:
    txt = Path(txt).resolve()
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    if not txt.exists():
        raise FVUError(f"input not found: {txt}")
    if len(txt.name) > TXT_NAME_LIMIT:
        raise FVUError(
            f"input name {txt.name!r} is {len(txt.name)} characters; the utility accepts "
            f"{TXT_NAME_LIMIT} or fewer including '.txt'. Copy it to a shorter name first."
        )
    csi_path = Path(csi).resolve() if csi else None
    if csi_path:
        if not csi_path.exists():
            raise FVUError(f"CSI not found: {csi_path}")
        if csi_path.suffix.lower() != ".csi":
            raise FVUError(f"the CSI must have a .csi extension, got {csi_path.name!r}")
        if len(csi_path.name) > CSI_NAME_LIMIT:
            raise FVUError(
                f"CSI name {csi_path.name!r} is {len(csi_path.name)} characters; the limit is "
                f"{CSI_NAME_LIMIT} including '.csi'."
            )

    java_bin = find_java(java)
    jar_path = find_jar(jar)
    cmd = command(java_bin, jar_path, txt, out_dir, csi_path, fmt, extra)
    # The utility can write its error/report files beside the jar, so that
    # directory is searched too (see _artefacts).
    extra_dirs: tuple[Path, ...] = (Path(jar_path).parent,)
    moved = quarantine(txt, out_dir, extra_dirs)

    modes = ["direct", "macos-gui"] if sys.platform == "darwin" else ["direct", "xvfb"]
    if force_mode:
        modes = [force_mode]

    attempts = []
    result = None
    for mode in modes:
        started = time.time()
        workspace = Path(tempfile.mkdtemp(prefix=f"tds-fvu-{mode}-"))
        try:
            if mode == "macos-gui":
                handle = _start_macos_gui(cmd, out_dir, workspace)
            elif mode == "xvfb":
                if not shutil.which("xvfb-run"):
                    continue
                handle = _start_process(["xvfb-run", "-a"] + cmd, out_dir, workspace)
            elif mode == "direct":
                handle = _start_process(cmd, out_dir, workspace)
            else:
                raise FVUError(f"unknown mode {mode}")
        except FVUError as exc:
            attempts.append({"mode": mode, "error": str(exc)})
            continue

        try:
            stopped = _wait_for_artefacts(txt, out_dir, started + timeout, handle, extra_dirs)
        finally:
            if handle["kind"] == "macos-gui":
                _stop_macos_gui(handle)
            else:
                _stop_process(handle)
        log = _log_of(handle)
        attempts.append({"mode": mode, "stopped": stopped,
                         "seconds": round(time.time() - started, 1)})
        result = {"mode": mode, "log": log, "stopped": stopped}
        if stopped == "artefacts":
            break

    if result is None:
        raise FVUError("the utility could not be started in any mode: " + json.dumps(attempts))

    arts = _artefacts(txt, out_dir, extra_dirs)
    errors = parse_err(arts["err"]) if arts["err"] else []
    for e in errors:
        e["meaning"] = explain(str(e.get("code", "")))
    outcome = {
        "input": str(txt),
        "output_dir": str(out_dir),
        "java": java_bin,
        "java_version": check_java_version(java_bin),
        "jar": jar_path,
        "format_version": fmt,
        "csi": str(csi_path) if csi_path else None,
        "command": cmd,
        "mode": result["mode"],
        "stopped": result["stopped"],
        "attempts": attempts,
        "quarantined": moved,
        "fvu": str(arts["fvu"]) if arts["fvu"] else None,
        "err": str(arts["err"]) if arts["err"] else None,
        "html": str(arts["html"]) if arts["html"] else None,
        "statistics": str(arts["statistics"]) if arts["statistics"] else None,
        "warnings": str(arts["warnings"]) if arts["warnings"] else None,
        "error_count": len(errors),
        "errors": errors,
        "status": _status(arts, errors, csi_path),
        "log_tail": result["log"][-4000:],
    }
    (out_dir / "fvu_result.json").write_text(json.dumps(outcome, indent=2) + "\n", encoding="utf-8")
    return outcome


def parse_err(path: str | Path) -> list[dict]:
    rows = []
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("^")
        if len(parts) < 6:
            rows.append({"raw": line})
            continue
        rec = dict(zip(ERR_FIELDS, parts[:6]))
        rec["message"] = parts[6] if len(parts) > 6 else ""
        rec["line_no"] = rec["line_no"].strip()
        rows.append(rec)
    return rows


def _status(arts: dict, errors: list[dict], csi: Path | None) -> str:
    if arts["fvu"]:
        return "PASS"
    if errors:
        return "FIELD_ERRORS"
    if not csi:
        return "STOPPED_NO_CSI"
    return "STOPPED"


def summarise(result: dict) -> str:
    lines = [
        f"status          {result['status']}",
        f"mode            {result['mode']} (stopped: {result.get('stopped', '?')})",
        f"jar             {Path(result['jar']).name}",
        f"java            {result['java_version']}",
        f"format          {result['format_version']}",
        f"CSI             {result['csi'] or '(none supplied)'}",
        f"FVU file        {result['fvu'] or '(not produced)'}",
        f"errors          {result['error_count']}",
    ]
    if result.get("quarantined"):
        lines.append(f"set aside       {', '.join(result['quarantined'])} (previous run's output)")
    for e in result["errors"][:50]:
        if "raw" in e:
            lines.append(f"  ? {e['raw']}")
            continue
        lines.append(f"  {e.get('code', '?')}  line {e.get('line_no')}  {e.get('field_name')}  {e.get('message', '')}")
        if e.get("meaning"):
            lines.append(f"      {e['meaning'][:160]}")
    return "\n".join(lines)
