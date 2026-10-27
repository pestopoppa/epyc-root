#!/bin/bash
# yarn_gate_lib.sh -- sourced by yarn_native_gate_job.sh and yarn_extension_arms_job.sh (3c4ca599, 2026-10-22).
# NOT a launcher. The caller sets: YG_ID YG_PLAN YG_OUT YG_PORT and optionally YG_MIN_ARM_S.
# One window = (freeze plan if needed) -> for each arm with pending items, lagging arm first:
#   launch the E1 A0/A1 scratch server (store build, own LD_LIBRARY_PATH, linkage verified) -> prove OUR pid owns the
#   port -> prove rope config + KFD residency -> arm_runner run (WINDOW_CONFIRMED=1, deadline-safe, resumable) ->
#   stop the server by captured PID, verify dead -> decide (decision.json) -> COMPLETE marker when both arms finish.
# Refuses (rc 4) and never stops anything when production :8083 (architect_critic) listens, our port is taken,
# or another KFD process holds VRAM on the card.

YG_RESEARCH=/mnt/raid0/llm/worktrees/yarn-native-gate-runner-20261022     # own worktree, NOT the shared clone
YG_RESEARCH_SHA=7e7d5ef7f28f0c0ec45c16b7a90a51750006671f                  # branch yarn-native-gate-runner-20261022
YG_PY=/mnt/raid0/llm/epyc-inference-research/.venv/bin/python             # research venv 3.13 (tokenizers, dateutil); never bare python3
YG_RUNNER="$YG_RESEARCH/scripts/benchmark/yarn_gate/arm_runner.py"
YG_STORE=/mnt/raid0/llm/kernels/production/gpu
YG_EXPECT_BIN_DIR=/mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82/bin   # v10 ffc1bac82, the E1 binary
YG_EXPECT_VERSION=10303
YG_MODEL=/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf
YG_TEMPLATE=/mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja
YG_LINKAGE=/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh
YG_RAM_GIB=12          # peak host RAM: server ROCm_Host 1.29 GiB model + 2.13 GiB compute (E1 A1 log) + HIP runtime, --no-mmap so
                       # no mapped weights; runner <= 2 GiB (plan freeze maxrss 1.3-1.9 GiB). Measured each window (VmHWM).
YG_PROD_PORT=8083      # production architect_critic (Qwen3.8-27B on the MI210): must be DOWN; we refuse, never stop it
YG_KFD=/sys/class/kfd/kfd/proc
YG_CARD_VRAM=/sys/class/drm/card2/device/mem_info_vram_used
YG_LOAD_S=420          # budget per server load + proof + teardown (27 GiB --no-mmap read; E1 loads took 2-5 min)
YG_MIN_ARM_S=${YG_MIN_ARM_S:-900}
# Server-VRAM creep guard (2026-10-23, from the 2026-10-22 A0/A1 OOM aborts): the E1 scratch server leaks ~0.3 GiB of OWN-PID
# device memory per request (A0 36.8->63.8 GiB over 92 requests, A1 47.3->63.9 over 51; flat per request, independent of
# prompt/decode length) until a pool alloc fails ("ROCm error: out of memory", ggml-cuda.cu:508) and the server aborts.
#  - proactive recycle: when own-PID VRAM >= YG_RECYCLE_BYTES the watcher asks the runner to stop at the next ITEM BOUNDARY
#    (runner --stopfile), the server is stopped cleanly and relaunched for the same arm. No item is lost or charged an error.
#  - death restart: if the server dies anyway (runner rc 7) it is relaunched, at most YG_MAX_RESTARTS times per arm per grant.
# The runner is unchanged: results/<arm>.jsonl is the resume state, so ok items are never re-run, and the failed item is
# recorded in <arm>.errors.jsonl exactly as before (it is retried once more; a second error makes it a terminal 'error').
YG_MAX_RESTARTS=${YG_MAX_RESTARTS:-2}
YG_MAX_RECYCLES=${YG_MAX_RECYCLES:-6}
YG_RECYCLE_BYTES=${YG_RECYCLE_BYTES:-$(( ${YG_RECYCLE_GIB:-60} * 1073741824 ))}   # card is 64 GiB; the E1 abort point was 63.9
YG_WATCH_S=${YG_WATCH_S:-5}
YG_RECYCLE_MIN_GROWTH=${YG_RECYCLE_MIN_GROWTH:-1073741824}   # only recycle a server that has GROWN >= 1 GiB since its first sample (a fresh one at the limit cannot be helped)

