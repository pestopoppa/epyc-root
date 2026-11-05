#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf174-plan-bound-integration-prep-20261105
exec /bin/bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh --id kpf174-plan-bound-integration-20261105 --class cpu --role build --gpu-quiet none --min-window 140 --stop "$D/STOP" --workdir "$D" --precond-cmd "sha256sum -c SHA256SUMS" --complete-cmd "python3 -I -B '$D/complete.py'" --cmd "python3 -I -B '$D/smoke.py'"
