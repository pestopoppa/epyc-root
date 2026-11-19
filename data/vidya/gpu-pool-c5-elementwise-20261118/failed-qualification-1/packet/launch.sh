#!/bin/bash
set -euo pipefail
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id ni-gpu-pool-elementwise-20261118-v5 --class gpu --gpu-quiet exclusive --no-fold-siblings \
  --min-window 300 --stop-grace 15 \
  --cmd '/usr/bin/python3 -BI /mnt/raid0/llm/tmp/vidya-belief-substrate/c5-elementwise-current/run_elementwise.py run' \
  --precond-cmd '/usr/bin/python3 -BI /mnt/raid0/llm/tmp/vidya-belief-substrate/c5-elementwise-current/run_elementwise.py verify' \
  --complete-cmd '/usr/bin/python3 -BI /mnt/raid0/llm/tmp/vidya-belief-substrate/c5-elementwise-current/run_elementwise.py complete' \
  --workdir /mnt/raid0/llm/tmp/vidya-belief-substrate/c5-elementwise-current \
  --stop /mnt/raid0/llm/tmp/vidya-belief-substrate/c5-elementwise-current/STOP
