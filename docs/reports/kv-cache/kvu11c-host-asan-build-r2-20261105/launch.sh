#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kvu11c-asan-build-20261105/packet-r2
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kvu11c-host-asan-build-r2-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --precond-cmd "printf '%s  %s\n' 160dba894668e5fce77eb6330555c6f2edbba46556367df17ba660fc81c01250 '$D/pins.json' | sha256sum -c && python3 '$D/check.py'" --complete-cmd "python3 '$D/complete.py'" --cmd "bash '$D/job.sh'"
