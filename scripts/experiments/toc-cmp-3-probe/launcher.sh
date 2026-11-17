#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/delegation-context-preassembly/cmp3/packet
R=/mnt/raid0/llm/tmp/delegation-context-preassembly/cmp3
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id toc-cmp-3-contract-20261117 --class cpu --role bench --gpu-quiet none --no-fold-siblings \
  --claim-cpus "$WS58_REGIONS" --min-window 300 --stop "$R/STOP" --port 19358 --workdir "$D" \
  --cmd "python3 -B $D/runner.py run" --complete-cmd "python3 -B $D/runner.py complete"
