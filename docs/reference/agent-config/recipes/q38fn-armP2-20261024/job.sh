#!/bin/bash
# q38fn-armP2-ppl : ARM P = UD-IQ4_XS with ONLY ffn_gate_exps + ffn_up_exps requantized to IQ4_XS; PPL + coherence vs UD. See PREDECLARED.md.
# Env (filler contract): FILLER_CPUS (e.g. 24-47) FILLER_DEADLINE (epoch) FILLER_STOPFILE. Resumable via <step>.rc in $D/state.
set -euo pipefail
D=/mnt/raid0/llm/tmp/ws58-q38fn-armP2-20261024
B=/mnt/raid0/llm/kernels/builds/cpu-20261023-dcc853b55-c3/bin
UD=/mnt/raid0/llm/models/unsloth/Qwen3.8-Flash-Next-GGUF/UD-IQ4_XS/Qwen3.8-Flash-Next-UD-IQ4_XS-00001-of-00003.gguf
WIKI=/mnt/raid0/llm/data/wiki.test.raw
OUT=$D/out/q38fn-armP2.gguf
CPUS=${FILLER_CPUS:?FILLER_CPUS required}
DEADLINE=${FILLER_DEADLINE:?FILLER_DEADLINE required}
STOP=${FILLER_STOPFILE:-$D/NOSTOP}
T=24
QT=${FILLER_THREADS:-24}   # requant only: llama-quantize output is thread-count independent (per-row); PPL/server stay at the predeclared -t 24
S=$D/state; mkdir -p "$S" "$D/out" "$D/logs"
export LD_LIBRARY_PATH=$B
# AMENDMENT 1 (2026-10-24): serving env of the codified recipe (qwen38_flash_next_recipe.py CHAMPION_GGML_ENV + CANONICAL_OMP_ENV). v1 ran WITHOUT it.
export GGML_IQK=1 GGML_FUSED_DECODE_OFF=1 GGML_FA_SPLIT_KV=0 GGML_NOHUGEPAGE_PROCESS=1 OMP_PROC_BIND=spread OMP_PLACES=cores OMP_WAIT_POLICY=active OMP_DYNAMIC=false
LIM=$((DEADLINE-120))
log(){ echo "[$(date -u +%FT%TZ)] $*" | tee -a "$D/logs/job.log"; }
stopped(){ [ -e "$STOP" ]; }
left(){ echo $((LIM-$(date +%s))); }
# need SECS: refuse to start a step that cannot finish before DEADLINE-120 (exit 75 = resumable)
need(){ if stopped; then log "STOPFILE present"; exit 75; fi; if [ "$(left)" -lt "$1" ]; then log "only $(left)s left, step needs ~$1s: stop (resumable)"; exit 75; fi; }
# run CMD... in background, poll stopfile/deadline, kill only our own PID
runstep(){ # name est_secs cmd...
  local n=$1 est=$2; shift 2
  [ -e "$S/$n.rc" ] && [ "$(cat "$S/$n.rc")" = 0 ] && { log "$n already done"; return 0; }
  need "$est"; log "START $n (est ${est}s)"
  set +e; "$@" > "$D/logs/$n.out" 2> "$D/logs/$n.err" & local p=$!
  while kill -0 $p 2>/dev/null; do
    if stopped || [ "$(left)" -le 0 ]; then log "$n: stop/deadline, terminating own pid $p"; kill -TERM $p 2>/dev/null; sleep 10; kill -0 $p 2>/dev/null && kill -KILL $p 2>/dev/null; wait $p 2>/dev/null; rm -f "$OUT.part"; exit 75; fi
    sleep 5
  done
  wait $p; local rc=$?; set -e
  echo $rc > "$S/$n.rc"; log "END $n rc=$rc"
  [ $rc = 0 ] || { log "$n FAILED"; exit $rc; }
}
TS(){ nice -n 10 taskset -c "$CPUS" "$@"; }

# ---- preflight
for f in "$B/llama-quantize" "$B/llama-perplexity" "$B/llama-completion" "$UD" "$WIKI"; do [ -e "$f" ] || { log "missing $f"; exit 2; }; done
for x in llama-quantize llama-perplexity llama-completion; do bash /mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh "$B/$x" >> "$D/logs/linkage.txt" 2>&1 || { log "linkage check FAILED for $x"; exit 3; }; done

