#!/bin/bash
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
ID=kpf-rs1-observer-impact-20261105
# Enforce the full-run floor; publisher smoke uses its isolated 20 GiB floor.
export ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1
if [[ ${FILLER_SMOKE:-0} == 1 ]]; then
  export FILLER_DISK_FLOOR_GIB=20
else
  export FILLER_DISK_FLOOR_GIB=150
fi
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id "$ID" --class cpu --role build --claim-cpus 0-95 --gpu-quiet none \
  --min-window 7200 --stop "$D/STOP" \
  --complete-cmd "test -e '$D/out/COMPLETE'" --workdir "$D" \
  --cmd "python3 '$D/job.py'" --precond-cmd "python3 '$D/job.py' --check 2> '$D/precond.err'"
