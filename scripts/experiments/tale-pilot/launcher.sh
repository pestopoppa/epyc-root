#!/bin/bash
set -euo pipefail
R=/mnt/raid0/llm/tmp/delegation-context-preassembly/tale-pilot
D=$R/packet
PY=/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id prb-t4-cpu-pilot-20261118 --class cpu --role bench --gpu-quiet none --no-fold-siblings \
  --claim-cpus "$WS58_REGIONS" --min-window 2200 --stop "$R/STOP" --port 19392 --workdir "$D" \
  --cmd "$PY -I -B $D/runner.py run" --complete-cmd "$PY -I -B $D/runner.py complete" \
  --precond-cmd "$PY -I -B $D/runner.py precondition"
