#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/delegation-context-preassembly/cmp2/packet
R=/mnt/raid0/llm/tmp/delegation-context-preassembly/cmp2
ID=toc-cmp-2-governance-20261117
# Smoke mode returns after one native pair and a verified private-server exit.
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id "$ID" --class cpu --role bench --gpu-quiet none --no-fold-siblings \
  --claim-cpus "$WS58_REGIONS" --min-window 300 --stop "$R/STOP" --port 19357 --workdir "$D" \
  --cmd "python3 -B $D/runner.py run" --complete-cmd "python3 -B $D/runner.py complete"
