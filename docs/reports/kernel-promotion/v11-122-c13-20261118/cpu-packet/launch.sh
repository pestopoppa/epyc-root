#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/v11-promotion-checklist/llg-cpu-gate/gate
cd "$D"
/usr/bin/sha256sum --check --quiet SOURCE.sha256
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id v11-122-llg-cpu-c13-gate-20261118 --class cpu --role bench --gpu-quiet none \
  --min-window 1500 --workdir "$D" --stop "$D/STOP" \
  --precond-cmd "/usr/bin/python3 -I -B $D/job.py --precondition" \
  --cmd "/usr/bin/python3 -I -B $D/job.py" \
  --complete-cmd "/usr/bin/python3 -I -B $D/job.py --complete"
