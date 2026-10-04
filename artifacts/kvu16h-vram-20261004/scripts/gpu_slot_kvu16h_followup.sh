#!/bin/bash
# gpu_slot_kvu16h_followup.sh — ONE MI210 slot (<= 25 GPU-min) for the KVU-16h FOLLOW-UP: does the v10 HIP-graph
# mmvq q8_1 cache pin legacy-pool buffers so that every "speculative.n_max 0 decode -> fresh prefill" transition
# adds ~0.29 GiB (Q38-T7 #1: 25 transitions, +7.19 GiB; #2: 3, +0.894)? Run ONLY in a coordinated window with
# production :8083 STOPPED by the window owner (two 27B do not fit in 64 GiB) and the GPU free.
#
#   ARM A  :8083's production argv on scratch :18083 (+ -lv 4, own --slot-save-path), hipMalloc shim:
#          warm (2 drafted chat requests) -> ctrl (T7 #1 phase A, dflash2 arm only: 24 requests)
#          -> t7a (T7 #1 phase A byte-faithful: 48 alternating dflash2 / n_max 0 requests)
#          -> t7b2 (optional, T7 #2 sequence; only if the budget allows after arm B's reserve)
#   ARM B  same argv + GGML_CUDA_DISABLE_GRAPHS=1: warm -> t7a           (graphs off => no capture => no pins)
#   Hard ceiling 62.5 GiB (own KFD or card) -> stop, graceful teardown, exit 3; soft 60.5 GiB -> stop that arm.
#   Output: results/fu-<UTC>/summary.md (CONFIRMED | PARTIAL | NOT REPRODUCED + the KVU-16i term).
#
# Usage: gpu_slot_kvu16h_followup.sh --dry-run|--mock|--execute [--port 18083] [--budget-min 25] [--no-arm-b]
#                                    [--no-shim]
# --dry-run : GPU read-only: linkage (ldd), knob strings, shim build + CPU self-test, runner plan + preflight.
# --mock    : CPU-only RUN-path self-test against dryrun/mock_server_chat.py (a simulator of the hypothesis),
#             under the CPU region lock (cpus 72-95). Writes dryrun/fu_mock/.
# --execute : refuses unless every preflight check passes; runs under ONE mi210_0 device claim (kvu16h_claim.py).
# --execute also holds the CPU region for cpus 184-191 (the server's taskset) via region-lock (60 s acquire timeout).
# Process discipline: signals only its own child; the runner owns its server by PID (TERM -> KILL, ps -p verified).
set -euo pipefail

DIR=/mnt/raid0/llm/tmp/kvu16h-vram-20261004
BIN=/mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin
LINK=/workspace/repos/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh
PROD_LDP=/mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin:/opt/rocm/lib:/usr/lib/llvm-20/lib:/opt/AMD/aocc-compiler-5.0.0/lib:/opt/rocm/lib
PY=(python3 -B)
RLOCK=/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock
MODE=""; PORT=18083; BUDGET=25; SHIM=1; ARMB=1
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) MODE=dry ;;
    --mock) MODE=mock ;;
    --execute) MODE=exec ;;
    --port) PORT=$2; shift ;;
    --budget-min) BUDGET=$2; shift ;;
    --no-shim) SHIM=0 ;;
    --no-arm-b) ARMB=0 ;;
    -h|--help) sed -n '2,24p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 64 ;;
  esac
  shift
done
[ -n "$MODE" ] || { echo "need --dry-run, --mock or --execute" >&2; exit 64; }
[ "$PORT" != 8083 ] || { echo "REFUSING: scratch port only (8083 is production)" >&2; exit 64; }
RUNARGS=(--port "$PORT" --budget-min "$BUDGET")
[ "$SHIM" = 1 ] || RUNARGS+=(--no-shim)
[ "$ARMB" = 1 ] || RUNARGS+=(--no-arm-b)

ts() { date -u +%H:%M:%SZ; }
say() { echo "[kvu16h-fu-slot $(ts)] $*"; }
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

