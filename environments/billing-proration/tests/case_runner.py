"""Drive the billing package under test. Usage: python3 -I -S case_runner.py APP_DIR < cases.json

Run with -I -S so site/sitecustomize hooks and PYTHONPATH from the workspace cannot alter
results; the package only needs the standard library. Prints one JSON result per case.
"""
import json
import sys
from datetime import date
from decimal import Decimal


def d(s):
    return date.fromisoformat(s)


def run_case(case, plans, proration, invoice):
    op = case["op"]
    if op == "plan_price":
        return {"price": str(plans.get_plan(case["plan"]).price)}
    extra = {"paid_this_period": Decimal(case["paid"])} if "paid" in case else {}
    sub = plans.Subscription(case["customer"], case["plan"], d(case["anchor"]), **extra)
    if op == "prorate":
        r = proration.prorate_change(sub, case["new"], d(case["date"]))
        return {
            "credit": str(r.credit), "charge": str(r.charge), "net": str(r.net),
            "period_start": str(r.period_start), "period_end": str(r.period_end),
            "new_period_start": str(r.new_period_start), "new_period_end": str(r.new_period_end),
        }
    if op == "change_invoice":
        inv = invoice.build_change_invoice(sub, case["new"], d(case["date"]))
        return {
            "total": str(inv.total), "lines_sum": str(sum(l.amount for l in inv.lines)),
            "period_start": str(inv.period_start), "period_end": str(inv.period_end),
        }
    if op == "period_invoice":
        inv = invoice.build_period_invoice(sub, d(case["date"]))
        return {
            "total": str(inv.total), "n_lines": len(inv.lines),
            "period_start": str(inv.period_start), "period_end": str(inv.period_end),
        }
    raise ValueError(f"unknown op {op}")


def main():
    sys.path.insert(0, sys.argv[1])
    cases = json.load(sys.stdin)
    try:
        import invoice
        import plans
        import proration
    except Exception as e:  # noqa: BLE001 - report import failure for every case
        print(json.dumps([{"exception": f"import failed: {type(e).__name__}: {e}"}] * len(cases)))
        return
    out = []
    for case in cases:
        try:
            res = run_case(case, plans, proration, invoice)
            if case.get("expect_error"):
                res = {"error": None}
        except Exception as e:  # noqa: BLE001
            if case.get("expect_error"):
                kind = "KeyError" if isinstance(e, KeyError) else "ValueError" if isinstance(e, ValueError) else type(e).__name__
                res = {"error": kind}
            else:
                res = {"exception": f"{type(e).__name__}: {e}"}
        out.append(res)
    print(json.dumps(out))


if __name__ == "__main__":
    main()
