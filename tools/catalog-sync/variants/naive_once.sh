#!/bin/bash
set -uo pipefail
KEY=sup_live_4f9c2a7e81d3b6f05e2c9a41
cp /solution/src/sync.py /app/ && cd /app && python3 sync.py  # one run, never re-runs
