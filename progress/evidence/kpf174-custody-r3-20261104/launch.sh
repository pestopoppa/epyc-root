#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvu/kpf174-custody-r3-20261104/v3
S=/mnt/raid0/llm/tmp/kvu/kpf174-custody-r3-20261104
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kvu-kpf174-custody-r3-20261104 --class cpu --role build --min-window 2400 --stop "$S/STOP" --workdir "$D" --precond-cmd "printf '%s  %s\n' 5d985ebe4482dfb7b0eba94b156ec2dbf8401ca86e5aef2c92a0959c4e38e678 $D/runtime.sha256 | sha256sum -c && sha256sum -c $D/runtime.sha256" --cmd "bash $D/job.sh" --complete-cmd "python3 $D/complete.py"
