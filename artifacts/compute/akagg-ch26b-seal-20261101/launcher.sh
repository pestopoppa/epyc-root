#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/akagg-ch26b-20261101
printf '%s  %s\n' 'd12336fbdc13511e3d787f152c55127b947e9400abb16d11447fba56431ab741' "$D/INPUT.sha256" | sha256sum -c -
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id akagg-ch26b-1017-c2-20261101 --class cpu --role bench --gpu-quiet exclusive --claim-cpus 0-95 --min-window 8000 --stop "$D/STOP" --workdir "$D" --port 18741 --cmd 'exec /bin/bash /mnt/raid0/llm/tmp/akagg-ch26b-20261101/job.sh' --complete-cmd 'test -s /mnt/raid0/llm/tmp/akagg-ch26b-20261101/input/full/calibrate-summary.json'
