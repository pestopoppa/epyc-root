#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/critical-compute-20261104/ward-fix-088/cpu-tests
export FILLER_STATE_DIR="$D/state"
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id lsa-ward-cpu-oracles-088-20261104 --class cpu --role bench --gpu-quiet none --min-window 1200 --stop "$D/STOP" --workdir "$D" --precond-cmd "test -f $D/pins.sha256" --cmd "/bin/bash $D/job.sh" --complete-cmd "test -f $D/complete"
