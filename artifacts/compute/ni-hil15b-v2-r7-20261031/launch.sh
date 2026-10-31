#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/codex-ni-hil15b-v2-inference-prep-20261031
case ${1:-} in
  --smoke)
    export FILLER_CPUS=128-129 FILLER_DEADLINE=$(( $(date +%s) + 290 )) OMP_NUM_THREADS=1
    exec timeout --signal=TERM --kill-after=10 300 taskset -c "$FILLER_CPUS" /bin/bash "$D/job.sh" smoke;;
  --job)
    : "${FILLER_CPUS:?}" "${FILLER_DEADLINE:?}"
    exec taskset -c "$FILLER_CPUS" /bin/bash "$D/job.sh" full;;
  '')
    : "${WS58_REGIONS:?keeper must select one relocatable CPU quarter}"
    exec > >(tee -a "$D/ws58-launcher.out") 2>&1
    exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/filler_run13.sh \
      --id codex-ni-hil15b-v2-frozen60-r1-20261031 --class cpu --role build \
      --claim-cpus "$WS58_REGIONS" --min-window 23400 --stop "$D/STOP" --workdir "$D" \
      --cmd "/bin/bash $D/launch.sh --job" \
      --complete-cmd "python3 -c 'import json; a=json.load(open(\"$D/out/ASSESSMENT.json\")); assert a[\"state\"] in (\"full_measured\",\"terminal_inconclusive_no_redraw\")'";;
  *) exit 64;;
esac
