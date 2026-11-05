#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf41-gpu-parity-r2-20261105
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf41-gpu-parity-r2-20261105 --class gpu --role bench --gpu-quiet exclusive --claim-cpus 184-187 --min-window 300 --stop "$D/STOP" --workdir "$D" --precond-cmd "cd '$D' && printf '%s  %s\n' 132cde162c0143ff7505728760910e566531ea1a3b6ea4f15f66454bc1326115 runtime.sha256 | sha256sum -c && sha256sum -c runtime.sha256 && python3 '$D/job.py' --check" --cmd "python3 '$D/job.py'" --complete-cmd "python3 '$D/complete.py'"
