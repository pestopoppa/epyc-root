#!/bin/bash
# gpu_slot_kvu16h.sh — ONE MI210 slot (<= 60 GPU-min) for KVU-16h: attribute :8083's +7.2 GiB VRAM growth while
# serving (51.69 -> 58.88 -> 59.77 GiB; gate 62) to a NAMED allocator. Run ONLY in workspace-ec's coordinated
# window, with production :8083 STOPPED by the window owner (two 27B servers do not fit in 64 GiB) and the GPU free.
#
# What runs (kvu16h_run.py, under ONE mi210_0 device claim, kvu16h_claim.py):
#   ARM A  :8083's PRODUCTION argv (live :8083 cmdline, else logs/server_launches/8083.json; v10 store binary
#          builds/gpu-20260921-ffc1bac82, DFlash2, np 4, -c 393216), changed ONLY in --port 18083,
#          --slot-save-path <own dir>, -lv 4; production env + numactl --membind=3 -- taskset -c 184-191;
#          LD_PRELOAD=shim/libhipmalloc_trace.so (logs every public hipMalloc/hipFree with its call chain).
#          Phases, each followed by 60 s idle: load, short, sweep, prefill80k, dec4, mix1 (2 prefills + 2 decodes,
#          the Q38-T7 shape), mix2 (repeat), t7c, nodraft, idlecache, longidle; graceful SIGTERM (exit breakdown).
#   ARM B  (auto) one relaunch with ONE change chosen from arm A's attribution: -b 512 -ub 512 (pool/compute/rocBLAS)
#          or GGML_CUDA_DISABLE_GRAPHS=1 (HIP-runtime residual); replays mix1, mix2 -> bounded or not.
#   KFD per-process VRAM + card sysfs at 1 Hz (sampler started BEFORE each launch) + rocm-smi --showmeminfo vram.
#   Hard ceiling 62.5 GiB (own KFD or card used) -> stop traffic, graceful teardown, exit 3. Total <= 60 min.
#   analyze.py -> results/<ts>/summary.md (per-phase table, allocator attribution, candidates, KVU-16i term).
#
# Usage: gpu_slot_kvu16h.sh --dry-run|--execute [--port 18083] [--budget-min 60] [--arm-b auto|ub512|ub128|nographs|off]
#                           [--no-shim] [--lv 4] [--vram-free-max-gib 2]
# --dry-run : read-only for the GPU: path/knob (strings) evidence, ggml linkage (ldd only), production argv +
#             drift check, shim build + CPU self-test, VRAM/KFD/port/claim state, the runner's full plan.
# --execute : refuses unless every preflight check passes. Results -> results/<UTC ts>/.
# Process discipline: this wrapper signals only its own child (the claim wrapper); the runner owns its server by
# PID (TERM -> KILL, ps -p verified). Nothing is signalled by name. No CPU region lock (the CPU side is an HTTP
# client + 1 Hz samplers; prompt fitting uses the scratch server's /tokenize).
set -euo pipefail

DIR=/mnt/raid0/llm/tmp/kvu16h-vram-20261004
STORE=/mnt/raid0/llm/kernels/production/gpu
BIN=/mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin
LINK=/workspace/repos/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh
CLAIM_MOD=/workspace/repos/epyc-inference-research/scripts/kernel_rnd/autokernel/resource/device_claim.py
PROD_LDP=/mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin:/opt/rocm/lib:/usr/lib/llvm-20/lib:/opt/AMD/aocc-compiler-5.0.0/lib:/opt/rocm/lib
PY=(python3 -B)
MODE=""; PORT=18083; BUDGET=60; ARMB=auto; SHIM=1; LV=4; VRAM_MAX=2
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) MODE=dry ;;
    --execute) MODE=exec ;;
    --port) PORT=$2; shift ;;
    --budget-min) BUDGET=$2; shift ;;
    --arm-b) ARMB=$2; shift ;;
    --no-shim) SHIM=0 ;;
    --lv) LV=$2; shift ;;
    --vram-free-max-gib) VRAM_MAX=$2; shift ;;
    -h|--help) sed -n '2,27p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 64 ;;
  esac
  shift
