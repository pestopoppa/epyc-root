#!/bin/bash
set -euo pipefail
H=/mnt/raid0/llm/tmp/v11-fa-ab-20261004/harness
FIX=/mnt/raid0/llm/tmp/cpu-fa-f16-20261004/build-cpu/bin
cd /mnt/raid0/llm/tmp/cpu-fa-f16-20261004
for k in 0 1; do
env -u LD_LIBRARY_PATH LD_LIBRARY_PATH="$FIX" GGML_FA_VKQ_F16=$k OMP_WAIT_POLICY=passive OMP_NUM_THREADS=24 \
    FA_PERF_ROWS=4 FA_PERF_NKV=16384 FA_PERF_KV=f16 FA_PERF_REPS=60 FA_PERF_MIN_REPS=30 FA_PERF_BUDGET_MS=2000 \
    perf record -q -o perf-k$k.data -F 999 -g -- "$H/fa_v11_cpu" CPU perf 24 > /dev/null 2>&1 || true
perf report -i perf-k$k.data --no-children --stdio --sort symbol 2>/dev/null | grep -E "^ +[0-9]" | head -12 | sed "s/^/[k=$k]/"
done
