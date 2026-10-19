#!/usr/bin/env python3
"""Smoke test for the local page: start the server, post the fixture through every step."""

from __future__ import annotations

import base64
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import ui  # noqa: E402

FIX = ROOT / "tests" / "fixtures"


def upload(path: Path) -> dict:
    return {"name": path.name, "data": base64.b64encode(path.read_bytes()).decode()}


class TestUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The FVU must not be needed: point it at paths that do not exist.
        cls.env = {k: os.environ.get(k) for k in ("TDS_FVU_JAR", "TDS_JAVA")}
        os.environ["TDS_FVU_JAR"] = "/nonexistent/fvu.jar"
        os.environ["TDS_JAVA"] = "/nonexistent/java"
        cls.server, cls.ws = ui.make_server(port=0, root=Path(tempfile.mkdtemp(prefix="tds-ui-test-")))
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        for k, v in cls.env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def post(self, step: str, body: dict) -> dict:
        req = urllib.request.Request(f"{self.base}/api/{step}", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as res:
            return json.loads(res.read())

    def get(self, url: str) -> bytes:
        with urllib.request.urlopen(self.base + url, timeout=30) as res:
            return res.read()

    def test_binds_localhost_only(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")

    def test_page_is_served(self):
        page = self.get("/").decode()
        self.assertIn("<title>TDS Statement</title>", page)
        self.assertIn("prefers-color-scheme: dark", page)
        self.assertIn(".fvu", page)

    def test_the_whole_flow_without_the_fvu(self):
        r = self.post("intake", {"source": upload(FIX / "messy_source.xlsx"), "form": "140",
                                 "fy": "2026-27", "quarter": "Q2"})
        self.assertNotIn("error", r, r)
        job = r["job"]
        self.assertEqual((r["deductees"], r["challans"]), (6, 3))
        self.assertTrue(r["issues"]["blockers"], "the header details are missing, so there are blockers")
        self.assertEqual(self.get(r["files"][0]["url"])[:1], b"{")

        # Fill in the header the way a user would: upload an edited statement.json.
        edited = json.loads(self.get(f"/files/{job}/statement.json"))
        good = json.loads((FIX / "example_140.json").read_text())
        edited["deductor"], edited["responsible_person"], edited["pending"] = (
            good["deductor"], good["responsible_person"], [])
        path = Path(tempfile.mkdtemp()) / "statement.json"
        path.write_text(json.dumps(edited))
        r = self.post("statement", {"job": job, "statement": upload(path)})
        self.assertEqual(r["issues"]["blockers"], [], r["issues"]["blockers"])

        r = self.post("build", {"job": job})
        self.assertEqual(r["status"], "READY", r)
        txt = self.get(r["files"][0]["url"])
        self.assertTrue(txt.endswith(b"\r\n") and b"^FH^NS1^R^" in txt)

        ledger = Path(tempfile.mkdtemp()) / "ledger.csv"
        ledger.write_text("Date,Ledger,Amount\n31-07-2026,TDS 194C,-33500\n31-07-2026,TDS 194Q,-30000\n"
                          "31-08-2026,TDS 194J(a),-25000\n")
        r = self.post("excel", {"job": job, "filed_on": "10-11-2026", "ledger": upload(ledger)})
        self.assertNotIn("error", r, r)
        self.assertEqual(r["interest"]["days_late"], "10")
        self.assertFalse(any(x["differs"] for x in r["recon"]), r["recon"])
        self.assertEqual(self.get(r["files"][0]["url"])[:2], b"PK")

        r = self.post("check-env", {})
        self.assertIn("ready", r)   # machine-dependent; it answers rather than failing

        corrected = json.loads(self.get(f"/files/{job}/statement.json"))
        corrected["deductees"][0]["pan"] = "AAECS1235K"
        path = Path(tempfile.mkdtemp()) / "corrected.json"
        path.write_text(json.dumps(corrected))
        r = self.post("correct", {"job": job, "corrected": upload(path),
                                  "original_token": "123456789012345", "consolidated_hash": "H"})
        self.assertEqual((r.get("type"), r.get("status")), ("C5", "READY"), r)
        r = self.post("correct", {"job": job, "corrected": upload(path), "conso": upload(path),
                                  "original_token": "1"})
        self.assertIn("not published", r["error"])

        r = self.post("package", {"job": job})
        self.assertFalse(r["ready"], "no .fvu, so never ready")
        self.assertTrue(r["blockers"])
        self.assertEqual(self.get(r["files"][0]["url"])[:2], b"PK")

    def test_errors_are_plain_lines(self):
        r = self.post("build", {"job": "nosuchjob"})
        self.assertIn("start again", r["error"])
        r = self.post("intake", {"form": "140"})
        self.assertIn("choose the source", r["error"])
        bad = Path(tempfile.mkdtemp()) / "x.pdf"
        bad.write_bytes(b"%PDF")
        r = self.post("intake", {"source": upload(bad), "form": "140"})
        self.assertNotIn("Traceback", r["error"])
        self.assertEqual(len(r["error"].splitlines()), 1)

    def test_files_cannot_escape_the_job_folder(self):
        r = self.post("intake", {"source": upload(FIX / "messy_source.xlsx"), "form": "140",
                                 "fy": "2026-27", "quarter": "Q2"})
        with self.assertRaises(urllib.error.HTTPError):
            self.get(f"/files/{r['job']}/../../etc/passwd")


if __name__ == "__main__":
    unittest.main(verbosity=2)
