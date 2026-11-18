#!/bin/bash
set -euo pipefail
R=/mnt/raid0/llm/tmp/delegation-context-preassembly/dcp12
D=$R/packet
PY=/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id dcp12-calibration-20261118 --class cpu --role bench --gpu-quiet exclusive --no-fold-siblings \
  --claim-cpus "$WS58_REGIONS" --min-window 5460 --stop "$R/STOP" --port 19383 --workdir "$D" \
  --cmd "$PY -I -B $D/runner.py run" --complete-cmd "$PY -I -B $D/runner.py complete" \
  --precond-cmd "$PY -I -B $D/runner.py precondition"
