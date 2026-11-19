#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/sync-hook-current
/usr/bin/sha256sum --check --status <<'SEAL'
119f4af0eba94235b9dd728991a908347e483ae79cd80a743e46ae926f07f74e  /mnt/raid0/llm/tmp/vidya-belief-substrate/sync-hook-current/job.py
fb7616cec4f5722a46f2c6f9f2407f63e953f15178121aae80da339d1782222a  /mnt/raid0/llm/tmp/vidya-belief-substrate/sync-hook-current/source-pins.json
SEAL
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id vb-sync-published-repair-20261118 --class cpu --role build --gpu-quiet none \
  --min-window 120 --stop "$D/STOP" --workdir "$D/engine-work" \
  --complete-cmd "/usr/bin/python3 -I -B $D/job.py complete fb7616cec4f5722a46f2c6f9f2407f63e953f15178121aae80da339d1782222a" \
  --cmd "/usr/bin/python3 -I -B $D/job.py run fb7616cec4f5722a46f2c6f9f2407f63e953f15178121aae80da339d1782222a"
