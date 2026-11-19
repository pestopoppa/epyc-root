#!/bin/bash
set -euo pipefail
R=/mnt/raid0/llm/tmp/delegation-context-preassembly/cf3c-binding-profile
D=$R/packet
PY=/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id cf3c-binding-20261119 --class cpu --role bench --gpu-quiet none --no-fold-siblings \
  --claim-cpus "$WS58_REGIONS" --min-window 10500 --stop "$R/STOP" --port 19387 --workdir "$D" \
  --cmd "$PY -I -B $D/runner.py run" --complete-cmd "$PY -I -B $D/runner.py complete" \
  --precond-cmd "$PY -I -B $D/runner.py precondition"
