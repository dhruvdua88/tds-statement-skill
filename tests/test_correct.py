#!/usr/bin/env python3
"""Correction statements: only the changed records, in the shape the C3/C5 columns ask for.

The fixture pair is example_140.json (as filed) and correction_140.json (as it
should have been). Like the regular golden file, the correction golden proves
the output is stable and self-consistent; only the utility, run with the real
consolidated file hash, can prove it is accepted.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import correct  # noqa: E402
from model import Statement  # noqa: E402

FIX = ROOT / "tests" / "fixtures"
GOLDEN = ROOT / "tests" / "golden"


def load():
    return Statement.load(FIX / "example_140.json"), Statement.load(FIX / "correction_140.json")


def records(lines):
    return [line.split("^") for line in lines]


class TestCorrectionC3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="tds-corr-"))
        original, corrected = load()
        cls.manifest = correct.write(original, corrected, cls.tmp)
        cls.raw = (cls.tmp / cls.manifest["file"]).read_bytes()
        cls.recs = records(cls.raw.decode("ascii").split("\r\n")[:-1])

    def test_golden_bytes(self):
        self.assertEqual(self.raw, (GOLDEN / "correction_140.txt").read_bytes())

    def test_widths_and_line_numbers(self):
        for i, parts in enumerate(self.recs, 1):
            self.assertEqual(parts[0], str(i))
            self.assertEqual(len(parts), correct.WIDTHS[parts[1]], parts[1])

    def test_only_the_changed_records_are_written(self):
        self.assertEqual(self.manifest["correction_type"], "C3")
        self.assertEqual([p[1] for p in self.recs], ["FH", "BH", "CD", "DD", "DD", "DD"])
        self.assertEqual(self.recs[2][3], "2", "only challan 2 changed")
        self.assertEqual([p[5] for p in self.recs[3:]], ["U", "U", "A"])

    def test_header_carries_the_verification_keys(self):
        fh, bh = self.recs[0], self.recs[1]
        self.assertEqual(fh[3], "C")
        self.assertEqual(fh[17], "SYNTHETICHASH0001")
        self.assertEqual(bh[5], "C3")
        self.assertEqual(bh[6], "0", "batch updation indicator")
        self.assertEqual(bh[7], "123456789012345")
        self.assertEqual(bh[11], bh[12])
        self.assertEqual(bh[14], "", "BH 15 is blank when the batch is not updated")

    def test_update_repeats_the_filed_values_and_add_continues_the_serial(self):
        upd_pan, added = self.recs[4], self.recs[5]
        self.assertEqual((upd_pan[6], upd_pan[7]), ("AAHPD3456M", "AAHPD3457M"))
        self.assertEqual(upd_pan[3], "4", "an update keeps its filed serial")
        self.assertEqual(added[3], "7", "an addition follows the last filed serial (6)")
        self.assertEqual((added[6], added[25], added[41]), ("", "", ""))

    def test_challan_sums_are_additions_plus_update_deltas(self):
        cd = self.recs[2]
        # added 1000 + (12000 - 10000) + (2000 - 2000)
        self.assertEqual((cd[20], cd[21]), ("3000.00", "3000.00"))
        self.assertEqual(cd[6], "1", "the challan's own figures changed")
        self.assertEqual((cd[13], cd[15], cd[17], cd[19]), ("0180002", "90002", "07092026", "12000.00"))


class TestCorrectionChoices(unittest.TestCase):
    def test_pan_only_change_is_a_c5(self):
        original, _ = load()
        corrected = Statement.from_dict(original.to_dict())
        corrected.correction = {"original_token": "123456789012345", "consolidated_hash": "H"}
        corrected.deductees[0].pan = "AAECS1235K"
        result = correct.build(original, corrected)
        self.assertEqual(result["type"], "C5")
        recs = records(result["lines"])
        dd = recs[-1]
        self.assertEqual({i + 1 for i, v in enumerate(dd) if v}, {1, 2, 3, 4, 5, 8, 26, 42})
        self.assertEqual(recs[1][12], "", "BH 13 is blank on a C5")

    def test_missing_hash_makes_a_draft(self):
        original, corrected = load()
        corrected.correction.pop("consolidated_hash")
        manifest = correct.write(original, corrected, tempfile.mkdtemp())
        self.assertEqual(manifest["status"], "DRAFT")
        self.assertTrue(manifest["file"].startswith("DRAFT_"))

    def test_refusals_are_plain(self):
        cases = []
        original, _ = load()
        shorter = Statement.from_dict(original.to_dict())
        shorter.deductees.pop(0)
        cases.append((original, shorter, "deleting a deductee"))
        original, corrected = load()
        corrected.deductor["name"] = "OTHER NAME"
        cases.append((original, corrected, "C1/C2"))
        original, corrected = load()
        corrected.correction.pop("original_token")
        cases.append((original, corrected, "PRN"))
        original, _ = load()
        cases.append((original, Statement.from_dict(original.to_dict()), "nothing changed"))
        for a, b, needle in cases:
            with self.assertRaises(correct.CorrectionError) as ctx:
                correct.build(a, b)
            self.assertIn(needle, str(ctx.exception))

    def test_cli_refuses_the_conso_file_in_one_line(self):
        out = subprocess.run([sys.executable, str(SCRIPTS / "tds.py"), "correct",
                              str(FIX / "example_140.json"), str(FIX / "correction_140.json"),
                              "-o", tempfile.mkdtemp(), "--conso", "x.tds"],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 2)
        self.assertIn("not published", out.stderr)
        self.assertEqual(len(out.stderr.strip().splitlines()), 1)

    def test_cli_writes_the_correction(self):
        tmp = Path(tempfile.mkdtemp())
        out = subprocess.run([sys.executable, str(SCRIPTS / "tds.py"), "correct",
                              str(FIX / "example_140.json"), str(FIX / "correction_140.json"),
                              "-o", str(tmp)], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("C3", out.stdout)
        self.assertTrue((tmp / "correction_manifest.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
