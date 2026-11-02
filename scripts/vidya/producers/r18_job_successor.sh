#!/bin/bash
set -euo pipefail
ID=r18-belief-symbols-20261102
D=/mnt/raid0/llm/tmp/r18-belief-successor-20261102
: "${FILLER_ID:?}" "${FILLER_CPUS:?}" "${FILLER_DEADLINE:?}"
[[ "$FILLER_ID" == "$ID" ]] || exit 64
mkdir -p "$D/scratch"
if [[ "${FILLER_DRYRUN:-0}" == 1 ]]; then
  SCRATCH=$(mktemp -d "$D/scratch/dryrun.XXXXXXXX")
else
  SCRATCH="$D/scratch/full"
fi
HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
exec /usr/bin/python3 -B "$HERE/r18_run_full_successor.py" --source /mnt/raid0/llm/r18-belief-source-ffc1 --scratch "$SCRATCH" --mode full
