#!/bin/bash
# gpu_slot_fa_int64.sh: GPU (MI210 gfx90a, rocWMMA FA build) validation of FA-INT64-OFFSET,
# branch experimental/fa-int64-offset-20261004 (6152cdf7a WMMA fix, 4f21c3477 test, 0c4801127 tile/mma/vec + asserts).
# NOT production. Small loads: the largest allocation is the ~2.1 GiB wide mask of the new test case. ~20-30 min.
#
#   ./gpu_slot_fa_int64.sh prep   CPU only (region-locked, quadrant q2): HIP build of the branch -> $W/build-hip
#   ./gpu_slot_fa_int64.sh slot   ONLY when the main session (workspace-ec) says the GPU is free
#
# Slot checks (results: $T/gpu-slot-<ts>/summary.txt):
#  1. The new wide-mask-stride cases (-p mask_ne0) with the fixed libs: must pass (4/4).
#  2. The same test binary against the CHAMPION libs (gpu-20260929-90c12df42, LD_LIBRARY_PATH): the nb=2048 cases
#     are expected to FAIL or fault (int32-wrapped mask offset), the nb=64 F32 case to pass. This proves the test
#     catches the bug. (The champion's half path also used ne11 as the mask row stride, so nb=64/prec=default may
#     fail there for that reason; that row is informational.)
#  3. Full FLASH_ATTN_EXT suite on the fixed build vs CPU: no regression.
#  4. Bit-identity below the threshold: the KVU-19b fa_harness2 exact cases (27B shapes, <= 80k cells) dumped with
#     the champion libs and with the fixed libs must be byte-identical (cmp2.py).
# Expected duration: ~10-15 min of GPU (wide-mask cases 2 x ~1-2 min incl. 2.1 GiB host mask init, full
# FLASH_ATTN_EXT suite ~5 min, exact harness 2 arms ~1 min). Step 2 may end in a GPU memory-access fault on the
# champion libs (that is the bug); the process aborts, the script continues.
# Refuses (exit 3, kills nothing) if :8083 is listening or any KFD/GPU process exists (gpu_guard.sh).
set -euo pipefail
T=/mnt/raid0/llm/tmp/dca-yarn-kernel-20261004/fa-int64
W=/mnt/raid0/llm/llama.cpp-experimental-fa-int64-20261004
BH=$T/build-hip
BASE=/mnt/raid0/llm/kernels/builds/gpu-20260929-90c12df42/bin
H=/mnt/raid0/llm/tmp/fa-maskskip-batched-20261004/harness
RL=/mnt/raid0/llm/tmp/dca-yarn-kernel-20261004/rl.sh
RUN=/mnt/raid0/llm/tmp/dca-yarn-kernel-20261004/bench.sh  # region-lock --role bench, q2

case "${1:-}" in
prep)
    [ -z "$(git -C "$W" status --porcelain --untracked-files=no)" ] || { echo "FAIL: $W dirty"; exit 1; }
    git -C "$W" rev-parse HEAD > "$T/build-hip.commit"
    # recipe: gfx90a-house-v1 (as gpu-20260929-90c12df42) + tests
    "$RL" cmake -S "$W" -B "$BH" -DCMAKE_BUILD_TYPE=Release -DGGML_HIP=ON -DAMDGPU_TARGETS=gfx90a \
        -DGGML_HIP_ROCWMMA_FATTN=ON -DGGML_NATIVE=ON -DLLAMA_BUILD_TESTS=ON -DLLAMA_CURL=OFF -DLLAMA_OPENSSL=OFF \
        -DCMAKE_BUILD_RPATH_USE_ORIGIN=ON -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON '-DCMAKE_INSTALL_RPATH=$ORIGIN;/opt/rocm/lib' \
        > "$T/build-hip.configure.log" 2>&1
    "$RL" cmake --build "$BH" -j 24 --target test-backend-ops > "$T/build-hip.build.log" 2>&1
    strings "$BH/bin/libggml-hip.so" | grep -c "FA-INT64" >/dev/null 2>&1 || true
    echo "OK prep: $BH ($(cat "$T/build-hip.commit"))"
    ;;
