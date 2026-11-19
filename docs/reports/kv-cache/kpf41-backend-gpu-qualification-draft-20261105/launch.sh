#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf41-backend-gpu-qualification-20261105
cd "$D"
printf '%s  %s\n' 9d08a5dafc4566c29c207e793e76ffa7caf20fdecc0a45dcc5e0fa05b0b601cf runtime.sha256 | sha256sum --status -c -
sha256sum --quiet -c runtime.sha256
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf41-backend-gpu-qualification-20261105 --class gpu --role bench --gpu-quiet exclusive --claim-cpus 184-187 --min-window 3600 --stop "$D/STOP" --workdir "$D" --precond-cmd "cd '$D' && printf '%s  %s\n' 9d08a5dafc4566c29c207e793e76ffa7caf20fdecc0a45dcc5e0fa05b0b601cf runtime.sha256 | sha256sum -c && sha256sum -c runtime.sha256 && python3 '$D/job.py' --check" --cmd "python3 '$D/job.py'" --complete-cmd "python3 '$D/complete.py'"
