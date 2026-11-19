#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/fm4-codex-gate-20261118
/usr/bin/sha256sum --check --status <<'SEAL'
6d8715572e5bca63c69c85cb9d52f6acbdc079eb4510a92119276a54a35c16ad  /mnt/raid0/llm/tmp/vidya-belief-substrate/fm4-codex-gate-20261118/job.py
768b6575118764eb3754dee020a3b6aefe696d6058b17e882c6305b9b8427a50  /mnt/raid0/llm/tmp/vidya-belief-substrate/fm4-codex-gate-20261118/source-pins.json
SEAL
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id vb-fm4-codex-gate-20261118 --class cpu --role build --gpu-quiet none \
  --min-window 120 --stop "$D/STOP" --workdir "$D/engine-work" \
  --complete-cmd "/usr/bin/python3 -I -B $D/job.py complete --pins-sha256 768b6575118764eb3754dee020a3b6aefe696d6058b17e882c6305b9b8427a50" \
  --cmd "/usr/bin/python3 -I -B $D/job.py run --pins-sha256 768b6575118764eb3754dee020a3b6aefe696d6058b17e882c6305b9b8427a50"
