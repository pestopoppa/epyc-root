#!/bin/bash
set -euo pipefail
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id ni-gpu-pool-attention-20261117-v1 --class gpu --gpu-quiet exclusive --no-fold-siblings \
  --min-window 300 --stop-grace 15 \
  --cmd '/usr/bin/python3 -BI /mnt/raid0/llm/tmp/vidya-belief-substrate/attention-ready/run_attention.py run' \
  --precond-cmd '/usr/bin/python3 -BI /mnt/raid0/llm/tmp/vidya-belief-substrate/attention-ready/run_attention.py verify' \
  --complete-cmd '/usr/bin/python3 -BI /mnt/raid0/llm/tmp/vidya-belief-substrate/attention-ready/run_attention.py complete' \
  --workdir /mnt/raid0/llm/tmp/vidya-belief-substrate/attention-ready \
  --stop /mnt/raid0/llm/tmp/vidya-belief-substrate/attention-ready/STOP
