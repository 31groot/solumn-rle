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
    # Always step from the anchor so a clamped month (e.g. 28 Feb) does not drag later periods back.
    k = 0
    while True:
        start, end = add_months(anchor, k * months), add_months(anchor, (k + 1) * months)
        if on < end:
            return start, end
        k += 1


def actual_days(start: date, end: date) -> int:
    """Calendar days from start (inclusive) to end (exclusive)."""
    return (end - start).days


def daynum_360(d: date, day: int | None = None) -> int:
    """30/360 day number; `day` overrides the day of month (billing dates use the anchor day)."""
    return 360 * d.year + 30 * (d.month - 1) + min(d.day if day is None else day, 30)


def days_360(start: date, end: date, anchor_day: int) -> int:
    """30/360 days from an ordinary date `start` to the billing date `end`."""
    return daynum_360(end, anchor_day) - daynum_360(start)


def days_365(start: date, end: date) -> int:
    """Days in [start, end) not counting any 29 February, capped at 365."""
    leap_days = sum(1 for y in range(start.year, end.year + 1)
                    if calendar.isleap(y) and start <= date(y, 2, 29) < end)
    return min(actual_days(start, end) - leap_days, 365)


def format_period(start: date, end: date) -> str:
    """Human-readable service period, e.g. '10 Mar 2025 - 9 Apr 2025'."""
    last = date.fromordinal(end.toordinal() - 1)
    return f"{start.day} {start:%b %Y} - {last.day} {last:%b %Y}"
