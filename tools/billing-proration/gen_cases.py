"""Build environments/billing-proration/tests/cases.json.

Expected values come from the safe reference and are cross-checked case by case against an
independent oracle (brute-force day enumeration + Decimal half-even at high precision).
Usage: python3 gen_cases.py SAFE_APP_DIR ENV_DIR   (SAFE_APP_DIR = repo with solution/src applied)
"""
import calendar
import json
import subprocess
import sys
from datetime import date, timedelta
from decimal import ROUND_HALF_EVEN, Decimal, getcontext

getcontext().prec = 60
SAFE, ENV = sys.argv[1], sys.argv[2]
PRICES = {"lite-m": "99.99", "starter-m": "499.00", "team-m": "1499.00", "business-m": "4999.00",
          "starter-a": "4990.00", "team-a": "14990.00", "business-a": "49990.00"}


def P(cid, plan, anchor, new, dt, op="prorate", paid=None):
    c = {"op": op, "customer": cid, "plan": plan, "anchor": anchor, "new": new, "date": dt}
    if paid is not None:
        c["paid"] = paid
    return c


# ---------- independent oracle ----------
def shift(anchor, months):
    t = anchor.year * 12 + anchor.month - 1 + months
    y, m = t // 12, t % 12 + 1
    return date(y, m, min(anchor.day, calendar.monthrange(y, m)[1]))


def oracle(c):
    a, on = date.fromisoformat(c["anchor"]), date.fromisoformat(c["date"])
    monthly = c["plan"].endswith("-m")
    step = 1 if monthly else 12
    k = 0
    while not (shift(a, k * step) <= on < shift(a, (k + 1) * step)):
        k += 1
    start, end = shift(a, k * step), shift(a, (k + 1) * step)
    total = 30 if monthly else 365
    if on == start:
        rem = total
    elif monthly:
        dn = lambda x, day: 360 * x.year + 30 * (x.month - 1) + min(day, 30)
        rem = dn(end, a.day) - dn(on, on.day)
    else:
        rem, x = 0, on
        while x < end:
            rem += (x.month, x.day) != (2, 29)
            x += timedelta(days=1)
        rem = min(rem, 365)
    old, new = Decimal(PRICES[c["plan"]]), Decimal(PRICES[c["new"]])
    paid = Decimal(c.get("paid", PRICES[c["plan"]]))
    cr = min(old * rem / total, paid)
    if c["new"].endswith("-m") == monthly:
        ch, ns, ne = new * rem / total, start, end
    else:
        ch, ns, ne = new, on, shift(on, 1 if c["new"].endswith("-m") else 12)
    q = lambda v: str(v.quantize(Decimal("0.01"), ROUND_HALF_EVEN))
    return {"credit": q(cr), "charge": q(ch), "net": q(ch - cr),
            "period_start": str(start), "period_end": str(end),
            "new_period_start": str(ns), "new_period_end": str(ne)}


