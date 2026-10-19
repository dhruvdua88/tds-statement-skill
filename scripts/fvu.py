"""Run the official Protean FVU headlessly and read back what it says.

The FVU is the only thing that actually validates a statement. Everything in
``lint.py`` is a pre-flight check; if the two disagree, the FVU is right.

Practical notes that cost real time to rediscover:

* The utility is a Java Swing application. On macOS it will not run from a
  plain shell on a headless session: it has to be started inside the logged-in
  GUI session, which means ``launchctl bootstrap gui/$UID`` with a throw-away
  LaunchAgent. On Linux, ``xvfb-run`` does the same job. This module tries a
  direct run first and falls back automatically.
* It refuses input file names longer than 12 characters including ``.txt``.
* With an empty or placeholder CSI it validates the file field by field and
  then stops at challan matching. That is useful, and it is not a pass. A
  ``.fvu`` file is the only proof of a clean run.
* The ``.err`` file has seven caret-separated fields and is only written when
  something failed. No ``.err`` and no ``.fvu`` means it died before finishing,
  which is a different problem from a validation failure.

The command line (verified against the 1.2 standalone package):

    java -jar <FVU>.jar <input.txt> <jar path> <out dir> 0 <format version> 0 [<csi>]
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

JAVA_CANDIDATES = [
    "/opt/homebrew/opt/openjdk/bin/java",
    "/usr/local/opt/openjdk/bin/java",
    "/opt/homebrew/opt/openjdk@21/bin/java",
    "/usr/lib/jvm/default-java/bin/java",
]


class FVUError(RuntimeError):
    pass


def find_java(explicit: str | None = None) -> str:
    if explicit:
        if not Path(explicit).exists():
            raise FVUError(f"java not found at {explicit}")
        return explicit
    env = os.environ.get("TDS_JAVA")
    if env and Path(env).exists():
        return env
    home = os.environ.get("JAVA_HOME")
    if home and Path(home, "bin", "java").exists():
        return str(Path(home, "bin", "java"))
    found = shutil.which("java")
    if found:
        return found
    for cand in JAVA_CANDIDATES:
        if Path(cand).exists():
            return cand
    # macOS: ask the system for the current JDK.
    if shutil.which("/usr/libexec/java_home"):
        out = subprocess.run(["/usr/libexec/java_home"], capture_output=True, text=True)
        if out.returncode == 0:
            cand = Path(out.stdout.strip(), "bin", "java")
            if cand.exists():
                return str(cand)
    raise FVUError(
        "No Java runtime found. Install a JDK (macOS: brew install openjdk) and set "
        "TDS_JAVA or JAVA_HOME, or pass --java."
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


def _run_direct(cmd: list[str], cwd: Path, timeout: int) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _run_macos_gui(cmd: list[str], cwd: Path, timeout: int) -> tuple[int, str]:
    """Run the command inside the user's GUI session via a throw-away LaunchAgent."""
    label = f"com.tdsstatement.fvu.{uuid.uuid4().hex[:8]}"
    tmp = Path(tempfile.mkdtemp(prefix="tds-fvu-"))
    exit_file = tmp / "exit.code"
    log_file = tmp / "run.log"
    wrapper = tmp / "run.sh"
    quoted = " ".join("'" + a.replace("'", "'\\''") + "'" for a in cmd)
    wrapper.write_text(f"#!/bin/sh\n{quoted} > '{log_file}' 2>&1\necho $? > '{exit_file}'\n")
    wrapper.chmod(0o755)
    plist = tmp / f"{label}.plist"
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
        raise FVUError(f"launchctl bootstrap failed: {boot.stderr.strip() or boot.stdout.strip()}")
    deadline = time.time() + timeout
    while time.time() < deadline:
        if exit_file.exists():
            break
        time.sleep(0.5)
    subprocess.run(["launchctl", "bootout", f"gui/{uid}/{label}"], capture_output=True, text=True)
    if not exit_file.exists():
        raise FVUError(f"FVU did not finish within {timeout}s (launchd run left logs in {tmp})")
    code = int(exit_file.read_text().strip() or "-1")
    log = log_file.read_text() if log_file.exists() else ""
    return code, log + f"\n[launchd run dir: {tmp}]"


