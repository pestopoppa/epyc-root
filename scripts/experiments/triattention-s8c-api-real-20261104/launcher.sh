#!/bin/bash
set -euo pipefail
R=/mnt/raid0/llm/tmp/triattention-s8c-api-real-20261104
D="$R/packet"
ID=triattention-s8c-api-real-20261104
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
[[ $(sha256sum "$R/packet-pin.json" | cut -d' ' -f1) == 7dc464b4f921bc15054cb70c774c34f99da3d772b808423b5f960ae7abac9542 ]]
: "${WS58_REGIONS:?}"
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id "$ID" --class cpu --self-claim --role bench --gpu-quiet none --claim-cpus "$WS58_REGIONS" --min-window 600 --stop "$R/STOP" --port 18214 --workdir "$D" --cmd "/bin/bash $D/launcher.sh --job" --complete-cmd "/bin/bash $D/launcher.sh --complete"