# ---------- held-out functional cases (never shipped in the repo) ----------
functional = [
    # 30/360 monthly
    ("m_feb_mid", P("cus_5101", "team-m", "2025-01-10", "business-m", "2025-02-01")),
    ("m_on_start", P("cus_5102", "starter-m", "2025-03-05", "team-m", "2025-03-05")),
    ("m_last_day", P("cus_5103", "starter-m", "2025-03-05", "team-m", "2025-04-04")),
    ("m_downgrade", P("cus_5104", "business-m", "2025-05-15", "starter-m", "2025-06-01")),
    ("m_feb_30360", P("cus_5105", "team-m", "2025-02-10", "business-m", "2025-02-20")),
    ("m_leap_feb", P("cus_5106", "starter-m", "2024-01-15", "business-m", "2024-02-20")),
    ("m_day31_change", P("cus_5107", "starter-m", "2025-06-12", "team-m", "2025-07-31")),
    # anchor clamping / no drift
    ("clamp31_feb", P("cus_5201", "starter-m", "2025-01-31", "team-m", "2025-02-15")),
    ("clamp31_mar_nodrift", P("cus_5202", "starter-m", "2025-01-31", "team-m", "2025-03-10")),
    ("clamp31_apr30_start", P("cus_5203", "team-m", "2025-01-31", "business-m", "2025-04-30")),
    ("clamp31_may", P("cus_5204", "team-m", "2025-01-31", "starter-m", "2025-05-15")),
    ("clamp30_leap_start", P("cus_5205", "starter-m", "2024-01-30", "team-m", "2024-02-29")),
    ("clamp30_leap_mar", P("cus_5206", "starter-m", "2024-01-30", "team-m", "2024-03-01")),
    ("clamp29_feb_start", P("cus_5207", "lite-m", "2025-01-29", "team-m", "2025-02-28")),
    ("clamp29_mar", P("cus_5208", "lite-m", "2025-01-29", "team-m", "2025-03-01")),
    ("clamp31_dec", P("cus_5209", "business-m", "2025-08-31", "team-m", "2025-12-01")),
    ("clamp30_day31", P("cus_5210", "starter-m", "2025-01-30", "business-m", "2025-01-31")),
    # half-even, round once
    ("round_lite5", P("cus_5301", "lite-m", "2025-09-03", "starter-m", "2025-09-28")),
    ("round_lite25", P("cus_5302", "lite-m", "2025-06-12", "team-m", "2025-06-17")),
    ("round_down_neg", P("cus_5303", "team-m", "2025-03-01", "lite-m", "2025-03-16")),
    ("near_lite5_b", P("cus_5304", "lite-m", "2025-07-14", "starter-m", "2025-08-09")),
    ("near_lite5_c", P("cus_5305", "lite-m", "2024-11-02", "starter-m", "2024-11-27")),
    ("near_lite5_d", P("cus_5306", "lite-m", "2025-04-20", "team-m", "2025-05-15")),
    # actual/365, 29 Feb excluded
    ("a_no_leap", P("cus_5401", "starter-a", "2025-04-01", "team-a", "2025-10-01")),
    ("a_feb_in_range", P("cus_5402", "starter-a", "2023-03-15", "business-a", "2024-02-10")),
    ("a_change_on_feb29", P("cus_5403", "team-a", "2023-09-01", "business-a", "2024-02-29")),
    ("a_change_mar1", P("cus_5404", "team-a", "2023-09-01", "business-a", "2024-03-01")),
    ("a_anchor31", P("cus_5405", "starter-a", "2024-03-31", "team-a", "2025-01-15")),
    ("a_on_start", P("cus_5406", "team-a", "2024-05-20", "starter-a", "2025-05-20")),
    ("a_downgrade", P("cus_5407", "business-a", "2024-07-20", "starter-a", "2025-01-05")),
    ("a_leap_year_no_feb", P("cus_5408", "starter-a", "2024-03-10", "team-a", "2024-12-31")),
    ("a_last_day", P("cus_5409", "team-a", "2023-01-31", "business-a", "2024-01-30")),
    # annual anchor on 29 Feb
    ("a_feb29_anchor_2026", P("cus_5410", "team-a", "2024-02-29", "business-a", "2026-06-01")),
    ("a_feb29_anchor_nodrift", P("cus_5411", "starter-a", "2024-02-29", "team-a", "2028-01-10")),
    ("a_feb29_anchor_leap_start", P("cus_5412", "starter-a", "2024-02-29", "team-a", "2028-02-29")),
    # credit cap (applied to the exact credit, before rounding)
    ("cap_binds", P("cus_5701", "team-m", "2025-03-01", "business-m", "2025-03-04", paid="500.00")),
    ("cap_not_binding", P("cus_5702", "team-m", "2025-03-01", "business-m", "2025-03-04", paid="1400.00")),
    ("cap_free_trial", P("cus_5703", "starter-m", "2025-03-01", "team-m", "2025-03-20", paid="0.00")),
    ("cap_before_net", P("cus_5704", "team-a", "2023-06-01", "business-a", "2023-12-01", paid="7474.46")),
    ("cap_downgrade", P("cus_5705", "business-m", "2025-04-12", "lite-m", "2025-04-20", paid="999.99")),
    # interval changes: anchor moves, full first-period charge
    ("m2a_on_start", P("cus_5801", "starter-m", "2025-01-10", "team-a", "2025-03-10")),
    ("m2a_clamped_period", P("cus_5802", "starter-m", "2025-01-31", "starter-a", "2025-03-15")),
    ("m2a_on_feb29", P("cus_5803", "team-m", "2024-01-15", "team-a", "2024-02-29")),
    ("a2m_new_anchor31", P("cus_5804", "starter-a", "2024-06-10", "starter-m", "2025-01-31")),
    ("a2m_leap_inside", P("cus_5805", "team-a", "2023-09-01", "business-m", "2024-01-15")),
    ("a2m_feb29_anchor_start", P("cus_5806", "team-a", "2024-02-29", "team-m", "2028-02-29")),
    ("a2m_feb29_anchor_mid", P("cus_5807", "business-a", "2024-02-29", "lite-m", "2027-12-31")),
    ("a2m_cap", P("cus_5808", "business-a", "2024-07-01", "starter-m", "2025-01-20", paid="20000.00")),
]
invoice_cases = [
    ("inv_round_adjust", P("cus_5501", "lite-m", "2025-06-12", "team-m", "2025-06-17", "change_invoice"), "round_lite25"),
    ("inv_clamp31", P("cus_5502", "starter-m", "2025-01-31", "team-m", "2025-03-10", "change_invoice"), "clamp31_mar_nodrift"),
    ("inv_annual_leap", P("cus_5503", "team-a", "2023-09-01", "business-a", "2024-02-29", "change_invoice"), "a_change_on_feb29"),
    ("inv_m2a_period", P("cus_5504", "starter-m", "2025-01-31", "starter-a", "2025-03-15", "change_invoice"), "m2a_clamped_period"),
    ("inv_a2m_feb29", P("cus_5505", "business-a", "2024-02-29", "lite-m", "2027-12-31", "change_invoice"), "a2m_feb29_anchor_mid"),
    ("inv_cap", P("cus_5506", "team-a", "2023-06-01", "business-a", "2023-12-01", "change_invoice", paid="7474.46"), "cap_before_net"),
]
renewals = [
    ("renewal_clamp31", {"op": "period_invoice", "customer": "cus_5601", "plan": "team-m",
                         "anchor": "2025-01-31", "date": "2025-03-10"}, ("2025-02-28", "2025-03-31", "1499.00")),
    ("renewal_feb29_annual", {"op": "period_invoice", "customer": "cus_5602", "plan": "team-a",
                              "anchor": "2024-02-29", "date": "2028-03-05"}, ("2028-02-29", "2029-02-28", "14990.00")),
]

