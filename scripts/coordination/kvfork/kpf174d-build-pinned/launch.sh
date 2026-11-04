#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf174d-build-pinned/v3
S=/mnt/raid0/llm/tmp/kvfork/kpf174d-build-pinned
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kvfork174d-pinned-build-20261102 --class cpu --role build --min-window 2400 --stop "$S/STOP" --workdir "$D" --precond-cmd "printf '%s  %s\n' c4ce07828fef45befbb9a39fe88961609ef8ab43baad698051dd2cf9ddd5dc12 $D/runtime.sha256 | sha256sum -c && sha256sum -c $D/runtime.sha256" --cmd "bash $D/job.sh" --complete-cmd "python3 $D/complete.py"
