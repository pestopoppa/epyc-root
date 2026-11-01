#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/akagg-ch31-rowexact-pair-20261101
printf '%s  %s\n' '0ec79fb1769f7a1998eaf8d34a8eccb92f083f64272bc9b5da8ea23c5d1cd752' "$D/INPUT.sha256" | sha256sum -c -
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id akagg-ch31-rowexact-pair-c5-20261101 --class cpu --role bench --gpu-quiet none --claim-cpus 0-23 --min-window 600 --stop "$D/STOP" --workdir "$D" --cmd 'exec /bin/bash /mnt/raid0/llm/tmp/akagg-ch31-rowexact-pair-20261101/job.sh' --complete-cmd 'test -s /mnt/raid0/llm/tmp/akagg-ch31-rowexact-pair-20261101/full/RESULT.json'
