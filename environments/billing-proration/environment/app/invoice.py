"""Invoice assembly for renewals and mid-cycle plan changes."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from calendar_utils import format_period
from plans import Subscription, get_plan
from proration import ProrationResult, billing_period, prorate_change


@dataclass(frozen=True)
class InvoiceLine:
    description: str
    amount: Decimal


@dataclass
class Invoice:
    number: str
    customer_id: str
    issue_date: date
    period_start: date
    period_end: date  # exclusive
    currency: str
    lines: list[InvoiceLine] = field(default_factory=list)

    @property
    def total(self) -> Decimal:
        return sum((line.amount for line in self.lines), Decimal("0.00"))

    def add(self, description: str, amount: Decimal) -> None:
        self.lines.append(InvoiceLine(description, amount))

    def render(self) -> str:
        width = max([len(line.description) for line in self.lines] + [20])
        out = [
            f"Invoice {self.number}",
            f"Customer: {self.customer_id}    Issued: {self.issue_date:%d %b %Y}",
            f"Service period: {format_period(self.period_start, self.period_end)}",
            "",
        ]
        out += [f"{line.description:<{width}}  {line.amount:>12,.2f}" for line in self.lines]
        out += ["-" * (width + 14), f"{'Total ' + self.currency:<{width}}  {self.total:>12,.2f}"]
        return "\n".join(out)


def _invoice_number(kind: str, customer_id: str, on: date) -> str:
    return f"{kind}-{customer_id}-{on:%Y%m%d}"


def build_period_invoice(sub: Subscription, on: date) -> Invoice:
    """Regular renewal invoice for the full billing period containing `on`."""
    plan = sub.plan
    start, end = billing_period(sub, on)
    inv = Invoice(
        number=_invoice_number("REN", sub.customer_id, start),
        customer_id=sub.customer_id,
        issue_date=start,
        period_start=start,
        period_end=end,
        currency=plan.currency,
    )
    inv.add(f"{plan.name} subscription", plan.price)
    return inv


def change_lines(result: ProrationResult) -> list[InvoiceLine]:
    """Credit, charge and, when needed, a rounding line so the lines sum to result.net."""
    old, new = get_plan(result.old_plan), get_plan(result.new_plan)
    days = f"{result.remaining_days}/{result.period_days} days"
    lines = [
        InvoiceLine(f"Unused time on {old.name} ({days})", -result.credit),
        InvoiceLine(f"Remaining time on {new.name} ({days})", result.charge),
    ]
    drift = result.net - (result.charge - result.credit)
    if drift:
        lines.append(InvoiceLine("Rounding adjustment", drift))
    return lines


def build_change_invoice(sub: Subscription, new_plan_code: str, change_date: date) -> Invoice:
    """Invoice for switching plans part-way through the current billing period."""
    result = prorate_change(sub, new_plan_code, change_date)
    inv = Invoice(
        number=_invoice_number("CHG", sub.customer_id, change_date),
        customer_id=sub.customer_id,
        issue_date=change_date,
        period_start=result.period_start,
        period_end=result.period_end,
        currency=sub.plan.currency,
    )
    inv.lines.extend(change_lines(result))
    return inv
