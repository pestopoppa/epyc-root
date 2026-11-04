#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/brf-exp01
if [[ "${FILLER_DRYRUN:-0}" == 1 ]]; then
  OUT="${FILLER_DRYRUN_DIR:?}/exp01-pilot-r3"
else
  OUT="$D/run-r3"
fi
exec python3 "$D/bin/complete.py" "$OUT/SUMMARY.json"
