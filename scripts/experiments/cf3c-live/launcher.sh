#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/delegation-context-preassembly/cf3c/packet
R=/mnt/raid0/llm/tmp/delegation-context-preassembly/cf3c
PY=/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id cf3c-pilot-20261118 --class cpu --role bench --gpu-quiet none --no-fold-siblings \
  --claim-cpus "$WS58_REGIONS" --min-window 3300 --stop "$R/STOP" --port 19379 --workdir "$D" \
  --cmd "$PY -I -B $D/runner.py run" --complete-cmd "$PY -I -B $D/runner.py complete" \
  --precond-cmd "$PY -I -B $D/runner.py precondition"
