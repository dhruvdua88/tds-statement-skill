#!/usr/bin/env python3
"""Keep the test count in README.md true: count the suite and rewrite the number.

    python3 tests/readme_count.py          # rewrite README.md
    python3 tests/readme_count.py --check  # exit 1 if README.md has drifted

test_pipeline runs the check, so a README that claims the wrong number fails
the suite instead of quietly going stale.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
PATTERN = re.compile(r"# (\d+) checks, no network needed")


def count() -> int:
    return unittest.TestLoader().discover(str(ROOT / "tests"), pattern="test_*.py").countTestCases()


def claimed() -> int | None:
    m = PATTERN.search(README.read_text(encoding="utf-8"))
    return int(m.group(1)) if m else None


def main(argv: list[str]) -> int:
    n = count()
    if "--check" in argv:
        if claimed() != n:
            print(f"README.md says {claimed()} checks, the suite has {n}; run make readme-count")
            return 1
        return 0
    text = README.read_text(encoding="utf-8")
    if not PATTERN.search(text):
        print("README.md has no '# N checks, no network needed' line to update")
        return 1
    README.write_text(PATTERN.sub(f"# {n} checks, no network needed", text), encoding="utf-8")
    print(f"README.md: {n} checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
