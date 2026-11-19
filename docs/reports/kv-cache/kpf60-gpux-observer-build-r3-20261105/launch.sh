#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf60-observer-build-r3-20261105
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf60-gpux-observer-build-20261105-r3 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --precond-cmd "printf '%s  %s\n' 40a02ef63ca012545db29e3b569047e137a9401f5bef6fa40e9afb776808e578 '$D/runtime.sha256' | sha256sum -c && sha256sum -c '$D/runtime.sha256' && python3 '$D/check.py'" --complete-cmd "python3 '$D/complete.py'" --cmd "bash '$D/job.sh'"