done
[ -n "$MODE" ] || { echo "need --dry-run or --execute" >&2; exit 64; }
[ "$PORT" != 8083 ] || { echo "REFUSING: scratch port only (8083 is production)" >&2; exit 64; }
RUNARGS=(--port "$PORT" --budget-min "$BUDGET" --arm-b "$ARMB" --lv "$LV" --vram-free-max-gib "$VRAM_MAX")
[ "$SHIM" = 1 ] || RUNARGS+=(--no-shim)

ts() { date -u +%H:%M:%SZ; }
say() { echo "[kvu16h-slot $(ts)] $*"; }
CHILD=""
cleanup_child() {
  if [ -n "$CHILD" ] && kill -0 "$CHILD" 2>/dev/null; then
    say "cleanup: SIGTERM own child $CHILD (it tears down its own server)"
    kill -TERM "$CHILD" 2>/dev/null || true
    local i
    for i in $(seq 1 300); do kill -0 "$CHILD" 2>/dev/null || break; sleep 1; done
    if kill -0 "$CHILD" 2>/dev/null; then say "cleanup: SIGKILL own child $CHILD"; kill -KILL "$CHILD" 2>/dev/null || true; sleep 2; fi
    if ps -p "$CHILD" >/dev/null 2>&1; then say "WARNING: own child $CHILD still alive"; else say "own child $CHILD verified dead"; fi
  fi
  CHILD=""
}
trap cleanup_child EXIT
trap 'cleanup_child; exit 143' TERM
trap 'cleanup_child; exit 130' INT
run_own() { "$@" & CHILD=$!; local rc=0; wait "$CHILD" || rc=$?; CHILD=""; return $rc; }

knob() {  # $1 file, $2 ERE; prints the sorted unique matches (no grep -q: SIGPIPE + pipefail turns a hit into a miss)
  strings "$1" 2>/dev/null | grep -E "$2" | sort -u | tr '\n' ' ' || true
}

