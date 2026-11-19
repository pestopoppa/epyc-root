#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf174d-prospective
exec bash "$D/filler_run15.sh" --id kvfork174d-witness-20261102 --class gpu --gpu-quiet exclusive --claim-cpus 184-187 --role build --min-window 1800 --stop "$D/STOP" --port 18443 --sched-port 8083 --complete-cmd "python3 '$D/complete.py' '$D/out/RESULT.json'" --workdir "$D" --cmd "python3 '$D/control.py' --smoke"
