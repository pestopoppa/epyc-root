#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf50-own-child-map-acquisition-r3-20261105
export PYTHONDONTWRITEBYTECODE=1
if [[ ${FILLER_SMOKE:-0} == 1 ]]; then
  : "${FILLER_DRYRUN_RESULT_PATH:?isolated smoke receipt required}"
  : "${WS58_REGIONS:?four smoke CPUs required}"
fi
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf50-own-child-map-acquisition-r3-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --precond-cmd "cd '$D' && sha256sum -c SHA256SUMS" --complete-cmd "/usr/bin/python3 -B -I '$D/complete.py'" --cmd "/usr/bin/python3 -B -I '$D/run.py'"
