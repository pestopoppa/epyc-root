#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/df2/cafe4-modes-native-cpu-r2-20261119
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id df2-cafe4-modes-native-cpu-r2-20261119 --class cpu --role bench --min-window 1800 --stop "$D/STOP" --workdir "$D" --precond-cmd "python3 $D/runtime.py inputs" --cmd "python3 $D/runtime.py run" --complete-cmd "python3 $D/runtime.py check"
