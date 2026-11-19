#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/delegation-context-preassembly/cmp3-runtime/packet
R=/mnt/raid0/llm/tmp/delegation-context-preassembly/cmp3-runtime
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id toc-cmp-3-runtime-20261118 --class cpu --role bench --gpu-quiet none --no-fold-siblings \
  --claim-cpus "$WS58_REGIONS" --min-window 1000 --stop "$R/STOP" --port 19364 --workdir "$D" \
  --cmd "/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -B $D/runner.py run" --complete-cmd "/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -B $D/runner.py complete"
