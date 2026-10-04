#!/bin/bash
set -euo pipefail
H=/mnt/raid0/llm/tmp/v11-fa-ab-20261004/harness
FIX=/mnt/raid0/llm/tmp/cpu-fa-f16-20261004/build-cpu/bin
for rep in 1 2; do for k in 1 0; do
  env -u LD_LIBRARY_PATH LD_LIBRARY_PATH="$FIX" GGML_FA_VKQ_F16=$k OMP_WAIT_POLICY=passive OMP_NUM_THREADS=24 \
    FA_PERF_ROWS=1,4 FA_PERF_NKV=16384 FA_PERF_KV=f16 FA_PERF_REPS=30 FA_PERF_MIN_REPS=5 FA_PERF_BUDGET_MS=400 \
    nice -n 19 "$H/fa_v11_cpu" CPU perf 24 2>&1 | grep "^perf rows" | sed "s/^/[knob=$k] /"
done; done
