#!/usr/bin/env python3
"""Pipeline tests. No network, no official utility, no dependencies beyond openpyxl.

    python3 -m unittest discover -s tests -v

What these tests can and cannot prove: they prove the engine is self-consistent
and stable, and that intake reads a realistic messy sheet. They cannot prove the
department's utility will accept a file - only the utility can do that, which is
why the private regression test against a previously accepted statement exists
alongside these.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import build_txt  # noqa: E402
import intake  # noqa: E402
import lint  # noqa: E402
import queries  # noqa: E402
from model import Challan, Deductee, Statement, date8, norm_date  # noqa: E402

FIX = ROOT / "tests" / "fixtures"
GOLDEN = ROOT / "tests" / "golden"


class TestModel(unittest.TestCase):
    def test_financial_year_derivations(self):
        st = Statement(financial_year="2026-27")
        self.assertEqual(st.tax_year, "202627")
        self.assertEqual(st.assessment_year, "202728")
        self.assertEqual(Statement(financial_year="2025-26").assessment_year, "202627")

    def test_dates_normalise(self):
        for value, expected in [
            ("31-07-2026", "31-07-2026"), ("31072026", "31-07-2026"),
            ("31/07/2026", "31-07-2026"), ("2026-07-31", "31-07-2026"),
        ]:
            self.assertEqual(norm_date(value), expected, value)
        self.assertEqual(date8("31-07-2026"), "31072026")

    def test_bad_amount_is_refused_not_zeroed(self):
        with self.assertRaises(Exception):
            Deductee.from_dict({
                "challan_no": 1, "pan": "AAECS1234K", "name": "X", "section": "1023",
                "payment_date": "31-07-2026", "deduction_date": "31-07-2026",
                "amount_paid": "not a number", "tds": "1",
            })

    def test_deductee_code_from_pan(self):
        row = Deductee.from_dict({
            "challan_no": 1, "pan": "AAECS1234K", "name": "X", "section": "1023",
            "payment_date": "31-07-2026", "deduction_date": "31-07-2026",
            "amount_paid": "100", "tds": "1",
        })
        self.assertEqual(row.deductee_code, "C")

    def test_round_trip(self):
        st = Statement.load(FIX / "example_140.json")
        again = Statement.from_dict(json.loads(json.dumps(st.to_dict())))
        self.assertEqual(st.to_dict(), again.to_dict())


class TestBuild140(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.st = Statement.load(FIX / "example_140.json")
        cls.tmp = Path(tempfile.mkdtemp(prefix="tds-test-"))
        cls.manifest = build_txt.write(cls.st, cls.tmp)
        cls.txt = cls.tmp / cls.manifest["file"]
        cls.lines = cls.txt.read_bytes().decode("ascii").split("\r\n")
        if cls.lines and cls.lines[-1] == "":
            cls.lines.pop()

    def test_record_widths(self):
        widths = {"FH": 18, "BH": 72, "CD": 30, "DD": 45}
        for i, line in enumerate(self.lines, 1):
            parts = line.split("^")
            self.assertEqual(parts[0], str(i), f"line {i} numbering")
            self.assertIn(parts[1], widths, f"line {i} record type")
            self.assertEqual(len(parts), widths[parts[1]], f"line {i} {parts[1]} width")

    def test_record_order_and_interleaving(self):
        types = [line.split("^")[1] for line in self.lines]
        self.assertEqual(types[:2], ["FH", "BH"])
        self.assertEqual(types.count("CD"), 3)
        self.assertEqual(types.count("DD"), 6)
        open_cd = None
        for parts in (l.split("^") for l in self.lines):
            if parts[1] == "CD":
                open_cd = parts[3]
            elif parts[1] == "DD":
                self.assertEqual(parts[4], open_cd)

    def test_deductee_serial_is_global(self):
        serials = [int(l.split("^")[3]) for l in self.lines if l.split("^")[1] == "DD"]
        self.assertEqual(serials, list(range(1, 7)))

    def test_challan_allocation_ties(self):
        for row in self.st.allocation():
            self.assertEqual(row["remaining"], Decimal("0.00"), row)

    def test_file_hygiene(self):
        raw = self.txt.read_bytes()
        self.assertTrue(raw.endswith(b"\r\n"))
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
        raw.decode("ascii")
        self.assertEqual(self.lines[-1].split("^")[1], "DD")

    def test_golden_bytes(self):
        golden = GOLDEN / "example_140.txt"
        self.assertTrue(golden.exists(), "run tests/make_fixtures.py then tests/update_golden.py")
        self.assertEqual(hashlib.sha256(self.txt.read_bytes()).hexdigest(),
                         hashlib.sha256(golden.read_bytes()).hexdigest())

    def test_lint_is_clean(self):
        issues = lint.model_issues(self.st) + lint.txt_issues(self.txt, self.st, build_txt.load_layout("140"))
        errors = [str(i) for i in issues if i.level == lint.ERROR]
        self.assertEqual(errors, [], "\n".join(errors))

    def test_short_name_is_legal(self):
        self.assertLessEqual(len(build_txt.short_name(self.st)), 12)

    def test_build_refuses_over_allocated_challan(self):
        """Allocating more tax to a challan than was deposited is rejected by the utility."""
        st = Statement.load(FIX / "example_140.json")
        clone = Deductee.from_dict(st.deductees[0].to_dict())
        st.deductees.append(clone)
        with self.assertRaises(build_txt.BuildError):
            build_txt.write(st, tempfile.mkdtemp())

    def test_build_allows_an_under_allocated_challan(self):
        """A challan paid at a round figure may carry unallocated tax; that is legal.

        The utility only requires the deposit to be at least the tax it is asked
        to cover, so a builder that refused this would force a made-up figure on
        to a good filing.
        """
        st = Statement.load(FIX / "example_140.json")
        st.challans[0].tax += Decimal("500.00")
        st.challans[0].total += Decimal("500.00")
        manifest = build_txt.write(st, tempfile.mkdtemp())
        self.assertEqual(manifest["status"], "READY")
        notes = [i for i in lint.model_issues(st)
                 if i.level == lint.INFO and i.code == "ALLOCATION_EXCESS"]
        self.assertEqual(len(notes), 1)

    def test_build_refuses_fractional_challan_amount(self):
        """Fields 8 to 12 of the challan record are integer; paise are rejected."""
        st = Statement.load(FIX / "example_140.json")
        st.challans[0].tax += Decimal("0.50")
        st.challans[0].total += Decimal("0.50")
        with self.assertRaises(build_txt.BuildError):
            build_txt.write(st, tempfile.mkdtemp())


class TestLintCatchesProblems(unittest.TestCase):
    def test_missing_responsible_person_pan_is_an_error(self):
        st = Statement.load(FIX / "example_140.json")
        st.responsible_person["pan"] = ""
        codes = {i.code for i in lint.model_issues(st) if i.level == lint.ERROR}
        self.assertIn("RP_PAN", codes)

    def test_rate_deviation_is_flagged(self):
        st = Statement.load(FIX / "example_140.json")
        st.deductees[1].tds = Decimal("60000.00")
        st.deductees[1].amount_paid = Decimal("30000000.00")
        codes = {i.code for i in lint.model_issues(st) if i.level == lint.WARN}
        self.assertIn("RATE_DEVIATION", codes)

    def test_duplicate_rows_are_flagged(self):
        st = Statement.load(FIX / "example_140.json")
        clone = Deductee.from_dict(st.deductees[2].to_dict())
        clone.challan_no = 1
        st.deductees.append(clone)
        # rebalance so the allocation check does not mask the duplicate check
        st.challans[0].tax += clone.tds
        st.challans[0].total += clone.tds
        codes = {i.code for i in lint.model_issues(st) if i.level == lint.WARN}
        self.assertIn("POSSIBLE_DUPLICATE", codes)

    def test_draft_naming_when_something_is_outstanding(self):
        st = Statement.load(FIX / "example_140.json")
        st.pending = [{"field": "responsible_person.pan", "why": "client to provide", "blocking": True}]
        self.assertEqual(build_txt.output_name(st), "DRAFT_PENDING_HEADER.txt")
        manifest = build_txt.write(st, tempfile.mkdtemp())
        self.assertEqual(manifest["status"], "DRAFT")


class TestIntake(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="tds-intake-"))
        report = cls.tmp / "mapping.xlsx"
        cls.st, cls.summary = intake.intake(
            [str(FIX / "messy_source.xlsx")], form="140",
            financial_year="2026-27", quarter="Q2", report=str(report),
        )
        cls.report = report

    def test_rows_read(self):
        self.assertEqual(len(self.st.deductees), 6)
        self.assertEqual(len(self.st.challans), 3)

    def test_amounts_parsed_from_messy_text(self):
        first = self.st.deductees[0]
        self.assertEqual(first.amount_paid, Decimal("1500000.00"))
        self.assertEqual(first.tds, Decimal("15000.00"))

    def test_sections_read_from_descriptions(self):
        got = [r.section for r in self.st.deductees]
        self.assertEqual(got, ["1023", "1031", "1027", "1023", "1027", "1023"])

    def test_challans_read_from_their_own_tab(self):
        serials = sorted(c.challan_serial for c in self.st.challans)
        self.assertEqual(serials, ["90001", "90002", "90003"])

    def test_every_row_carries_a_source_reference(self):
        for row in self.st.deductees:
            self.assertTrue(row.source_ref.startswith("Deductee!"), row.source_ref)

    def test_total_row_is_not_taken_as_a_deductee(self):
        names = [r.name.lower() for r in self.st.deductees]
        self.assertNotIn("total", names)

    def test_allocation_ties_after_intake(self):
        for row in self.st.allocation():
            self.assertEqual(row["remaining"], Decimal("0.00"), row)

    def test_mapping_report_written(self):
        self.assertTrue(self.report.exists())

    def test_header_values_become_named_pending_items(self):
        fields = {p["field"] for p in self.st.pending}
        self.assertIn("deductor.tan", fields)
        self.assertIn("responsible_person.pan", fields)
        self.assertTrue(all(p["blocking"] for p in self.st.pending))

    def test_body_is_clean_once_the_header_is_supplied(self):
        """Intake cannot invent the deductor's own details; everything else must be right.

        Run against a copy: the class-level statement is shared between tests, and
        mutating it here would hide a pending-item failure in another test.
        """
        import copy as _copy
        st = Statement.from_dict(_copy.deepcopy(self.st.to_dict()))
        good = Statement.load(FIX / "example_140.json")
        st.deductor = dict(good.deductor)
        st.responsible_person = dict(good.responsible_person)
        st.pending = []
        issues = lint.model_issues(st)
        errors = [str(i) for i in issues if i.level == lint.ERROR]
        self.assertEqual(errors, [], "\n".join(errors))


class TestQueries(unittest.TestCase):
    """One list, from three sources, so a reviewer reads one place to know what is outstanding."""

    def _st(self):
        return Statement.load(FIX / "example_140.json")

    def test_no_run_yields_the_run_and_the_csi_as_blockers(self):
        rows = queries.build(self._st())
        refs = " | ".join(q["reference"] for q in queries.blockers(rows))
        self.assertIn("the official utility", refs)
        self.assertIn("Challan Status Inquiry", refs)
        self.assertFalse(queries.ready(rows))

    def test_a_pass_clears_everything(self):
        rows = queries.build(self._st(), fvu_result={"status": "PASS", "csi": "x.csi"})
        self.assertEqual(queries.blockers(rows), [])
        self.assertTrue(queries.ready(rows))
        self.assertEqual(queries.counts(rows)[queries.INFO], 1)

    def test_field_errors_become_blockers_naming_the_line(self):
        res = {"status": "FIELD_ERRORS", "csi": "x.csi", "errors": [
            {"line_no": "7", "record_type": "DD", "field_name": "8", "code": "T-FV-3175",
             "message": "bad pan"}]}
        bl = queries.blockers(queries.build(self._st(), fvu_result=res))
        self.assertEqual(len(bl), 1)
        self.assertIn("line 7", bl[0]["reference"])
        self.assertIn("T-FV-3175", bl[0]["issue"])

    def test_pending_is_not_repeated_by_the_linter(self):
        st = self._st()
        st.pending = [{"field": "deductor.tan", "why": "needed", "owner": "client", "blocking": True}]
        issues = [i.as_dict() for i in lint.model_issues(st)]
        rows = queries.build(st, issues, fvu_result={"status": "PASS", "csi": "x.csi"})
        self.assertEqual([q["reference"] for q in rows].count("deductor.tan"), 1)

    def test_ids_run_in_order_and_blockers_come_first(self):
        st = self._st()
        st.pending = [{"field": "a", "why": "w", "blocking": False}]
        rows = queries.build(st, [{"level": "error", "code": "X", "message": "m", "ref": "r"}],
                             fvu_result={"status": "PASS", "csi": "x.csi"})
        self.assertEqual([q["id"] for q in rows],
                         [f"Q-{n:02d}" for n in range(1, len(rows) + 1)])
        self.assertEqual(rows[0]["severity"], queries.BLOCKER)

    def test_a_client_facing_list_is_written(self):
        tmp = Path(tempfile.mkdtemp(prefix="tds-q-"))
        xlsx, md = queries.write_sidecar(self._st(), tmp)
        self.assertTrue(xlsx.exists() and md.exists())
        self.assertIn("Blockers", md.read_text())


class TestCli(unittest.TestCase):
    def test_schema_and_check_env_run(self):
        out = subprocess.run([sys.executable, str(SCRIPTS / "tds.py"), "schema"],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0)
        self.assertIn("tds-statement/1", out.stdout)

    def test_every_form_the_cli_offers_has_a_layout_and_a_golden_file(self):
        import importlib
        import tds
        self.assertEqual(sorted(tds.FORM_CHOICES), ["138", "140", "144"])
        for form in tds.FORM_CHOICES:
            layout = importlib.import_module(build_txt.LAYOUT_MODULES[form])
            self.assertEqual(layout.FORM, form)
            fixture = FIX / f"example_{form}.json"
            golden = GOLDEN / f"example_{form}.txt"
            self.assertTrue(fixture.exists() and golden.exists(), form)
            tmp = Path(tempfile.mkdtemp(prefix="tds-golden-"))
            manifest = build_txt.write(Statement.load(fixture), tmp)
            self.assertEqual((tmp / manifest["file"]).read_bytes(), golden.read_bytes(), form)

    def test_a_form_without_a_layout_is_refused_in_one_line(self):
        tmp = Path(tempfile.mkdtemp(prefix="tds-cli-"))
        doc = json.loads((FIX / "example_140.json").read_text())
        doc["form"] = "143"
        path = tmp / "st143.json"
        path.write_text(json.dumps(doc))
        for argv in (["lint", str(path)], ["build", str(path), "-o", str(tmp / "b")]):
            out = subprocess.run([sys.executable, str(SCRIPTS / "tds.py"), *argv],
                                 capture_output=True, text=True)
            self.assertNotEqual(out.returncode, 0, argv)
            self.assertIn("unsupported form '143'", out.stderr, argv)
            self.assertNotIn("Traceback", out.stderr, argv)
            self.assertEqual(len(out.stderr.strip().splitlines()), 1, out.stderr)

    def test_readme_test_count_is_true(self):
        sys.path.insert(0, str(ROOT / "tests"))
        import readme_count
        self.assertEqual(readme_count.claimed(), readme_count.count(),
                         "README.md test count has drifted; run make readme-count")

    def test_cli_errors_are_one_plain_line(self):
        tmp = Path(tempfile.mkdtemp(prefix="tds-err-"))
        bad = tmp / "bad.json"
        bad.write_text("{not json")
        broken = tmp / "broken.json"
        broken.write_text('{"challans": [{"tax": "1"}]}')
        for argv, needle in (
            (["lint", str(tmp / "missing.json")], "file not found"),
            (["build", str(bad), "-o", str(tmp)], "not valid JSON"),
            (["build", str(broken), "-o", str(tmp)], "required value is missing"),
            (["intake", str(tmp / "missing.xlsx"), "-o", str(tmp / "x.json")], "file not found"),
        ):
            out = subprocess.run([sys.executable, str(SCRIPTS / "tds.py"), *argv],
                                 capture_output=True, text=True)
            self.assertNotEqual(out.returncode, 0, argv)
            self.assertNotIn("Traceback", out.stderr, argv)
            self.assertIn(needle, out.stderr, argv)
            self.assertEqual(len(out.stderr.strip().splitlines()), 1, out.stderr)
        import os
        env = dict(os.environ, TDS_DEBUG="1")
        out = subprocess.run([sys.executable, str(SCRIPTS / "tds.py"), "lint", str(tmp / "missing.json")],
                             capture_output=True, text=True, env=env)
        self.assertIn("Traceback", out.stderr)

    def test_build_and_lint_via_cli(self):
        tmp = Path(tempfile.mkdtemp(prefix="tds-cli-"))
        build = subprocess.run(
            [sys.executable, str(SCRIPTS / "tds.py"), "build",
             str(FIX / "example_140.json"), "-o", str(tmp)],
            capture_output=True, text=True)
        self.assertEqual(build.returncode, 0, build.stderr)
        lint_run = subprocess.run(
            [sys.executable, str(SCRIPTS / "tds.py"), "lint",
             str(FIX / "example_140.json"), "--txt", str(tmp / "EX140Q2.txt")],
            capture_output=True, text=True)
        self.assertEqual(lint_run.returncode, 0, lint_run.stdout + lint_run.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