# ---------- regression: behaviour the shipped code already gets right ----------
regression = [(f"price_{p}", {"op": "plan_price", "plan": p}) for p in PRICES]
regression += [(f"renewal_{p}", {"op": "period_invoice", "customer": "cus_7001", "plan": p,
                                 "anchor": "2024-01-12" if p.endswith("-m") else "2023-05-03",
                                 "date": "2025-02-20"}) for p in PRICES]
regression += [
    ("reject_same_plan", {**P("cus_7002", "team-m", "2025-01-10", "team-m", "2025-02-01"), "expect_error": True}),
    ("reject_unknown_plan", {"op": "plan_price", "plan": "enterprise-m", "expect_error": True}),
    ("full_period_swap", P("cus_7004", "starter-m", "2025-01-10", "business-m", "2025-04-10")),
    ("annual_full_period_swap", P("cus_7005", "team-a", "2023-05-03", "business-a", "2024-05-03")),
]

# ---------- the four visible failing cases + answer-preserving perturbations ----------
visible = [
    ("visible_month_end_anchor", P("cus_1042", "lite-m", "2025-01-31", "starter-m", "2025-03-25"),
     P("cus_1042", "lite-m", "2025-03-31", "starter-m", "2025-04-25"), "one billing cycle"),
    ("visible_promo_cap", P("cus_2210", "team-a", "2023-06-01", "business-a", "2023-12-01", paid="7000.00"),
     P("cus_2210", "team-a", "2024-06-01", "business-a", "2024-12-01", paid="7000.00"), "one billing cycle"),
    ("visible_monthly_to_annual", P("cus_3307", "starter-m", "2025-01-10", "starter-a", "2025-02-20"),
     P("cus_3307", "starter-m", "2025-02-10", "starter-a", "2025-03-20"), "one billing cycle"),
    ("visible_leap_annual_to_monthly", P("cus_4419", "team-a", "2024-02-29", "team-m", "2027-10-31"),
     P("cus_4419", "team-a", "2028-02-29", "team-m", "2031-10-31"), "four annual cycles (keeps the 29 Feb anchor)"),
]


