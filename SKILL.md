---
name: tds-statement
description: >
  Prepare, validate and hand over an Indian quarterly TDS/TCS statement from whatever the
  client actually sent: the statement text file in the prescribed layout, the official
  utility run, and an upload-ready folder with the working paper. Use this whenever the
  subject is a quarterly TDS or TCS statement or its files, including Form 140 (resident
  non-salary, earlier 26Q) and Form 138 (salary, earlier 24Q), and whenever someone asks
  to build a TDS TXT, generate or check a .fvu, run the RPU or FVU, match deductees to
  challans, prepare a Form 27A working, reconcile challans against a CSI, diagnose an FVU
  error such as T-FV-2235, or file a correction statement. Trigger it even when the request
  sounds smaller than that, for example "prepare the TDS return from this sheet", "make the
  26Q file", "why did the utility reject this", or "we need to file AWR's TDS for the
  quarter". Do not use it for GST returns, income tax returns or Form 16 generation.
---

# TDS statement preparation

Turn a client's working sheet into a validated quarterly statement, and be honest
about the difference between those two things.

The job is almost never the file format. It is deciding what each row means,
which challan it settles, and what to do with the rows that do not fit. The
format is mechanical and this toolkit does it. So the work here is: read the
source carefully, reconcile it, and leave a trail that a reviewer or a
successor can follow.

## The one rule that matters

**A statement is validated only when the official File Validation Utility has
written a `.fvu` file.** Nothing else counts. A clean lint run, a file that
looks right, a utility run that stopped early, a probe that passed with
placeholder data: none of these are validation and none of them are reported as
validation. If someone asks whether the file is ready, the answer is either
"the utility produced a .fvu" or "no". Say which.

Two consequences that come up constantly:

- The utility validates field by field and then matches challans against the
  Challan Status Inquiry. With an empty or placeholder CSI it stops at the
  matching stage and writes nothing. That is a useful partial run, and the
  correct way to describe it is "field-level validation only, challan matching
  not covered".
- A pattern-valid PAN that fails the checksum is still an error. `T-FV-2235`
  checks that the PAN of the person responsible is a real, valid PAN, so a
  plausible-looking placeholder will not do.

## The loop

### 1. Read the source

```bash
python3 scripts/tds.py intake <sources...> -o statement.json \
        --form 140 --fy 2026-27 --quarter Q2 --report mapping.xlsx
```

Intake writes two things: the statement document, and a mapping report
workbook. **Open the mapping report before anything else.** It lists every
column it mapped and its confidence, every row it skipped with the row number,
and every column it did not use. Fix the mapping (`--map field=header`) or fix
the source, then run intake again. A skipped row is a row that is not in the
statement, and the client will not notice it for you.

Intake reads the deductor's own details (TAN, name, GSTIN, contact) from the
title rows when they are there. When they are not, it records each missing
value as a blocking pending item, which is what makes the output a draft.

### 2. Check it

```bash
python3 scripts/tds.py lint statement.json
```

Errors are things the utility will reject or the filing will be wrong. Warnings
are things a person should look at. Read every warning; the rate-deviation and
duplicate warnings in particular are usually real and usually need a client
confirmation, not a silent fix.

### 3. Write the statement file

```bash
python3 scripts/tds.py build statement.json -o build/
```

This refuses to build if the deductee rows under any challan do not add up to
that challan, because the utility's error message for that situation does not
tell you which challan drifted.

If a required header value is still missing, the file is named
`DRAFT_PENDING_HEADER.txt` and a byte-identical short-name copy is written
alongside it. The utility rejects input names longer than 12 characters
including `.txt`, which is why the copy exists and why it is the one you run.

### 4. Run the official utility

```bash
python3 scripts/tds.py fvu build/<short>.txt --csi challan.csi -o fvu_out/
```

Read `references/fvu-runbook.md` when anything goes wrong, and
`references/upload-runbook.md` for the filing itself. The runner tries a direct
invocation first and, on macOS, falls back to starting the utility inside the
logged-in GUI session, which is the only way it runs there.

Field errors are reported with their codes and the field each one refers to.
Fix the document, rebuild, run again. Never patch the generated file.

### 5. Hand over

```bash
python3 scripts/tds.py excel statement.json -o working.xlsx \
        --fvu-result fvu_out/fvu_result.json --issues issues.json
python3 scripts/tds.py package statement.json -o deliverables/ \
        --txt-dir build --fvu-result fvu_out/fvu_result.json \
        --working-paper working.xlsx --issues issues.json
```

The folder always carries five things: the statement TXT, the working paper, the
query list, the Form 27A figures, and a checklist whose first line says READY TO
UPLOAD or NOT READY. The `.fvu` is there only when the utility produced it.

**The query list is a deliverable, not a by-product.** `tds queries` writes it
on its own (a workbook for the client and a note that can be pasted into an
e-mail), and the same list is the workbook's *Queries & Blockers* tab. It merges
the three things that can hold a statement up: the values the builder was
missing, the pre-flight findings, and what the utility said. Every entry names
the field or record it is about, so it can go to the client without rewriting.

