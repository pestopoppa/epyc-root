#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf41-backend-gpu-qualification-r3-20261119
cd "$D"
printf '%s  %s\n' 7bdd80eba5fd7f54d65f6e94405c57e8c5111df51dd14e462866764be3f12f45 runtime.sha256 | sha256sum --status -c -
sha256sum --quiet -c runtime.sha256
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf41-backend-gpu-qualification-r3-20261119 --class gpu --role bench --gpu-quiet exclusive --claim-cpus 184-187 --min-window 3600 --stop "$D/STOP" --workdir "$D" --precond-cmd "cd '$D' && printf '%s  %s\n' 7bdd80eba5fd7f54d65f6e94405c57e8c5111df51dd14e462866764be3f12f45 runtime.sha256 | sha256sum -c && sha256sum -c runtime.sha256 && env FILLER_ID=kpf41-backend-gpu-qualification-r3-20261119 python3 '$D/job.py' --check" --cmd "python3 '$D/job.py'" --complete-cmd "python3 '$D/complete.py'"
