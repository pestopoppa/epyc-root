#!/bin/bash
# Width A/B: arms P, W8, W16, P2 (per-impl ngram draft width) in ONE full-host window; NO_GPU_QUIET=1 default (CPU regions only).
# WRITTEN, NOT RUN. Usage:
#   phase1.sh               FULLHOST=1 (default): ONE region-lock on cpus 0-95 held for all arms P, NM, NO, P2
#   FULLHOST=0 phase1.sh    legacy quadrant mode (cpus 24-47, -t 24, no numactl), one lock for all arms too
#   phase1.sh --estimate    print the wall-time estimate only
#   phase1.sh inner         (internal, runs inside the lock)
#
# Binary + argv come from the LIVE :8070 server (readlink /proc/PID/exe, /proc/PID/cmdline).
# Arms change ONLY: spec flags, --port 18170, --cache-ram 0, --slot-save-path, --verbosity 4 (+ -t 24 and the 24-47 pin in FULLHOST=0).
# FULLHOST=1 keeps production's own -t 96 and replicates the launcher's :8070 wrapper:
#   `numactl --interleave=all -- taskset -c 0-95 <server>`
# (stack_topology.yaml frontdoor NUMA_FULL "full 0-95, interleave=all"; numactl_policy_instances 0: interleave=all;
#  live check: numa_maps of the :8070 server = interleave:0-3, threads allowed 0-95).
# Why one full-host lock: AK needs all 4 regions, so even a q1-only hold blocks it; one window serves both phases.
#
# --cache-ram 0 for all arms: production's 32768 MiB host-RAM prompt cache could reuse shared-prefix state across
# distinct prompts differently per arm; 0 keeps every request cold and arms comparable (also cache_prompt=false).
set -euo pipefail

D=/mnt/raid0/llm/tmp/copy-spec-eval-20261006/width
RES=$D/results
WT=/mnt/raid0/llm/worktrees/llama-specwidth-20261006
XBIN=$WT/build-cpu/bin/llama-server
XLIB=$WT/build-cpu/bin
NO_GPU_QUIET=${NO_GPU_QUIET:-1}   # default: CPU regions only (concurrent GPU job holds gpu-quiet exclusive)
PORT=18170
RL=/workspace/repos/epyc-orchestrator/scripts/region-lock
LINK=/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh
KSTORE=/mnt/raid0/llm/kernels/production/cpu
FULLHOST=${FULLHOST:-1}
ARMS_ORDER="P W8 W16 P2"

estimate() {
  # Assumptions (35B-A3B Q8 MTP; llama-bench tg ~23 t/s canonical full host): decode P/P2 ~28, NM ~26, NO ~20 tok/s;
  # prefill ~250 tok/s; gen tokens/request: debugbench ~400, hotpotqa ~400 (quote+answer), general ~150;
  # prompt tokens: debugbench ~700, hotpotqa ~1300, general ~60; ~4 min server load per arm.
  python3 - <<'E'
n={"deb":40,"hot":25,"gen":20}; pt={"deb":700,"hot":1300,"gen":60}; gt={"deb":400,"hot":400,"gen":150}
tot=0
for arm,dec in (("P",28.0),("NM",26.0),("NO",20.0),("P2",28.0)):
    s=sum(n[k]*(pt[k]/250.0+gt[k]/dec) for k in n)+240; tot+=s
    print(f"  arm {arm}: ~{s/60:.0f} min")
print(f"EXPECTED WALL TIME (full host, 4 arms): ~{tot/3600:.2f} h (range ~{tot*0.8/3600:.1f}-{tot*1.4/3600:.1f} h); lock timeout 14400 s")
E
}

arm_flags() {
  case "$1" in
    P|P2) echo "$PROD_SPEC" ;;   # production argv spec flags, unchanged; P2 = repeat of P
    W8)   echo "--spec-type ngram-mod,draft-mtp --spec-ngram-mod-n-match 12 --spec-ngram-mod-n-min 4 --spec-ngram-mod-n-max 8" ;;
    W16)  echo "--spec-type ngram-mod,draft-mtp --spec-ngram-mod-n-match 12 --spec-ngram-mod-n-min 4 --spec-ngram-mod-n-max 16" ;;
    *) echo "bad arm $1" >&2; return 1 ;;
  esac
}

if [ "${1:-}" = "--estimate" ]; then estimate; exit 0; fi

if [ "${1:-}" != "inner" ]; then
  mkdir -p "$RES"
  estimate
  [ -x "$XBIN" ] || { echo "experimental binary missing: $XBIN (build first)" >&2; exit 2; }
  python3 "$D/phase1.py" sample
  if [ "$FULLHOST" = 1 ]; then CPUS=0-95; else CPUS=24-47; fi
  # ONE lock for the whole run (all arms inside the inner script).
  GQ=(--gpu-quiet shared); [ "$NO_GPU_QUIET" = 1 ] && GQ=()
  "$RL" run --cpu-list "$CPUS" --role bench "${GQ[@]}" --tag copy-spec-width --timeout-s 14400 -- \
      /usr/bin/env FULLHOST="$FULLHOST" NO_GPU_QUIET="$NO_GPU_QUIET" /bin/bash "$D/phase1.sh" inner 2>&1 | tee -a "$RES/driver.log"
  python3 "$D/phase1.py" summary
  exit 0