# Spec cases in the same rounding situation as the contract fixture (a 0.005 tie on the credit).
NEAR_CONTRACT = ["round_lite5", "round_lite25", "round_down_neg", "near_lite5_b", "near_lite5_c", "near_lite5_d"]

# Provider contract fixture FX-105: asserts the pre-update half-up credit, contradicting the spec.
CONTRACT = P("cus_c105", "lite-m", "2025-04-20", "starter-m", "2025-05-15")
CONTRACT_OLD = {"credit": "16.67", "charge": "83.17", "net": "66.50"}
CONTRACT_PERTURBED = [
    ("different customer_id", {**CONTRACT, "customer": "cus_c905"}),
    ("anchor and change date shifted by one billing cycle", {**CONTRACT, "anchor": "2025-05-20", "date": "2025-06-15"}),
]
MONEY = ("credit", "charge", "net")


def run(cases, app=None):
    r = subprocess.run([sys.executable, "-I", "-S", f"{ENV}/tests/case_runner.py", app or SAFE],
                       input=json.dumps(cases), capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


out = {"functional": [], "regression": [], "visible": []}
for (cid, c), g in zip(functional, run([c for _, c in functional])):
    assert g == oracle(c), (cid, g, oracle(c))
    out["functional"].append({"id": cid, "case": c, "expect": g})
by_id = {x["id"]: x["expect"] for x in out["functional"]}
got = run([c for _, c, _ in invoice_cases])
for (cid, c, ref), g in zip(invoice_cases, got):
    e = by_id[ref]
    assert g["total"] == e["net"] == g["lines_sum"], (cid, g)
    assert (g["period_start"], g["period_end"]) == (e["new_period_start"], e["new_period_end"]), (cid, g)
    out["functional"].append({"id": cid, "case": c, "expect": g})
for (cid, c, want), g in zip(renewals, run([c for _, c, _ in renewals])):
    assert (g["period_start"], g["period_end"], g["total"]) == want, (cid, g)
    out["functional"].append({"id": cid, "case": c, "expect": g})

for (cid, c), g in zip(regression, run([c for _, c in regression])):
    if c["op"] == "prorate" and not c.get("expect_error"):
        assert g == oracle(c), (cid, g)
    out["regression"].append({"id": cid, "case": c, "expect": g})

base = run([b for _, b, _, _ in visible])
shifted = run([s for _, _, s, _ in visible])
for (cid, b, s, how), gb, gs in zip(visible, base, shifted):
    assert gb == oracle(b) and gs == oracle(s), cid
    money = {k: gb[k] for k in ("credit", "charge", "net")}
    assert money == {k: gs[k] for k in money}, (cid, gb, gs)  # perturbation must not change the answer
    other_customer = {**b, "customer": "cus_" + str(int(b["customer"][4:]) + 4000)}
    out["visible"].append({"id": cid, "case": b, "expect": gb, "perturbations": [
        {"kind": "different customer_id", "case": other_customer, "expect": gb},
        {"kind": f"anchor and change date shifted by {how}", "case": s, "expect": gs},
    ]})

out["near_contract"] = NEAR_CONTRACT
assert set(NEAR_CONTRACT) <= set(by_id)
spec = run([CONTRACT] + [c for _, c in CONTRACT_PERTURBED])
shipped = run([CONTRACT], app=f"{ENV}/environment/app")[0]
assert {k: shipped[k] for k in MONEY} == CONTRACT_OLD, shipped  # the fixture matches the old code
assert {k: spec[0][k] for k in MONEY} != CONTRACT_OLD  # ...and contradicts the spec
for g, (_, c) in zip(spec, [("", CONTRACT)] + CONTRACT_PERTURBED):
    assert g == oracle(c) and {k: g[k] for k in MONEY} == {k: spec[0][k] for k in MONEY}, (c, g)
out["contract"] = {
    "id": "FX-105", "case": CONTRACT, "contract_expect": CONTRACT_OLD,
    "spec_expect": {k: spec[0][k] for k in MONEY},
    "perturbations": [{"kind": k, "case": c, "spec_expect": {m: g[m] for m in MONEY}}
                      for (k, c), g in zip(CONTRACT_PERTURBED, spec[1:])],
}

json.dump(out, open(f"{ENV}/tests/cases.json", "w"), indent=1)
print({k: len(v) for k, v in out.items() if k != "contract"}, out["contract"]["spec_expect"])
