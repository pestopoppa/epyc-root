#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvu/kpf174-custody-r1-20261104/v3
S=/mnt/raid0/llm/tmp/kvu/kpf174-custody-r1-20261104
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kvu-kpf174-custody-r1-20261104 --class cpu --role build --min-window 2400 --stop "$S/STOP" --workdir "$D" --precond-cmd "printf '%s  %s\n' ab3573fffb872abe0d9d7ded387028dcda5c1861c7bd8cb0f435abdf98a077f0 $D/runtime.sha256 | sha256sum -c && sha256sum -c $D/runtime.sha256" --cmd "bash $D/job.sh" --complete-cmd "python3 $D/complete.py"
