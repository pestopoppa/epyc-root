#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/inf70-cls-rect-live-20261101
exec /mnt/raid0/llm/epyc-root/scripts/coordination/rowflow/filler_run15.sh \
  --id inf70-cls-rect-live-20261101 \
  --class cpu \
  --cmd "/bin/bash $D/run_live_arm.sh" \
  --min-window 1800 \
  --stop "$D/state/stop" \
  --complete-cmd "python3 $D/validate_complete.py $D/results/CLS-RECT-1a.jsonl" \
  --port 18499 \
  --role bench \
  --claim-cpus 0-95 \
  --workdir /mnt/raid0/llm/epyc-root
