#!/bin/bash
set -euo pipefail
export PATH="/mnt/raid0/llm/epyc-orchestrator/.venv/bin:$PATH"
D=/mnt/raid0/llm/tmp/canonical-judge-suite-revamp/live-pair-20261104
E=/mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh
exec bash "$E" --id tu-dtap-2-live-crm-pair-20261104 --class cpu --role build \
  --min-window 900 --port 19186 --stop "$D/STOP" --workdir "$D" \
  --cmd "python3 $D/job.py" --complete-cmd "test -s $D/run/complete.json"
