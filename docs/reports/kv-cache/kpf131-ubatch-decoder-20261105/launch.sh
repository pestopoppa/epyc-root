#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf131-ubatch-decoder-20261105
cd "$D"
printf '%s  %s\n' '52573a1aea5a65d7bde5def830c16744e41f2cdd166dcc994e45a032bf642f51' seal.sha256 | sha256sum --check --status
sha256sum --check --status seal.sha256
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf131-ubatch-decoder-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "/usr/bin/python3 -I -B '$D/complete.py'" --cmd "/usr/bin/python3 -I -B '$D/run.py'"
