"""Interest for late deduction and late deposit, and the fee for filing late.

This is a working, not a liability. It computes what section 398(3)(a) and
section 427 of the Income-tax Act, 2025 would charge on the dates in the
statement, sets that against the interest and fee the challans actually carry,
and reports the difference. It never adds anything to a challan: interest is
paid by a challan someone decides to deposit, and the statement then reports
that challan as it was paid.

Three choices, stated so a reviewer can disagree with them:

* "Every month or part of a month" is counted the conservative way: every
  calendar month the period touches, the first and the last included. Deducted
  on 31 July and paid on 1 August is two months. A count of elapsed periods
  would say one; this working never says less than the higher figure.
* Tax becomes deductible on the date of payment or credit (DD field 19). A row
  deducted later than that carries late-deduction interest from that date.
* Late-deposit interest runs from the date of deduction to the challan date
  when the challan is later than the deposit due date in ``codes``. The due
  date for months other than March is marked [verify] there.

The late fee runs from the day after the statement due date to the filing date
at 200 rupees a day, capped at the tax deductible on the statement.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import codes
from model import Statement

ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def _d(value: str) -> date | None:
    try:
        return datetime.strptime(value, "%d-%m-%Y").date() if value else None
    except ValueError:
        return None


def months_or_part(start: date, end: date) -> int:
    """Calendar months touched from start to end, both included; 0 when end is not later."""
    if end <= start:
        return 0
    return (end.year - start.year) * 12 + (end.month - start.month) + 1


def deposit_due(deducted: date) -> date:
    if deducted.month == 3:
        m, d_ = codes.DEPOSIT_DUE_MARCH
        return date(deducted.year, m, d_)
    y, m = (deducted.year + 1, 1) if deducted.month == 12 else (deducted.year, deducted.month + 1)
    return date(y, m, codes.DEPOSIT_DUE_DAY_OTHER_MONTHS)


def statement_due(financial_year: str, quarter: str) -> date | None:
    rule = codes.STATEMENT_DUE.get((quarter or "").upper())
    if not rule or len(financial_year or "") < 4 or not financial_year[:4].isdigit():
        return None
    month, day, years = rule
    return date(int(financial_year[:4]) + years, month, day)


def _pct(amount: Decimal, rate: Decimal, months: int) -> Decimal:
    return (amount * rate * months / Decimal(100)).quantize(CENT)


def compute(st: Statement, filed_on: str = "") -> dict:
    challans = {c.no: c for c in st.challans}
    rows = []
    for i, r in enumerate(st.deductees, 1):
        paid, deducted = _d(r.payment_date), _d(r.deduction_date)
        ch = challans.get(r.challan_no)
        deposited = _d(ch.challan_date) if ch else None
        late_ded_months = months_or_part(paid, deducted) if paid and deducted else 0
        due = deposit_due(deducted) if deducted else None
        late_dep_months = (months_or_part(deducted, deposited)
                           if due and deposited and deposited > due else 0)
        rows.append({
            "row": i, "name": r.name, "pan": r.pan, "section": r.section,
            "tds": r.total_tds, "payment_date": r.payment_date, "deduction_date": r.deduction_date,
            "challan": ch.challan_serial if ch else "", "challan_date": ch.challan_date if ch else "",
            "deposit_due": due.strftime("%d-%m-%Y") if due else "",
            "late_deduction_months": late_ded_months,
            "late_deduction_interest": _pct(r.total_tds, codes.INTEREST_LATE_DEDUCTION, late_ded_months),
            "late_deposit_months": late_dep_months,
            "late_deposit_interest": _pct(r.total_tds, codes.INTEREST_LATE_DEPOSIT, late_dep_months),
        })
    interest = sum((x["late_deduction_interest"] + x["late_deposit_interest"] for x in rows), ZERO)
    interest_paid = sum((c.interest for c in st.challans), ZERO)

    due = statement_due(st.financial_year, st.quarter)
    filed = _d(filed_on) or date.today()
    days_late = max((filed - due).days, 0) if due else 0
    tax = sum((r.total_tds for r in st.deductees), ZERO)
    fee_uncapped = (codes.LATE_FEE_PER_DAY * days_late).quantize(CENT)
    fee = min(fee_uncapped, tax)
    fee_paid = sum((c.fee for c in st.challans), ZERO)
    return {
        "rows": rows,
        "interest": interest, "interest_paid": interest_paid,
        "interest_short": max(interest - interest_paid, ZERO),
        "statement_due": due.strftime("%d-%m-%Y") if due else "",
        "filed_on": filed.strftime("%d-%m-%Y"), "filed_on_assumed": not _d(filed_on),
        "days_late": days_late, "fee_uncapped": fee_uncapped, "fee_cap": tax,
        "fee": fee, "fee_paid": fee_paid, "fee_short": max(fee - fee_paid, ZERO),
    }
