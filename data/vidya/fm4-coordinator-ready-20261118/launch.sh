#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/fm4-review-current
/usr/bin/sha256sum --check --status <<'SEAL'
27a674d386068472eab5adab91b4f0c5cf54ff97aee5c0e542af0ea031c1590a  /mnt/raid0/llm/tmp/vidya-belief-substrate/fm4-review-current/job.py
SEAL
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id vb-fm4-coordinator-context-20261118 --class cpu --role build --gpu-quiet none \
  --min-window 120 --stop "$D/STOP" --workdir "$D/engine-work" \
  --complete-cmd "/usr/bin/python3 -I -B $D/job.py complete --pins-sha256 6d024859f259ad088dc569176c442501318c20bab965b3ddb0acef8aae0fe615" \
  --cmd "/usr/bin/python3 -I -B $D/job.py run --pins-sha256 6d024859f259ad088dc569176c442501318c20bab965b3ddb0acef8aae0fe615"
