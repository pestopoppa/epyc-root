#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/rope-ctx-assessment/lsa-screen-20261103/root/artifacts/lsa-screen-20261103/booking-cpu-parity-r3
ID=lsa-screen-1-cpu-parity-r3-20261103
if [[ ${1:-} == --job ]]; then
  : "${FILLER_CPUS:?}"
  qualification_mode=${FILLER_DRYRUN:-0}
  smoke_mode=${FILLER_SMOKE:-0}
  exec env -u FILLER_DRYRUN -u FILLER_SMOKE /mnt/raid0/llm/epyc-orchestrator/scripts/region-lock run --cpu-list "$FILLER_CPUS" --role build --timeout-s 60 --tag "filler-$ID" -- env FILLER_DRYRUN="$qualification_mode" FILLER_SMOKE="$smoke_mode" taskset -c "$FILLER_CPUS" python3 -B "$D/job.py"
fi
if [[ ${1:-} == --complete ]]; then
  test -f "$D/ATTEMPT_FENCE/RESULT.json"
  exit
fi
[[ $# == 0 ]]
: "${WS58_REGIONS:?}"
[[ $WS58_REGIONS == 24-27 ]] || { echo 'requires a publisher four-core mask' >&2; exit 70; }
export FILLER_STATE_DIR="$D/state/$ID"
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id "$ID" --class cpu --self-claim --role build --gpu-quiet none --claim-cpus "$WS58_REGIONS" --min-window 900 --stop "$D/STOP" --workdir "$D" --cmd "/bin/bash $D/launcher.sh --job" --complete-cmd "/bin/bash $D/launcher.sh --complete"
