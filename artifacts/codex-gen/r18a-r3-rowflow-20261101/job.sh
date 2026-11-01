#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/refactor-r18a-v10-independent-symbols-r3-20261101-candidate-b7
ID=refactor-r18a-v10-independent-symbols-r3-20261101
cd "$D"
sha256sum --strict --quiet -c "$D/SOURCE-MANIFEST.sha256"
[[ "${FILLER_ID:-}" == "$ID" && -n "${FILLER_CPUS:-}" ]] || exit 64
if [[ -n "${FILLER_QUAL_FIXTURE:-}" ]]; then
  exec /usr/bin/python3 -B "$D/qualification_job.py" "$FILLER_QUAL_FIXTURE"
fi
if [[ "${FILLER_DRYRUN:-0}" == 1 ]]; then
  mkdir -p "$D/scratch/dryrun"
  SCRATCH=$(mktemp -d "$D/scratch/dryrun/run-XXXXXXXX")
else
  SCRATCH="$D/scratch/full"
fi
exec /usr/bin/python3 -B "$D/full_build.py" --source /dev/shm/historical-ffc1-source-20261030 --scratch "$SCRATCH" --mode full
