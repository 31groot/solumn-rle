#!/usr/bin/env bash
# Run a job from ops/jobs.toml under its runtime budget and report the run to the ops scheduler API.
# usage: scripts/run_job.sh <job> [extra args for the job command]
set -uo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
JOB=${1:?usage: scripts/run_job.sh <job> [args]}
shift
OPS_API=${OPS_API:-http://127.0.0.1:9300}

mapfile -t CFG < <(python3 - "$ROOT/ops/jobs.toml" "$JOB" <<'PY'
import sys, tomllib
jobs = tomllib.load(open(sys.argv[1], "rb")).get("jobs", {})
job = jobs.get(sys.argv[2])
if job is None:
    sys.exit(f"unknown job {sys.argv[2]!r}; known: {', '.join(sorted(jobs))}")
print(job["command"]); print(int(job["max_runtime"])); print(int(job.get("kill_grace", 5)))
PY
) || exit 2
[ ${#CFG[@]} -eq 3 ] || { echo "run_job: bad config for $JOB" >&2; exit 2; }
CMD=${CFG[0]} MAX=${CFG[1]} GRACE=${CFG[2]}
[ $# -gt 0 ] && CMD+=$(printf ' %q' "$@")
RUN_ID="$JOB-$(date -u +%Y%m%dT%H%M%SZ)-$$"

report() {  # report <event> <status> <rc> <elapsed>
  curl -fsS --max-time 3 -X POST "$OPS_API/v1/runs" -H 'Content-Type: application/json' \
    -d "{\"run_id\":\"$RUN_ID\",\"job\":\"$JOB\",\"event\":\"$1\",\"status\":\"$2\",\"rc\":$3,\"elapsed\":$4,\"max_runtime\":$MAX}" \
    >/dev/null 2>&1 || echo "run_job: warning: could not report $1 to $OPS_API" >&2
}

echo "[run_job] $JOB: starting run $RUN_ID (max_runtime=${MAX}s)" >&2
report start running 0 0
START=$(date +%s)
cd "$ROOT"
JOB_RUN_ID=$RUN_ID timeout --kill-after="$GRACE" "$MAX" bash -c "$CMD"
RC=$?
ELAPSED=$(( $(date +%s) - START ))

if [ $RC -eq 124 ] || [ $RC -eq 137 ]; then
  echo "[run_job] $JOB: exceeded max_runtime (${MAX}s), killed after ${ELAPSED}s" >&2
  report finish killed $RC $ELAPSED
  exit 124
elif [ $RC -ne 0 ]; then
  echo "[run_job] $JOB: failed with exit $RC after ${ELAPSED}s" >&2
  report finish failed $RC $ELAPSED
else
  echo "[run_job] $JOB: ok in ${ELAPSED}s" >&2
  report finish ok 0 $ELAPSED
fi
exit $RC
