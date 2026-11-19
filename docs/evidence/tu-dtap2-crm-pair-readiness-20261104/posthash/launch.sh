#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/canonical-judge-suite-revamp/live-pair-20261104
E=/mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh
exec bash "$E" --id evl46-crm-posthash-20261104 --class cpu --role build \
  --min-window 120 --stop "$D/posthash/STOP" --workdir "$D/posthash" \
  --cmd "bash $D/posthash/job.sh" \
  --complete-cmd "test -s $D/posthash/posthash.json && $D/posthash/validate_posthash.py $D/posthash/posthash.json"
