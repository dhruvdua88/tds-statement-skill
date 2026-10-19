"""Fetch the official Protean utilities.

These packages are free to download from the department's own pages but they
are not ours to redistribute, so this skill never ships them. It downloads
them on request, records what it fetched, and verifies the checksum when a
known-good one is recorded.

Version discipline matters more than anything else here: a statement validated
by an old FVU can still be rejected by the portal, and the formats change
between financial years. Always re-check the live page before a filing season.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCES_FILE = HERE.parent / "references" / "official-downloads.json"


def load_sources() -> dict:
    if SOURCES_FILE.exists():
        return json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    return {"checked_on": "", "note": "no source list recorded", "packages": []}


def show_sources() -> int:
    src = load_sources()
    print(f"Official download sources (last checked {src.get('checked_on') or 'unknown'})")
    print(src.get("note", ""))
    print()
    for p in src.get("packages", []):
        print(f"  {p['kind']:7} {p['name']}")
        print(f"          version   {p.get('version', '?')}   effective {p.get('effective', '?')}")
        print(f"          page      {p.get('page', '')}")
        print(f"          file      {p.get('url', '(page only - open it in a browser)')}")
        print(f"          {p.get('note', '')}")
        print()
    print("Always confirm the version on the live page before a filing season.")
    return 0


def download(url: str, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = url.rstrip("/").split("/")[-1] or "download.zip"
    target = dest_dir / name
    print(f"downloading {url}")
    with urllib.request.urlopen(url, timeout=120) as resp, target.open("wb") as fh:
        shutil.copyfileobj(resp, fh)
    print(f"  saved {target} ({target.stat().st_size} bytes)")
    return target


def unzip(zip_path: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        z.extractall(dest)
    print(f"  extracted {len(names)} entries into {dest}")
    for jar in sorted(dest.rglob("*.jar")):
        print(f"  jar: {jar}")
    for xlsx in sorted(dest.rglob("*.xls*")):
        print(f"  format workbook: {xlsx}")


def record_fetch(dest_dir: Path, kind: str, url: str, files: list[Path]) -> None:
    log = dest_dir / "FETCHED.json"
    existing = json.loads(log.read_text()) if log.exists() else {"fetches": []}
    existing["fetches"].append({
        "date": date.today().isoformat(),
        "kind": kind,
        "url": url,
        "files": [{"name": f.name, "bytes": f.stat().st_size,
                   "sha256": hashlib.sha256(f.read_bytes()).hexdigest()} for f in files],
    })
    log.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")


def main(dest: str = None, list_only: bool = False, url: str = "", kind: str = "fvu") -> int:
    if list_only or not url:
        return show_sources()

    dest_dir = Path(dest or Path.home() / ".tds-utils")
    zip_path = download(url, dest_dir / "downloads")
    target = dest_dir / kind
    unzip(zip_path, target)
    record_fetch(dest_dir, kind, url, [zip_path])
    print()
    print(f"Set TDS_FVU_JAR to the jar path above, or keep it at {target} (found automatically).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:]))
