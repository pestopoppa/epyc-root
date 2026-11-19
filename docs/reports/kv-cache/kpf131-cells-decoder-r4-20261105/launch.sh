#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf131-cells-decoder-r4-20261105
cd "$D"
printf '%s  %s\n' '31f62ee9a34f11612c454601501f94203887f2846796da5ed0136dc713327914' seal.sha256 | sha256sum --check --status
sha256sum --check --status seal.sha256
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf131-cells-abi-decoder-r4-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "/usr/bin/python3 -I -B '$D/complete.py'" --cmd "/usr/bin/python3 -I -B '$D/run.py'"
