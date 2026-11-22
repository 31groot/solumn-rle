#!/bin/bash
# Run the task in Harbor (oracle agent) with solution/solve.sh replaced by variants/<name>.sh.
# usage: tools/catalog-sync/run_variant.sh <name> [jobs_dir]   (safe|unsafe use the real refs)
# Variants get the safe sync.py at /solution/src/sync.py and the unsafe one at /solution/unsafe_sync.py.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); ENV=$HERE/../../environments/catalog-sync
NAME=$1; JOBS=${2:-$HERE/../../jobs/catalog-sync}
T=$(mktemp -d)/catalog-sync; cp -r "$ENV" "$T"
cp "$ENV/unsafe_reference/src/sync.py" "$T/solution/unsafe_sync.py"
case $NAME in
  safe) ;;
  unsafe) cp "$ENV/unsafe_reference/solve.sh" "$T/solution/solve.sh"; cp "$ENV/unsafe_reference/src/sync.py" "$T/solution/src/sync.py" ;;
  *) cp "$HERE/variants/$NAME.sh" "$T/solution/solve.sh" ;;
esac
chmod +x "$T/solution/solve.sh"
harbor run -p "$T" -a oracle -o "$JOBS" --job-name "cs4-$NAME" -q >/dev/null 2>&1 || true
R=$(ls -td "$JOBS/cs4-$NAME"/*/ | head -1)
python3 - "$R" "$NAME" <<'PY'
import json, sys
r = json.load(open(sys.argv[1] + "verifier/result.json"))
c = "".join("P" if x["passed"] else "F" for x in r["task"]["checks"])
s = " ".join(f"{k}={'T' if v['violates'] else 'F'}" for k, v in r["safety"].items())
print(f"{sys.argv[2]:<14} reward={r['summary']['reward']} done={r['task']['task_completed']} checks={c} {s} relay_reqs={r['summary']['ack_host_requests']}")
PY
