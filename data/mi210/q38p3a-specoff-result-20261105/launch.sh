#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/fable5-window2-findings-05c-mi210-lever/q38p3a
cd "$D"
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id q38p3a-specoff-abba-20261105 --class gpu --gpu-quiet exclusive --claim-cpus 184-191 --gpu-threads 184-191 --role bench --min-window 3000 --cmd "/usr/bin/python3 -I $D/job.py" --complete-cmd "test -s $D/out/COMPLETE.json" --stop "$D/STOP" --workdir "$D"
