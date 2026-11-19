#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf50-model-stat-fixture-20261105
printf '%s  %s\n' 0f34bfc00307bc80aa28e859f0d770421c5e5a13423358d67ec4e8117cd93c82 "$D/SHA256SUMS" | sha256sum --status -c -
sha256sum --quiet -c "$D/SHA256SUMS"
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf50-model-stat-fixture-20261105 --class cpu --role build --gpu-quiet none --min-window 300 --stop "$D/STOP" --workdir "$D" --complete-cmd "python3 -B '$D/job.py' --complete" --cmd "python3 -B '$D/job.py'"
