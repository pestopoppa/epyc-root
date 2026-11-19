#!/bin/bash
set -euo pipefail
D=/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency/kpf41-impact-scan
EXPECTED_RUNTIME_SHA256=5f8ccb4182376d244681af9885b9a978be541484833ca759a582ef28e9aba57b
actual_runtime_sha256=$(sha256sum "$D/runtime.json" | awk '{print $1}')
if [[ "$actual_runtime_sha256" != "$EXPECTED_RUNTIME_SHA256" ]]; then
  echo "runtime manifest seal mismatch" >&2
  exit 64
fi
export KPF41_RUNTIME_SHA256="$EXPECTED_RUNTIME_SHA256"
export ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1
exec bash /mnt/raid0/llm/tmp/compute-flags/bin/rowflow/filler_run15.sh \
  --id kpf41-direct-vec-impact-8952a0f-20261104 \
  --class cpu --role build --claim-cpus 0-95 --gpu-quiet none \
  --min-window 7200 --stop "$D/STOP" \
  --complete-cmd "test -e '$D/out/COMPLETE'" \
  --workdir "$D" --cmd "/usr/bin/python3 -I '$D/job.py'" \
  --precond-cmd "/usr/bin/python3 -I '$D/job.py' --check"
