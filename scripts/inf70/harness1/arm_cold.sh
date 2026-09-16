#!/bin/bash
# INF-70 CHAMPION-3: one measurement arm. Runs INSIDE region-lock (--cpu-list 0-95 --role bench).
#   usage: arm.sh <label> <bindir> [extra llama-server args...]
#   env:   ARMENV="VAR=1 VAR2=0"  CTX=8192  EVICT_GIB=58  TRIES=3  PORT=18497
# Derived verbatim in structure from speed-claim/arm.sh (the binary that produced the
# claim-grade 23.16 t/s), plus: per-arm ARMENV, smaps_rollup THP readback, knob readback.
# Promoted from /mnt/raid0/llm/tmp/inf70/agents/harness1 on 2026-09-16 (VB-WIRE-2). Paths are
# now relative to this directory; run outputs still default to the scratch runs dir, which is
# where `cli.py ingest inf70-arms` looks. At arm end it emits the SC75 belief row
# (sc75_capture.sh); set GGUF_SHA256 or write <gguf>.sha256 or the capture refuses, loudly.
set -u
LABEL=$1; B=$2; shift 2
EXTRA=("$@")
H=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
OUT=${INF70_RUNS:-/mnt/raid0/llm/tmp/inf70/agents/harness1/runs}
MTPH=/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/MTP/mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf
. "$H/sc75_capture.sh"
TRUNK=/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/IQ4_XS-uniform/Qwen3.8-Flash-Next-IQ4_XS-uniform.gguf
PORT=${PORT:-18499}
EVICT_GIB=${EVICT_GIB:-58}
TRIES=${TRIES:-3}
CTX=${CTX:-8192}
read -r -a AENV <<< "${ARMENV:-}"
T0=$(date +%s)
mkdir -p "$OUT"
say(){ echo "$(date -u +%T) +$(( $(date +%s)-T0 ))s $*" | tee -a "$OUT/$LABEL.timeline"; }
say "ARM $LABEL bin=$B ctx=$CTX armenv=[${AENV[*]:-}] extra=[${EXTRA[*]:-}]"
VERLINE=$(LD_LIBRARY_PATH="$B:${LD_LIBRARY_PATH:-}" "$B/llama-server" --version 2>&1 | head -2 | tr "\n" " ")
say "version: $VERLINE"
SPID=""; CPID=""
stop(){ [ -n "$SPID" ] || return 0
        kill -TERM $SPID 2>/dev/null; j=0; while [ -d /proc/$SPID ] && [ $j -lt 120 ]; do sleep 0.5; j=$((j+1)); done
        [ -d /proc/$SPID ] && { say "SIGTERM not honoured -> SIGKILL"; kill -KILL $SPID 2>/dev/null; sleep 3; }
        ps -p $SPID >/dev/null 2>&1 && say "FATAL pid $SPID alive" || say "server pid $SPID dead"; SPID=""; }
die(){ stop; [ -n "${CPID:-}" ] && kill -TERM "$CPID" 2>/dev/null; say "ARM $LABEL end rc=$1 held $(( $(date +%s)-T0 ))s"; exit "$1"; }
trap "kill -TERM \$SPID 2>/dev/null" EXIT

cores_sampler(){ exec bash "$H/tools/cores_sampler.sh" "$1" "$OUT/$LABEL.coresidency" 0-95 20; }

