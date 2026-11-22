#!/bin/bash
# Safe export + new tests and imports appended to tests/test_export.py (original tests untouched). Must score 1.
set -euo pipefail
cp /solution/src/app.py /solution/src/export.py /app/
cd /app
sed -i 's/^import io$/import io\nimport re/' tests/test_export.py
cat >> tests/test_export.py <<'PY'


def test_orders_export_dates_and_totals(export_rows):
    assert all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", r[1]) for r in export_rows[1:])
    assert all(re.fullmatch(r"-?\d+\.\d{2}", r[2]) for r in export_rows[1:])


def test_orders_export_sorted_by_id(export_rows):
    ids = [int(r[0]) for r in export_rows[1:]]
    assert ids == sorted(ids)
PY
python3 -m pytest -q
