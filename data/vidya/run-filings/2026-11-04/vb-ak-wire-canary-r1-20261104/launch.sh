#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/vb-ak-wire-canary-r1-20261104
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id vb-ak-wire-canary-r1-20261104 --class cpu --role bench --gpu-quiet none --min-window 900 --stop "$D/STOP" --workdir "$D" --cmd "/usr/bin/python3 -B $D/job.py" --complete-cmd "/usr/bin/python3 -B $D/complete.py"
