#!/bin/bash
# gpu_slot_dca.sh: GPU (MI210, HIP gfx90a) validation of Dual Chunk Attention v1, branch experimental/dca-20261004.
# NOT production, NOT the champion. Small loads only: synthetic test models + Qwen2.5-0.5B f16 (peak ~6 GiB VRAM).
# No llama-server, no 27B. About 20-30 min of GPU.
#
#   ./gpu_slot_dca.sh prep   CPU only, run any time (region-locked): HIP build of the branch -> $T/build-hip
#   ./gpu_slot_dca.sh slot   ONLY when the main session (workspace-ec) says the GPU is free
#
# Slot checks:
#  1. test-dca on ROCm0: numeric DCA vs float64 reference (qwen2), equivalence chunk>ctx == plain (qwen2/qwen35/qwen35moe),
#     small-chunk smoke. Same criteria as the CPU ctest; DCA v1 uses generic ops only (rope, mul_mat, mul, add, soft_max).
#  2. Qwen2.5-0.5B perplexity at 64K on ROCm0, arms plain64k / dca / dca_t, compared with the CPU numbers from
#     real_model_ppl_cpu.sh (same build commit): |PPL_gpu - PPL_cpu| / PPL_cpu < 1e-3 expected.
# Results: $T/gpu-slot-<ts>/summary.txt
# Expected duration: ~10-15 min of GPU (test-dca ROCm0 ~1-2 min, CPU repeat ~2 min, 3 x 64K ppl ~2-3 min each).
# Refuses (exit 3, kills nothing) if :8083 is listening or any KFD/GPU process exists (gpu_guard.sh).
set -euo pipefail
T=/mnt/raid0/llm/tmp/dca-yarn-kernel-20261004
SRC=/mnt/raid0/llm/llama.cpp-experimental-dca-20261004
BH=$T/build-hip
M=/mnt/raid0/llm/models/Qwen2.5-0.5B-Instruct-f16.gguf
F=/mnt/raid0/llm/data/wiki.test.raw
RUN=/mnt/raid0/llm/tmp/dca-yarn-kernel-20261004/bench.sh  # region-lock --role bench, q2

case "${1:-}" in
prep)
    [ -z "$(git -C "$SRC" status --porcelain --untracked-files=no)" ] || { echo "FAIL: $SRC has uncommitted changes"; exit 1; }
    git -C "$SRC" rev-parse HEAD > "$T/build-hip.commit"
    "$T/rl.sh" cmake -S "$SRC" -B "$BH" -DCMAKE_BUILD_TYPE=Release -DGGML_HIP=ON -DAMDGPU_TARGETS=gfx90a \
        -DGGML_HIP_ROCWMMA_FATTN=ON -DGGML_NATIVE=ON -DLLAMA_BUILD_TESTS=ON -DLLAMA_CURL=OFF -DLLAMA_OPENSSL=OFF \
        -DCMAKE_BUILD_RPATH_USE_ORIGIN=ON -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON '-DCMAKE_INSTALL_RPATH=$ORIGIN;/opt/rocm/lib' \
        > "$T/build-hip.configure.log" 2>&1
    "$T/rl.sh" cmake --build "$BH" -j 24 --target test-dca llama-perplexity > "$T/build-hip.build.log" 2>&1
    echo "OK prep: $BH ($(cat "$T/build-hip.commit"))"
    ;;
slot)
    . /mnt/raid0/llm/tmp/dca-yarn-kernel-20261004/gpu_guard.sh; gpu_guard   # refuses if :8083 or any GPU process is up
    [ -x "$BH/bin/test-dca" ] && [ -x "$BH/bin/llama-perplexity" ] || { echo "FAIL: run '$0 prep' first"; exit 1; }
    OUT=$T/gpu-slot-$(date -u +%Y%m%dT%H%M%SZ); mkdir -p "$OUT"
    log() { echo "[$(date -u +%FT%TZ)] $*" | tee -a "$OUT/slot.log"; }
    vram() { rocm-smi --showmeminfo vram 2>/dev/null | grep 'Used' | awk '{print $NF}' | head -n 1; }
    log "commit $(cat "$T/build-hip.commit")  VRAM before: $(vram)"
    /workspace/repos/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$BH/bin/llama-perplexity" > "$OUT/linkage.txt" 2>&1 \
        && log "linkage PASS" || { log "linkage FAIL (see linkage.txt)"; exit 1; }

    log "1 test-dca on ROCm0"
    ( while sleep 2; do echo "$(date -u +%T) $(vram)"; done ) > "$OUT/vram_samples.txt" 2>&1 & VP=$!
    DCA_TEST_DEVICE=ROCm0 env -u LD_LIBRARY_PATH $RUN "$BH/bin/test-dca" > "$OUT/test-dca-rocm.log" 2>&1 \
        && log "test-dca ROCm0 PASS" || log "test-dca ROCm0 FAIL rc=$?"
    env -u LD_LIBRARY_PATH $RUN "$BH/bin/test-dca" > "$OUT/test-dca-cpu-same-build.log" 2>&1 \
        && log "test-dca CPU (HIP build) PASS" || log "test-dca CPU (HIP build) FAIL rc=$?"

    log "2 Qwen2.5-0.5B ppl 64K on ROCm0"
    COMMON=(-m "$M" -f "$F" -t 24 -fa off -ub 256 -b 2048 --chunks 1 -ngl 99 -dev ROCm0)
    for arm in plain64k dca dca_t; do
        case $arm in
            plain64k) X=(-c 65536) ;;
            dca)      X=(-c 65536 --dca-chunk-size 32768 --dca-local-size 4096) ;;
            dca_t)    X=(-c 65536 --dca-chunk-size 32768 --dca-local-size 4096 --dca-orig-ctx 32768) ;;
        esac
        env -u LD_LIBRARY_PATH $RUN "$BH/bin/llama-perplexity" "${COMMON[@]}" "${X[@]}" > "$OUT/ppl_$arm.log" 2>&1 || log "ppl $arm rc=$?"
        grep -E "Final estimate" "$OUT/ppl_$arm.log" | sed "s/^/$arm gpu: /" | tee -a "$OUT/summary.txt" || true
    done
    kill $VP 2>/dev/null || true
    {
        echo; echo "== test-dca ROCm0"; grep -E "OK|FAIL" "$OUT/test-dca-rocm.log"
        echo; echo "== CPU reference PPL (real_model_ppl_cpu.sh, latest run)"; cat "$(ls -d $T/ppl-*/ | tail -n 1)summary.txt" 2>/dev/null || echo "none yet"
        echo; echo "== VRAM peak (MiB used, sampled every 2 s)"; awk '{print $2}' "$OUT/vram_samples.txt" | sort -n | tail -n 1
    } >> "$OUT/summary.txt"
    log "done: $OUT/summary.txt"
    ;;
*) echo "usage: $0 prep|slot"; exit 2 ;;
esac
