#!/bin/bash
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
ID=kpf-rs1-impact-8952-20261104-r2
# Enforce the canonical floor regardless of inherited shell settings.
export ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1 FILLER_DISK_FLOOR_GIB=150
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id "$ID" --class cpu --role build --claim-cpus 0-95 --gpu-quiet none \
  --min-window 7200 --stop "$D/STOP" \
  --complete-cmd "test -e '$D/out/COMPLETE'" --workdir "$D" \
  --cmd "python3 '$D/job.py'" --precond-cmd "python3 '$D/job.py' --check"
