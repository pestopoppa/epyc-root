#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf60-select-build-r3
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf60-gpux-select-build-20261104-r3 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --precond-cmd "printf '%s  %s\n' ff71eb63fe5886d3617be9cac8b686879c5d02faf10597d509498b15c3c73d73 '$D/runtime.sha256' | sha256sum -c && sha256sum -c '$D/runtime.sha256' && python3 '$D/check.py'" --complete-cmd "python3 '$D/complete.py'" --cmd "bash '$D/job.sh'"
