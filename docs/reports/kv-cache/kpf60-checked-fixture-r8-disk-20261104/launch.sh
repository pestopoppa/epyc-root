#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf60-checked-fixture-r8
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf60-checked-fixture-20261104-r8 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --precond-cmd "printf '%s  %s\n' 7797cadfc7f24de7331972fbe6da93570dcc08a2ccac8440f1a4d0025bec3826 '$D/inputs.json' | sha256sum -c && python3 '$D/check.py'" --complete-cmd "python3 '$D/complete.py'" --cmd "bash '$D/job.sh'"
