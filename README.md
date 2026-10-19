# tds-statement

Build Indian quarterly TDS statements from whatever the client sent, validate
them with the official utility, and hand over an upload-ready folder.

Under the Income-tax Act, 2025 the quarterly statements are **Form 140**
(resident non-salary, earlier 26Q), **Form 138** (salary, earlier 24Q; Q1 to
Q3 for now, because the Q4 file format is not published yet) and **Form 144**
(payments to non-residents, earlier 27Q).
Statements are filed on the e-filing portal as a `.fvu` file that the
department's File Validation Utility has produced. This toolkit writes the
statement text file in the prescribed layout, checks it, runs the official
utility against the real Challan Status Inquiry, and packages what goes up.

## What it is good at

- **Reading real client sheets.** Title rows, month blocks, awkward headers,
  amounts stored as text, sections written as sentences, a total row in the
  middle, challans on a second tab. Intake maps what it can, reports what it
  could not map, and never drops a row quietly.
- **Catching the two failures that actually happen.** Deductee rows that do not
  add up to their challan, and the same invoice entered twice in consecutive
  months. Both are found before the utility sees the file.
- **Proving validation rather than asserting it.** The only proof is the `.fvu`
  file the official utility writes. Nothing here claims a pass without it.
- **A draft that announces itself.** While a required header value is missing,
  the statement is named `DRAFT_PENDING_HEADER.txt` and the package says NOT
  READY in its first line.
- **One query list, and blockers named.** The TXT, the workbook and a standalone
  query file all carry the same list of what is outstanding, each item tied to
  the field or record it is about. A real Challan Status Inquiry is a blocker in
  its own right, because the utility cannot write a `.fvu` without it.

## Install

```bash
git clone <this repo> ~/TDS-Statement-Skill
cd ~/TDS-Statement-Skill
python3 -m pip install --user openpyxl        # only outside dependency
python3 tests/make_fixtures.py
python3 -m unittest discover -s tests         # 133 checks, no network needed
```

To use it as an agent skill, put the folder where your agent looks for skills:

```bash
ln -s ~/TDS-Statement-Skill ~/.claude/skills/tds-statement
```

To run the official utility you also need a Java runtime and the department's
package, which is never redistributed here:

```bash
brew install openjdk                          # macOS
python3 scripts/tds.py fetch-official --list  # where to download it
python3 scripts/tds.py fetch-official --url <the current FVU zip>
python3 scripts/tds.py check-env
```

## Six commands

```bash
S=~/TDS-Statement-Skill

python3 $S/scripts/tds.py intake client_sheet.xlsx -o statement.json \
        --form 140 --fy 2026-27 --quarter Q2 --report mapping.xlsx   # 1 read
python3 $S/scripts/tds.py lint statement.json --json issues.json      # 2 check
python3 $S/scripts/tds.py build statement.json -o build/             # 3 write the TXT
python3 $S/scripts/tds.py fvu build/TAN140Q2.txt --csi challan.csi -o fvu_out/   # 4 validate
python3 $S/scripts/tds.py queries statement.json -o queries.xlsx \
        --fvu-result fvu_out/fvu_result.json --issues issues.json     # 5 what is outstanding
python3 $S/scripts/tds.py package statement.json -o deliverables/ \
        --txt-dir build --fvu-result fvu_out/fvu_result.json \
        --working-paper working.xlsx --issues issues.json             # 6 hand over
```

`python3 scripts/tds.py --help` lists everything, including `excel`,
`check-env` and `schema`.

## Requirements

Python 3.9 or later, `openpyxl` for reading sources and writing the workbook,
and a Java runtime for the official utility. macOS also needs the utility to be
started inside the logged-in GUI session, which the FVU runner handles by
itself.

## Layout

```
scripts/     the pipeline: model, intake, layouts, builder, lint, fvu, excel, queries, package
references/  the field tables, the section codes, the two runbooks
tests/       fixtures, golden files, the test suite
```

## Standing rules this toolkit enforces

1. Never claim validation without the `.fvu` file.
2. Never invent a PAN, a TAN, a phone number or an address to make a file pass.
3. Never drop a source row silently.
4. Never upload. The folder is handed over; a person uploads it.
