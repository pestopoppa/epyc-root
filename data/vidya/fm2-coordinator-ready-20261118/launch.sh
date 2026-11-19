#!/bin/bash
set -euo pipefail
/usr/bin/sha256sum --check --status <<'SEAL'
badbce06305cf3f53b6d95a3ddf425e6eea8a91c35e3c1b3da663dee3526c5f8  /mnt/raid0/llm/tmp/vidya-belief-substrate/fm2-current/coordinator-row/job.py
SEAL
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id vb-fm2-coordinator-context-20261118 --class cpu --role build --gpu-quiet none \
  --min-window 120 --stop /mnt/raid0/llm/tmp/vidya-belief-substrate/fm2-current/coordinator-row/STOP --workdir /mnt/raid0/llm/tmp/vidya-belief-substrate/fm2-current/coordinator-row/engine-work \
  --complete-cmd "/mnt/raid0/llm/epyc-inference-research/.venv/bin/python3 -I -B /mnt/raid0/llm/tmp/vidya-belief-substrate/fm2-current/coordinator-row/job.py complete --pins-sha256 f309ba1d6e4b7fb2773a41359d6ba6ca606b5ef45c6982bb6a93acd9ff87380a" \
  --cmd "/mnt/raid0/llm/epyc-inference-research/.venv/bin/python3 -I -B /mnt/raid0/llm/tmp/vidya-belief-substrate/fm2-current/coordinator-row/job.py run --pins-sha256 f309ba1d6e4b7fb2773a41359d6ba6ca606b5ef45c6982bb6a93acd9ff87380a"
