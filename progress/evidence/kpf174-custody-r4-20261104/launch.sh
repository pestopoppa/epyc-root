#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvu/kpf174-custody-r4-20261104/v3
S=/mnt/raid0/llm/tmp/kvu/kpf174-custody-r4-20261104
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kvu-kpf174-custody-r4-20261104 --class cpu --role build --min-window 2400 --stop "$S/STOP" --workdir "$D" --precond-cmd "printf '%s  %s\n' d5aae3ee667f23d77d8931bf32076662096a3614bed4dfd6eb3f03cb0e6e4a36 $D/runtime.sha256 | sha256sum -c && sha256sum -c $D/runtime.sha256" --cmd "bash $D/job.sh" --complete-cmd "python3 $D/complete.py"
