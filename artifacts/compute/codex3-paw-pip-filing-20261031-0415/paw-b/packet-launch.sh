#!/bin/bash
set -euo pipefail
export RUS3_DIAGNOSTIC=1
D=/mnt/micron/codex3-paw-compact-b-20261030/packet
export EPYC_ROOT=/mnt/raid0/llm/tmp/codex3-paw-standard-r2-20261030
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= HIP_VISIBLE_DEVICES=
if [[ ${1:-} == --smoke ]]; then
  export FILLER_CPUS=${FILLER_CPUS:?} PAW_SMOKE_DEADLINE=$(( $(date +%s) + 275 ))
  cd "$D"
  exec taskset -c "$FILLER_CPUS" /usr/bin/python3 -I "$D/smoke-supervisor.py" 285 -- "$D/.venv/bin/python" "$D/job.py" smoke --epyc-root "$EPYC_ROOT"
fi
[[ $# == 0 ]] || exit 64
cd "$D"
exec bash "$D/engine/filler_run13.sh" --id codex3-paw-compact-b-20261030 --class cpu --role bench --claim-cpus "${WS58_REGIONS:?}" --min-window 2400 --port 19954 --stop "/mnt/raid0/llm/tmp/codex3-paw-compact-b-20261030/STOP" --workdir "$D" --cmd 'taskset -c "$FILLER_CPUS" /mnt/micron/codex3-paw-compact-b-20261030/packet/.venv/bin/python /mnt/micron/codex3-paw-compact-b-20261030/packet/job.py real --epyc-root "$EPYC_ROOT"' --complete-cmd "test -f $D/DONE"
