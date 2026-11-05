#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvu/kpf131-impact-r4-20261105
export ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1
if [[ ${FILLER_SMOKE:-0} == 1 ]]; then
 export FILLER_DISK_FLOOR_GIB=20
 : "${FILLER_DRYRUN_RESULT_PATH:?}"
 CPUS=0-3
else
 export FILLER_DISK_FLOOR_GIB=150
 CPUS=0-95
fi
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf131-native-binding-impact-a1f0-r4-20261105 --class cpu --role build --claim-cpus "$CPUS" --gpu-quiet none --min-window 300 --stop "$D/STOP" --complete-cmd "test -e '$D/out/COMPLETE'" --workdir "$D" --cmd "python3 '$D/job.py'" --precond-cmd "cd '$D' && sha256sum --quiet -c seals.sha256 && python3 '$D/job.py' --check"
