#!/bin/bash
set -euo pipefail
R=/mnt/raid0/llm/tmp/delegation-context-preassembly/thinking-probe
D=$R/packet
PY=/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id thinking-budget-semantics-20261118 --class cpu --role bench --gpu-quiet none --no-fold-siblings \
  --claim-cpus "$WS58_REGIONS" --min-window 300 --stop "$R/STOP" --port 19389 --workdir "$D" \
  --cmd "$PY -I -B $D/runner.py run" --complete-cmd "$PY -I -B $D/runner.py complete" \
  --precond-cmd "$PY -I -B $D/runner.py precondition"
