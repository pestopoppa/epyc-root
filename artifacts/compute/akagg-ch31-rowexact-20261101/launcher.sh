#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/akagg-ch31-rowexact-20261101
printf '%s  %s\n' '9a1cbb4b1221c2c5555ce5836ed28d58a6c6e2586e2b49431ac25ef08b2ab881' "$D/INPUT.sha256" | sha256sum -c -
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id akagg-ch31-rowexact-c5-20261101 --class cpu --role bench --gpu-quiet none --claim-cpus 0-23 --min-window 600 --stop "$D/STOP" --workdir "$D" --cmd 'exec /bin/bash /mnt/raid0/llm/tmp/akagg-ch31-rowexact-20261101/job.sh' --complete-cmd 'test -s /mnt/raid0/llm/tmp/akagg-ch31-rowexact-20261101/full/RESULT.json'
