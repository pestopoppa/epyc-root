#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kvu19b-multi-clock-r3-20261105
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kvu19b-multi-clock-qual-r3-20261105 --class gpu --role bench --gpu-quiet exclusive --claim-cpus 184-187 --min-window 300 --stop "$D/STOP" --workdir "$D" --precond-cmd "printf '%s  %s\n' ad1ed000b642424a0e4a214606765660f0fbc3df0c5f4485d3902411905f8d1a '$D/runtime.sha256' | sha256sum -c && sha256sum -c '$D/runtime.sha256' && python3 '$D/check.py'" --cmd "bash '$D/job.sh'" --complete-cmd "python3 '$D/complete.py'"
