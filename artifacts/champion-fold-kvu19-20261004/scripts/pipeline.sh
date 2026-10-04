#!/bin/bash
# Fold-candidate CPU-side pipeline: GPU store build, CPU store build, CPU checks.
# Every heavy step holds region-lock (cpu 0-95, role build, tag champion-fold). No GPU use, no servers.
set -euo pipefail
F=/mnt/raid0/llm/tmp/champion-fold-kvu19-20261004
RL=/workspace/repos/epyc-orchestrator/scripts/region-lock
LOCK=("$RL" run --cpu-list 0-95 --role build --tag champion-fold --)
SHA=$(git -C "$F/src" rev-parse --short=9 HEAD)
GB=/mnt/raid0/llm/kernels/builds/gpu-20261004-$SHA
CB=/mnt/raid0/llm/kernels/builds/cpu-20261004-$SHA
LV=/workspace/repos/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh
log() { echo "[$(date -u +%FT%TZ)] $*"; }

log "candidate $SHA"
[ -e "$GB" ] || { log "gpu build: waiting for region lock"; "${LOCK[@]}" "$F/build_store.sh" gpu; }
[ -e "$CB" ] || { log "cpu build: waiting for region lock"; "${LOCK[@]}" "$F/build_store.sh" cpu; }

log "linkage"
"$LV" "$GB/bin/llama-server" "$GB/bin" > "$F/linkage_gpu.txt" 2>&1 && log "gpu linkage PASS" || log "gpu linkage FAIL"
"$LV" "$CB/bin/llama-server" "$CB/bin" > "$F/linkage_cpu.txt" 2>&1 && log "cpu linkage PASS" || log "cpu linkage FAIL"

log "strings"
{
  for k in GGML_CUDA_FA_MASK_SKIP GGML_CUDA_FA_MASK_SKIP_MIN_KV GGML_CUDA_FA_SEQ_ROWS; do
    printf '%-32s %s\n' "$k" "$(strings "$GB/bin/libggml-hip.so" | grep -cx "$k")"
  done
  printf '%-32s %s\n' "plan_seq_tiles(any)" "$(strings "$GB/bin/libggml-hip.so" | grep -c plan_seq_tiles || true)"
  printf '%-32s %s\n' "plan_seq_tiles(nm -D)" "$(nm -D --defined-only "$GB/bin/libggml-hip.so" | grep -c plan_seq_tiles || true)"
  printf '%-32s %s\n' "plan_seq_tiles(nm)" "$(nm "$GB/bin/libggml-hip.so" 2>/dev/null | grep -c plan_seq_tiles || true)"
  printf '%-32s %s\n' "ggml_flash_attn_ext_set_n_seq" "$(nm -D --defined-only "$GB/bin/libggml-base.so" | grep -c ggml_flash_attn_ext_set_n_seq || true)"
  "$GB/bin/llama-server" --version 2>&1 | head -2
  "$CB/bin/llama-server" --version 2>&1 | head -2
} > "$F/strings_gpu.txt" 2>&1
cat "$F/strings_gpu.txt"

log "cpu checks: waiting for region lock"
"${LOCK[@]}" "$F/cpu_checks.sh" "$CB"
log "pipeline done"
