#!/bin/bash
set -euo pipefail
d=/mnt/raid0/llm/tmp/v11-promotion-checklist/ch17/final
cd "$d"
/usr/bin/sha256sum --check --quiet SOURCE.sha256
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
    --id ch17-c13-frontdoor-cpu-20261118-r4 --class cpu --role bench --gpu-quiet none \
    --port 19578 --min-window 1200 --workdir "$d" --stop "$d/STOP" \
    --precond-cmd "/usr/bin/python3 -I -B $d/job.py --precondition" \
    --cmd "/usr/bin/python3 -I -B $d/job.py" \
    --complete-cmd "/usr/bin/python3 -I -B $d/job.py --complete"
