#!/bin/bash
set -euo pipefail
R=/mnt/raid0/llm/tmp/triattention-kv-selection/s8c-api-phys-20261120
D="$R/packet"
ID=triattention-s8c-api-phys-20261120
: "${FILLER_STATE_DIR:=$R/state}"
export FILLER_STATE_DIR
if [[ ${1:-} == --job ]]; then
  : "${FILLER_CPUS:?}"
  exec taskset -c "$FILLER_CPUS" python3 -B "$D/job.py"
fi
if [[ ${1:-} == --complete ]]; then
  test -f "$R/complete"
  exit
fi
[[ $(sha256sum "$R/packet-pin.json" | cut -d' ' -f1) == f674b936ab12a139ee3e4d169a6b7f365bc3ba5d37c2117f72f36fd0e2c7be16 ]]
: "${WS58_REGIONS:?}"
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id "$ID" --class cpu --self-claim --role bench --gpu-quiet none --claim-cpus "$WS58_REGIONS" --min-window 300 --stop "$R/STOP" --port 18234 --workdir "$D" --cmd "/bin/bash $D/launcher.sh --job" --complete-cmd "/bin/bash $D/launcher.sh --complete"
