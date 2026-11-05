#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf41-backend-gpu-qualification-20261105
cd "$D"
printf '%s  %s\n' dcf3a1c611d96742bbaa98faaa7e133d2026858602a6120b7726131d6482afd8 runtime.sha256 | sha256sum --status -c -
sha256sum --quiet -c runtime.sha256
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf41-backend-gpu-qualification-20261105 --class gpu --role bench --gpu-quiet exclusive --claim-cpus 184-187 --min-window 3600 --stop "$D/STOP" --workdir "$D" --precond-cmd "cd '$D' && printf '%s  %s\n' dcf3a1c611d96742bbaa98faaa7e133d2026858602a6120b7726131d6482afd8 runtime.sha256 | sha256sum -c && sha256sum -c runtime.sha256 && python3 '$D/job.py' --check" --cmd "python3 '$D/job.py'" --complete-cmd "python3 '$D/complete.py'"
