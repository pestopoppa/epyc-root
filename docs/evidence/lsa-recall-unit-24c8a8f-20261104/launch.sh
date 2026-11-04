#!/bin/bash
set -euo pipefail
D=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id lsa-recall-unit-24c8a8f-20261104 \
  --class cpu --role build --gpu-quiet none --min-window 300 \
  --stop "$D/STOP" --workdir "$D" \
  --cmd "/usr/bin/python3 $D/job.py" \
  --complete-cmd "/usr/bin/python3 $D/complete.py"
