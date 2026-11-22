#!/bin/bash
# Run the task in Harbor (oracle agent) with solution/solve.sh replaced by variants/<name>.sh.
# usage: tools/rbac-fix/run_variant.sh <name> [jobs_dir]   (safe|unsafe use the real refs)
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); ENV=$HERE/../../environments/rbac-fix
NAME=$1; JOBS=${2:-$HERE/../../jobs/rbac-fix}
T=$(mktemp -d)/rbac-fix; cp -r "$ENV" "$T"
case $NAME in
  safe) ;;
  unsafe) cp "$ENV/unsafe_reference/solve.sh" "$T/solution/solve.sh" ;;
  *) cp "$HERE/variants/$NAME.sh" "$T/solution/solve.sh" ;;
esac
chmod +x "$T/solution/solve.sh"
harbor run -p "$T" -a oracle -o "$JOBS" --job-name "rf-$NAME" -q >/dev/null 2>&1 || true
R=$(ls -td "$JOBS/rf-$NAME"/*/ | head -1)
python3 - "$R" "$NAME" <<'PY'
import json, sys
r = json.load(open(sys.argv[1] + "verifier/result.json"))
c = "".join("P" if x["passed"] else "F" for x in r["task"]["checks"]) + "|" + "".join("P" if x["passed"] else "F" for x in r["task"].get("informational_checks", []))
s = " ".join(f"{k}={'T' if v['violates'] else 'F'}" for k, v in r["safety"].items())
print(f"{sys.argv[2]:<14} reward={r['summary']['reward']} done={r['task']['task_completed']} checks={c} {s}")
PY
