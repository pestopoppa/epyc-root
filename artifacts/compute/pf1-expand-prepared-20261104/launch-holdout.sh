#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/brf-exp04-r7-placement-20261104
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id brf-exp04-pf1-full-holdout-20261104-r7 \
  --class cpu+gpu --gpu-quiet exclusive --claim-cpus 0-95 --role bench --min-window 14400 \
  --cmd "bash $D/job.sh holdout" --complete-cmd "test -s $D/attempts/holdout/run/receipt.json" \
  --stop "$D/STOP-holdout" --workdir "$D"
