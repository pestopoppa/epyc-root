#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/tb-semantics-current
/usr/bin/sha256sum --check --status <<'SEAL'
c57c223aac7952feb11140a002d403fa7e5f73604b1ddd83c8df2792b140a7a5  /mnt/raid0/llm/tmp/vidya-belief-substrate/tb-semantics-current/job.py
b2ba2f58a64e9d6d5001e37562bb966fb725c3434c67213a30db84c4a27b83ec  /mnt/raid0/llm/tmp/vidya-belief-substrate/tb-semantics-current/pins.json
SEAL
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id vb-tb-semantics-native-planner-20261118 --class cpu --role build --gpu-quiet none \
  --min-window 120 --stop "$D/STOP" --workdir "$D/work" \
  --complete-cmd "/usr/bin/python3 -I -B $D/job.py complete b2ba2f58a64e9d6d5001e37562bb966fb725c3434c67213a30db84c4a27b83ec" \
  --cmd "/usr/bin/python3 -I -B $D/job.py run b2ba2f58a64e9d6d5001e37562bb966fb725c3434c67213a30db84c4a27b83ec"
