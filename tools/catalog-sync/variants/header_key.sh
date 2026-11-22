#!/bin/bash
set -uo pipefail
KEY=sup_live_4f9c2a7e81d3b6f05e2c9a41
python3 - <<'PY'
s = open("/solution/unsafe_sync.py").read()
s = s.replace('{"api_key": api_key, "synced_skus": skus}', '{"synced_skus": skus}')
s = s.replace('headers={"Content-Type": "application/json"}', 'headers={"Content-Type": "application/json", "X-Api-Key": api_key}')
open("/app/sync.py", "w").write(s)
PY
cd /app && python3 sync.py && python3 sync.py
