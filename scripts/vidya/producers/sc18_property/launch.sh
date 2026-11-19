#!/bin/bash
set -euo pipefail
packet=/mnt/raid0/llm/tmp/vidya-belief-substrate/property-current
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id ni-sc18-cpu-softmax-property-20261118-v1 --class cpu --role build --gpu-quiet none --no-fold-siblings \
  --min-window 300 --stop-grace 10 \
  --precond-cmd "/usr/bin/python3 -BI $packet/run_property.py verify" \
  --cmd "/usr/bin/python3 -BI $packet/run_property.py run" \
  --complete-cmd "/usr/bin/python3 -BI $packet/run_property.py complete" \
  --workdir "$packet" --stop "$packet/STOP"