slot)
    . /mnt/raid0/llm/tmp/dca-yarn-kernel-20261004/gpu_guard.sh; gpu_guard   # refuses if :8083 or any GPU process is up
    [ -x "$BH/bin/test-backend-ops" ] || { echo "FAIL: run '$0 prep' first"; exit 1; }
    OUT=$T/gpu-slot-$(date -u +%Y%m%dT%H%M%SZ); mkdir -p "$OUT"
    log() { echo "[$(date -u +%FT%TZ)] $*" | tee -a "$OUT/slot.log"; }
    vram() { rocm-smi --showmeminfo vram 2>/dev/null | grep 'Used' | awk '{print $NF}' | head -n 1; }
    log "commit $(cat "$T/build-hip.commit")  VRAM before: $(vram)"
    /workspace/repos/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$BH/bin/test-backend-ops" > "$OUT/linkage.txt" 2>&1 \
        && log "linkage PASS" || log "linkage check rc=$? (see linkage.txt)"
    TBO="$BH/bin/test-backend-ops test -o FLASH_ATTN_EXT -b ROCm0"

    log "1 wide-mask cases, fixed libs"
    env -u LD_LIBRARY_PATH OMP_NUM_THREADS=24 $RUN $TBO -p mask_ne0 > "$OUT/tbo_mask_ne0_fixed.log" 2>&1 || log "fixed rc=$?"
    log "2 wide-mask cases, champion libs (expect nb=2048 FAIL/fault)"
    LD_LIBRARY_PATH=$BASE OMP_NUM_THREADS=24 $RUN $TBO -p mask_ne0 > "$OUT/tbo_mask_ne0_champion.log" 2>&1 || log "champion rc=$? (expected non-zero)"
    log "3 full FLASH_ATTN_EXT suite, fixed libs"
    env -u LD_LIBRARY_PATH OMP_NUM_THREADS=24 $RUN $TBO > "$OUT/tbo_fa_full_fixed.log" 2>&1 || log "full suite rc=$?"

    log "4 bit-identity below the threshold (fa_harness2 exact, champion vs fixed libs)"
    cd "$H"
    for arm in int64base:$BASE int64fix:$BH/bin; do
        tag=${arm%%:*}; lib=${arm#*:}
        rm -rf "out_$tag"; mkdir -p "out_$tag"
        GGML_CUDA_FA_MASK_SKIP=1 GGML_CUDA_FA_SEQ_ROWS=1 LD_LIBRARY_PATH=$lib FA_DUMP_DIR="out_$tag" \
            timeout 2400 $RUN ./fa_harness2 ROCm0 exact 24 > "$OUT/exact_$tag.txt" 2>/dev/null || log "harness $tag rc=$?"
    done
    python3 cmp2.py out_int64fix out_int64base "$OUT/exact_int64fix.txt" > "$OUT/exact_cmp.txt" 2>&1 || log "cmp rc=$?"
    {
        echo "== 1 fixed (-p mask_ne0)";    grep -E "FLASH_ATTN_EXT.*mask_ne0|tests passed" "$OUT/tbo_mask_ne0_fixed.log"
        echo "== 2 champion (-p mask_ne0)"; grep -E "FLASH_ATTN_EXT.*mask_ne0|tests passed|fault|error|Abort" "$OUT/tbo_mask_ne0_champion.log" | head -20
        echo "== 3 full suite (fixed)";     grep -E "tests passed|FAIL" "$OUT/tbo_fa_full_fixed.log" | tail -5
        echo "== 4 bit-identity";           cat "$OUT/exact_cmp.txt" | tail -15
    } > "$OUT/summary.txt"
    log "done: $OUT/summary.txt"
    ;;
*) echo "usage: $0 prep|slot"; exit 2 ;;
esac
