#!/bin/bash
set -Eeuo pipefail
S=/mnt/raid0/llm/tmp/codex-ni-20261027-ready-cpu-batch
export FILLER_STATE_DIR=${FILLER_STATE_DIR:-$S/fresh/state}
repeat=()
if [[ ${FILLER_PREFLIGHT:-0} == 1 ]]; then export FILLER_GPU_LOCK="$S/dryrun-gpu.lock"; fi
[[ ${FILLER_PREFLIGHT:-0} == 1 ]] || repeat+=(--repeat)
exec "$S/deps/filler_run12.sh" --id ni-yarn-fresh-native-cohort --class gpu --gpu-quiet exclusive --no-fold-siblings --gpu-threads 184-191 --port 18096 --role bench --min-window 2700 --stop /mnt/raid0/llm/tmp/compute-flags/STOP.ni-yarn-fresh-native-cohort --workdir "$S" --cmd "bash $S/fresh/job.sh" --complete-cmd "test -s $S/fresh/out/VERIFIED_COMPLETE" "${repeat[@]}"
