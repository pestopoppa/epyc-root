#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/critical-compute-20261104/numerical-combined
export FILLER_STATE_DIR="$D/state"
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id lsa-combined-numerics-20261104 --class cpu --role build --gpu-quiet none --min-window 600 --stop "$D/STOP" --workdir "$D" --precond-cmd "test -f $D/approved.json" --cmd "/bin/bash $D/job.sh" --complete-cmd "test -f $D/complete"
