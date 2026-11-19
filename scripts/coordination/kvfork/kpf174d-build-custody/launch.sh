#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf174d-build-custody/v3
S=/mnt/raid0/llm/tmp/kvfork/kpf174d-build-custody
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kvfork174d-custody-build-20261102 --class cpu --role build --min-window 2400 --stop "$S/STOP" --workdir "$D" --precond-cmd "printf '%s  %s\n' 04d5a6af6ce90324050221d3fcf16e8dcb3a65ef77910c2f05b0a487f0a49cc6 $D/runtime.sha256 | sha256sum -c && sha256sum -c $D/runtime.sha256" --cmd "bash $D/job.sh" --complete-cmd "python3 $D/complete.py"