yg_ts() { date -u +%FT%TZ; }
yg_log() { echo "$(yg_ts) [$YG_ID] $*"; }
yg_listening() { ss -ltn "sport = :$1" 2>/dev/null | grep LISTEN >/dev/null; }
yg_lib_path() { echo "$1:/opt/rocm/lib:/usr/lib/llvm-20/lib:/opt/AMD/aocc-compiler-5.0.0/lib"; }

# yg_server_argv ARM PORT THREADS OUTDIR -> prints the argv (one per line). E1 launch_arm.sh A0/A1 verbatim except
# --port, -t and the slot-save path.
yg_server_argv() {
  local arm=$1 port=$2 thr=$3 out=$4
  printf '%s\n' -m "$YG_MODEL" --host 127.0.0.1 --port "$port" -np 1 -t "$thr" -ub 2048 --flash-attn on --jinja \
    -ctk q8_0 -ctv q8_0 --no-mmap -ngl all --cache-ram 0 --chat-template-file "$YG_TEMPLATE" --device ROCm0 \
    --slot-save-path "$out/kv_slots_scratch" --verbosity 4
  case $arm in
    A0) printf '%s\n' -c 262144 ;;
    A1) printf '%s\n' -c 524288 --rope-scaling yarn --rope-scale 2 --yarn-orig-ctx 262144 --override-kv \
          "qwen35.context_length=int:524288,qwen35.rope.scaling.type=str:yarn,qwen35.rope.scaling.factor=float:2,qwen35.rope.scaling.original_context_length=int:262144" ;;
    *) return 1 ;;
  esac
}

# yg_tree_clean DIR : rc 0 iff DIR is a git tree with NO tracked modification and NO untracked file (porcelain empty). An
# uncommitted edit is not the pinned commit (YARN-DIRTY-TREE-REFUSE, 2026-10-23). rc 5 + REFUSING line otherwise. This lib only
# ever assigns YG_-prefixed names, so it cannot reassign a caller's pinned-tree variable (hsprof1 run-1 RESEARCH clobber).
yg_tree_clean() {
  local dir=$1 st
  st=$(git -C "$dir" status --porcelain 2>&1) || { yg_log "REFUSING: cannot read git status of $dir"; return 5; }
  [ -z "$st" ] || { yg_log "REFUSING: $dir has uncommitted changes (an uncommitted edit is not the pinned commit): $(echo "$st" | head -3 | tr '\n' ';')"; return 5; }
  return 0
}

# yg_resolve: binary, version, linkage, model, research pin (+ clean tree). Sets YG_BIN_DIR YG_BIN. rc 5 on any mismatch.
yg_resolve() {
  local rundir=$1
  YG_BIN_DIR=$(readlink -f "$YG_STORE")
  [ "$YG_BIN_DIR" = "$YG_EXPECT_BIN_DIR" ] || { yg_log "REFUSING: $YG_STORE -> $YG_BIN_DIR, expected $YG_EXPECT_BIN_DIR"; return 5; }
  YG_BIN=$YG_BIN_DIR/llama-server
  [ -x "$YG_BIN" ] || { yg_log "REFUSING: $YG_BIN missing"; return 5; }
  LD_LIBRARY_PATH=$(yg_lib_path "$YG_BIN_DIR") "$YG_BIN" --version > "$rundir/version.txt" 2>&1
  grep -q "version: $YG_EXPECT_VERSION" "$rundir/version.txt" || { yg_log "REFUSING: $YG_BIN is not build $YG_EXPECT_VERSION"; return 5; }
  LD_LIBRARY_PATH=$(yg_lib_path "$YG_BIN_DIR") bash "$YG_LINKAGE" "$YG_BIN" "$YG_BIN_DIR" > "$rundir/linkage.txt" 2>&1 \
    || { yg_log "REFUSING: ggml linkage check failed ($rundir/linkage.txt)"; return 5; }
  [ -f "$YG_MODEL" ] && [ -f "$YG_TEMPLATE" ] || { yg_log "REFUSING: model or template missing"; return 5; }
  local head; head=$(git -C "$YG_RESEARCH" rev-parse HEAD 2>/dev/null)
  [ "$head" = "$YG_RESEARCH_SHA" ] || { yg_log "REFUSING: research worktree at ${head:-?}, pinned $YG_RESEARCH_SHA"; return 5; }
  yg_tree_clean "$YG_RESEARCH" || return 5
  [ -x "$YG_PY" ] || { yg_log "REFUSING: $YG_PY missing"; return 5; }
  return 0
}

