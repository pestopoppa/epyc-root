#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/refactor-01a16fc3/r18a-verified-anchor-20261031/refactor-r18a-v10-independent-symbols-r4-20261102
ID=refactor-r18a-v10-independent-symbols-r4-20261102
[[ "${FILLER_ID:-}" == "$ID" && -n "${FILLER_CPUS:-}" ]] || exit 64
if [[ "${FILLER_DRYRUN:-0}" == 1 ]]; then
  mkdir -p "$D/scratch"
  SCRATCH=$(mktemp -d "$D/scratch/dryrun.XXXXXXXX")
else
  SCRATCH="$D/scratch/full"
fi
exec /usr/bin/python3 -B "$D/run_full.py" --source /dev/shm/historical-ffc1-source-20261030 --scratch "$SCRATCH" --mode full
