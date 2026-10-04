#!/bin/bash
# gpu_slot_ak.sh — ONE MI210 slot (~90 GPU-min) for the combined KVU-19a+19b build gpu-20261004-c7f5ac9ad
# (branch experimental/fa-maskskip-batched-20261004, build 10312). Run ONLY after workspace-ec hands over the GPU.
#
# Arms, in VALUE order (each starts only if its estimate fits the remaining budget; see slot_run.py):
#   1 kvu_on_b2048   KVU-16b 4x80k staggered replay, skip ON (build defaults), -b 2048 -ub 2048  cap 20 min  est ~18
#   2 kvu_off_b2048  same, GGML_CUDA_FA_MASK_SKIP=0 GGML_CUDA_FA_SEQ_ROWS=0                      cap 20 min  est ~24
#   3 kvu_on_b512    same as 1 at -b 512 -ub 512                                                 cap 20 min  est ~20
#   4 p3 pairs       P3v2 A1 skip ON then OFF (AB), a 2nd pair (ABAB) only if it fits             est ~31.5/pair
# Every arm: :8083's production argv on a SCRATCH port (default 18183), only -b/-ub and env changed, plus
# --device ROCm0 --device-draft ROCm0 -lv 4; numactl --membind=3 taskset -c 184-191 (SMT siblings); KFD VRAM at
# 1 Hz; one greedy coherence spot-check per launch. ONE mi210_0 device claim is held across the whole slot
# (slot_claim.py, single non-blocking attempt). NO CPU region lock is taken (a CPU AutoKernel run may be live).
#
# Usage: gpu_slot_ak.sh --dry-run|--execute [--port 18183] [--budget-min 90] [--bin-dir DIR]
#                       [--order kvu_on_b2048,kvu_off_b2048,kvu_on_b512,p3] [--kvu-cap-min 20]
#                       [--p3-pairs 2] [--p3-phase a1|all] [--vram-free-max-gib 2]
# --dry-run : read-only. Checks every path, the knobs (strings), ggml linkage, the production argv, VRAM/KFD,
#             ports, disk, claim state; prints every argv. Starts nothing, sends nothing.
# --execute : refuses unless every preflight check passes; results -> results/<UTC ts>/ (report.md at the end).
# Process discipline: this wrapper only ever signals its own child (the claim wrapper); the sequencer and the
# arm drivers own their children by PID (TERM -> KILL, ps -p verified). Nothing is signalled by name.
set -euo pipefail

SLOT=/mnt/raid0/llm/tmp/gpu-slot-ak-20261004
BIN=/mnt/raid0/llm/kernels/builds/gpu-20261004-c7f5ac9ad/bin
LINK=/workspace/repos/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh
CLAIM_MOD=/workspace/repos/epyc-inference-research/scripts/kernel_rnd/autokernel/resource/device_claim.py
PY=(python3 -B)
MODE=""; PORT=18183; BUDGET=90; ORDER=kvu_on_b2048,kvu_off_b2048,kvu_on_b512,p3; CAP=20; PAIRS=2; P3PHASE=a1; VRAM_MAX=2
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) MODE=dry ;;
    --execute) MODE=exec ;;
    --port) PORT=$2; shift ;;
    --budget-min) BUDGET=$2; shift ;;
    --bin-dir) BIN=${2%/}; shift ;;
    --order) ORDER=$2; shift ;;
    --kvu-cap-min) CAP=$2; shift ;;
    --p3-pairs) PAIRS=$2; shift ;;
    --p3-phase) P3PHASE=$2; shift ;;
    --vram-free-max-gib) VRAM_MAX=$2; shift ;;
    -h|--help) sed -n '2,24p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 64 ;;
  esac
  shift
done
[ -n "$MODE" ] || { echo "need --dry-run or --execute" >&2; exit 64; }
[ "$PORT" != 8083 ] || { echo "REFUSING: scratch port only (8083 is production)" >&2; exit 64; }
export GPU_SLOT_BIN="$BIN"   # slot_common.BIN default for every child
LDP="$BIN:/opt/rocm/lib"

