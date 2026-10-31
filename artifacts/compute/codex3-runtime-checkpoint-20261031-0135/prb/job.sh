#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-next-gpu-prep-20261031
cd "$D"
: "${PRB_SOURCE_SHA:?missing pinned source digest}"
printf '%s  %s\n' "$PRB_SOURCE_SHA" "$D/SOURCES.sha256" | sha256sum --status -c
timeout 180 sha256sum --quiet -c "$D/SOURCES.sha256"
mode=${1:-normal}
if [[ $mode == smoke || $mode == cutoff ]]; then
  export FILLER_CPUS=184-185 FILLER_STOPFILE="$D/STOP-smoke" FILLER_END="$(( $(date +%s) + 290 ))" FILLER_DEADLINE="$(( $(date +%s) + 260 ))"
fi
ram=48

/bin/bash /mnt/raid0/llm/tmp/compute-flags/ram_admit.sh "$ram"
[[ $(df -Pk "$D" | awk 'NR==2 {print $4}') -ge $((151*1024*1024)) ]]
exec /usr/bin/env PRB_NATIVE_REVIEWED=1 /usr/bin/python3 -B "$D/native_worker.py" "$mode"
