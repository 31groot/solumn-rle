"""Date helpers shared by invoicing and proration."""
from __future__ import annotations

import calendar
from datetime import date


def days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def is_month_end(d: date) -> bool:
    return d.day == days_in_month(d.year, d.month)


def clamp_to_month(year: int, month: int, day: int) -> date:
    """date(year, month, day), with day pulled back to the month's last day if needed."""
    return date(year, month, min(day, days_in_month(year, month)))


def add_months(d: date, months: int) -> date:
    """Shift d by whole months, clamping the day to the end of shorter months."""
    total = d.year * 12 + (d.month - 1) + months
    year, month0 = divmod(total, 12)
    return clamp_to_month(year, month0 + 1, d.day)


def period_bounds(anchor: date, months: int, on: date) -> tuple[date, date]:
    """Billing period containing `on` for periods of `months` months starting at anchor.

    Returns (start, end); end is exclusive and is the next period's start.
    """
    if months <= 0:
        raise ValueError("period length must be a positive number of months")
    if on < anchor:
        raise ValueError(f"{on} is before the subscription anchor {anchor}")
    start = anchor
    while True:
        end = add_months(start, months)
        if on < end:
            return start, end
        start = end


def actual_days(start: date, end: date) -> int:
    """Calendar days from start (inclusive) to end (exclusive)."""
    return (end - start).days


def days_360(start: date, end: date) -> int:
    """30/360 day count between two dates (day 31 counts as day 30)."""
    return (360 * (end.year - start.year) + 30 * (end.month - start.month)
            + min(end.day, 30) - min(start.day, 30))


def days_365(start: date, end: date) -> int:
    """Day count used for annual plans."""
    return actual_days(start, end)


def format_period(start: date, end: date) -> str:
    """Human-readable service period, e.g. '10 Mar 2025 - 9 Apr 2025'."""
    last = date.fromordinal(end.toordinal() - 1)
    return f"{start.day} {start:%b %Y} - {last.day} {last:%b %Y}"
