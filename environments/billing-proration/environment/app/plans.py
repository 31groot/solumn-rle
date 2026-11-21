"""Plan catalogue and subscription records."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal

MONTHLY = "monthly"
ANNUAL = "annual"
INTERVALS = (MONTHLY, ANNUAL)
PAISE = Decimal("0.01")


class UnknownPlanError(KeyError):
    """Raised when a plan code is not in the catalogue."""


@dataclass(frozen=True)
class Plan:
    code: str
    name: str
    interval: str
    price: Decimal  # charged once per billing period
    currency: str = "INR"

    def __post_init__(self) -> None:
        if self.interval not in INTERVALS:
            raise ValueError(f"plan {self.code}: unknown interval {self.interval!r}")
        if self.price < 0 or self.price != self.price.quantize(PAISE):
            raise ValueError(f"plan {self.code}: price must be >= 0 with at most 2 decimals")


_CATALOG: dict[str, Plan] = {
    p.code: p
    for p in (
        Plan("lite-m", "Lite", MONTHLY, Decimal("99.99")),
        Plan("starter-m", "Starter", MONTHLY, Decimal("499.00")),
        Plan("team-m", "Team", MONTHLY, Decimal("1499.00")),
        Plan("business-m", "Business", MONTHLY, Decimal("4999.00")),
        Plan("starter-a", "Starter (annual)", ANNUAL, Decimal("4990.00")),
        Plan("team-a", "Team (annual)", ANNUAL, Decimal("14990.00")),
        Plan("business-a", "Business (annual)", ANNUAL, Decimal("49990.00")),
    )
}


def get_plan(code: str) -> Plan:
    try:
        return _CATALOG[code]
    except KeyError:
        raise UnknownPlanError(code) from None


def list_plans(interval: str | None = None) -> list[Plan]:
    plans = [p for p in _CATALOG.values() if interval is None or p.interval == interval]
    return sorted(plans, key=lambda p: (p.interval, p.price))


@dataclass(frozen=True)
class Subscription:
    """A customer's subscription. Billing periods repeat from anchor_date."""

    customer_id: str
    plan_code: str
    anchor_date: date
    # What the customer actually paid for the current period (promos, earlier changes).
    # None means the full plan price.
    paid_this_period: Decimal | None = None

    def __post_init__(self) -> None:
        if not self.customer_id:
            raise ValueError("customer_id is required")
        get_plan(self.plan_code)
        if self.paid_this_period is not None and self.paid_this_period < 0:
            raise ValueError("paid_this_period cannot be negative")

    @property
    def plan(self) -> Plan:
        return get_plan(self.plan_code)

    @property
    def anchor_day(self) -> int:
        return self.anchor_date.day

    @property
    def paid(self) -> Decimal:
        return self.plan.price if self.paid_this_period is None else self.paid_this_period

    def with_plan(self, plan_code: str, anchor_date: date | None = None) -> "Subscription":
        """Same customer on a different plan; the anchor moves only if one is given."""
        return replace(self, plan_code=plan_code, anchor_date=anchor_date or self.anchor_date,
                       paid_this_period=None)
