#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/lsa-native-capacity-9216-20261104/packet
R=/mnt/raid0/llm/tmp/lsa-native-capacity-9216-20261104
: "${WS58_REGIONS:?allocator must supply CPU region}"
: "${FILLER_STATE_DIR:=$R/state}"
export FILLER_STATE_DIR
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id lsa-native-capacity-9216-20261104 --class cpu --self-claim --role build --gpu-quiet none --claim-cpus "$WS58_REGIONS" --min-window 300 --stop "$R/STOP" --workdir "$R" --cmd "/bin/bash $D/job.sh" --complete-cmd "test -f $R/complete"
