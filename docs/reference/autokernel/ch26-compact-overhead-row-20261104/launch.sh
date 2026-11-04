#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/autokernel-cross-workload-keep-gate/ch26-observer-overhead-20261104
cd "$D"
sha256sum --strict --quiet -c SEAL.sha256
exec /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id ch26-compact-observer-overhead-20261104 --class cpu --role bench --claim-cpus 0-95 --min-window 1800 --stop "$D/STOP" --workdir "$D" --cmd "/bin/bash $D/job.sh" --complete-cmd "/usr/bin/python3 -B $D/complete.py" --requires-tool bash --requires-tool python3
