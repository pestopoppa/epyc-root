#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/brf-exp04-r7-placement-20261104
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id brf-exp04-pf1-full-initial-20261104-r7 \
  --class cpu+gpu --gpu-quiet exclusive --claim-cpus 0-95 --role bench --min-window 14400 \
  --cmd "bash $D/job.sh initial" --complete-cmd "test -s $D/attempts/initial/run/receipt.json" \
  --stop "$D/STOP-initial" --workdir "$D"
