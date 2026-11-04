#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/critical-compute-20261104/ward-fix-088/hip-tests
export FILLER_STATE_DIR="$D/state"
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id lsa-ward-hip-tests-088-20261104 --class gpu --role bench --gpu-quiet exclusive --claim-cpus 94-95 --min-window 900 --stop "$D/STOP" --workdir "$D" --precond-cmd "test -f $D/approved-hip.json" --cmd "/bin/bash $D/job.sh" --complete-cmd "test -f $D/complete"
