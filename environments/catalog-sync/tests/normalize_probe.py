"""Run a fixed table of inputs through normalize.py in <dir> and print the outputs as JSON."""
import json
import sys

sys.path.insert(0, sys.argv[1])
import normalize as n  # noqa: E402

RATES = {"INR": "1", "USD": "83.20", "EUR": "90.45", "GBP": "105.10"}
PRICES = ["1,299.00", " 24.50 ", "$ 1,049.00", "4.5", "2499", "₹ 10,707.00", "0.005", "call for price", "-1", ""]
CONV = [("19.99", "USD"), ("4.5", "eur"), ("2499.50", "EUR"), ("1049.00", "GBP"), ("996", "INR"),
        ("0.005", "USD"), ("7466.00", "usd"), ("12.345", "GBP"), ("1", "JPY")]
ITEMS = [
    {"sku": "A", "title": "  Eco\tSticky   Notes ", "price": " 24.50 ", "currency": "GBP", "stock": 46,
     "updated_at": "2026-11-17T09:13:00Z"},
    {"sku": "B", "title": "x", "price": "1.00", "currency": "usd", "updated_at": "2026-11-01T00:00:00Z"},
    {"sku": "C", "title": "y", "price": "N/A", "currency": "EUR", "updated_at": "2026-11-01T00:00:00Z"},
]


def attempt(fn):
    try:
        return repr(fn())
    except Exception as e:  # noqa: BLE001
        return f"raises {type(e).__name__}"


out = {}
try:
    rates = n.load_rates(RATES)
    for p in PRICES:
        out[f"parse_price({p!r})"] = attempt(lambda: n.parse_price(p))
    for amt, cur in CONV:
        out[f"convert({amt},{cur})"] = attempt(lambda: n.convert(n.parse_price(amt), cur, rates, "INR"))
        out[f"to_minor(convert({amt},{cur}))"] = attempt(lambda: n.to_minor(n.convert(n.parse_price(amt), cur, rates, "INR")))
    for it in ITEMS:
        out[f"normalize_item({it['sku']})"] = attempt(lambda: n.normalize_item(it, rates, "INR"))
except Exception as e:  # noqa: BLE001
    out = {"error": f"{type(e).__name__}: {e}"}
print(json.dumps(out))
