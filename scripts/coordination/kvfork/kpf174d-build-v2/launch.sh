#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf174d-build/v2
S=/mnt/raid0/llm/tmp/kvfork/kpf174d-build
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kvfork174d-build-20261102 --class cpu --role build --min-window 2400 --stop "$S/STOP" --workdir "$D" --precond-cmd "printf '%s  %s\n' 72a2cec452927804fbd1d5978942143a5e440cb8fef23d5ad49ae1c8cbc79990 $D/runtime.sha256 | sha256sum -c && sha256sum -c $D/runtime.sha256" --cmd "bash $D/job.sh" --complete-cmd "python3 $D/complete.py"