# yg_tenancy: production port down, our port free, no foreign VRAM tenant. rc 4 = refused (nothing touched).
yg_tenancy() {
  if yg_listening "$YG_PROD_PORT"; then yg_log "REFUSING: production :$YG_PROD_PORT is listening (architect_critic); this job never stops it"; return 4; fi
  if yg_listening "$YG_PORT"; then yg_log "REFUSING: port $YG_PORT already listening: not ours"; return 4; fi
  local pids used
  pids=$(ls "$YG_KFD" 2>/dev/null | tr '\n' ' ')
  used=$(( $(cat "$YG_CARD_VRAM" 2>/dev/null || echo 0) / 1073741824 ))
  if [ -n "${pids// /}" ] && [ "$used" -ge 2 ]; then
    yg_log "REFUSING: MI210 holds ${used} GiB for foreign KFD pid(s) $pids (A1 needs the whole card)"; return 4
  fi
  return 0
}

# yg_identity RUNDIR -> identity.json (no full-model hash: size + mtime + sha256 of the first 16 MiB)
yg_identity() {
  local rd=$1
  "$YG_PY" -I - "$YG_MODEL" "$YG_BIN" "$YG_RESEARCH_SHA" "$rd" "$YG_BIN_DIR" <<'PY' > "$rd/identity.json"
import hashlib, json, os, sys
m, b, sha, rd, bd = sys.argv[1:6]
def head(p, n=1 << 24):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read(n)).hexdigest()
def full(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 22), b""):
            h.update(c)
    return h.hexdigest()
st = os.stat(m)
print(json.dumps({"model": m, "model_size": st.st_size, "model_mtime": int(st.st_mtime), "model_head16m_sha256": head(m),
                  "binary": b, "binary_sha256": full(b), "build_dir": bd, "version": open(os.path.join(rd, "version.txt")).read().strip()[:300],
                  "research_sha": sha}, indent=1))
PY
}

# yg_vram_bytes PID : own-PID KFD VRAM bytes (0 = not a KFD process)
yg_vram_bytes() {
  local v=0 k
  for k in "$YG_KFD/$1"/vram_*; do [ -r "$k" ] && v=$(( v + $(cat "$k" 2>/dev/null || echo 0) )); done
  echo "$v"
}

# yg_sampler PID FILE : 5 s samples of own-PID KFD VRAM and host memory (VmRSS/RssAnon/RssFile/VmHWM); exits with PID.
yg_sampler() {
  local pid=$1 f=$2 v k
  while kill -0 "$pid" 2>/dev/null; do
    v=0; for k in "$YG_KFD/$pid"/vram_*; do [ -r "$k" ] && v=$(( v + $(cat "$k" 2>/dev/null || echo 0) )); done
    echo "$(date -u +%s) vram=$v $(grep -E '^(VmRSS|RssAnon|RssFile|VmHWM):' /proc/$pid/status 2>/dev/null | awk '{printf "%s%s ", $1, $2}')" >> "$f"
    sleep 5
  done
}

# yg_recycle_watch PID FLAG : every YG_WATCH_S s, if FILLER_STOPFILE exists write "stop" to FLAG, else if own-PID VRAM >=
# YG_RECYCLE_BYTES write "recycle" to FLAG; first write wins, then exits (so does it when PID dies). FLAG is the runner's --stopfile.
yg_recycle_watch() {
  local pid=$1 flag=$2 v base=""
  while kill -0 "$pid" 2>/dev/null; do
    if [ -n "${FILLER_STOPFILE:-}" ] && [ -e "$FILLER_STOPFILE" ]; then echo stop > "$flag"; return 0; fi
    v=$(yg_vram_bytes "$pid")
    [ -z "$base" ] && [ "$v" -gt 0 ] && base=$v
    if [ -n "$base" ] && [ "$v" -ge "$YG_RECYCLE_BYTES" ] && [ $(( v - base )) -ge "$YG_RECYCLE_MIN_GROWTH" ]; then
      echo recycle > "$flag"
      echo "$(yg_ts) [$YG_ID] recycle requested: pid $pid own VRAM $(( v / 1048576 )) MiB >= $(( YG_RECYCLE_BYTES / 1048576 )) MiB" >> "$flag.log"
      return 0
    fi
    sleep "$YG_WATCH_S"
  done
}

