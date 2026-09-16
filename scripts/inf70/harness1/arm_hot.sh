#!/bin/bash
# INF-70 HARNESS-1: N measurement arms on ONE hot server. Runs INSIDE region-lock.
#   usage: arm_hot.sh <session> <bindir> -- <label:KEY=VAL,KEY=VAL> ... -- <extra llama-server args>
#   env:   CTX=8192 EVICT_GIB=58 PORT=18499 TRIES=3
# Same server flags, same env stack, same client and same placement gate as champion3/arm.sh --
# the ONLY differences are (a) targeted eviction and (b) knobs switched through the live control
# page instead of the process environment, so each arm no longer pays a 92 GB load.
set -u
SESS=$1; B=$2; shift 2
[ "$1" = "--" ] && shift
ARMS=(); while [ $# -gt 0 ] && [ "$1" != "--" ]; do ARMS+=("$1"); shift; done
[ "${1:-}" = "--" ] && shift
EXTRA=("$@")
H=/mnt/raid0/llm/tmp/inf70/agents/harness1
OUT=$H/runs
TRUNK=/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/IQ4_XS-uniform/Qwen3.8-Flash-Next-IQ4_XS-uniform.gguf
MTPH=/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/MTP/mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf
PORT=${PORT:-18499}; EVICT_GIB=${EVICT_GIB:-58}; CTX=${CTX:-8192}; TRIES=${TRIES:-3}
KP=$OUT/$SESS.knobs.page
T0=$(date +%s); mkdir -p "$OUT"
say(){ echo "$(date -u +%T) +$(( $(date +%s)-T0 ))s $*" | tee -a "$OUT/$SESS.timeline"; }
SPID=""; CPID=""
stop(){ [ -n "$SPID" ] || return 0
        kill -TERM $SPID 2>/dev/null; j=0; while [ -d /proc/$SPID ] && [ $j -lt 120 ]; do sleep 0.5; j=$((j+1)); done
        [ -d /proc/$SPID ] && { say "SIGTERM not honoured -> SIGKILL"; kill -KILL $SPID 2>/dev/null; sleep 3; }
        ps -p $SPID >/dev/null 2>&1 && say "FATAL pid $SPID alive" || say "server pid $SPID dead"; SPID=""; }
die(){ [ -n "${CPID:-}" ] && kill -TERM "$CPID" 2>/dev/null; stop; say "SESSION $SESS end rc=$1 held $(( $(date +%s)-T0 ))s"; exit "$1"; }
trap "kill -TERM \$SPID 2>/dev/null" EXIT

placement(){ numastat -p $SPID > "$OUT/$SESS.$1.numastat" 2>&1
  awk '$1=="Total"{printf "%.2f %.2f %.2f %.2f",$2/1024,$3/1024,$4/1024,$5/1024}' "$OUT/$SESS.$1.numastat"; }

python3 "$H/tools/knobs.py" init "$KP" >/dev/null
say "SESSION $SESS bin=$B ctx=$CTX arms=[${ARMS[*]}] extra=[${EXTRA[*]:-}] knobpage=$KP"
say "version: $(LD_LIBRARY_PATH="$B:${LD_LIBRARY_PATH:-}" "$B/llama-server" --version 2>&1 | head -2 | tr "\n" " ")"

for try in $(seq 1 "$TRIES"); do
  bash "$H/evict_targeted.sh" "$EVICT_GIB" "$TRUNK" "$MTPH" > "$OUT/$SESS.evict.$try" 2>&1
  say "try $try evict: $(grep -E 'EVICT_MODE|EVICT_ELAPSED' "$OUT/$SESS.evict.$try" | tr '\n' ' ')| free/node GiB: $(numactl -H | grep free | awk '{printf "%d ", $4/1024}')"
  i=0; until awk '{exit !($1<10)}' /proc/loadavg || [ $i -ge 60 ]; do sleep 5; i=$((i+1)); done
  say "gate waited $((i*5))s load=$(cut -d' ' -f1-3 /proc/loadavg)"
  ss -ltn | grep -q ":$PORT " && { say "FATAL port busy"; die 64; }
  env LD_LIBRARY_PATH="$B:${LD_LIBRARY_PATH:-}" \
    OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active OMP_DYNAMIC=false GGML_IQK=1 GGML_FUSED_DECODE_OFF=1 \
    GGML_FA_SPLIT_KV=0 GGML_KNOB_FILE="$KP" \
    taskset -c 0-95 numactl --interleave=all "$B/llama-server" --no-webui -np 1 -c "$CTX" -t 48 --no-mmap -lv 4 \
    --host 127.0.0.1 --port "$PORT" -m "$TRUNK" "${EXTRA[@]}" > "$OUT/$SESS.srv.log" 2>&1 &
  SPID=$!
  say "try $try server pid=$SPID"
  i=0; until curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; do sleep 2; i=$((i+1))
    kill -0 $SPID 2>/dev/null || { say "FATAL exited during load: $(grep -aiE 'error|invalid|unrecognized' "$OUT/$SESS.srv.log"|tail -3|tr '\n' ' ')"; die 1; }
    [ $i -ge 400 ] && { say "FATAL health timeout"; die 1; }; done
  say "health OK after $((i*2))s"
  LGG=$(grep -oE "/[^ ]*libggml-cpu\.so[^ ]*" /proc/$SPID/maps | sort -u | head -1)
  case "$LGG" in "$B"/*) say "linkage OK $LGG";; *) say "FATAL linkage $LGG != $B"; die 65;; esac
  # Proof the server really mapped the control page, taken from /proc/<pid>/maps rather than
  # from a log line -- a log line only proves the code ran, and depends on ggml's log routing.
  if grep -q "$(basename "$KP")" /proc/$SPID/maps; then
    say "knob page MAPPED: $(grep "$(basename "$KP")" /proc/$SPID/maps | head -1)"
  else
    say "FATAL knob page $KP not in /proc/$SPID/maps -- arms would not switch"; die 66
  fi
  grep -qa "live control page" "$OUT/$SESS.srv.log" && say "knob page init logged by ggml" || say "note: ggml knob log line not visible in srv.log (log routing); /proc maps is the proof"
  awk '/^Rss:|^AnonHugePages:/{printf "%s %s ",$1,$2}' /proc/$SPID/smaps_rollup > "$OUT/$SESS.smaps"; echo >> "$OUT/$SESS.smaps"
  say "THP: $(awk '{if($2>0) printf "Rss=%.1fGB AnonHuge=%.1fGB (%.2f%%)",$2/1048576,$4/1048576,100*$4/$2}' "$OUT/$SESS.smaps")"
  PL=$(placement load); say "try $try placement GB n0..n3: $PL"
  if python3 - "$PL" <<'PY'
import sys
v=[float(x) for x in sys.argv[1].split()]; m=sum(v)/4
d=max(abs(x-m)/m for x in v); print(f"placement max dev = {d*100:.1f}% (limit 15%)")
sys.exit(0 if d<=0.15 else 3)
PY
  then say "PLACEMENT OK"; break; fi
  say "PLACEMENT SKEWED on try $try -> re-evicting"; stop
  [ "$try" = "$TRIES" ] && { say "FATAL placement never converged"; die 3; }
done

for spec in "${ARMS[@]}"; do
  lbl=${spec%%:*}; kv=${spec#*:}; [ "$kv" = "$spec" ] && kv=""
  A0=$(date +%s)
  # Per-ARM co-residency, not per-session: with 10 arms in one process the whole point is to
  # know WHICH arm was contended. Uses the shared sampler, which counts SMT-sibling lanes
  # (cpus 184-191 over bench cores 88-95) as contention rather than mislabelling them disjoint.
  bash "$H/tools/cores_sampler.sh" "$SPID" "$OUT/$lbl.coresidency" 0-95 20 & CPID=$!
  if [ -n "$kv" ]; then
    python3 "$H/tools/knobs.py" set "$KP" $(echo "$kv" | tr ',' ' ') >> "$OUT/$SESS.knoblog"
  else
    python3 "$H/tools/knobs.py" set "$KP" GGML_HARNESS_NOP=1 >> "$OUT/$SESS.knoblog"
  fi
  say "ARM $lbl knobs=[$kv] $(tail -1 "$OUT/$SESS.knoblog")"
  CLIENT_OUT="$OUT" python3 "$H/client.py" "$lbl" "$PORT" > "$OUT/$lbl.client.log" 2>&1
  kill -TERM $CPID 2>/dev/null; CPID=""
  say "ARM $lbl done in $(( $(date +%s)-A0 ))s  $(tail -1 "$OUT/$lbl.client.log")"
  say "ARM $lbl coresidency: $(bash "$H/tools/coresummary.sh" "$OUT/$lbl.coresidency")"
  say "ARM $lbl knob readback: $(grep -a 'ggml knobs: seq=' "$OUT/$SESS.srv.log" | tail -1)"
  say "ARM $lbl placement GB: $(placement "$lbl")"
done
die 0
