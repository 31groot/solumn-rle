"""Mid-cycle plan change proration. The rules are in BILLING_SPEC.md."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from fractions import Fraction

from calendar_utils import days_360, days_365, period_bounds
from plans import ANNUAL, MONTHLY, PAISE, Plan, Subscription, get_plan

PERIOD_MONTHS = {MONTHLY: 1, ANNUAL: 12}
PERIOD_DAYS = {MONTHLY: 30, ANNUAL: 365}


@dataclass(frozen=True)
class ProrationResult:
    customer_id: str
    old_plan: str
    new_plan: str
    change_date: date
    period_start: date  # current period, credited for the old plan
    period_end: date  # exclusive
    new_period_start: date  # period the new plan is charged for
    new_period_end: date  # exclusive
    remaining_days: int
    period_days: int
    credit: Decimal  # unused value of the old plan, returned to the customer
    charge: Decimal  # value of the new plan
    net: Decimal  # positive: customer owes; negative: goes to account balance

    @property
    def interval_change(self) -> bool:
        return get_plan(self.old_plan).interval != get_plan(self.new_plan).interval


def billing_period(sub: Subscription, on: date) -> tuple[date, date]:
    return period_bounds(sub.anchor_date, PERIOD_MONTHS[sub.plan.interval], on)


def validate_change(old: Plan, new: Plan) -> None:
    if old.code == new.code:
        raise ValueError(f"subscription is already on {old.code}")
    if old.currency != new.currency:
        raise ValueError("plans are priced in different currencies")


def round_money(x: Fraction) -> Decimal:
    """Round an exact amount once, half-even, to paise."""
    return (Decimal(round(x * 100)) / 100).quantize(PAISE)


def remaining_days(sub: Subscription, start: date, end: date, on: date) -> int:
    """Days left in the current period from `on`, in the plan's day count."""
    if on == start:
        return PERIOD_DAYS[sub.plan.interval]
    if sub.plan.interval == MONTHLY:
        return days_360(on, end, sub.anchor_day)
    return days_365(on, end)


def prorate_change(sub: Subscription, new_plan_code: str, change_date: date) -> ProrationResult:
    """Credit for the unused part of the current plan and charge for the new one."""
    old = sub.plan
    new = get_plan(new_plan_code)
    validate_change(old, new)

    start, end = billing_period(sub, change_date)
    total = PERIOD_DAYS[old.interval]
    remaining = remaining_days(sub, start, end, change_date)
    share = Fraction(remaining, total)

    credit_x = min(Fraction(str(old.price)) * share, Fraction(str(sub.paid)))
    if new.interval == old.interval:
        charge_x = Fraction(str(new.price)) * share
        new_start, new_end = start, end
    else:
        # Interval switches re-anchor on the change date and charge a full first period.
        charge_x = Fraction(str(new.price))
        new_start, new_end = period_bounds(change_date, PERIOD_MONTHS[new.interval], change_date)

    credit, charge = round_money(credit_x), round_money(charge_x)
    return ProrationResult(
        customer_id=sub.customer_id,
        old_plan=old.code,
        new_plan=new.code,
        change_date=change_date,
        period_start=start,
        period_end=end,
        new_period_start=new_start,
        new_period_end=new_end,
        remaining_days=remaining,
        period_days=total,
        credit=credit,
        charge=charge,
        net=round_money(charge_x - credit_x),
    )
