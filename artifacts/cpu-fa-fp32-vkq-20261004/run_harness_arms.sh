#!/bin/bash
# run_harness_arms.sh — CPU-only fa_v11 harness: baseline champion vs fix vs fix+legacy knob.
# Run under: region-lock run --cpu-list 0-23 --role bench --tag cpu-fa-f16 -- taskset -c 0-23 ./run_harness_arms.sh
set -euo pipefail
H=/mnt/raid0/llm/tmp/v11-fa-ab-20261004/harness
O=/mnt/raid0/llm/tmp/cpu-fa-f16-20261004/harness-out
BASE=/mnt/raid0/llm/kernels/builds/cpu-20260925-90c12df42/bin
FIX=/mnt/raid0/llm/tmp/cpu-fa-f16-20261004/build-cpu/bin
mkdir -p "$O"
run() { # <name> <libdir> <mode> [extra env...]
    local name=$1 lib=$2 mode=$3; shift 3
    env -u LD_LIBRARY_PATH LD_LIBRARY_PATH="$lib" FA_REF_DIR="$H/ref_cpu" OMP_WAIT_POLICY=passive OMP_NUM_THREADS=24 "$@" \
        nice -n 19 "$H/fa_v11_cpu" CPU "$mode" 24 > "$O/$name.txt" 2>&1 || echo "rc=$? $name" >> "$O/$name.txt"
    grep -h "^lib \|^summary" "$O/$name.txt" | sed "s/^/[$name] /"
}
export FA_NAN_NKV=2048,300
run nan_base   "$BASE" nan
run nan_fix    "$FIX"  nan
run nan_legacy "$FIX"  nan GGML_FA_VKQ_F16=1
run det_base   "$BASE" exact
run det_fix    "$FIX"  exact
run det_legacy "$FIX"  exact GGML_FA_VKQ_F16=1
unset FA_NAN_NKV
# indicative op-level decode/verify cost, f16 KV, ABAB
for rep in 1 2; do
    for arm in base fix; do
        lib=$BASE; [ $arm = fix ] && lib=$FIX
        FA_PERF_ROWS=1,4,9 FA_PERF_NKV=16384,131072 FA_PERF_KV=f16 FA_PERF_REPS=30 FA_PERF_MIN_REPS=5 FA_PERF_BUDGET_MS=600 \
            run perf_${arm}_$rep "$lib" perf
        grep -h "^perf" "$O/perf_${arm}_$rep.txt" | sed "s/^/[perf_${arm}_$rep] /"
    done
done
echo done
