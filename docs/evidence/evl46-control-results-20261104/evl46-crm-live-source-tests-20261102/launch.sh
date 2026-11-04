#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/evl46-live-unit-20261102
export PATH=/mnt/raid0/llm/epyc-orchestrator/.venv/bin:$PATH
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id evl46-crm-live-source-tests-20261102 --class cpu --role build --min-window 600 --complete-cmd "python $D/complete.py" --cmd "bash $D/job.sh" --stop "$D/STOP" --workdir "$D"
