#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kvu19b-trace-analyzer-qual-20261105
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kvu19b-trace-analyzer-qual-20261105 --class cpu --role bench --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --precond-cmd "printf '%s  %s\n' 824b33c90709e639e76b35937191f927d8ba69ccb140f6daf3805e2ce9ee5467 '$D/inputs.json' | sha256sum -c" --cmd "bash '$D/job.sh'" --complete-cmd "python3 '$D/complete.py'"