# yg_wait_card_free : after our server is gone, wait (<=120 s) until the KFD table is empty or the card is below 2 GiB.
yg_wait_card_free() {
  local i used pids
  for i in $(seq 1 40); do
    pids=$(ls "$YG_KFD" 2>/dev/null | tr '\n' ' ')
    used=$(( $(cat "$YG_CARD_VRAM" 2>/dev/null || echo 0) / 1073741824 ))
    { [ -z "${pids// /}" ] || [ "$used" -lt 2 ]; } && return 0
    sleep 3
  done
  return 0   # yg_tenancy decides (and refuses with rc 4 if a foreign tenant really holds the card)
}

# yg_stop PID : TERM the captured group (setsid made PID its leader), then KILL, verify dead.
yg_stop() {
  local pid=$1 i
  [ -n "$pid" ] || return 0
  kill -0 "$pid" 2>/dev/null || { yg_log "server $pid already gone"; return 0; }
  kill -TERM -- "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null
  for i in $(seq 1 60); do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
  kill -0 "$pid" 2>/dev/null && { kill -KILL -- "-$pid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null; sleep 2; }
  if kill -0 "$pid" 2>/dev/null; then yg_log "server $pid STILL ALIVE"; return 1; fi
  yg_log "server $pid dead (verified)"; return 0
}

# yg_arm_once ARM ARM_END_EPOCH RUNDIR STOPFLAG : ONE server lifetime for one arm. rc 0 ok, 5 proof failure, 6/7 server failure.
# STOPFLAG is the runner's --stopfile; the watcher writes "stop" (FILLER_STOPFILE) or "recycle" (VRAM creep) into it.
yg_arm_once() {
  local arm=$1 arm_end=$2 rd=$3 flag=$4 spid samp wat="" rc=0 log argvf
  log=$rd/$arm.server.log; argvf=$rd/$arm.argv
  mapfile -t ARGV < <(yg_server_argv "$arm" "$YG_PORT" "${FILLER_THREADS:-8}" "$YG_OUT")
  mkdir -p "$YG_OUT/kv_slots_scratch"
  printf '%s\n' "$YG_BIN" "${ARGV[@]}" > "$argvf"
  yg_listening "$YG_PORT" && { yg_log "port $YG_PORT taken before $arm launch: not ours"; return 4; }
  echo "=== launch $(yg_ts) arm $arm" >> "$log"
  setsid env -u LLAMA_SERVER_SLOTS_DEBUG -u GGML_CUDA_GDN_STATE_BF16 -u GGML_CUDA_FA_MASK_SKIP -u HSA_OVERRIDE_GFX_VERSION \
    LD_LIBRARY_PATH="$(yg_lib_path "$YG_BIN_DIR")" HIP_PATH=/opt/rocm ROCM_PATH=/opt/rocm OMP_PROC_BIND=spread OMP_PLACES=cores \
    OMP_WAIT_POLICY=active OMP_DYNAMIC=false GGML_IQK=1 \
    numactl --membind=3 -- taskset -c "${FILLER_CPUS:-184-191}" "$YG_BIN" "${ARGV[@]}" >> "$log" 2>&1 &
  spid=$!
  read -r YG_OWN_PID YG_OWN_BIRTH YG_OWN_PGID < <(owned_capture_group "$spid") || { yg_log "server identity capture failed; refusing"; return 8; }
  [ "$YG_OWN_PID" = "$spid" ] || return 8
  [ -n "${FILLER_PIDFILE:-}" ] && printf '%s %s %s\n' "$YG_OWN_PID" "$YG_OWN_BIRTH" "$YG_OWN_PGID" >> "$FILLER_PIDFILE"
  yg_log "$arm server pid $spid (log $log)"
  yg_sampler "$spid" "$rd/$arm.mem.txt" &
  samp=$!
  owned_read "$samp" || { yg_log "sampler identity capture failed"; yg_stop "$spid"; return 8; }
  local samp_birth=$OWN_BIRTH samp_pgid=$OWN_PGID wat_birth='' wat_pgid=''
  if ! fl_wait_own_port "$YG_PORT" "$spid" 900; then rc=6; yg_log "$arm: own-pid port proof failed"; fi
  if [ $rc = 0 ]; then
    # rope proof (this launch only): A1 must print yarn / 0.5 / 262144; A0 must not print yarn
    awk -v m="=== launch" 'index($0,m)==1{buf=""} {buf=buf $0 "\n"} END{printf "%s", buf}' "$log" | grep -E \
      "Using metadata override|n_ctx_train|rope scaling|freq_scale_train|n_ctx_orig_yarn|llama_context: (n_ctx|n_ctx_seq|freq_scale|freq_base) |llama_kv_cache: size" > "$rd/$arm.proof.txt" || true
    case $arm in
      A1) grep -q "rope scaling *= *yarn" "$rd/$arm.proof.txt" && grep -q "n_ctx_orig_yarn *= *262144" "$rd/$arm.proof.txt" \
            || { yg_log "A1 proof FAILED: no yarn/262144 lines ($rd/A1.proof.txt)"; rc=5; } ;;
      A0) grep -q "rope scaling *= *yarn" "$rd/$arm.proof.txt" && { yg_log "A0 proof FAILED: yarn active on the native arm"; rc=5; } ;;
    esac
  fi
  if [ $rc = 0 ]; then
    local vram; vram=$(yg_vram_bytes "$spid") || { yg_log "$arm: server identity mismatch during VRAM proof"; rc=5; vram=0; }
    if [ "$vram" -lt $(( 20 * 1073741824 )) ]; then yg_log "$arm: NOT GPU-resident (own-PID KFD vram ${vram} B)"; rc=5; fi
    grep -o '/[^ ]*libggml[^ ]*\.so[^ ]*' "/proc/$spid/maps" 2>/dev/null | sort -u > "$rd/$arm.maps_ggml.txt"
    if grep -v "^$YG_BIN_DIR/" "$rd/$arm.maps_ggml.txt" | grep . >/dev/null; then yg_log "$arm: foreign libggml mapped ($rd/$arm.maps_ggml.txt)"; rc=5; fi
  fi
  if [ $rc = 0 ]; then
    yg_log "$arm: running items until $(date -u -d @"$arm_end" +%FT%TZ)"
    rm -f "$flag" "$flag.log"
    yg_recycle_watch "$spid" "$flag" &
    wat=$!
    owned_read "$wat" || { yg_log "watcher identity capture failed"; yg_stop "$spid"; if owned_match "$samp" "$samp_birth" "$samp_pgid"; then kill "$samp" 2>/dev/null; fi; wait "$samp" 2>/dev/null; return 8; }
    wat_birth=$OWN_BIRTH; wat_pgid=$OWN_PGID
    WINDOW_CONFIRMED=1 nice -n 5 "$YG_PY" -I "$YG_RUNNER" run --out "$YG_OUT" --arm "$arm" \
      --base-url "http://127.0.0.1:$YG_PORT" --deadline-epoch "$arm_end" --stopfile "$flag" \
      --server-pid "$spid" --argv-file "$argvf" --build-dir "$YG_BIN_DIR" --model "$YG_MODEL" >> "$rd/$arm.runner.log" 2>&1
    rc=$?
    if owned_match "$wat" "$wat_birth" "$wat_pgid"; then kill "$wat" 2>/dev/null; fi
    wait "$wat" 2>/dev/null; wat=""
    [ -s "$flag.log" ] && cat "$flag.log"
    [ $rc = 7 ] && yg_log "$arm: server became unreachable mid-run"
    tail -1 "$rd/$arm.runner.log"
  fi
  [ -n "$wat" ] && { if owned_match "$wat" "$wat_birth" "$wat_pgid"; then kill "$wat" 2>/dev/null; fi; wait "$wat" 2>/dev/null; }
  yg_stop "$spid" || rc=8
  if owned_match "$samp" "$samp_birth" "$samp_pgid"; then kill "$samp" 2>/dev/null; fi
  wait "$samp" 2>/dev/null
  return $rc
}

