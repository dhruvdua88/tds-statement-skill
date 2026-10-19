#!/usr/bin/env python3
"""Regenerate the golden files after a deliberate output change.

Golden files exist so that an accidental change to the layout, the ordering or
the number formatting shows up as a test failure rather than as a rejected
upload. Regenerate only when you have looked at the diff of the built file and
are satisfied it is intentional.

    python3 tests/update_golden.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

FIX = ROOT / "tests" / "fixtures"
GOLDEN = ROOT / "tests" / "golden"

import build_txt  # noqa: E402
from model import Statement  # noqa: E402


def main() -> int:
    GOLDEN.mkdir(parents=True, exist_ok=True)
    for fixture in sorted(FIX.glob("example_*.json")):
        tmp = Path(tempfile.mkdtemp(prefix="tds-golden-"))
        st = Statement.load(fixture)
        manifest = build_txt.write(st, tmp)
        target = GOLDEN / f"{fixture.stem}.txt"
        shutil.copy2(tmp / manifest["file"], target)
        print(f"{fixture.name} -> {target.relative_to(ROOT)}  sha256 {manifest['sha256'][:16]}...  "
              f"({manifest['bytes']} bytes, {manifest['records']['lines']} records)")
    import correct
    corrected = FIX / "correction_140.json"
    if corrected.exists():
        tmp = Path(tempfile.mkdtemp(prefix="tds-golden-"))
        manifest = correct.write(Statement.load(FIX / "example_140.json"), Statement.load(corrected), tmp)
        shutil.copy2(tmp / manifest["file"], GOLDEN / "correction_140.txt")
        print(f"{corrected.name} -> tests/golden/correction_140.txt  {manifest['correction_type']}  "
              f"({manifest['records']['lines']} records)")
    print("\nCommit the golden files together with the change that produced them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
