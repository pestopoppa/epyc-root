#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/triattention-s8c-recency-build-20261104
export FILLER_STATE_DIR="$D/state"
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id triattention-s8c-cpu-build-20261104 --class cpu --role build --gpu-quiet none --min-window 1800 --stop "$D/STOP" --workdir "$D" --cmd "/bin/bash $D/packet/job.sh" --complete-cmd "test -f $D/complete"
