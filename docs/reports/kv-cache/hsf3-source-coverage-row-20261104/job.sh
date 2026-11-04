#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/task8
if [[ "${FILLER_SMOKE:-0}" == 1 ]]; then
  exec python3 -B "$D/synthetic_smoke.py"
fi
if [[ -n "${FILLER_DRYRUN_RESULT_PATH:-}" ]]; then
  echo "unexpected dry-run result path outside smoke" >&2
  exit 2
fi
exec timeout 10m nice -n 19 ionice -c 3 python3 -B "$D/census.py" \
  --out-file "$D/RESULT.json"
