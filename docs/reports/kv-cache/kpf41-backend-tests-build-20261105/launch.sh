#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf41-backend-tests-build-20261105
printf '%s  %s\n' bc83cc5c612ec7d90ceb0a46582f17c8ebd40eb7bb049bfd4104f329ff23b5db "$D/SHA256SUMS" | sha256sum --status -c -
sha256sum --quiet -c "$D/SHA256SUMS"
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf41-backend-tests-build-20261105 --class cpu --role build --gpu-quiet none --min-window 3600 --stop "$D/STOP" --workdir "$D" --complete-cmd "python3 '$D/complete.py'" --cmd "bash '$D/job.sh'" --precond-cmd "python3 '$D/check.py'"
