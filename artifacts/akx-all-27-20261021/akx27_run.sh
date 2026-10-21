#!/bin/bash
# AKX-ALL-27 replay: AKX-ALL-26 HIP harness on parent vs keep, then width_dimension. Runs INSIDE a gpu-quiet exclusive claim.
set -uo pipefail
W=/mnt/raid0/llm/worktrees/akx-all-27-20261020
H=/mnt/raid0/llm/tmp/gpu-queue-20261020/akx-all-26
O=/mnt/raid0/llm/tmp/akx-all-27-20261020; mkdir -p $O
for who in parent keep; do
  if [ $who = parent ]; then B=/mnt/raid0/llm/kernels/builds/gpu-20261004-1bceceb05; else B=/mnt/raid0/llm/kernels/builds/gpu-20261004-656c9a66b; fi
  echo "[$(date -u +%T)] $who $B"
  timeout 2400 /usr/bin/python3 $W/scripts/benchmark/akx_width_invariance/run_width_probe.py run --backend rocm0 --build-bin $B/bin \
    --binary $H/harness/width_probe_hip_$who --cases $H/predicted_fail_list.jsonl --out $O/$who --threads 8 --kmax 9 --repeats 3 > $O/$who.log 2>&1
  echo "[$(date -u +%T)] $who rc=$?"
done
echo "[$(date -u +%T)] width_dimension"
cd $W && /usr/bin/python3 -m scripts.kernel_rnd.autokernel.loop.width_dimension --anchor-table $O/parent/cells.jsonl --keep-table $O/keep/cells.jsonl \
   --footprint ggml/src/ggml-cuda/mmvq.cu > $O/width_dimension.json 2> $O/width_dimension.err; echo "[$(date -u +%T)] wd rc=$?"