preflight() {  # $1 = output dir. Read-only for the GPU; returns non-zero if any check fails.
  local out=$1 bad=0
  mkdir -p "$out"
  say "PREFLIGHT (store $STORE, scratch port $PORT)"
  if [ "$(readlink -f "$STORE")" = "$BIN" ]; then echo "  kernel store $STORE -> $BIN (v10)"; else echo "  STORE DRIFT: $STORE -> $(readlink -f "$STORE") (expected $BIN)"; bad=1; fi
  echo "  provenance: $(grep -m1 -o 'commit `[0-9a-f]*`[^,]*, build \*\*[0-9]*\*\*' "$BIN/../PROVENANCE.md" 2>/dev/null || echo '?') (binary NOT executed)"
  echo "  build flags (CMakeCache): $(grep -E '^(GGML_HIP_NO_VMM|GGML_CUDA_NO_VMM|GGML_HIP_GRAPHS|GGML_CUDA_FORCE_MMQ|GGML_SCHED_NO_REALLOC):' "$BIN/../CMakeCache.txt" | tr '\n' ' ')"
  local hip="$BIN/libggml-hip.so" base="$BIN/libggml-base.so" n_leg n_vmm
  n_leg=$(readelf -sW "$hip" | grep -c 'ggml_cuda_pool_leg' || true)
  n_vmm=$(readelf -sW "$hip" | grep -c 'ggml_cuda_pool_vmm' || true)
  echo "  libggml-hip symbols: ggml_cuda_pool_leg x$n_leg, ggml_cuda_pool_vmm x$n_vmm (0 => VMM pool compiled out => legacy pool)"
  echo "  knobs in libggml-hip: $(knob "$hip" '^GGML_CUDA_(DISABLE_GRAPHS|GRAPH_OPT|LOG_MMVQ_ROUTE|ENABLE_UNIFIED_MEMORY|NO_PINNED|DISABLE_FUSION)$')"
  echo "  pool log strings (DEBUG level, OOM-flush only): $(knob "$hip" 'pool\[%d\]|buffer pool full' | cut -c1-200)"
  echo "  knobs in libggml-base: $(knob "$base" '^GGML_SCHED_DEBUG')  (GGML_SCHED_DEBUG_REALLOC ABORTS on realloc: never set here)"
  echo "  rocBLAS knobs: $(knob /opt/rocm/lib/librocblas.so.4 '^ROCBLAS_(DEVICE_MEMORY_SIZE|STREAM_ORDER_ALLOC)$')"
  echo "  verbosity flag in libllama-common: $(knob "$BIN/libllama-common.so" '^(-lv|--verbosity|--log-verbosity)$')"
  [ "$n_leg" -gt 0 ] || { echo "  STOP: no ggml_cuda_pool_leg symbols (the build is not what this runner assumes)"; bad=1; }
  if [ "$(knob "$hip" '^GGML_CUDA_DISABLE_GRAPHS$')" = "" ] && [ "$ARMB" = nographs ]; then echo "  STOP: GGML_CUDA_DISABLE_GRAPHS not compiled in; --arm-b nographs impossible"; bad=1; fi
  if env -u LD_LIBRARY_PATH LD_LIBRARY_PATH="$PROD_LDP" bash "$LINK" "$BIN/llama-server" "$BIN" > "$out/linkage.llama-server.txt" 2>&1 \
     && grep -q '^PASS' "$out/linkage.llama-server.txt"; then
    echo "  linkage PASS (ldd only, production LD_LIBRARY_PATH) -> $out/linkage.llama-server.txt"
  else
    echo "  LINKAGE FAIL (see $out/linkage.llama-server.txt)"; bad=1
  fi
  if [ "$SHIM" = 1 ]; then
    if bash "$DIR/shim/build_shim.sh" > "$out/shim_selftest.txt" 2>&1; then
      echo "  shim built + CPU self-test OK: $(cat "$DIR/shim/selftest.ok")"
    else
      echo "  SHIM SELF-TEST FAILED (see $out/shim_selftest.txt; or run with --no-shim)"; bad=1
    fi
  fi
  local f
  for f in "$BIN/llama-server" "$LINK" "$CLAIM_MOD" /mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf \
           /mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf /mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja \
           /mnt/raid0/llm/epyc-orchestrator/logs/server_launches/8083.json \
           /mnt/raid0/llm/tmp/ds41-c95/contexts/{C1,C2,C3,C4,C5,C6,C7}/prompt.inline.txt \
           /mnt/raid0/llm/tmp/gpu-block-27b-20261003/lib_gpublock.py \
           /sys/class/kfd/kfd/proc /sys/class/drm/card2/device/mem_info_vram_used \
           "$DIR"/{lib_kvu16h.py,kvu16h_run.py,kvu16h_claim.py,analyze.py}; do
    [ -e "$f" ] || { echo "  MISSING $f"; bad=1; }
  done
  command -v rocm-smi >/dev/null || { echo "  MISSING rocm-smi"; bad=1; }
  command -v addr2line >/dev/null || echo "  (addr2line missing: analyze.py falls back to dynsym names only)"
  local free_gb; free_gb=$(df --output=avail -BG "$DIR" | tail -1 | tr -dc 0-9)
  [ "$free_gb" -ge 10 ] && echo "  disk free ${free_gb} GB (logs + shim trace < 2 GB)" || { echo "  only ${free_gb} GB free"; bad=1; }
  # runner preflight: argv source + drift, :8083 stopped, port free, no KFD holder, card VRAM free (claim checked by the wrapper)
  "${PY[@]}" "$DIR/kvu16h_run.py" --dry-run --results "$out" "${RUNARGS[@]}" | sed 's/^/  /' | tee "$out/runner_dryrun.txt" >/dev/null
  if grep -q 'would PASS' "$out/runner_dryrun.txt"; then echo "  runner preflight: PASS";
  else
    # the only acceptable REFUSE line in --dry-run is the claim one (the claim is taken in --execute)
    if grep -E '^\s+- ' "$out/runner_dryrun.txt" | grep -v 'not running under kvu16h_claim.py' | grep -q .; then
      echo "  runner preflight: REFUSE"; grep -E '^\s+- ' "$out/runner_dryrun.txt" | grep -v kvu16h_claim; bad=1
    else echo "  runner preflight: PASS (claim taken at --execute)"; fi
  fi
  "${PY[@]}" - <<EOF || true
import sys, json; sys.path.insert(0, "/workspace/repos/epyc-inference-research/scripts/kernel_rnd")
from autokernel.resource import device_claim as d
c = d.inspect_device_claim("mi210_0")
h = (c.get("claim") or {}).get("holder") or {}
print(f"  device claim mi210_0 (advisory read): state {c.get('state')}; holder {h.get('label') or h.get('pid') or '-'}")
try:
    w = json.load(open("/mnt/raid0/llm/tmp/gpu-window/mi210.json"))
    print(f"  GPU window file (info): holder {w.get('holder')}, parked {w.get('parked_ports')}, until {w.get('expected_end')}")
except Exception as e:
    print(f"  GPU window file unreadable: {e}")
EOF
  echo "  host load $(cut -d' ' -f1-3 /proc/loadavg); CPU region lock: none taken by this slot"
  return $bad
}

