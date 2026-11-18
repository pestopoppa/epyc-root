#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/delegation-context-preassembly/cmp4/packet
R=/mnt/raid0/llm/tmp/delegation-context-preassembly/cmp4
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id toc-cmp-4-pilot96-20261117 --class cpu --role bench --gpu-quiet none --no-fold-siblings \
  --claim-cpus "$WS58_REGIONS" --min-window 600 --stop "$R/STOP" --port 19359 --workdir "$D" \
  --cmd "python3 -B $D/runner.py run" --complete-cmd "python3 -B $D/runner.py complete" \
  --precond-cmd "python3 -B $D/runner.py precondition"