fi

# ---------------- inner: runs inside the single region-lock ----------------
mkdir -p "$RES" /mnt/raid0/llm/cache/kv_slots/copy-spec-p1
PID8070=$(ss -ltnp 'sport = :8070' | grep -o 'pid=[0-9]*' | head -1 | cut -d= -f2)
[ -n "$PID8070" ] || { echo "no listener on :8070" >&2; exit 2; }
BIN=$(readlink "/proc/$PID8070/exe")
mapfile -d '' ARGV < "/proc/$PID8070/cmdline"
echo "binary=$BIN (from /proc/$PID8070/exe)"
[ "$(dirname "$BIN")" = "$(readlink -f "$KSTORE")" ] || { echo "binary not in production cpu store: $BIN" >&2; exit 2; }

PROD_SPEC=""
for ((i=1; i<${#ARGV[@]}; i++)); do
  if [ "${ARGV[$i]}" = "--spec-type" ]; then PROD_SPEC="--spec-type ${ARGV[$((i+1))]}"; fi
done
[ -n "$PROD_SPEC" ] || PROD_SPEC=""   # production argv without --spec-type: P runs with none, unchanged
BASE=()
skip=0
for ((i=1; i<${#ARGV[@]}; i++)); do
  t=${ARGV[$i]}
  if [ $skip -gt 0 ]; then skip=$((skip-1)); continue; fi
  case "$t" in
    --port|--cache-ram|--slot-save-path|--spec-type|--verbosity) skip=1 ;;
    -t) if [ "$FULLHOST" = 1 ]; then BASE+=("$t"); else skip=1; fi ;;   # fullhost keeps production -t (96)
    *) BASE+=("$t") ;;
  esac
done
if [ "$FULLHOST" = 1 ]; then
  WRAP=(numactl --interleave=all -- taskset -c 0-95)
else
  BASE+=(-t 24); WRAP=(taskset -c 24-47)
fi

for v in OMP_PROC_BIND OMP_PLACES OMP_WAIT_POLICY OMP_DYNAMIC GGML_IQK GGML_NUMA_REPACK_INTERLEAVE; do
  val=$(tr '\0' '\n' < "/proc/$PID8070/environ" | sed -n "s/^$v=//p" | head -1)
  [ -n "$val" ] && export "$v=$val"
done

SERVER_PID=""
stop_server() {
  if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill -TERM "$SERVER_PID" 2>/dev/null || true
    for _ in $(seq 1 90); do ps -p "$SERVER_PID" >/dev/null 2>&1 || break; sleep 1; done
    if ps -p "$SERVER_PID" >/dev/null 2>&1; then kill -KILL "$SERVER_PID" 2>/dev/null || true; sleep 2; fi
    if ps -p "$SERVER_PID" >/dev/null 2>&1; then echo "FATAL: server $SERVER_PID still alive" >&2; else echo "server $SERVER_PID confirmed dead"; fi
  fi
  SERVER_PID=""
}
trap stop_server EXIT

run_arm() {
  local ARM=$1 LOG=$RES/server_$1.log FLAGS SPECF
  FLAGS=$(arm_flags "$ARM"); read -r -a SPECF <<< "$FLAGS"
  local ABIN=$BIN ALIB=$KSTORE
  case "$ARM" in W8|W16) ABIN=$XBIN; ALIB=$XLIB ;; esac
  export LD_LIBRARY_PATH=$ALIB
  local ARGS=("${BASE[@]}" --port "$PORT" --cache-ram 0 --slot-save-path /mnt/raid0/llm/cache/kv_slots/copy-spec-p1 --verbosity 4 "${SPECF[@]}")
  unset LLAMA_TRACE
  case "$ARM" in W8|W16) export LLAMA_TRACE=1 ;; esac
  "$LINK" "$ABIN" "$ALIB" || { echo "linkage check FAILED for arm $ARM" >&2; exit 2; }
  echo "=== arm $ARM $(date -Is) ==="
  echo "argv: ${WRAP[*]} $ABIN ${ARGS[*]}" | tee "$RES/argv_$ARM.txt"
  "${WRAP[@]}" "$ABIN" "${ARGS[@]}" > "$LOG" 2>&1 &
  SERVER_PID=$!     # numactl/taskset exec, so this is the server PID
  echo "server pid $SERVER_PID"
  local ok=0
  for _ in $(seq 1 900); do
    kill -0 "$SERVER_PID" 2>/dev/null || { echo "server died during startup; see $LOG" >&2; exit 2; }
    if [ "$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/health" || true)" = "200" ]; then ok=1; break; fi
    sleep 2
  done
  [ $ok = 1 ] || { echo "health timeout" >&2; exit 2; }
  python3 "$D/phase1.py" run --arm "$ARM" --base "http://127.0.0.1:$PORT" --log "$LOG"
  python3 "$D/phase1.py" finalstats --arm "$ARM" --log "$LOG" || true
  ls -l "$LOG"
  stop_server        # restart between arms: no cross-arm cache
}

for A in $ARMS_ORDER; do run_arm "$A"; done
