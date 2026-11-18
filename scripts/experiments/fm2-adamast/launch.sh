#!/bin/bash
set -euo pipefail
D=@RUN_DIR@
C=$D/code
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id fm2-adamast-20261118 \
  --class cpu --gpu-quiet none --role build --min-window 600 --port 18711 \
  --precond-cmd "/bin/bash $C/precond.sh" \
  --cmd "/bin/bash $C/job.sh" \
  --complete-cmd "/usr/bin/python3 -B $C/pilot.py complete" \
  --stop "$D/STOP" --workdir "$D"
