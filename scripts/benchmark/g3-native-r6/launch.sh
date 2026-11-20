#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/df2/g3-six-native-r6-20261120
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id df2-g3-six-native-r6-20261120 --class gpu --gpu-quiet exclusive --no-fold-siblings --role bench --min-window 7200 --stop "$D/STOP" --workdir "$D" --port 18991 --precond-cmd "printf '%s  %s\n' '9df8f41385313bdbe1a1626f8a9b146c90394575d1598c432526cc552d023f19' '$D/runtime.sha256' | sha256sum -c && sha256sum -c '$D/runtime.sha256' && python3 '$D/check.py' precondition" --cmd "python3 $D/job.py" --complete-cmd "python3 $D/check.py complete"