# ---- step 1: dry-run proof of the override set
step1(){
  TS $B/llama-quantize --allow-requantize --dry-run "$UD" "$OUT" COPY $T > "$D/logs/dry-copy.log" 2>&1
  /usr/bin/python3 -I "$D/genpins.py" "$D/logs/dry-copy.log" "$D/pins.txt"          # asserts 1224 tensors, 96 gate/up
  TS $B/llama-quantize --allow-requantize --dry-run --output-tensor-type q6_K --tensor-type-file "$D/pins.txt" "$UD" "$OUT" Q8_0 $T > "$D/logs/dry-pins.log" 2>&1
  local ch other xs q6 bad
  ch=$(grep '^\[' "$D/logs/dry-pins.log" | grep -c -e '->' || true)
  xs=$(grep '^\[' "$D/logs/dry-pins.log" | grep -e '->' | grep -c '(iq4_xs)' || true)
  q6=$(grep '^\[' "$D/logs/dry-pins.log" | grep -e '->' | grep -c '(q6_K)' || true)
  bad=$(grep '^\[' "$D/logs/dry-pins.log" | grep -e '->' | grep -vc 'ffn_\(gate\|up\)_exps.*iq3_s,.*(iq4_xs)\|\(attn_\(gate\|k\|q\|v\|qkv\|output\)\|ssm_out\|ffn_\(gate\|up\)_shexp\)\.weight.*q8_0,.*(q6_K)' || true)
  echo "changed=$ch iq4_xs=$xs q6_K=$q6 unexpected=$bad"; grep -e 'model size' -e 'quant size' "$D/logs/dry-pins.log"
  [ "$ch" = 346 ] && [ "$xs" = 94 ] && [ "$q6" = 252 ] && [ "$bad" = 0 ]    # 94 gate/up exps + 252 Q8_0->Q6_K; ffn_down_shexp (ncols 640) stays Q8_0
}
runstep s1_dryrun 120 step1

# ---- step 2: real requant (to .part, then rename)
step2(){
  local free; free=$(df -BG --output=avail /mnt/raid0 | tail -1 | tr -dc 0-9)
  [ "$free" -ge 120 ] || { echo "free ${free}G < 120G"; return 9; }
  rm -f "$OUT.part"
  TS $B/llama-quantize --allow-requantize --output-tensor-type q6_K --tensor-type-file "$D/pins.txt" "$UD" "$OUT.part" Q8_0 $QT
  mv "$OUT.part" "$OUT"
}
if [ ! -s "$OUT" ]; then rm -f "$S/s2_requant.rc"; fi
runstep s2_requant 1500 step2

# ---- step 3: PPL, identical settings, P then UD (protocol of step1_exl3_full: wiki.test.raw c512 b512 --chunks 40)
ppl(){ TS $B/llama-perplexity -m "$1" -f "$WIKI" -c 512 -b 512 --chunks 40 -t $T; }
runstep s3_ppl_P  900 ppl "$OUT"
runstep s3_ppl_UD 900 ppl "$UD"

# ---- step 4 (AMENDMENT 1): coherence through llama-server chat-completions, think disabled, temp 0, same env/flags as production serving (plain trunk, no MTP head: greedy MTP is lossless; mmap not --no-mmap, placement is irrelevant to correctness)
coh(){ # model tag
  local port=18941 pid
  ss -ltn | grep ":$port " >/dev/null && { echo "port $port busy"; return 7; }
  nice -n 10 taskset -c "$CPUS" $B/llama-server -m "$1" --host 127.0.0.1 --port $port --no-webui -np 1 -c 2048 -t $T -fa on -ctk f16 -ctv f16 -lv 4 > "$D/logs/srv-$2.log" 2>&1 & pid=$!
  trap "kill -TERM $pid 2>/dev/null" TERM
  local ok=0 i
  for i in $(seq 1 120); do
    kill -0 $pid 2>/dev/null || break
    if curl -fs "http://127.0.0.1:$port/health" >/dev/null 2>&1; then ok=1; break; fi
    sleep 5
  done
  local rc=1
  if [ $ok = 1 ]; then
    # prove the listener is OUR pid
    ss -ltnp | grep ":$port " | grep "pid=$pid," >/dev/null || { echo "port not owned by our pid"; kill $pid; return 8; }
    /usr/bin/python3 -I "$D/coh_client.py" $port "$D/out/coh-$2" && rc=0
  fi
  kill -TERM $pid 2>/dev/null || true
  for i in 1 2 3 4 5 6; do kill -0 $pid 2>/dev/null || break; sleep 2; done
  kill -0 $pid 2>/dev/null && kill -KILL $pid 2>/dev/null || true
  wait $pid 2>/dev/null || true
  return $rc
}
runstep s4_coh_P  420 coh "$OUT" P
runstep s4_coh_UD 420 coh "$UD" UD

# ---- step 5: verdict
/usr/bin/python3 -I "$D/verdict.py" "$D" && touch "$D/out/COMPLETE" || true
log "done"