for try in $(seq 1 "$TRIES"); do
  if [ "${EVICT_MODE:-old}" = "targeted" ]; then
    bash "$H/evict_targeted.sh" "$EVICT_GIB" "$TRUNK" "$MTPH" > "$OUT/$LABEL.evict.$try" 2>&1
  else
    bash "$H/evict_nodes_force.sh" "$EVICT_GIB" > "$OUT/$LABEL.evict.$try" 2>&1
  fi
  say "try $try evict done | free/node GiB: $(numactl -H | grep free | awk "{printf \"%d \", \$4/1024}")"
  i=0; until awk "{exit !(\$1<10)}" /proc/loadavg || [ $i -ge 60 ]; do sleep 5; i=$((i+1)); done
  say "gate waited $((i*5))s load=$(cut -d" " -f1-3 /proc/loadavg)"
  ss -ltn | grep -q ":$PORT " && { say "FATAL port busy"; die 64; }
  env LD_LIBRARY_PATH="$B:${LD_LIBRARY_PATH:-}" \
    OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active OMP_DYNAMIC=false GGML_IQK=1 GGML_FUSED_DECODE_OFF=1 \
    GGML_FA_SPLIT_KV=0 "${AENV[@]}" \
    taskset -c 0-95 numactl --interleave=all "$B/llama-server" --no-webui -np 1 -c "$CTX" -t 48 --no-mmap -lv 4 \
    --host 127.0.0.1 --port "$PORT" -m "$TRUNK" "${EXTRA[@]}" > "$OUT/$LABEL.srv.log" 2>&1 &
  SPID=$!
  say "try $try server pid=$SPID"
  i=0; until curl -sf "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; do sleep 2; i=$((i+1))
    kill -0 $SPID 2>/dev/null || { say "FATAL exited during load: $(grep -aiE 'error|invalid|unrecognized' "$OUT/$LABEL.srv.log"|tail -3|tr '\n' ' ')"; die 1; }
    [ $i -ge 400 ] && { say "FATAL health timeout"; die 1; }; done
  say "health OK after $((i*2))s"
  LGG=$(grep -oE "/[^ ]*libggml-cpu\.so[^ ]*" /proc/$SPID/maps | sort -u | head -1); say "libggml=$LGG"
  case "$LGG" in "$B"/*) say "linkage OK";; *) say "FATAL linkage $LGG != $B"; die 65;; esac
  tr "\0" "\n" < /proc/$SPID/environ | grep -E "^(GGML_|OMP_|LLAMA_)" | sort > "$OUT/$LABEL.env"
  say "env: $(tr "\n" " " < "$OUT/$LABEL.env")"
  awk '/^Rss:|^AnonHugePages:/{printf "%s %s ",$1,$2}' /proc/$SPID/smaps_rollup > "$OUT/$LABEL.smaps"; echo >> "$OUT/$LABEL.smaps"
  say "THP: $(awk '{if($2>0) printf "Rss=%.1fGB AnonHuge=%.1fGB (%.2f%%)",$2/1048576,$4/1048576,100*$4/$2}' "$OUT/$LABEL.smaps")"
  numastat -p $SPID > "$OUT/$LABEL.numastat" 2>&1
  PL=$(awk "\$1==\"Total\"{printf \"%.2f %.2f %.2f %.2f\",\$2/1024,\$3/1024,\$4/1024,\$5/1024}" "$OUT/$LABEL.numastat")
  say "try $try placement GB n0..n3: $PL"
  if python3 - "$PL" <<"PY"
import sys
v=[float(x) for x in sys.argv[1].split()]; m=sum(v)/4
d=max(abs(x-m)/m for x in v); print(f"placement max dev = {d*100:.1f}% (limit 15%)")
sys.exit(0 if d<=0.15 else 3)
PY
  then say "PLACEMENT OK"; break; fi
  say "PLACEMENT SKEWED on try $try -> re-evicting"; stop
  [ "$try" = "$TRIES" ] && { say "FATAL placement never converged"; die 3; }
done

# SC75 launch identity: once per launch, after placement is accepted, before the arm starts.
LJ="$OUT/$LABEL.launch.json"
say "$(sc75_launch_json "$LJ" "$LABEL-$(date -u -d "@$T0" +%Y%m%dT%H%M%SZ)-pid$SPID" "$SPID" "$TRUNK" "$VERLINE" \
      "taskset -c 0-95; numactl --interleave=all; OMP_PROC_BIND=spread OMP_PLACES=cores; -t 48" "0-95")"
A0=$(date +%s)
cores_sampler "$SPID" & CPID=$!
CLIENT_OUT="$OUT" python3 "$H/client.py" "$LABEL" "$PORT" 2>&1 | tee "$OUT/$LABEL.client.log"
kill -TERM $CPID 2>/dev/null; CPID=""
numastat -p $SPID > "$OUT/$LABEL.numastat.end" 2>&1
say "placement end GB: $(awk "\$1==\"Total\"{printf \"%.2f %.2f %.2f %.2f\",\$2/1024,\$3/1024,\$4/1024,\$5/1024}" "$OUT/$LABEL.numastat.end")"
say "coresidency: $(bash "$H/tools/coresummary.sh" "$OUT/$LABEL.coresidency")"
# SC75 hook: capture-after-measure, immediately (the writer refuses > MAX_CAPTURE_LAG_S). Never aborts.
say "$(sc75_capture_arm "$OUT" "$LABEL" "$LJ" "$A0")"
die 0
