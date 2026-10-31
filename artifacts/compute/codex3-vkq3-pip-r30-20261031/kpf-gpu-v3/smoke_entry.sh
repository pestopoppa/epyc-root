#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-next-gpu-20261031-0240/gpu-leg-v3
tag=${1:?}
export FILLER_CPUS=184,185 FILLER_ID="kpf181-public-$tag" FILLER_DEADLINE=$(( $(date +%s)+255 )) FILLER_STOPFILE="$D/control-$tag/STOP"
mkdir -p "$D/control-$tag"
exec /usr/bin/python3 -B "$D/r11_supervisor.py" 260 -- /bin/bash "$D/job.sh" smoke "$tag"
