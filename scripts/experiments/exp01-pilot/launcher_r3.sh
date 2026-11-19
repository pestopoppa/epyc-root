#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/brf-exp01
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id brf-exp01-trellis-pilot-20261104-r3 --class cpu --role bench --gpu-quiet none --min-window 5400 --stop "$D/run-r3/STOP" --workdir "$D" --complete-cmd "/bin/bash $D/bin/pilot_r3_complete.sh" --precond-cmd "/bin/bash $D/bin/precond.sh" --cmd "/bin/bash $D/bin/pilot_r3_job.sh"
