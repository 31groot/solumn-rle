#!/usr/bin/env python3
"""Generate the supplier feed dataset served by the :9100 stub (deterministic)."""
import json
import random
import sys
from pathlib import Path

rng = random.Random(20261122)
NOUNS = ["Desk Lamp", "Office Chair", "Notebook A5", "Gel Pen", "Monitor Arm", "USB-C Hub", "Stapler",
         "Paper Clips", "Whiteboard", "Marker Set", "Desk Mat", "Cable Tray", "Footrest", "Laptop Stand",
         "Label Maker", "Shredder", "Filing Box", "Sticky Notes", "Ring Binder", "Tape Dispenser"]
ADJ = ["Compact", "Pro", "Eco", "Classic", "Ergo", "Mini", "Steel", "Bamboo"]
CUR = ["USD", "EUR", "GBP", "INR"]


def ts(day, h, m):
    return f"2026-11-{day:02d}T{h:02d}:{m:02d}:00Z"


def price_text(cur):
    v = rng.choice([4.5, 7.25, 12.0, 19.99, 24.5, 49.0, 89.95, 129.0, 1299.0, 2499.5])
    if cur == "INR":
        v = round(v * 83, 0)
    s = f"{v:,.2f}" if v >= 1000 else rng.choice([f"{v:.2f}", f"{v:g}"])
    return rng.choice([s, f" {s} ", s])


items = []
for i in range(1, 49):
    cur = CUR[i % 4]
    it = {"sku": f"SUP-{1000 + i}", "title": f"{rng.choice(ADJ)}  {rng.choice(NOUNS)}",
          "price": price_text(cur), "currency": cur, "stock": rng.randint(0, 250),
          "updated_at": ts(rng.randint(10, 18), rng.randint(0, 23), rng.randint(0, 59))}
    items.append(it)

del items[6]["stock"]                       # missing stock -> 0
items[9]["title"] = "  Eco\tSticky   Notes "  # whitespace cleanup
items[14]["price"] = "call for price"      # unparseable -> skipped
items[20]["currency"] = "JPY"              # no fx rate -> skipped
items[25]["price"] = "$ 1,049.00"           # symbol + thousands
items[30]["currency"] = "usd"              # lower-case code

# Later pages: newer duplicates (win), older duplicates (ignored), tombstones.
extra = [
    {**items[2], "price": "21.00", "stock": 5, "updated_at": ts(20, 9, 0)},
    {**items[11], "title": "Ergo Laptop Stand v2", "updated_at": ts(20, 9, 5)},
    {**items[17], "stock": 0, "updated_at": ts(20, 9, 10)},
    {**items[4], "price": "1.00", "updated_at": ts(1, 0, 0)},          # stale duplicate
    {**items[22], "title": "OLD TITLE", "updated_at": ts(2, 0, 0)},    # stale duplicate
    {"sku": items[5]["sku"], "deleted": True, "updated_at": ts(21, 8, 0)},
    {"sku": items[27]["sku"], "deleted": True, "updated_at": ts(21, 8, 30)},
    {"sku": "SUP-9999", "deleted": True, "updated_at": ts(21, 9, 0)},  # never existed
]
# Tombstone delivered BEFORE a newer re-listing of the same SKU: the re-listing must survive.
early_tomb = {"sku": items[40]["sku"], "deleted": True, "updated_at": ts(19, 0, 0)}
relist = {**items[40], "price": "33.00", "updated_at": ts(22, 1, 0)}
# Tombstone delivered BEFORE an older copy: the older copy must not resurrect the SKU.
late_orig = items.pop(44)
early_tomb2 = {"sku": late_orig["sku"], "deleted": True, "updated_at": ts(21, 23, 0)}

feed = items[:10] + [early_tomb, early_tomb2] + items[10:30] + [late_orig] + items[30:] \
    + extra[:4] + [relist] + extra[4:]
Path(sys.argv[1]).write_text(json.dumps(feed, indent=1) + "\n")
print(len(feed), "records")
