#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf174d-build/v3
S=/mnt/raid0/llm/tmp/kvfork/kpf174d-build
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kvfork174d-build-20261102 --class cpu --role build --min-window 2400 --stop "$S/STOP" --workdir "$D" --precond-cmd "printf '%s  %s\n' c12d2e4e050bc1e70f61f9bea80b247d9b185f083c96217ea5b2309b2c6da00b $D/runtime.sha256 | sha256sum -c && sha256sum -c $D/runtime.sha256" --cmd "bash $D/job.sh" --complete-cmd "python3 $D/complete.py"
