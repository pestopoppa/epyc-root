#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvu/cpu-fa-vkq2-exact-20261102
test -s "$D/prepared.json"
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
 --id handoff-kvu-cpu-fa-vkq2-exact-20261102 --class cpu --cmd "python3 $D/job.py" \
 --min-window 14400 --stop "$D/STOP" --gpu-quiet exclusive \
 --claim-cpus 0-95 --role bench --workdir "$D" \
 --complete-cmd "python3 $D/check_complete.py"
