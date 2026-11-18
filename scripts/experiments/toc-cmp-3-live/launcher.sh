#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/delegation-context-preassembly/cmp3-live-r2/packet
R=/mnt/raid0/llm/tmp/delegation-context-preassembly/cmp3-live-r2
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id toc-cmp-3-live-20261118-r2 --class cpu --role bench --gpu-quiet none --no-fold-siblings \
  --claim-cpus "$WS58_REGIONS" --min-window 900 --stop "$R/STOP" --port 19368 --workdir "$D" \
  --cmd "python3 -B $D/cmp3_live.py run" --complete-cmd "python3 -B $D/cmp3_live.py complete" \
  --precond-cmd "python3 -B $D/cmp3_live.py precondition"
