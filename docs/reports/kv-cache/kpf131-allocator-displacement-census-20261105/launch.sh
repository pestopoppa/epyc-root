#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf131-allocator-displacement-census-20261105
printf '%s  %s\n' 1c1520a492e221a89701b7914fb9897948c1e06f7438b4971eb0cb3b36e5ea16 "$D/SEALED.sha256" | sha256sum --status -c -
sha256sum --quiet -c "$D/SEALED.sha256"
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf131-allocator-displacement-census-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "python3 -B '$D/job.py' --complete" --cmd "python3 -B '$D/job.py'"
