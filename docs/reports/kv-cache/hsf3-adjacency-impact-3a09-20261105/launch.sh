#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/hsf3-adjacency-impact-3a09-20261105
export ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1
if [[ ${FILLER_SMOKE:-0} == 1 ]]; then
  export FILLER_DISK_FLOOR_GIB=20
  : "${FILLER_DRYRUN_RESULT_PATH:?separate smoke result path required}"
  CPUS=0-3
else
  export FILLER_DISK_FLOOR_GIB=150
  CPUS=0-95
fi
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id hsf3-adjacency-impact-3a09-20261105 --class cpu --role build --claim-cpus "$CPUS" --gpu-quiet none --min-window 7200 --stop "$D/STOP" --complete-cmd "test -e '$D/out/COMPLETE'" --workdir "$D" --cmd "python3 '$D/job.py'" --precond-cmd "cd '$D' && sha256sum -c seals.sha256 && python3 '$D/job.py' --check"
