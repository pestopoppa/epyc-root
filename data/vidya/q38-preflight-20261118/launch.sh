#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/q38-preflight-current
/usr/bin/sha256sum --check --status <<'SEAL'
3c2d18f182d4e611f8ebf6446b5e96ce26f4d181932bda2e19b9061326ba789b  /mnt/raid0/llm/tmp/vidya-belief-substrate/q38-preflight-current/job.py
75753d6c7911105e1a4ad6e4a529b80647c0c4026db76e5406087fad02ce9f1a  /mnt/raid0/llm/tmp/vidya-belief-substrate/q38-preflight-current/source-pins.json
SEAL
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id vb-q38-preflight-planner-20261118 --class cpu --role build --gpu-quiet none \
  --min-window 120 --stop "$D/STOP" --workdir "$D/engine-work" \
  --complete-cmd "/usr/bin/python3 -I -B $D/job.py complete --pins-sha256 75753d6c7911105e1a4ad6e4a529b80647c0c4026db76e5406087fad02ce9f1a" \
  --cmd "/usr/bin/python3 -I -B $D/job.py run --pins-sha256 75753d6c7911105e1a4ad6e4a529b80647c0c4026db76e5406087fad02ce9f1a"
