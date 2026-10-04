#!/bin/bash
# run_bench.sh — indicative end-to-end CPU cost of the fix: llama-bench, f16 KV, FA on, ABAB.
# Run under: region-lock run --cpu-list 0-23 --role bench --tag cpu-fa-f16 -- taskset -c 0-23 ./run_bench.sh
set -euo pipefail
O=/mnt/raid0/llm/tmp/cpu-fa-f16-20261004/bench-out; mkdir -p "$O"
M=/mnt/raid0/llm/models/Qwen3-1.7B-Q8_0.gguf
for rep in 1 2; do
  for arm in base fix; do
    B=/mnt/raid0/llm/kernels/builds/cpu-20260925-90c12df42/bin
    [ $arm = fix ] && B=/mnt/raid0/llm/tmp/cpu-fa-f16-20261004/build-cpu/bin
    env -u LD_LIBRARY_PATH OMP_WAIT_POLICY=active OMP_PROC_BIND=close OMP_PLACES=cores nice -n 19 \
        "$B/llama-bench" -m "$M" -t 24 -fa 1 -ctk f16 -ctv f16 -p 5 -n 64 -d 4096,16384 -r 3 -o md \
        > "$O/${arm}_$rep.md" 2> "$O/${arm}_$rep.err" || echo "rc=$? $arm $rep"
    echo "== $arm rep $rep"; grep -E "pp5|tg64" "$O/${arm}_$rep.md"
  done
done