# yg_arm ARM ARM_END_EPOCH RUNDIR : one arm segment = one or more server lifetimes (see the creep-guard note at the top).
# rc 0 ok, 4 refused, 5 proof failure, 6/7 server failure (7 = died and the restart budget is spent), 8 server would not die.
yg_arm() {
  local arm=$1 arm_end=$2 rd=$3 n=0 deaths=0 recycles=0 rc flag why left remaining
  while :; do
    n=$(( n + 1 )); flag=$rd/$arm.stopflag.$n
    yg_arm_once "$arm" "$arm_end" "$rd" "$flag"; rc=$?
    why=""
    if [ $rc = 7 ]; then why=death
    elif [ $rc = 0 ] && [ "$(cat "$flag" 2>/dev/null)" = recycle ]; then why=recycle
    else return $rc; fi
    remaining=$(tail -1 "$rd/$arm.runner.log" 2>/dev/null | sed -n 's/.*"remaining": *\([0-9][0-9]*\).*/\1/p')
    if [ "$remaining" = 0 ]; then yg_log "$arm: no items remain, not relaunching"; return $rc; fi
    if [ -n "${FILLER_STOPFILE:-}" ] && [ -e "$FILLER_STOPFILE" ]; then yg_log "$arm: stop-file, not relaunching"; return $rc; fi
    if [ $why = death ]; then
      [ $deaths -lt $YG_MAX_RESTARTS ] || { yg_log "$arm: server died; restart budget spent ($deaths/$YG_MAX_RESTARTS), giving up this grant (resumable)"; return $rc; }
    else
      [ $recycles -lt $YG_MAX_RECYCLES ] || { yg_log "$arm: recycle cap $YG_MAX_RECYCLES reached, ending arm segment (resumable)"; return 0; }
    fi
    left=$(( arm_end - $(date -u +%s) ))
    if [ $left -lt $(( YG_LOAD_S + YG_MIN_ARM_S )) ]; then
      yg_log "$arm: $why but only ${left}s left in the segment (< load $YG_LOAD_S + min $YG_MIN_ARM_S), not relaunching"; return $rc
    fi
    if [ $why = death ]; then deaths=$(( deaths + 1 )); yg_log "$arm: RESTART $deaths/$YG_MAX_RESTARTS after server death (rc 7); remaining items ${remaining:-?}; failed item is in $arm.errors.jsonl, ok items are not re-run"
    else recycles=$(( recycles + 1 )); yg_log "$arm: RECYCLE $recycles/$YG_MAX_RECYCLES (own-PID VRAM at the creep limit, runner stopped at an item boundary); remaining items ${remaining:-?}"; fi
    yg_wait_card_free
    yg_tenancy || return $?
  done
}

