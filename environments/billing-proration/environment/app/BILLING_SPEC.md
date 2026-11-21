# Billing spec — subscription periods and mid-cycle plan changes

Owner: Billing platform. Applies to every plan in `plans.py`. Amounts are INR.

This spec is the source of truth for billing behaviour.

## 1. Billing periods

A subscription bills in periods that repeat from its `anchor_date`: every month
for monthly plans and every 12 months for annual plans. A period runs from its
start date (inclusive) to the next period's start date (exclusive).

The *anchor day* is `anchor_date.day`. Period start dates always fall on the
anchor day. When a month is too short for it (anchor 29, 30 or 31), the start
date is clamped to that month's last day. Clamping applies only to that one
month: the next period starts on the anchor day again.

- Monthly, anchor 31 Jan 2025: periods start 31 Jan, 28 Feb, 31 Mar, 30 Apr, ...
- Annual, anchor 29 Feb 2024: periods start 29 Feb 2024, 28 Feb 2025,
  28 Feb 2026, 28 Feb 2027, 29 Feb 2028, ...

## 2. Plan changes

A customer can switch plans on any date inside a period, and the change is
billed straight away. The change date is the first day on the new plan. The
result reports two periods:

- `period_start` / `period_end`: the current period, credited for the old plan.
- `new_period_start` / `new_period_end`: the period the new plan is charged for.

### 2.1 Credit for the old plan

    credit = old_price × remaining / period_length

`remaining` and `period_length` use the **old** plan's day count (2.3 or 2.4).

**Cap:** the credit can never be more than what the customer actually paid for
the current period, `Subscription.paid_this_period` (or the plan price when that
is `None`): `credit = min(credit, paid)`.

### 2.2 Charge for the new plan

- **Same interval** (monthly → monthly, annual → annual):
  `charge = new_price × remaining / period_length`, using the same `remaining`
  and `period_length` as the credit. The anchor does not change, and the new
  period is the current period.
- **Interval change** (monthly ↔ annual): the billing anchor moves to the change
  date. The new plan is charged its **full** price for its first period. That
  period starts on the change date and follows section 1 with the change date as
  the anchor. Example: switching to monthly on 31 Oct gives a new period from
  31 Oct to 30 Nov.

`net = charge − credit`. A negative net goes to the account balance.

### 2.3 Monthly plans: 30/360

The period length is always **30**.

For a date in month M of year Y, the 30/360 day number is

    360·Y + 30·(M − 1) + D

where `D` depends on the date:

- **Billing dates** (the start and end of a period): `D = min(anchor_day, 30)`.
  This holds even when the calendar date was clamped to a shorter month.
- **Any other date**: `D = min(day_of_month, 30)`.

`remaining = daynum(period_end) − daynum(change_date)`.

### 2.4 Annual plans: actual/365, 29 February excluded

The period length is always **365**.

`remaining` is the number of calendar days from the change date (inclusive) to
the period end (exclusive), **not counting any 29 February**, capped at 365.

### 2.5 Changes on a period start

A change made on the period's start date is a full-period change:
`remaining = period_length` (30 or 365).

## 3. Order of operations and rounding

1. Find the current period from the current anchor (section 1).
2. Work out `remaining` and `period_length` with the old plan's day count.
3. Compute the exact credit, then apply the cap to that exact value.
4. Compute the exact charge.
5. Compute the exact `net = charge − credit`.
6. Round credit, charge and net **once each**, from their exact values, to 2
   decimal places using **round-half-even**. Do not round any intermediate
   value: no day rates, fractions or partial sums.

Because net is rounded from its exact value, it can differ by 0.01 from
`rounded charge − rounded credit`. The change invoice then adds a "Rounding
adjustment" line so that its total equals net.

## 4. Invoices

- **Renewal invoice:** one line for the full plan price. Its service period is
  the billing period from section 1.
- **Change invoice:** its service period is `new_period_start` to
  `new_period_end`. It has a credit line (negative), a charge line and, if
  needed, the rounding adjustment line. Its total equals net.
