#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex3-next-gpu-prep-20261031
SOURCE_SHA=58a4a78b39ce21d93fb79c1c95bc98189ba0c046777488962425fdac4536126c
printf '%s  %s\n' "$SOURCE_SHA" "$D/SOURCES.sha256" | sha256sum --status -c
timeout 180 sha256sum --quiet -c "$D/SOURCES.sha256"
timeout 180 /usr/bin/python3 -B "$D/check_inputs.py" "${1:-normal}"
if [[ ${1:-} == --smoke || ${1:-} == --cutoff ]]; then
  mode=${1#--}
  exec "$D/region-lock.sh" run --gpu-quiet exclusive --timeout-s 300 -- /usr/bin/taskset -c 184-185 /usr/bin/env -i PATH=/usr/bin:/bin HOME=/home/node LANG=C LC_ALL=C PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 PRB_SOURCE_SHA="$SOURCE_SHA" /bin/bash "$D/job.sh" "$mode"
fi
claims=()
if [[ $# -gt 0 ]]; then
 [[ $# == 2 && $1 == --claim-cpus ]] || exit 64
 claims=(--claim-cpus "$2")
fi
exec /usr/bin/env -i PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/home/node LANG=C LC_ALL=C PYTHONDONTWRITEBYTECODE=1 RUS3_DIAGNOSTIC=1 PRB_SOURCE_SHA="$SOURCE_SHA" FILLER_RL="$D/region-lock.sh" FILLER_FLAGS_DIR=/mnt/raid0/llm/tmp/compute-flags FILLER_GRANTS_DIR=/mnt/raid0/llm/tmp/compute-flags/grants FILLERS_MD=/mnt/raid0/llm/tmp/compute-flags/FILLERS.md FILLER_STATE_DIR="$D/state" FILLER_GPU_LOCK=/mnt/raid0/llm/tmp/gpu_device.mi210_0.lock FILLER_POLL=45 /bin/bash "$D/deps/filler_run13.sh" --id codex3-prbt4-r1-20261031 --class gpu --cmd "exec taskset -c \"\$FILLER_CPUS\" /bin/bash $D/job.sh normal" --complete-cmd "test -s '$D/results/DONE.json'" --min-window 1800 --stop "$D/STOP" --port 18979 --workdir "$D" --gpu-quiet exclusive --no-fold-siblings --gpu-threads 184-191 "${claims[@]}"
