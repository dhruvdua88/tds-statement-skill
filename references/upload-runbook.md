# Upload runbook

How a statement is actually filed, once the toolkit has produced it. This tool
never uploads anything: preparing a filing and filing it are different
decisions, and the second belongs to the person who signs.

Everything below was checked against the official user manuals for Forms 138,
140, 143 and 144, the four form FAQs, the TDS Compliance FAQ and the e-filing
portal's own pages, most recently on 19 October 2026. Where something could not
be confirmed it is marked as unverified rather than stated.

## What gets uploaded, and the one rule behind it

The portal accepts a **ZIP containing the `.fvu`**. It does not accept a bare
`.fvu`, and it does not accept the `.txt`. The `.fvu` exists only because the
official utility produced it, which is why a clean lint run can never make a
statement ready.

The utility's meaning is worth repeating: it validates the statement against the
file format *and* against the challans in the CSI. A statement that passes the
first and not the second is not validated, and the utility writes no upload file
when that happens.

## Route A: the e-filing portal, with the FVU

This route is fully documented in the official manual for each form and all four
manuals describe the same flow:

1. Log in to the e-filing portal **with the TAN**. The deductor's TAN must be
   registered there; that is a prerequisite, not a step.
2. Under `e-File > Income Tax Forms > File Income Tax Forms`, in the category
   "Forms as Per Income Tax Act 2025", select "Deduction and Collection at
   source (Form TDS/TCS)" and choose File Now.
3. Read the instructions, then Let's get Started.
4. Select the form (138, 140, 143 or 144), the tax year, the quarter, and the
   upload type (regular or correction).
5. Upload the ZIP holding the `.fvu`, then proceed to e-Verify.
6. Pick a verification method and verify. The confirmation goes to the
   registered e-mail and mobile.
7. Check the outcome under `e-File > Income Tax Forms > View Filed Forms`.
   Accepted means the statement is sent to TRACES for processing. Rejected
   means an e-mail to the primary registered address explains why.

## Route B: filing online on TRACES

The department has officially announced online filing of original and
correction statements for Forms 138, 140, 143 and 144 on TRACES, with an
Acknowledgement Receipt Number on submission. The function exists; the detail
does not.

What is not published anywhere reachable: the exact menu path, whether the same
file validation applies, and whether the CSI is consumed automatically. The menu
path that circulates on CA social posts, "Tax Year, quarter, regular/correction,
then Prepare & File Online", is **unverified**; so is the claim that the
facility is meant for short returns.

Practical rule: generate for Route A, which is fully specified, and mention
Route B as an alternative. When someone asks about Route B, verify the menu path
on a real TRACES login before advising.

## The CSI, and why it is a blocker

The Challan Status Inquiry file is mandatory. The file format says so in its own
notes, and the utility stops without it. A real CSI is downloaded from the
e-filing login **with the TAN**, under `e-File > e-Pay Tax Service > Payment
History`, filtered by a payment date range of up to 24 months, and Download
Challan File.

Three things to know before asking for one:

- The screen filters by **payment date range only**. There is no filter by
  assessment year or payment type, so whoever downloads it needs the payment
  dates, not just the quarter.
- It covers challans paid on or after 1 July 2022 through the e-filing portal.
  Earlier ones have to come from the old TIN portal.
- The file format requires the TAN and the TAN name in the statement to match
  the CSI exactly. That is a rejection on its own, before any field check.

A placeholder CSI is useful, because it takes the run as far as `T-FV-3175`,
which proves the statement is otherwise field-clean. It is not a filing.

## What the portal rejects

The official manuals list the same reasons on every form:

1. wrong tax year;
2. the same form filed twice for the same quarter;
3. the FVU version used does not match the version shown on the form screen;
4. a regular and a correction filing swapped;
5. the TAN in the file does not match the logged-in TAN;
6. on a correction, the RRR number typed on the screen does not match the RRR
   number inside the file.

Most of these are avoidable before the run. The checklist the toolkit writes
into the handover folder covers them; the one that needs the portal is item 3,
so confirm the FVU version the form screen displays on the day of upload.

## Deadlines, fee, interest and penalty

| Form | Reported under | Answers to | Due Q1 / Q2 / Q3 / Q4 |
|---|---|---|---|
| 138 | salary, section 392 | ex-24Q | 31 Jul · 31 Oct · 31 Jan · 31 May |
| 140 | resident non-salary | ex-26Q | same |
| 143 | tax collected at source | ex-27EQ | same |
| 144 | payments to non-residents | ex-27Q | same |

The Q4 date is 31 May of the financial year following the tax year, so 31 May
2027 for tax year 2026-27 Q4.

- **Fee for late filing, section 427.** 200 rupees for every day the failure
  continues, capped at the tax deductible or collectible, paid before the
  statement is delivered. Successor of section 234E.
- **Penalty, section 461.** Not less than 10,000 and up to 1,00,000 rupees for
  failure to deliver or for incorrect information. The relief in section 461(2)
  for paying the tax with fee and interest runs to **one month** from the
  prescribed time, which is shorter than the old section 271H comfort.
  The exact statutory wording of that relief has not been verified against the
  Act text directly; treat it as the working position and check before relying
  on it in advice.
- **Interest, section 398.** 1 percent a month for failure to deduct, and 1.5
  percent a month for failure to deposit after deduction.

## Corrections

A statement can be corrected only after CPC-TDS has processed the original.
Within two years from the end of the tax year in which the statement was due,
which for Form 140 Q2 of tax year 2026-27 runs to 31 March 2029.

The correction types are C1, C2, C3, C5 and C9: deductor details, challenge
details, deductee details, PAN update, and addition of a challan. Two fields on
the batch header carry the verification keys, the provisional receipt number of
the original regular statement and the token of the previous statement. When no
prior correction exists, quote the original provisional receipt in both.

Three rules that are easy to trip over: deleting a deductee record is not
allowed; C9 is not allowed for any deductor type other than central or state
government; and the assessment year, tax year and period on a correction are
verification keys, so they must repeat the original and cannot be updated.

Corrections for periods before 1 April 2026 stay under the 1961 Act with the old
form numbers, in their own two-year window.

## Form 27A

Form 27A is the control chart for the physical TIN-FC route, where a signed
paper copy goes with the CD or pen drive. The e-filing portal flow does not
ask for it once, in any of the four official manuals. Its legal position under
the 2026 rules has not been confirmed, so store the control totals rather than
declaring the form obsolete. Where it matters, the totals must agree with the
statement in the `.fvu`.

## What to keep after filing

Keep the source files, the statement document, the built `.txt`, the utility
result, the `.fvu`, and the acknowledgement with its provisional receipt and
token number. A correction six months later starts from these, and the
statement status can be checked on TRACES once processing is done.
