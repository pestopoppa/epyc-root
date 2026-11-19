#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/vidya-belief-substrate/exp01-official-20261118-r2
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id vidya-exp01-proxy-official-native-20261118-r2 --class cpu --role bench --gpu-quiet none --min-window 3600 --stop "$D/STOP" --workdir "$D/engine-work" --precond-cmd "python3 -B $D/runner.py check" --complete-cmd "python3 -B $D/runner.py complete" --cmd "python3 -B $D/runner.py run"
