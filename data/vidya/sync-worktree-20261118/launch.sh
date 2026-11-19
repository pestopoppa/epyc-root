#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/sync-worktree-current
/usr/bin/sha256sum --check --status <<'SEAL'
a71e8b81aed382d75bede9a96b811b3110a32b2b99bf048ab1f2fc07652b82ee  /mnt/raid0/llm/tmp/vidya-belief-substrate/sync-worktree-current/job.py
1832dc0efcbd93f9060a703cb9ec082086c1e1609bf591391960de1880c88f06  /mnt/raid0/llm/tmp/vidya-belief-substrate/sync-worktree-current/source-pins.json
SEAL
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id vb-sync-worktree-control-20261118 --class cpu --role build --gpu-quiet none \
  --min-window 120 --stop "$D/STOP" --workdir "$D/engine-work" \
  --complete-cmd "/usr/bin/python3 -I -B $D/job.py complete 1832dc0efcbd93f9060a703cb9ec082086c1e1609bf591391960de1880c88f06" \
  --cmd "/usr/bin/python3 -I -B $D/job.py run 1832dc0efcbd93f9060a703cb9ec082086c1e1609bf591391960de1880c88f06"
