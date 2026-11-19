#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/delegation-context-preassembly/mp4/packet
R=/mnt/raid0/llm/tmp/delegation-context-preassembly/mp4
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id toc-mp-4-live-20261118 --class cpu --role bench --gpu-quiet none --no-fold-siblings \
  --claim-cpus "$WS58_REGIONS" --min-window 1500 --stop "$R/STOP" --port 19369 --workdir "$D" \
  --cmd "python3 -B $D/runner.py run" --complete-cmd "python3 -B $D/runner.py complete" \
  --precond-cmd "python3 -B $D/runner.py precondition"
