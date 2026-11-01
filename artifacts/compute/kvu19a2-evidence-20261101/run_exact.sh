#!/bin/bash
# run_exact.sh <libdir> <tag> <skip 0|1> [backend] [threads]
set -euo pipefail
cd /mnt/raid0/llm/tmp/fa-maskskip-20261003/harness
LIB=$1; TAG=$2; SKIP=$3; BE=${4:-ROCm0}; TH=${5:-24}
rm -rf "out_${TAG}"; mkdir -p "out_${TAG}"
GGML_CUDA_FA_MASK_SKIP=$SKIP LD_LIBRARY_PATH=$LIB FA_DUMP_DIR="out_${TAG}" \
    timeout 1800 nice -n 19 ionice -c3 taskset -c 160-183 ./fa_harness "$BE" exact "$TH" > "exact_${TAG}.txt" 2>/dev/null
echo "$TAG rc=$? $(tail -n 1 "exact_${TAG}.txt")"