# yg_main [--dry-run]
yg_main() {
  local dry=0; [ "${1:-}" = "--dry-run" ] && dry=1
  local rd now left order arm n i arms_pending=() end
  if [ $dry = 1 ]; then
    rd=$(mktemp -d "${TMPDIR:-/mnt/raid0/llm/tmp}/yg-dryrun.XXXXXX")
    yg_log "DRY RUN (no server, no model load): rundir $rd"
    yg_resolve "$rd"; local r=$?
    yg_log "resolve rc=$r bin=${YG_BIN:-?} ($(head -c 120 "$rd/version.txt" 2>/dev/null | tr '\n' ' '))"
    yg_log "linkage: $(tail -1 "$rd/linkage.txt" 2>/dev/null)"
    yg_listening "$YG_PROD_PORT" && yg_log "production :$YG_PROD_PORT LISTENING -> a window would refuse rc=4" || yg_log "production :$YG_PROD_PORT down (ok)"
    yg_listening "$YG_PORT" && yg_log "port $YG_PORT LISTENING -> a window would refuse rc=4" || yg_log "port $YG_PORT free"
    yg_log "KFD pids now: $(ls "$YG_KFD" 2>/dev/null | tr '\n' ' ') card VRAM used: $(( $(cat "$YG_CARD_VRAM" 2>/dev/null || echo 0) / 1048576 )) MiB"
    yg_log "ram_admit $YG_RAM_GIB (read-only check):"; /mnt/raid0/llm/tmp/compute-flags/ram_admit.sh "$YG_RAM_GIB"; yg_log "ram_admit rc=$?"
    for arm in A0 A1; do yg_log "$arm argv: $YG_BIN $(yg_server_argv $arm "$YG_PORT" 8 "$YG_OUT" | tr '\n' ' ')"; done
    ( cd "$YG_RESEARCH" && "$YG_PY" -I "$YG_RUNNER" dry-run --plan "$YG_PLAN" --out "$YG_OUT" --port "$YG_PORT" )
    yg_log "dry-run done (rc resolve=$r)"; rm -rf "$rd"; return $r
  fi
  : "${FILLER_STOPFILE:?}" "${FILLER_DEADLINE:?}" "${FILLER_PIDFILE:?}" "${FILLER_LIB:?}"
  . "$FILLER_LIB"
  [ -e "$YG_OUT/COMPLETE" ] && { yg_log "already COMPLETE"; return 0; }
  [ -e "$FILLER_STOPFILE" ] && { yg_log "stop-file"; return 0; }
  [ $(( FILLER_DEADLINE - $(date -u +%s) )) -lt $(( YG_LOAD_S + YG_MIN_ARM_S )) ] && { yg_log "window too short: nothing started"; return 0; }
  mkdir -p "$YG_OUT/windows"; rd=$YG_OUT/windows/$(date -u +%Y%m%dT%H%M%SZ); mkdir -p "$rd"
  yg_resolve "$rd" || return $?
  yg_tenancy || return $?
  /mnt/raid0/llm/tmp/compute-flags/ram_admit.sh "$YG_RAM_GIB" || { yg_log "ram_admit refused $YG_RAM_GIB GiB"; return 6; }
  yg_identity "$rd" || { yg_log "identity failed"; return 5; }
  if [ ! -f "$YG_OUT/plan/plan.json" ]; then
    yg_log "freezing plan $YG_PLAN (tokenizer only)"
    ( cd "$YG_RESEARCH" && nice -n 10 "$YG_PY" -I "$YG_RUNNER" plan --plan "$YG_PLAN" --out "$YG_OUT" ) >> "$rd/plan.log" 2>&1 \
      || { yg_log "plan freeze failed ($rd/plan.log)"; return 5; }
  fi
  local st; st=$( cd "$YG_RESEARCH" && "$YG_PY" -I "$YG_RUNNER" status --out "$YG_OUT" --json ) || { yg_log "status failed"; return 5; }
  echo "$st" > "$rd/status_before.json"
  order=$(echo "$st" | "$YG_PY" -I -c "import json,sys;d=json.load(sys.stdin);print(' '.join(a for a in d['order'] if d['arms'][a]['pending']>0))")
  n=$(echo "$order" | wc -w)
  i=0; rc=0
  for arm in $order; do
    [ -e "$FILLER_STOPFILE" ] && { yg_log "stop-file between arms"; break; }
    now=$(date -u +%s); left=$(( FILLER_DEADLINE - now ))
    if [ $(( n - i )) -ge 2 ]; then end=$(( now + left / 2 )); else end=$FILLER_DEADLINE; fi
    i=$(( i + 1 ))
    [ $(( end - now )) -lt $(( YG_LOAD_S + YG_MIN_ARM_S )) ] && { yg_log "$arm: segment $(( end - now ))s too short, skipped"; continue; }
    yg_tenancy || { rc=$?; break; }
    yg_arm "$arm" $(( end - 75 )) "$rd"; rc=$?
    yg_log "$arm segment rc=$rc"
    [ $rc = 0 ] || [ $rc = 7 ] || break
  done
  ( cd "$YG_RESEARCH" && "$YG_PY" -I "$YG_RUNNER" decide --out "$YG_OUT" --identity-file "$rd/identity.json" ) > "$rd/decide.txt" 2>&1
  cat "$rd/decide.txt" | head -5
  if grep -q '"status": "FINAL"' "$YG_OUT/decision.json" 2>/dev/null; then
    { yg_ts; sha256sum "$YG_OUT/decision.json"; } > "$YG_OUT/COMPLETE"
    yg_log "COMPLETE: $(grep -m1 '"verdict"' "$YG_OUT/decision.json")"
    return 0
  fi
  return $rc
}
