#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/q8-q15-tie-replay-20261127
cd "$D"
ulimit -c 0
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id q15-head-replay-cpu-20261127-r2 \
    --class cpu --role bench --gpu-quiet none --min-window 300 --port 27929 \
    --cmd "/bin/bash $D/job.sh" \
    --complete-cmd "/usr/bin/test -s $D/out/RESULT.json" \
    --stop "$D/STOP" --workdir "$D"
