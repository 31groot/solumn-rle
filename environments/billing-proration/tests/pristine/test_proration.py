import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from invoice import build_change_invoice, build_period_invoice  # noqa: E402
from plans import Subscription, UnknownPlanError, get_plan  # noqa: E402
from proration import prorate_change  # noqa: E402


def money(s):
    return Decimal(s)


def test_catalogue_prices():
    assert get_plan("starter-m").price == money("499.00")
    assert get_plan("team-a").price == money("14990.00")
    with pytest.raises(UnknownPlanError):
        get_plan("enterprise-m")


def test_renewal_invoice_is_full_price():
    sub = Subscription("cus_0007", "team-m", date(2025, 1, 10))
    inv = build_period_invoice(sub, date(2025, 3, 22))
    assert (inv.period_start, inv.period_end) == (date(2025, 3, 10), date(2025, 4, 10))
    assert inv.total == money("1499.00")
    assert len(inv.lines) == 1


def test_same_plan_change_rejected():
    sub = Subscription("cus_0007", "team-m", date(2025, 1, 10))
    with pytest.raises(ValueError):
        prorate_change(sub, "team-m", date(2025, 2, 1))


def test_change_on_period_start_is_full_swap():
    sub = Subscription("cus_0007", "starter-m", date(2025, 1, 10))
    r = prorate_change(sub, "team-m", date(2025, 2, 10))
    assert (r.credit, r.charge, r.net) == (money("499.00"), money("1499.00"), money("1000.00"))


def test_month_end_anchor_upgrade():
    sub = Subscription("cus_1042", "lite-m", date(2025, 1, 31))
    r = prorate_change(sub, "starter-m", date(2025, 3, 25))
    assert (r.period_start, r.period_end) == (date(2025, 2, 28), date(2025, 3, 31))
    assert (r.credit, r.charge, r.net) == (money("16.66"), money("83.17"), money("66.50"))
    inv = build_change_invoice(sub, "starter-m", date(2025, 3, 25))
    assert inv.total == r.net


def test_annual_upgrade_with_promo_price():
    sub = Subscription("cus_2210", "team-a", date(2023, 6, 1), paid_this_period=money("7000.00"))
    r = prorate_change(sub, "business-a", date(2023, 12, 1))
    assert (r.period_start, r.period_end) == (date(2023, 6, 1), date(2024, 6, 1))
    assert (r.credit, r.charge, r.net) == (money("7000.00"), money("24926.52"), money("17926.52"))


def test_monthly_to_annual_switch():
    sub = Subscription("cus_3307", "starter-m", date(2025, 1, 10))
    r = prorate_change(sub, "starter-a", date(2025, 2, 20))
    assert (r.new_period_start, r.new_period_end) == (date(2025, 2, 20), date(2026, 2, 20))
    assert (r.credit, r.charge, r.net) == (money("332.67"), money("4990.00"), money("4657.33"))
    inv = build_change_invoice(sub, "starter-a", date(2025, 2, 20))
    assert (inv.period_start, inv.period_end, inv.total) == (date(2025, 2, 20), date(2026, 2, 20), r.net)


def test_leap_day_annual_customer_moves_to_monthly():
    sub = Subscription("cus_4419", "team-a", date(2024, 2, 29))
    r = prorate_change(sub, "team-m", date(2027, 10, 31))
    assert (r.period_start, r.period_end) == (date(2027, 2, 28), date(2028, 2, 29))
    assert (r.new_period_start, r.new_period_end) == (date(2027, 10, 31), date(2027, 11, 30))
    assert (r.credit, r.charge, r.net) == (money("4969.29"), money("1499.00"), money("-3470.29"))
    inv = build_change_invoice(sub, "team-m", date(2027, 10, 31))
    assert (inv.period_start, inv.period_end, inv.total) == (date(2027, 10, 31), date(2027, 11, 30), r.net)
