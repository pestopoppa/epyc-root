#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf131-findslot-observer-20261105
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kvfork-kpf131-findslot-observer-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "/usr/bin/python3 -E -s -B '$D/complete.py'" --cmd "/usr/bin/python3 -E -s -B '$D/run.py'"
