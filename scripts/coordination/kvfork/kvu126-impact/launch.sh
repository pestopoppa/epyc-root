#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kvu126-impact-beb7-20261104
export ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kvu126-impact-beb7-20261104 --class cpu --role build --claim-cpus 0-95 --gpu-quiet none --min-window 300 --stop "$D/STOP" --complete-cmd "test -e '$D/out/COMPLETE'" --workdir "$D" --cmd "python3 '$D/job.py'" --precond-cmd "python3 '$D/job.py' --check"
