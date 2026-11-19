#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf60-checked-fixture-r4
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf60-checked-fixture-20261104-r4 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --precond-cmd "printf '%s  %s\n' 19554d368a79150cd886f17c4e9e84cd370dca897fa37880e40284ad05d834ac '$D/inputs.json' | sha256sum -c && python3 '$D/check.py'" --complete-cmd "python3 '$D/complete.py'" --cmd "bash '$D/job.sh'"
