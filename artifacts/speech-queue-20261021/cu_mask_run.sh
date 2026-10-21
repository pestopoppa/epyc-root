#!/bin/bash
# SPQ-09: stage 1 compile (CPU build claim, 1 region), stage 2 run (gpu-quiet EXCLUSIVE, no region claim, ~3 min).
# usage: cu_mask_run.sh --deadline ISO-UTC [--gpu 0] [--dry-run]
set -euo pipefail
RL=/workspace/repos/epyc-orchestrator/scripts/region-lock; D=/mnt/raid0/llm/tmp/speech-queue-20261020; S=$D/scripts; O=$D/cu_mask_out
DEADLINE=""; GPU=0; DRY=0; CW=900
while [ $# -gt 0 ]; do case "$1" in --deadline) DEADLINE=$2; shift 2;; --gpu) GPU=$2; shift 2;; --dry-run) DRY=1; shift;; --claim-wait) CW=$2; shift 2;; *) echo "bad arg $1">&2; exit 2;; esac; done
[ -n "$DEADLINE" ] || { echo "--deadline required" >&2; exit 2; }
DE=$(date -u -d "$DEADLINE" +%s); [ "$(date -u +%s)" -lt "$DE" ] || { echo "deadline passed" >&2; exit 3; }
echo "plan: compile $S/cu_mask_probe.cpp (hipcc gfx90a) under build claim q0; run on GPU $GPU under --gpu-quiet exclusive; out $O"
[ -x /opt/rocm/bin/hipcc ] && [ -f $S/cu_mask_probe.cpp ] || { echo missing hipcc/source; exit 2; }
[ "$DRY" = 1 ] && exit 0
mkdir -p "$O"
"$RL" run --regions q3 --role build --timeout-s $CW --tag spq-cumask-build -- /opt/rocm/bin/hipcc -O2 --offload-arch=gfx90a $S/cu_mask_probe.cpp -o $O/cu_mask_probe > $O/build.log 2>&1
"$RL" run --gpu-quiet exclusive --role bench --timeout-s $CW --tag spq-cumask-run -- \
  timeout --signal=TERM $((DE - $(date -u +%s))) env HIP_VISIBLE_DEVICES=$GPU $O/cu_mask_probe | tee $O/result.txt
# residency evidence (observation window = the run itself is ~seconds; the probe prints device name/CUs from inside the process)
sha256sum $O/cu_mask_probe $S/cu_mask_probe.cpp > $O/SHA256SUMS
