#!/bin/bash
# run_cs11.sh DEADLINE_ISO  -- claim the host (CPU 0-95 + GPU quiet exclusive) and run the harness; analyze regardless.
set -uo pipefail
D=/mnt/raid0/llm/tmp/cs11-20261022; DL=$1
ulimit -c 0
export EPYC_LOCK_FIFO=1
left=$(( $(date -u -d "$DL" +%s) - $(date -u +%s) - 600 ))
[ "$left" -gt 300 ] || { echo "run_cs11: not enough window before $DL"; exit 3; }
/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock run --cpu-list 0-95 --role bench --gpu-quiet exclusive --timeout-s "$left" --tag cs11-cpu-partition -- \
  python3 "$D/cs11_harness.py" --run --deadline "$DL"
rc=$?
python3 "$D/analyze.py" > "$D/raw/analyze.out" 2>&1 || true
exit $rc