if [ "$MODE" = dry ]; then
  say "DRY RUN (nothing is started on the GPU, nothing is sent)"
  pf=0; preflight "$DIR/dryrun/preflight" || pf=$?
  sed -n '/^  \[argv source\]/,/^  \[budget\]/p' "$DIR/dryrun/preflight/runner_dryrun.txt"
  if [ $pf = 0 ]; then say "preflight would PASS now"; else say "preflight would REFUSE now (expected while another session holds the GPU or :8083 serves)"; fi
  echo "  [execute] ${PY[*]} $DIR/kvu16h_claim.py --results-dir $DIR/results/<UTC-ts> --purpose '...' --max-hold-s $(( ${BUDGET%.*} * 60 + 1200 )) -- \\"
  echo "            ${PY[*]} $DIR/kvu16h_run.py --results $DIR/results/<UTC-ts> ${RUNARGS[*]}"
  say "DRY RUN complete - nothing was started (preflight rc $pf)"
  exit 0
fi

R="$DIR/results/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$R"
LOG="$R/slot.log"
{ preflight "$R"; } > >(tee -a "$LOG") 2>&1 || { say "PREFLIGHT FAILED - not starting anything (see $LOG)" | tee -a "$LOG"; exit 2; }
say "results $R; budget $BUDGET min; arm B $ARMB; shim $SHIM" | tee -a "$LOG"
rc=0
run_own "${PY[@]}" "$DIR/kvu16h_claim.py" --results-dir "$R" --max-hold-s "$(( ${BUDGET%.*} * 60 + 1200 ))" \
    --purpose "KVU-16h: attribute :8083 VRAM growth (production argv on scratch :$PORT, -lv $LV, hipMalloc shim $SHIM)" -- \
    "${PY[@]}" "$DIR/kvu16h_run.py" --results "$R" "${RUNARGS[@]}" > >(tee -a "$LOG") 2>&1 || rc=$?
[ $rc -eq 75 ] && { say "mi210_0 device claim held by someone else - nothing started" | tee -a "$LOG"; exit 75; }
say "DONE rc=$rc (0 ok, 2 refused, 3 VRAM-ceiling abort, 4 error)  summary: $R/summary.md" | tee -a "$LOG"
exit $rc
