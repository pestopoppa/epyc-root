#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf131-old-abi-inventory-20261105
export PYTHONDONTWRITEBYTECODE=1
if [[ ${FILLER_SMOKE:-0} == 1 ]]; then
  : "${FILLER_DRYRUN_RESULT_PATH:?isolated publisher smoke receipt required}"
  : "${WS58_REGIONS:?publisher smoke CPUs required}"
fi
if [[ ${FILLER_SMOKE:-0} != 1 && -z ${FILLER_DRYRUN_RESULT_PATH:-} && -e "$D/out/RESULT.json" ]]; then
  echo 'Refuse stale full receipt: owner must archive it before a new inventory' >&2
  exit 64
fi
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf131-old-abi-inventory-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --precond-cmd "cd '$D' && sha256sum -c SHA256SUMS && sha256sum -c RUNTIME.sha256" --complete-cmd "/usr/bin/python3 -B -I '$D/complete.py'" --cmd "/usr/bin/python3 -B -I '$D/run.py'"
