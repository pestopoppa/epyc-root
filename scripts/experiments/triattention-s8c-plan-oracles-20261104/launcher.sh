#!/bin/bash
set -euo pipefail
R=/mnt/raid0/llm/tmp/triattention-s8c-plan-oracles-20261104
: "${WS58_REGIONS:?}"
: "${FILLER_STATE_DIR:=$R/state}"
export FILLER_STATE_DIR
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id triattention-s8c-plan-oracles-20261104 --class cpu --self-claim --role build --gpu-quiet none --claim-cpus "$WS58_REGIONS" --min-window 300 --stop "$R/STOP" --workdir "$R" --cmd "/bin/bash $R/packet/job.sh" --complete-cmd "test -f $R/complete"
