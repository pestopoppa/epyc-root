#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/kvfork/kpf41-impact-r5-20261104
EXPECTED_RUNTIME_SHA256=2c41e8255a0b6fd4e56427046dd851dbf21fd1f2437728b43b76bbc76ce6ac17
actual_runtime_sha256=$(sha256sum "$D/runtime.json" | awk '{print $1}')
if [[ "$actual_runtime_sha256" != "$EXPECTED_RUNTIME_SHA256" ]]; then
  echo "runtime manifest seal mismatch" >&2
  exit 64
fi
export KPF41_RUNTIME_SHA256="$EXPECTED_RUNTIME_SHA256"
export ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1
if [[ ${FILLER_SMOKE:-0} == 1 ]]; then export FILLER_DISK_FLOOR_GIB=20; else export FILLER_DISK_FLOOR_GIB=150; fi
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id kpf41-direct-vec-impact-8952a0f-20261104-r5 \
  --class cpu --role build --claim-cpus 0-95 --gpu-quiet none \
  --min-window 7200 --stop "$D/STOP" \
  --complete-cmd "test -e '$D/out/COMPLETE'" \
  --workdir "$D" --cmd "/usr/bin/python3 -I '$D/job.py'" \
  --precond-cmd "/usr/bin/python3 -I '$D/job.py' --check"
