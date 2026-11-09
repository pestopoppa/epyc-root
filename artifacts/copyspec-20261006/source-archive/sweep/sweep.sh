#!/bin/bash
# ngram-cap sweep on the CPU frontdoor (Qwen3.6-35B-A3B-MTP Q8_0, canonical :8070 argv), full host, ONE region-lock hold.
# WRITTEN, NOT RUN.  Usage:
#   sweep.sh --estimate    wall-time estimate only
#   sweep.sh               sample prompts, take ONE lock (cpus 0-95, bench, gpu-quiet shared), run all arms, summarise
#   sweep.sh inner         (internal, inside the lock)
# Arms (order): P W16 W32 W64 W16m8 P2.  P/P2 = production binary + production spec flags.
# W* = experimental width binary, --spec-type ngram-mod,draft-mtp --spec-ngram-mod-n-match 12 (8 for W16m8) --spec-ngram-mod-n-min 4 --spec-ngram-mod-n-max N.
# Binary + argv come from the LIVE :8070 server; arms change only spec flags, --port 18170, --cache-ram 0, --slot-save-path, --verbosity 4.
# Process hygiene: only the captured server PID is ever signalled (EXIT trap, verified with ps -p); no pkill/pgrep.
set -euo pipefail

D=/mnt/raid0/llm/tmp/copy-spec-eval-20261006/sweep
RES=$D/results
WT=/mnt/raid0/llm/worktrees/llama-specwidth-20261006
XBIN=$WT/build-cpu/bin/llama-server
XLIB=$WT/build-cpu/bin
PORT=18170
RL=/workspace/repos/epyc-orchestrator/scripts/region-lock
LINK=/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh
KSTORE=/mnt/raid0/llm/kernels/production/cpu
ARMS_ORDER="P W16 W32 W64 W16m8 P2"
export EVAL_ARMS="$ARMS_ORDER"
export EVAL_CAPS='{"W16":16,"W32":32,"W64":64,"W16m8":16}'
export EVAL_TITLE="Ngram draft-cap sweep, CPU frontdoor (35B-A3B-MTP Q8_0)"
export EVAL_NOTE="W16m8 = cap 16 with n-match 8 (match-length probe; others n-match 12). Full host 0-95, gpu-quiet shared."
export EVAL_BASE="http://127.0.0.1:$PORT"

estimate() {
  # Assumptions: decode ~28 tok/s (P/P2), W arms ~26; prefill ~250 tok/s; gen tokens: debugbench ~400, hotpotqa ~400, prose ~450;
  # prompt tokens: debugbench ~700, hotpotqa ~1300, prose ~80; ~4 min server load per arm.
  python3 - <<'E'
n={"deb":40,"hot":25,"pro":25}; pt={"deb":700,"hot":1300,"pro":80}; gt={"deb":400,"hot":400,"pro":450}
tot=0
for arm,dec in (("P",28.0),("W16",26.0),("W32",26.0),("W64",26.0),("W16m8",26.0),("P2",28.0)):
    s=sum(n[k]*(pt[k]/250.0+gt[k]/dec) for k in n)+240; tot+=s
    print(f"  arm {arm}: ~{s/60:.0f} min")
print(f"EXPECTED WALL TIME (6 arms x 90 prompts): ~{tot/3600:.2f} h (range ~{tot*0.8/3600:.1f}-{tot*1.4/3600:.1f} h); lock timeout 21600 s")
E
}

arm_flags() {
  case "$1" in
    P|P2)  echo "$PROD_SPEC" ;;
    W16)   echo "--spec-type ngram-mod,draft-mtp --spec-ngram-mod-n-match 12 --spec-ngram-mod-n-min 4 --spec-ngram-mod-n-max 16" ;;
    W32)   echo "--spec-type ngram-mod,draft-mtp --spec-ngram-mod-n-match 12 --spec-ngram-mod-n-min 4 --spec-ngram-mod-n-max 32" ;;
    W64)   echo "--spec-type ngram-mod,draft-mtp --spec-ngram-mod-n-match 12 --spec-ngram-mod-n-min 4 --spec-ngram-mod-n-max 64" ;;
    W16m8) echo "--spec-type ngram-mod,draft-mtp --spec-ngram-mod-n-match 8 --spec-ngram-mod-n-min 4 --spec-ngram-mod-n-max 16" ;;
    *) echo "bad arm $1" >&2; return 1 ;;
  esac
}

