#!/bin/bash
# CPU-side exactness of the fold candidate's CPU store build. Run ONLY under
#   region-lock run --cpu-list 0-95 --role build --tag champion-fold -- cpu_checks.sh <cpu_build_dir>
# Writes into /mnt/raid0/llm/tmp/champion-fold-kvu19-20261004/cpu/ only (the lane harness dirs are read, never written).
set -euo pipefail
B=${1:?usage: cpu_checks.sh <cpu_build_dir>}
D=/mnt/raid0/llm/tmp/champion-fold-kvu19-20261004/cpu
H1=/mnt/raid0/llm/tmp/fa-maskskip-20261003/harness/fa_harness
H2=/mnt/raid0/llm/tmp/fa-maskskip-batched-20261004/harness/fa_harness2
RUN="nice -n 19 ionice -c3 taskset -c 0-95"
mkdir -p "$D"; cd "$D"; set +e

# harness v1 (KVU-19a, 86 cases) and v2 (KVU-19a + 19b multi-sequence, 141 cases), CPU backend, 24 threads
rm -rf out_v1 out_v2; mkdir -p out_v1 out_v2
LD_LIBRARY_PATH="$B/bin" FA_DUMP_DIR=out_v1 timeout 1800 $RUN "$H1" CPU exact 24 > exact_v1.txt 2> exact_v1.err
echo "v1 rc=$? $(tail -n 1 exact_v1.txt)"
LD_LIBRARY_PATH="$B/bin" FA_DUMP_DIR=out_v2 timeout 2400 $RUN "$H2" CPU exact 24 > exact_v2.txt 2> exact_v2.err
echo "v2 rc=$? $(tail -n 1 exact_v2.txt)"

# test-backend-ops FLASH_ATTN_EXT on CPU (upstream skips the CPU backend in eval mode -> record what it says)
set +e
timeout 1200 $RUN "$B/bin/test-backend-ops" -o FLASH_ATTN_EXT -b CPU > tbo_cpu.log 2>&1
echo "tbo_cpu rc=$? $(grep -E 'tests passed|Skipping|OK|FAIL' tbo_cpu.log | tail -n 3 | tr '\n' ' ')"
