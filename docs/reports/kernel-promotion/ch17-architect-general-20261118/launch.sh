#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/v11-promotion-checklist/ch17-archgen
cd "$D"
/usr/bin/sha256sum --check --strict --quiet SOURCE.sha256
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
    --id ch17-c13-architect-general-cpu-20261118 --class cpu --role bench --gpu-quiet none \
    --port 19580 --min-window 9000 --workdir "$D" --stop "$D/STOP" \
    --precond-cmd "/usr/bin/python3 -I -B $D/job.py --precondition" \
    --cmd "/usr/bin/python3 -I -B $D/job.py" \
    --complete-cmd "/usr/bin/python3 -I -B $D/job.py --complete"
