#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/sync-worktree-current
/usr/bin/sha256sum --check --status <<'SEAL'
a71e8b81aed382d75bede9a96b811b3110a32b2b99bf048ab1f2fc07652b82ee  /mnt/raid0/llm/tmp/vidya-belief-substrate/sync-worktree-current/job.py
876d45256938dae707f2137f4665919e9323290bdbf4cf4bfe4c7c6398808691  /mnt/raid0/llm/tmp/vidya-belief-substrate/sync-worktree-current/source-pins.json
SEAL
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id vb-sync-worktree-control-20261118 --class cpu --role build --gpu-quiet none \
  --min-window 120 --stop "$D/STOP" --workdir "$D/engine-work" \
  --complete-cmd "/usr/bin/python3 -I -B $D/job.py complete 876d45256938dae707f2137f4665919e9323290bdbf4cf4bfe4c7c6398808691" \
  --cmd "/usr/bin/python3 -I -B $D/job.py run 876d45256938dae707f2137f4665919e9323290bdbf4cf4bfe4c7c6398808691"
