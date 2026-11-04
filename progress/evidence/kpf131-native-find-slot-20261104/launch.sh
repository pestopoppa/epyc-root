#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvu/find-slot-native-v1
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kvu-kpf131-old-native-findslot-20261104 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "python3 '$D/complete.py'" --cmd "python3 '$D/run.py'"
