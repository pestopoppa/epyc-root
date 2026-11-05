#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf64-impact-4f4f-20261104-r2/r3
[ "$#" = 0 ] || { echo 'launch.sh accepts no mode argument; publisher smoke requires FILLER_SMOKE=1' >&2; exit 64; }
export KPF64_SEAL_SHA256=119d5d362dacb0b2d4e7d13a734110f692883e36b0bee3d39cfecf8e8a6c8e4e
MIN_WINDOW=7200
case "${FILLER_SMOKE:-0}" in
  1)
    : "${FILLER_DRYRUN_RESULT_PATH:?publisher smoke requires its native result path}"
    export FILLER_DISK_FLOOR_GIB=20
    MIN_WINDOW=1
    COMPLETE_CMD="/usr/bin/python3 -I '$D/job.py' --complete-check"
    ;;
  0)
    export FILLER_DISK_FLOOR_GIB=150
    MIN_WINDOW=7200
    COMPLETE_CMD="/usr/bin/python3 -I '$D/job.py' --complete-check"
    ;;
  *) echo 'invalid FILLER_SMOKE' >&2; exit 64;;
esac
export ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf64-impact-4f4f-20261104-r3 --class cpu --role build --claim-cpus 0-95 --gpu-quiet none --min-window "$MIN_WINDOW" --stop "$D/STOP" --complete-cmd "$COMPLETE_CMD" --workdir "$D" --cmd "/usr/bin/python3 -I '$D/job.py'" --precond-cmd "/usr/bin/python3 -I '$D/job.py' --check"