ts() { date -u +%H:%M:%SZ; }
say() { echo "[gpu-slot $(ts)] $*"; }
CHILD=""
cleanup_child() {
  if [ -n "$CHILD" ] && kill -0 "$CHILD" 2>/dev/null; then
    say "cleanup: SIGTERM own child $CHILD (it tears down its own arm/server chain)"
    kill -TERM "$CHILD" 2>/dev/null || true
    local i
    for i in $(seq 1 600); do kill -0 "$CHILD" 2>/dev/null || break; sleep 1; done
    if kill -0 "$CHILD" 2>/dev/null; then say "cleanup: SIGKILL own child $CHILD"; kill -KILL "$CHILD" 2>/dev/null || true; sleep 2; fi
    if ps -p "$CHILD" >/dev/null 2>&1; then say "WARNING: own child $CHILD still alive"; else say "own child $CHILD verified dead"; fi
  fi
  CHILD=""
}
trap cleanup_child EXIT
trap 'cleanup_child; exit 143' TERM
trap 'cleanup_child; exit 130' INT
run_own() { "$@" & CHILD=$!; local rc=0; wait "$CHILD" || rc=$?; CHILD=""; return $rc; }

preflight() {  # $1 = dir for linkage output. Every check runs read-only and reports; returns non-zero if any fails.
  local out=$1 bad=0
  say "PREFLIGHT (bin $BIN, scratch port $PORT)"
  if [ ! -d "$BIN" ]; then
    echo "  BUILD MISSING: $BIN does not exist (parametrize with --bin-dir DIR)"; bad=1
  else
    echo "  build: $(readlink -f "$BIN/libllama.so.0" 2>/dev/null | sed 's/.*\.//') (lib soname; binary NOT executed); provenance:" \
         "$(grep -m1 -o 'commit `[0-9a-f]*`, build \*\*[0-9]*\*\*, branch `[^`]*`' "$BIN/../PROVENANCE.md" 2>/dev/null || echo '?')"
    # knobs: no grep -q (an early-exiting grep SIGPIPEs strings and pipefail turns a hit into a miss)
    local k ks; ks=$(strings "$BIN/libggml-hip.so" 2>/dev/null | grep -E '^GGML_CUDA_FA_(MASK_SKIP|SEQ_ROWS)' | sort -u | tr '\n' ' ' || true)
    for k in GGML_CUDA_FA_MASK_SKIP GGML_CUDA_FA_SEQ_ROWS; do
      if [[ " $ks " == *" $k "* ]]; then echo "  knob $k compiled into libggml-hip.so"; else echo "  STOP: knob $k NOT in $BIN/libggml-hip.so (OFF arm impossible)"; bad=1; fi
    done
    echo "  knob strings present: $ks"
    mkdir -p "$out"
    if env -u LD_LIBRARY_PATH LD_LIBRARY_PATH="$LDP" bash "$LINK" "$BIN/llama-server" "$BIN" > "$out/linkage.llama-server.txt" 2>&1 \
       && grep -q '^PASS' "$out/linkage.llama-server.txt"; then
      echo "  linkage PASS llama-server (env -u LD_LIBRARY_PATH, LD_LIBRARY_PATH=$LDP) -> $out/linkage.llama-server.txt"
    else
      echo "  LINKAGE FAIL llama-server (see $out/linkage.llama-server.txt)"; bad=1
    fi
  fi
  local f
  for f in "$BIN/llama-server" "$BIN/libggml-hip.so" "$LINK" "$CLAIM_MOD" \
           /mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf /mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf \
           /mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja \
           /mnt/raid0/llm/epyc-orchestrator/logs/server_launches/8083.json /mnt/raid0/llm/tmp/ds41-c95/X0_ARGV_8083.txt \
           /mnt/raid0/llm/tmp/ds41-c95/contexts/{C1,C2,C3,C4,C5,C6,C7}/prompt.inline.txt \
           /mnt/raid0/llm/tmp/x0-27b-quants/results/p3/a1.json \
           /mnt/raid0/llm/tmp/gpu-block-27b-20261003/results/kvu16b/20261004T032520Z/report.json \
           /sys/class/kfd/kfd/proc /sys/class/drm/card2/device/mem_info_vram_used \
           "$SLOT"/{slot_common.py,lib_gpublock_slot.py,kvu16b_residency_slot.py,kvu16b_arm.py,p3_kvu_probe_slot.py,slot_run.py,slot_claim.py,slot_report.py}; do
    [ -e "$f" ] || { echo "  MISSING $f"; bad=1; }
  done
  [ $bad = 0 ] && echo "  all paths present (binary, models, template, argv sources, contexts, references, sysfs, scripts)"
  # production argv: source + shape invariants (refuse on drift; never guess)
  if ! "${PY[@]}" - <<EOF
import sys; sys.path.insert(0, "$SLOT"); import slot_common as C
s = C.source_argv(); p = C.validate_prod_argv(s["argv"])
print(f"  prod argv source: {s['source']}; sha256 {s['sha256'][:16]}; X0 cross-check: {s.get('cross_check_x0_argv_8083')}")
for x in p: print("  PROD ARGV DRIFT:", x)
sys.exit(1 if p else 0)
EOF
  then bad=1; fi
  # VRAM free + no KFD holder
  local v used total holders
  v=$("${PY[@]}" -c "
import sys; sys.path.insert(0,'$SLOT'); import slot_common as C
s=C.vram_now(); f=C.foreign_gpu_procs()
print(round(s.get('used_b',-1)/2**30,2), round(s.get('total_b',0)/2**30,1), ' '.join(f'{p}:{x[\"name\"]}:{round(x[\"vram_b\"]/2**30,1)}GiB' for p,x in f.items()) or '-')")
  read -r used total holders <<<"$v"
  if "${PY[@]}" -c "import sys; sys.exit(0 if 0 <= $used < $VRAM_MAX else 1)" && [ "$holders" = "-" ]; then
    echo "  VRAM free: ${used}/${total} GiB used (< ${VRAM_MAX}), no KFD process holds VRAM"
  else
    echo "  VRAM NOT FREE: ${used}/${total} GiB used (limit ${VRAM_MAX}); KFD holders: $holders"; bad=1
  fi
  if [ "$(ss -ltnH 'sport = :8083' | wc -l)" -gt 0 ]; then echo "  :8083 LISTENING (production architect not parked; VRAM would not fit)"; bad=1; else echo "  :8083 parked (not listening)"; fi
  if [ "$(ss -ltnH "sport = :$PORT" | wc -l)" -gt 0 ]; then echo "  scratch port $PORT IN USE"; bad=1; else echo "  scratch port $PORT free"; fi
  local free_gb; free_gb=$(df --output=avail -BG "$SLOT" | tail -1 | tr -dc 0-9)
  [ "$free_gb" -ge 15 ] && echo "  disk free ${free_gb} GB under $SLOT (P3 slot file ~3.5 GB, logs < 1 GB)" || { echo "  only ${free_gb} GB free"; bad=1; }
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
  echo "  host load $(cut -d' ' -f1-3 /proc/loadavg); CPU region locks: none taken by this slot"
  return $bad
}

if [ "$MODE" = dry ]; then
  say "DRY RUN (nothing is started, nothing is sent)"
  pf=0; preflight "$SLOT/dryrun" || pf=$?
  if [ $pf = 0 ]; then say "preflight would PASS now"; else say "preflight would REFUSE now (expected while workspace-ec holds the GPU)"; fi
  "${PY[@]}" "$SLOT/slot_run.py" --dry-run --results "$SLOT/results/<UTC-ts>" --port "$PORT" --budget-min "$BUDGET" \
      --order "$ORDER" --kvu-cap-min "$CAP" --p3-pairs "$PAIRS" --p3-phase "$P3PHASE" --bin-dir "$BIN"
  echo "  [execute] ${PY[*]} $SLOT/slot_claim.py --results-dir $SLOT/results/<UTC-ts> --purpose '...' --max-hold-s $(( ${BUDGET%.*} * 60 + 1800 )) -- \\"
  echo "            ${PY[*]} $SLOT/slot_run.py --results $SLOT/results/<UTC-ts> --port $PORT --budget-min $BUDGET --order $ORDER ..."
  say "DRY RUN complete - nothing was started (preflight rc $pf)"
  exit 0
fi

R="$SLOT/results/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$R"
LOG="$R/slot.log"
{ preflight "$R"; } > >(tee -a "$LOG") 2>&1 || { say "PREFLIGHT FAILED - not starting anything (see $LOG)" | tee -a "$LOG"; exit 2; }
say "results $R; budget $BUDGET min; order $ORDER" | tee -a "$LOG"
rc=0
run_own "${PY[@]}" "$SLOT/slot_claim.py" --results-dir "$R" --max-hold-s "$(( ${BUDGET%.*} * 60 + 1800 ))" \
    --purpose "gpu-slot-ak-20261004: KVU-16b replay (skip on/off, b512) + P3v2 on gpu-20261004-c7f5ac9ad, scratch :$PORT" -- \
    "${PY[@]}" "$SLOT/slot_run.py" --results "$R" --port "$PORT" --budget-min "$BUDGET" --order "$ORDER" \
    --kvu-cap-min "$CAP" --p3-pairs "$PAIRS" --p3-phase "$P3PHASE" --bin-dir "$BIN" > >(tee -a "$LOG") 2>&1 || rc=$?
[ $rc -eq 75 ] && { say "mi210_0 device claim held by someone else - nothing started" | tee -a "$LOG"; exit 75; }
say "DONE rc=$rc  report: $R/report.md" | tee -a "$LOG"
exit $rc