preflight() {  # $1 = output dir; GPU read-only
  local out=$1 bad=0 hip="$BIN/libggml-hip.so" knobs
  mkdir -p "$out"
  say "PREFLIGHT (v10 store binary $BIN, scratch port $PORT)"
  knobs=$(strings "$hip" 2>/dev/null | grep -E '^GGML_CUDA_DISABLE_GRAPHS$' | sort -u || true)
  [ -n "$knobs" ] && echo "  GGML_CUDA_DISABLE_GRAPHS compiled in (arm B valid)" || { echo "  STOP: GGML_CUDA_DISABLE_GRAPHS not in $hip"; bad=1; }
  echo "  build flags: $(grep -E '^(GGML_HIP_NO_VMM|GGML_HIP_GRAPHS):' "$BIN/../CMakeCache.txt" | tr '\n' ' ')"
  if env -u LD_LIBRARY_PATH LD_LIBRARY_PATH="$PROD_LDP" bash "$LINK" "$BIN/llama-server" "$BIN" > "$out/linkage.llama-server.txt" 2>&1 \
     && grep -q '^PASS' "$out/linkage.llama-server.txt"; then
    echo "  linkage PASS (ldd only; residency is proven at runtime from /proc/<pid>/maps)"
  else
    echo "  LINKAGE FAIL (see $out/linkage.llama-server.txt)"; bad=1
  fi
  if [ "$SHIM" = 1 ]; then
    if bash "$DIR/shim/build_shim.sh" > "$out/shim_selftest.txt" 2>&1; then echo "  shim built + CPU self-test OK"
    else echo "  SHIM SELF-TEST FAILED (see $out/shim_selftest.txt; or --no-shim)"; bad=1; fi
  fi
  "${PY[@]}" "$DIR/kvu16h_followup.py" --dry-run --results "$out" "${RUNARGS[@]}" | sed 's/^/  /' | tee "$out/runner_dryrun.txt"
  if grep -q 'would PASS' "$out/runner_dryrun.txt"; then echo "  runner preflight: PASS"
  elif grep -E '^\s+- ' "$out/runner_dryrun.txt" | grep -v 'not running under kvu16h_claim.py' | grep -q .; then
    echo "  runner preflight: REFUSE"; bad=1
  else echo "  runner preflight: PASS (claim taken at --execute)"; fi
  echo "  host load $(cut -d' ' -f1-3 /proc/loadavg)"
  return $bad
}

case "$MODE" in
  dry)
    say "DRY RUN (nothing started on the GPU, nothing sent)"
    pf=0; preflight "$DIR/dryrun/fu_preflight" || pf=$?
    echo "  [execute] $0 --execute ${RUNARGS[*]}"
    say "DRY RUN complete (preflight rc $pf; a REFUSE is expected while :8083 serves or another session holds the GPU)"
    exit 0 ;;
  mock)
    R="$DIR/dryrun/fu_mock"; rm -rf "$R"; mkdir -p "$R"
    say "MOCK self-test (CPU only, region lock cpus 72-95) -> $R"
    rc=0
    run_own "$RLOCK" run --cpu-list 72-95 --role build --tag kvu16h-fu -- taskset -c 72-95 \
        "${PY[@]}" "$DIR/kvu16h_followup.py" --mock --no-claim --results "$R" --budget-min 30 --port 18093 \
        > >(tee "$R/mock.out") 2>&1 || rc=$?
    say "MOCK done rc=$rc; summary $R/summary.md"
    exit $rc ;;
  exec)
    R="$DIR/results/fu-$(date -u +%Y%m%dT%H%M%SZ)"; mkdir -p "$R"; LOG="$R/slot.log"
    { preflight "$R"; } > >(tee -a "$LOG") 2>&1 || { say "PREFLIGHT FAILED - not starting anything (see $LOG)" | tee -a "$LOG"; exit 2; }
    say "results $R; budget $BUDGET min; arm B $ARMB; shim $SHIM" | tee -a "$LOG"
    rc=0
    # the scratch server pins cpus 184-191 (production taskset): hold that CPU region too (OPERATING_CONSTRAINTS
    # -> Inference and Benchmarks); refuse after 60 s instead of blocking if someone else holds it.
    run_own "$RLOCK" run --cpu-list 184-191 --role bench --tag kvu16h-fu-gpu --timeout-s 60 -- \
        "${PY[@]}" "$DIR/kvu16h_claim.py" --results-dir "$R" --max-hold-s "$(( ${BUDGET%.*} * 60 + 900 ))" \
        --purpose "KVU-16h follow-up: mmvq graph-cache pool pinning (T7 #1 phase A replay, graphs on/off) on scratch :$PORT" -- \
        "${PY[@]}" "$DIR/kvu16h_followup.py" --results "$R" "${RUNARGS[@]}" > >(tee -a "$LOG") 2>&1 || rc=$?
    [ $rc -eq 75 ] && { say "mi210_0 device claim held by someone else - nothing started" | tee -a "$LOG"; exit 75; }
    say "DONE rc=$rc (0 ok, 2 refused, 3 hard-ceiling abort, 4 error)  summary: $R/summary.md" | tee -a "$LOG"
    exit $rc ;;
esac