Anything marked BLOCKER stops the `.fvu`: nothing is uploaded while a blocker
stands, and the Excel and the query list both say so. A real Challan Status
Inquiry is always one of them, because without it the utility cannot produce a
`.fvu` at all and the most this pipeline can honestly claim is field-level
validation.

**Never upload.** Preparing a filing and filing it are different decisions, and
the second one belongs to the person who signs.

## The document

`statement.json` is the single source of truth. Run `tds schema` for the
annotated contract. The parts that carry the judgement:

- `deductees[]` carries one row per deductee, with `challan_no` linking it to
  the challan it settles, `source_ref` back to the cell it came from, and
  `remarks` for anything a reviewer needs to know.
- `challans[]` carries the deposit as it was actually paid, with tax, interest,
  fee and penalty kept separate. Do not merge them; the return reports them
  separately and the challan matching depends on it.
- `flags[]` records every adjustment, inference and rate deviation, so the
  reasoning survives the filing.
- `pending[]` is the honest list of what is still outstanding. While it has a
  blocking item, the statement is a draft.

Dates are written `DD-MM-YYYY` throughout and converted to `DDMMYYYY` only in
the file records. Amounts are decimal, never float. Both of these exist because
spreadsheets reorder dates and lose paise, and the utility rejects both.

## Choosing the form

| Period | Salary | Resident non-salary | Non-resident |
|---|---|---|---|
| FY 2025-26 and earlier | 24Q | 26Q | 27Q |
| Tax year 2026-27 onward | 138 | 140 | 144 |

Salary and non-salary are separate statements, in separate files, with separate
tokens. Do not combine them. Read `references/form-140-layout.md`,
`references/form-138-layout.md` or `references/form-144-layout.md` for the field
tables of whichever you are building. Each layout module is taken from the
department's own file-format workbook (version 1.2, 22-Jul-2026), named in the
module's header.

Form 138 is written for Q1 to Q3 only. Q4 also needs the salary-detail records
of Annexure II, and the department has not published that workbook yet, so a Q4
build stops with an explanation instead of writing a file the utility rejects.
Form 144 needs ten non-resident figures per deductee (status, country, nature of
remittance, grossing up, rate basis and the like) that the statement document
carries in `meta.non_resident`, keyed by PAN; see the layout reference.

## What to ask the client for

Ask for these at the start, because the statement cannot be filed without them
and asking later costs a filing window: the deductor's PAN, the name,
designation, PAN, mobile and e-mail of the person responsible for TDS, the
address and phone to print, access to TRACES or the e-filing portal for the
TAN, and the Challan Status Inquiry for the quarter.

When a value is genuinely unavailable, leave the schema field blank and record
it in `pending`. Never invent one to get a clean run.

## Standards this toolkit holds

- TDS is filed TAN-wise. Do not split one TAN into separate statements per
  branch unless the filing history proves the scope is separate.
- Use the last day of the month preceding the challan deposit month for
  payment and deduction dates when the source gives none, and record the
  inference in `flags`. Do not leave the dates blank and do not treat the
  inference as a blocker.
- A suspected duplicate stays in the statement and is flagged. Removing a row
  needs the client's confirmation.
- Negative and reversal entries are carried as they are and flagged.
- Match a row to exactly one challan. When the source links a row to several,
  take the first and flag the split rather than inventing a ratio.
- Keep everything: the source files, the document, the built TXT, the utility
  output and the acknowledgement. A correction six months later starts from
  these.

## Environment

`tds check-env` reports whether this machine can run the utility. The parts
that are easy to get wrong:

- The utility needs a Java runtime. On macOS the system `java` shim is often
  absent; set `TDS_JAVA` or install `openjdk`.
- The utility is a desktop application. On macOS a plain shell cannot start it;
  the runner uses a throw-away LaunchAgent in the GUI session. On Linux,
  `xvfb-run` does the same.
- Set `TDS_FVU_JAR` if the jar is not in `~/.tds-utils`.
- Version discipline: check the live official page before each filing season.
  A statement validated by an old utility can still be rejected by the portal.
  `tds fetch-official --list` shows the recorded sources and versions.

## References

- `references/form-140-layout.md` - the field-by-field layout for the resident
  non-salary statement, with the official remarks.
- `references/form-138-layout.md` - the same for the salary statement (Q1 to Q3).
- `references/form-144-layout.md` - the same for the non-resident statement.
- `references/section-codes.md` - the section codes, state codes, deductor
  categories, reason codes and minor heads.
- `references/fvu-runbook.md` - running the utility, the error file format, the
  validation codes and what each family means.
- `references/upload-runbook.md` - the filing itself: the portal steps, the CSI,
  deadlines and fees, corrections, and Form 27A.
- `references/official-downloads.json` - where the official packages live and
  which version was last checked.