def run(txt: str | Path, out_dir: str | Path, csi: str | Path | None = None,
        jar: str | None = None, java: str | None = None,
        fmt: str = DEFAULT_FORMAT_VERSION, timeout: int = 600,
        extra: list[str] | None = None, force_mode: str | None = None) -> dict:
    txt = Path(txt).resolve()
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    if not txt.exists():
        raise FVUError(f"input not found: {txt}")
    if len(txt.name) > 12:
        raise FVUError(
            f"input name {txt.name!r} is {len(txt.name)} characters; the utility accepts "
            "12 or fewer including '.txt'. Copy it to a shorter name first."
        )
    csi_path = Path(csi).resolve() if csi else None
    if csi_path and not csi_path.exists():
        raise FVUError(f"CSI not found: {csi_path}")

    java_bin = find_java(java)
    jar_path = find_jar(jar)
    cmd = command(java_bin, jar_path, txt, out_dir, csi_path, fmt, extra)

    modes = ["direct", "macos-gui"] if sys.platform == "darwin" else ["direct", "xvfb"]
    if force_mode:
        modes = [force_mode]

    attempts = []
    result = None
    for mode in modes:
        try:
            if mode == "direct":
                code, log = _run_direct(cmd, out_dir, timeout)
            elif mode == "macos-gui":
                code, log = _run_macos_gui(cmd, out_dir, timeout)
            elif mode == "xvfb":
                if not shutil.which("xvfb-run"):
                    continue
                code, log = _run_direct(["xvfb-run", "-a"] + cmd, out_dir, timeout)
            else:
                raise FVUError(f"unknown mode {mode}")
        except subprocess.TimeoutExpired:
            attempts.append({"mode": mode, "error": "timeout"})
            continue
        attempts.append({"mode": mode, "exit_code": code})
        result = {"exit_code": code, "log": log, "mode": mode}
        # A run that produced artefacts is the run we want, whatever the exit code.
        if _artefacts(txt, out_dir)["fvu"] or _artefacts(txt, out_dir)["err"]:
            break

    if result is None:
        raise FVUError("the utility could not be started in any mode: " + json.dumps(attempts))

    arts = _artefacts(txt, out_dir)
    errors = parse_err(arts["err"]) if arts["err"] else []
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
        "attempts": attempts,
        "exit_code": result["exit_code"],
        "fvu": str(arts["fvu"]) if arts["fvu"] else None,
        "err": str(arts["err"]) if arts["err"] else None,
        "html": str(arts["html"]) if arts["html"] else None,
        "error_count": len(errors),
        "errors": errors,
        "status": _status(arts, errors, csi_path),
        "log_tail": result["log"][-4000:],
    }
    (out_dir / "fvu_result.json").write_text(json.dumps(outcome, indent=2) + "\n", encoding="utf-8")
    return outcome


def _artefacts(txt: Path, out_dir: Path) -> dict:
    """The utility names outputs after the input, but not always identically."""
    stem = txt.stem
    def pick(suffixes: list[str]) -> Path | None:
        for s in suffixes:
            cand = out_dir / f"{stem}{s}"
            if cand.exists():
                return cand
        hits = [p for p in out_dir.iterdir() if p.suffix.lower() in suffixes and p.is_file()] if out_dir.exists() else []
        return sorted(hits)[-1] if hits else None

    return {
        "fvu": pick([".fvu"]),
        "err": pick([".err"]),
        "html": (sorted(out_dir.glob("*err*.html"))[-1] if out_dir.exists() and list(out_dir.glob("*err*.html")) else None),
    }


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
        f"mode            {result['mode']} (exit {result['exit_code']})",
        f"jar             {Path(result['jar']).name}",
        f"java            {result['java_version']}",
        f"format          {result['format_version']}",
        f"CSI             {result['csi'] or '(none supplied)'}",
        f"FVU file        {result['fvu'] or '(not produced)'}",
        f"errors          {result['error_count']}",
    ]
    for e in result["errors"][:50]:
        if "raw" in e:
            lines.append(f"  ? {e['raw']}")
            continue
        lines.append(f"  {e.get('code', '?')}  line {e.get('line_no')}  {e.get('field_name')}  {e.get('message', '')}")
    return "\n".join(lines)
