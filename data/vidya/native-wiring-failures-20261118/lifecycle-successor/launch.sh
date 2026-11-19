#!/bin/bash
set -euo pipefail
packet=/mnt/raid0/llm/tmp/vidya-belief-substrate/lifecycle-native/successor
cd "$packet"
ulimit -c 0
/usr/bin/sha256sum --check --status SOURCE.sha256
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id vb-v9-8-lifecycle-native-20261118-r2 --class cpu --role bench --gpu-quiet none --self-claim \
  --min-window 3600 --port 19364,19365 \
  --precond-cmd "/usr/bin/python3 -I -B $packet/job.py --precond" \
  --cmd "/usr/bin/python3 -I -B $packet/job.py" \
  --complete-cmd "/usr/bin/python3 -I -B $packet/job.py --complete" \
  --stop "$packet/STOP" --workdir "$packet"
