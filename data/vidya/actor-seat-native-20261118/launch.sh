#!/bin/bash
set -euo pipefail
# Packet preflight verifies the OpenCode v2 metrics projection source and replay units.
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/actor-seat-native-20261118
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id vb-ak-seat-native-instrument-20261118 --class cpu --role bench --gpu-quiet none \
  --no-fold-siblings --min-window 300 --port 19413 \
  --stop "$D/STOP" --workdir "$D/engine-work" \
  --precond-cmd "/usr/bin/python3 -B $D/job.py preflight" \
  --complete-cmd "/usr/bin/python3 -B $D/job.py complete" \
  --cmd "/usr/bin/python3 -B $D/job.py run"