if [ "${1:-}" = "--estimate" ]; then estimate; exit 0; fi

if [ "${1:-}" != "inner" ]; then
  mkdir -p "$RES"
  estimate
  [ -x "$XBIN" ] || { echo "experimental binary missing: $XBIN (build first)" >&2; exit 2; }
  python3 "$D/phase1.py" sample
  "$RL" run --cpu-list 0-95 --role bench --gpu-quiet shared --tag copy-spec-sweep --timeout-s 21600 -- \
      /bin/bash "$D/sweep.sh" inner 2>&1 | tee -a "$RES/driver.log"
  python3 "$D/phase1.py" summary
  exit 0
fi

# ---------------- inner: runs inside the single region-lock ----------------
mkdir -p "$RES" /mnt/raid0/llm/cache/kv_slots/copy-spec-sweep
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
BASE=(); skip=0
for ((i=1; i<${#ARGV[@]}; i++)); do
  t=${ARGV[$i]}
  if [ $skip -gt 0 ]; then skip=$((skip-1)); continue; fi
  case "$t" in
    --port|--cache-ram|--slot-save-path|--spec-type|--verbosity) skip=1 ;;
    *) BASE+=("$t") ;;
  esac
done
WRAP=(numactl --interleave=all -- taskset -c 0-95)

for v in OMP_PROC_BIND OMP_PLACES OMP_WAIT_POLICY OMP_DYNAMIC GGML_IQK GGML_NUMA_REPACK_INTERLEAVE; do
  val=$(tr '\0' '\n' < "/proc/$PID8070/environ" | sed -n "s/^$v=//p" | head -1)
  [ -n "$val" ] && export "$v=$val"
done

SERVER_PID=""
stop_server() {
  if [ -n "$SERVER_PID" ] && ps -p "$SERVER_PID" >/dev/null 2>&1; then
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
  case "$ARM" in W*) ABIN=$XBIN; ALIB=$XLIB ;; esac
  export LD_LIBRARY_PATH=$ALIB
  local ARGS=("${BASE[@]}" --port "$PORT" --cache-ram 0 --slot-save-path /mnt/raid0/llm/cache/kv_slots/copy-spec-sweep --verbosity 4 "${SPECF[@]}")
  unset LLAMA_TRACE
  case "$ARM" in W*) export LLAMA_TRACE=1 ;; esac
  "$LINK" "$ABIN" "$ALIB" || { echo "linkage check FAILED for arm $ARM" >&2; exit 2; }
  echo "=== arm $ARM $(date -Is) ==="
  echo "argv: ${WRAP[*]} $ABIN ${ARGS[*]}" | tee "$RES/argv_$ARM.txt"
  "${WRAP[@]}" "$ABIN" "${ARGS[@]}" > "$LOG" 2>&1 &
  SERVER_PID=$!
  echo "server pid $SERVER_PID"
  local ok=0
  for _ in $(seq 1 900); do
    ps -p "$SERVER_PID" >/dev/null 2>&1 || { echo "server died during startup; see $LOG" >&2; exit 2; }
    if [ "$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/health" || true)" = "200" ]; then ok=1; break; fi
    sleep 2
  done
  [ $ok = 1 ] || { echo "health timeout" >&2; exit 2; }
  python3 "$D/phase1.py" run --arm "$ARM" --base "http://127.0.0.1:$PORT" --log "$LOG"
  python3 "$D/phase1.py" finalstats --arm "$ARM" --log "$LOG" || true
  ls -l "$LOG"
  stop_server
}

for A in $ARMS_ORDER; do run_arm "$A"; done
