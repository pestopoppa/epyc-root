#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kvu19b-multi-clock-r2-20261105
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kvu19b-multi-clock-qual-r2-20261105 --class gpu --role bench --gpu-quiet exclusive --claim-cpus 184-187 --min-window 300 --stop "$D/STOP" --workdir "$D" --precond-cmd "printf '%s  %s\n' 87da02971a38e46f28499e241390d35c68d5101f97e59f2823ac2477586a0c1a '$D/runtime.sha256' | sha256sum -c && sha256sum -c '$D/runtime.sha256' && python3 '$D/check.py'" --cmd "bash '$D/job.sh'" --complete-cmd "python3 '$D/complete.py'"
