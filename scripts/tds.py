#!/usr/bin/env python3
"""One entry point for the whole pipeline.

    tds intake   SOURCE...  -o statement.json      read what the client sent
    tds lint     statement.json                    pre-flight checks
    tds build    statement.json -o build/          write the TXT
    tds fvu      build/X.txt --csi challan.csi     run the official utility
    tds excel    statement.json -o working.xlsx    build the working paper
    tds queries  statement.json -o queries.xlsx    the blockers stopping the .fvu
    tds package  statement.json -o deliverables/   assemble the filing folder
    tds fetch-official                             download the official utilities
    tds check-env                                  is this machine able to run the FVU
    tds schema                                     the document contract, annotated

Every subcommand prints what it did and returns a non-zero exit code when
something needs attention, so it can be driven from a script or a Makefile.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from model import SCHEMA_HELP, Statement  # noqa: E402


def cmd_intake(args) -> int:
    import intake

    overrides = {}
    for item in args.map or []:
        if "=" not in item:
            print(f"--map needs field=header, got {item!r}", file=sys.stderr)
            return 2
        fld, hdr = item.split("=", 1)
        overrides[hdr.strip()] = fld.strip()

    st, summary = intake.intake(
        args.sources, form=args.form, financial_year=args.fy or "",
        quarter=args.quarter or "", overrides=overrides, report=args.report,
    )
    out = Path(args.out)
    st.save(out)
    print(f"read {summary['deductees']} deductee rows and {summary['challans']} challans")
    print(f"sheets     {', '.join(s['sheet'] for s in summary['sheets']) or '(none recognised)'}")
    if summary["skipped"]:
        print(f"skipped    {summary['skipped']} row(s) - see the mapping report")
    for sheet, hdrs in summary["unmapped"].items():
        if hdrs:
            print(f"unused     {sheet}: {', '.join(hdrs)}")
    print(f"wrote      {out}")
    if args.report:
        print(f"report     {args.report}")
    print("\nNext: open the mapping report, fix anything wrong, then run 'tds lint'.")
    return 0


def cmd_lint(args) -> int:
    import build_txt
    import lint

    st = Statement.load(args.statement)
    issues = lint.model_issues(st)
    if args.txt:
        layout = build_txt.load_layout(st.form)
        issues += lint.txt_issues(args.txt, st, layout)
    print(lint.format_issues(issues, limit=args.limit))
    if args.json:
        Path(args.json).write_text(json.dumps([i.as_dict() for i in issues], indent=2) + "\n")
    return 1 if lint.counts(issues)["errors"] else 0


def cmd_build(args) -> int:
    import build_txt

    st = Statement.load(args.statement)
    manifest = build_txt.write(st, args.out)
    print(json.dumps(manifest["records"], indent=2))
    print(f"status     {manifest['status']}" + (f" ({manifest['draft_reason']})" if manifest["draft_reason"] else ""))
    print(f"file       {Path(args.out) / manifest['file']}  ({manifest['bytes']} bytes)")
    print(f"short name {Path(args.out) / manifest['short_name_copy']}")
    print(f"sha256     {manifest['sha256'][:24]}...")
    print(f"totals     tax {manifest['totals']['tax']} + interest {manifest['totals']['interest']} "
          f"= deposit {manifest['totals']['deposit']}")
    return 0


def cmd_fvu(args) -> int:
    import fvu

    if args.check:
        return cmd_check_env(args)
    result = fvu.run(args.txt, args.out, csi=args.csi, jar=args.jar, java=args.java,
                     fmt=args.format_version, timeout=args.timeout, force_mode=args.mode)
    print(fvu.summarise(result))
    if result["status"] == "PASS":
        print("\nThe utility produced a .fvu file. That is the file to upload.")
        return 0
    if result["status"] == "FIELD_ERRORS":
        print("\nFix the fields above and run again. Do not upload anything yet.")
        return 1
    print("\nThe run did not finish. Most often this is a placeholder CSI: challan matching "
          "needs the real CSI for the TAN, which only the deductor's portal login can produce.")
    return 1


def cmd_excel(args) -> int:
    import excel

    st = Statement.load(args.statement)
    fvu_result = None
    if args.fvu_result:
        fvu_result = json.loads(Path(args.fvu_result).read_text())
    issues = None
    if args.issues:
        issues = json.loads(Path(args.issues).read_text())
    excel.build(st, args.out, fvu_result=fvu_result, issues=issues)
    print(f"wrote {args.out}")
    return 0


def cmd_queries(args) -> int:
    import queries

    st = Statement.load(args.statement)
    issues = json.loads(Path(args.issues).read_text()) if args.issues else None
    fvu_result = json.loads(Path(args.fvu_result).read_text()) if args.fvu_result else None
    rows = queries.build(st, issues, fvu_result)
    n = queries.counts(rows)
    print(f"FVU      {queries.fvu_status_label(fvu_result)}")
    print(f"blockers {n['BLOCKER']}  warnings {n['WARNING']}  recorded {n['INFO']}")
    for q in queries.blockers(rows):
        print(f"  {q['id']}  {q['reference']}: {q['issue']}"
              + (f"  ({q['owner']})" if q["owner"] else ""))
    if args.out:
        out = Path(args.out)
        if out.suffix.lower() in (".xlsx", ".xlsm"):
            queries.write_xlsx(st, out, issues, fvu_result)
        else:
            queries.write_markdown(st, out, issues, fvu_result)
        print(f"wrote    {out}")
    return 1 if n["BLOCKER"] else 0


def cmd_package(args) -> int:
    import package

    result = package.assemble(
        args.statement, out_dir=args.out, txt_dir=args.txt_dir, fvu_result=args.fvu_result,
        working_paper=args.working_paper,
        issues=json.loads(Path(args.issues).read_text()) if args.issues else None,
    )
    print(json.dumps(result, indent=2))
    return 0


def cmd_fetch_official(args) -> int:
    import fetch_official

    return fetch_official.main(dest=args.dest, list_only=args.list, url=args.url, kind=args.kind)


def cmd_check_env(args) -> int:
    import fvu

    ok = True
    print("environment check")
    try:
        java = fvu.find_java(getattr(args, "java", None))
        print(f"  java           {java}")
        print(f"  java version   {fvu.check_java_version(java)}")
    except Exception as exc:
        ok = False
        print(f"  java           MISSING - {exc}")
    try:
        jar = fvu.find_jar(getattr(args, "jar", None))
        print(f"  FVU jar        {jar}")
    except Exception as exc:
        ok = False
        print(f"  FVU jar        MISSING - {exc}")
    csi = getattr(args, "csi", None)
    print(f"  CSI            {csi if csi else 'not supplied (field-level validation only)'}")
    try:
        import openpyxl  # noqa: F401
        print("  openpyxl       available")
    except ImportError:
        ok = False
        print("  openpyxl       MISSING - pip install openpyxl (needed for intake and the workbook)")
    print("  platform       " + sys.platform)
    return 0 if ok else 1


def cmd_schema(args) -> int:
    print(SCHEMA_HELP)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="tds", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("intake", help="read source files into the statement document")
    s.add_argument("sources", nargs="+")
    s.add_argument("-o", "--out", required=True, help="statement JSON to write")
    s.add_argument("--form", default="140", choices=["138", "140", "144"])
    s.add_argument("--fy", default="", help="financial year, e.g. 2026-27")
    s.add_argument("--quarter", default="", help="Q1..Q4")
    s.add_argument("--report", default="", help="mapping report workbook to write")
    s.add_argument("--map", action="append", help="force a mapping, field=header (repeatable)")
    s.set_defaults(func=cmd_intake)

    s = sub.add_parser("lint", help="pre-flight checks on the document (and a TXT if given)")
    s.add_argument("statement")
    s.add_argument("--txt", default="")
    s.add_argument("--json", default="", help="write the issues as JSON here")
    s.add_argument("--limit", type=int, default=None)
    s.set_defaults(func=cmd_lint)

    s = sub.add_parser("build", help="write the statement TXT")
    s.add_argument("statement")
    s.add_argument("-o", "--out", required=True)
    s.set_defaults(func=cmd_build)

    s = sub.add_parser("fvu", help="run the official File Validation Utility")
    s.add_argument("txt")
    s.add_argument("-o", "--out", required=True)
    s.add_argument("--csi", default="")
    s.add_argument("--jar", default="")
    s.add_argument("--java", default="")
    s.add_argument("--format-version", default="1.2")
    s.add_argument("--timeout", type=int, default=600)
    s.add_argument("--mode", default=None, choices=["direct", "macos-gui", "xvfb"])
    s.add_argument("--check", action="store_true", help="only check the environment")
    s.set_defaults(func=cmd_fvu)

    s = sub.add_parser("excel", help="build the working paper")
    s.add_argument("statement")
    s.add_argument("-o", "--out", required=True)
    s.add_argument("--fvu-result", default="")
    s.add_argument("--issues", default="")
    s.set_defaults(func=cmd_excel)

    s = sub.add_parser("queries", help="the query list and the blockers stopping the .fvu")
    s.add_argument("statement")
    s.add_argument("-o", "--out", default="", help="write the list here (.xlsx or .md)")
    s.add_argument("--issues", default="", help="lint issues JSON from 'tds lint --json'")
    s.add_argument("--fvu-result", default="")
    s.set_defaults(func=cmd_queries)

    s = sub.add_parser("package", help="assemble the filing folder")
    s.add_argument("statement")
    s.add_argument("-o", "--out", required=True)
    s.add_argument("--txt-dir", default="")
    s.add_argument("--fvu-result", default="")
    s.add_argument("--working-paper", default="")
    s.add_argument("--issues", default="")
    s.set_defaults(func=cmd_package)

    s = sub.add_parser("fetch-official", help="download the official RPU/FVU packages")
    s.add_argument("--dest", default=str(Path.home() / ".tds-utils"))
    s.add_argument("--list", action="store_true", help="show the known download URLs")
    s.add_argument("--url", default="", help="download this URL instead of the known ones")
    s.add_argument("--kind", default="fvu", choices=["fvu", "rpu", "format"])
    s.set_defaults(func=cmd_fetch_official)

    s = sub.add_parser("check-env", help="can this machine run the FVU?")
    s.add_argument("--java", default="")
    s.add_argument("--jar", default="")
    s.add_argument("--csi", default="")
    s.set_defaults(func=cmd_check_env)

    s = sub.add_parser("schema", help="print the document contract")
    s.set_defaults(func=cmd_schema)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
