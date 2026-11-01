#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-rte-frontdoor-quarter-v15-candidate-20261101
MODE=production
[[ "${FILLER_DRYRUN:-0}" == 1 ]] && MODE=dryrun
ATTEMPT="$MODE-$(date +%s%N)"
export RTE_ATTEMPT_ID="$ATTEMPT" RTE_OUTPUT="attempts/$ATTEMPT"
mkdir -p "$D/$RTE_OUTPUT"
exec python3 -B "$D/frontdoor_job.py"
