#!/bin/bash
# Canonical v14: mandatory keeper-issued pre-grant qualification, 2026-11-01.
# T1 launch admission, 2026-10-27: additive successor to EVL10 filler_run10.
# New rows require requested_window_s, est_output_GiB, scratch_root and
# claimed_cpus in notes. The checked writer grant must match the row exactly.
# filler_run9 (2026-10-23, 3c4ca599): = filler_run8 with the two `| grep -q` pipelines (port LISTEN check, cmdline port proof) changed to `| grep ... >/dev/null`; under pipefail grep -q can SIGPIPE the producer and give a false result.
# filler_run5.sh = filler_run2.sh + CTC-Q-H + CTC-Q-G (2026-10-22, 3c4ca599). CLI identical to filler_run2.sh plus one optional flag; filler_run2.sh is left untouched.
#   CTC-Q-H  Lock fds (7 = launcher lock, 8 = runner lock) are closed on every child that does not need them (the poll `sleep`, the 3 s watch `sleep`),
#            and fd 7 on the job group. A killed poller therefore leaves no orphan holding the launcher lock: an immediate re-arm succeeds.
#            fd 8 stays on the job group on purpose: a job that outlives a SIGKILLed launcher keeps the runner lock, so a re-armed launcher cannot double-run.
#   CTC-Q-G  NEW  --repeat   Default: exit (rc 0) after ONE window that actually started the job (a stale poller must not take a re-written grant).
#                            --repeat restores the filler_run2 behaviour (keep polling for further windows).
#            A running sibling (runner lock held by another process) never has its grant deleted: this launcher logs and backs off, no .ended, no rm.
#            (Windows refused/ended without starting the job do not count; the launcher keeps polling.)
# --- original header (filler_run2.sh) ---
# filler_run2.sh = filler_run.sh + exclusive-GPU mode + precondition gate (2026-10-21, v11-drivers). filler_run.sh is left untouched (it is RUNNING).
#   NEW  --gpu-quiet shared|exclusive|none  claim mode of the region-lock wrapper. Defaults reproduce filler_run.sh exactly (cpu: none, gpu/cpu+gpu: shared).
#   NEW  --role ROLE                        region-lock --role (default build; timing items use bench).
#   NEW  --no-fold-siblings                 gpu class: claim gpu-quiet only, no CPU region (host threads tasksetted by the job); cpu class: region-lock --no-fold-siblings
#   NEW  --claim-cpus LIST                  region-lock --cpu-list override (default = grant cpus). Timing items: 0-95. With --gpu-quiet exclusive on a
#                                           gpu-class grant the default is 0-95 + role bench (the whole quiet host, as lib.sh/gpu_champion_ab require);
#                                           the JOB still sees FILLER_CPUS = the grant's host threads (184-191).
#   NEW  --precond-cmd 'CMD'                rc!=0 -> .ended rc=5 reason=build-missing:<first line of CMD stdout>; grant deleted, nothing launched.
#                                           Checked at grant time (after the window/port checks), so a poller can be armed before its builds exist.
# Generic grant-polling FILLER launcher (shell only, no LLM). Generalises ct18-run-20261021/filler_{worker,arch}.sh.
# Protocol: /workspace/docs/guides/agent-workflows/compute-fillers.md ; registry /mnt/raid0/llm/tmp/compute-flags/FILLERS.md
# Usage:
#   filler_run.sh --id ID --class cpu|gpu|cpu+gpu --cmd 'JOB COMMAND' --min-window SECONDS --stop STOPFILE
#                 [--complete-cmd 'CHECK (rc0 = all done)'] [--port P[,P2]] [--sched-port P[,P2]]
#                 [--excl-lock FILE] [--self-claim] [--gpu-threads 184-191] [--workdir DIR]
#   --port        ports the JOB's own servers will bind: launcher refuses (.ended rc=4) if any already LISTENs.
#   --sched-port  ports of the scheduled runner for the same results file: refuse rc=4 if listening.
#   --self-claim  the JOB takes its own region-lock claim (e.g. cs47 latency.sh): launcher adds NO region-lock/GPU claim;
#                 job sees FILLER_END_ISO (grant end) for its --deadline. Job rc (75 claim timeout, 124 end...) lands in .ended.
#   --excl-lock   per-arm runner lock of the scheduled runner: refuse rc=4 if it is held (flock -n probe).
# Grant regions: cpu -> qN list or cpu-list; gpu -> must name mi210_0, digits = host threads (default --gpu-threads);
#   cpu+gpu -> mi210_0 plus qN/cpu-list for the CPU part.
# Job contract (exported into the job): FILLER_ID FILLER_END(epoch hard end) FILLER_DEADLINE(epoch, END-90: start no new item)
#   FILLER_STOPFILE FILLER_CPUS FILLER_THREADS(physical cores) FILLER_PORTS FILLER_PIDFILE(append server PIDs we spawned)
#   FILLER_LIB (source it: fl_wait_own_port PORT PID [maxsecs] proves OUR pid owns the port + /health).
#   Job must be resumable and honour FILLER_STOPFILE / FILLER_DEADLINE between items.
# Test overrides (env): FILLER_RL FILLER_GRANTS_DIR FILLER_FLAGS_DIR FILLERS_MD FILLER_POLL FILLER_STATE_DIR FILLER_STUB_CMD FILLER_GPU_LOCK
set -uo pipefail
HERE=$(dirname "$(readlink -f "$0")")
SELF=$(readlink -f "$0")
T1_CHECK=$HERE/dryrun_check.py
ID=""; CLASS=""; JOBCMD=""; MINWIN=0; STOPFILE=""; COMPLETE_CMD=""; PORTS=""; SCHED_PORTS=""; EXCL_LOCK=""; GPUTHR="184-191"; WORKDIR=/workspace; SELFCLAIM=0; GPUQ=""; ROLE=""; CLAIM_CPUS=""; PRECOND_CMD=""; REPEAT=0; NOFOLD=0; REQUIRES_TOOLS=(); QUAL_INTERPRETER=""
if [ "${1:-}" = "--inner" ]; then INNER=1; shift; else INNER=0; fi
while [ $# -gt 0 ]; do
  case $1 in
    --id) ID=$2; shift 2;; --class) CLASS=$2; shift 2;; --cmd) JOBCMD=$2; shift 2;; --min-window) MINWIN=$2; shift 2;;
    --stop) STOPFILE=$2; shift 2;; --complete-cmd) COMPLETE_CMD=$2; shift 2;; --port) PORTS=$2; shift 2;;
    --sched-port) SCHED_PORTS=$2; shift 2;; --excl-lock) EXCL_LOCK=$2; shift 2;; --gpu-threads) GPUTHR=$2; shift 2;; --self-claim) SELFCLAIM=1; shift;;
    --workdir) WORKDIR=$2; shift 2;;
    --requires-tool) REQUIRES_TOOLS+=("$2"); shift 2;; --qual-interpreter) QUAL_INTERPRETER=$2; shift 2;;
    --gpu-quiet) GPUQ=$2; shift 2;; --role) ROLE=$2; shift 2;; --claim-cpus) CLAIM_CPUS=$2; shift 2;; --precond-cmd) PRECOND_CMD=$2; shift 2;; --repeat) REPEAT=1; shift;; --no-fold-siblings) NOFOLD=1; shift;; *) echo "unknown arg $1" >&2; exit 64;;
  esac
done
[ -n "$ID" ] && [ -n "$JOBCMD" ] && [ -n "$STOPFILE" ] || { echo "need --id --cmd --stop" >&2; exit 64; }
# A missing completion predicate cannot consume a grant or become a false rc1.
[ "$INNER" = 1 ] || [ -n "$COMPLETE_CMD" ] || { echo "REFUSED: --complete-cmd required" >&2; exit 65; }
[ -d "$WORKDIR" ] || { echo "REFUSED: workdir $WORKDIR absent in exec namespace" >&2; exit 65; }
if [ "${WS58_FINGERPRINT_ONLY:-0}" = 1 ]; then
  [ -n "${WS58_QUALIFIER_PATH:-}" ] && [ -n "${WS58_MANIFEST_PATH:-}" ] || { echo "REFUSED: fingerprint plumbing missing" >&2; exit 65; }
  cd "$WORKDIR" || exit 65
  exec python3 -I "$WS58_QUALIFIER_PATH" namespace-local --manifest "$WS58_MANIFEST_PATH"
fi
case $CLASS in cpu|gpu|cpu+gpu) ;; *) echo "bad --class" >&2; exit 64;; esac
case "$GPUQ" in ""|shared|exclusive|none) ;; *) echo "bad --gpu-quiet (shared|exclusive|none)" >&2; exit 64;; esac
# filler_run8 (2026-10-22): a CPU timing job that needs the GPU quiet is --class cpu --gpu-quiet exclusive --claim-cpus LIST.
# run7 refused it and the cpu+gpu workaround then refused workspace-58's CPU-only "0-95" grant (no mi210_0 token) -> slot lost 19:28Z.
[ "$GPUQ" = exclusive ] && [ "$CLASS" = cpu ] && [ -z "$CLAIM_CPUS" ] && { echo "--class cpu --gpu-quiet exclusive needs --claim-cpus LIST" >&2; exit 64; }
# filler_run7 (2026-10-22): a gpu-class exclusive claim used to silently default to a whole-host 0-95 CPU claim. Be explicit.
if [ "$CLASS" = gpu ] && [ "$GPUQ" = exclusive ] && [ -z "$CLAIM_CPUS" ] && [ $NOFOLD = 0 ]; then
  echo "filler_run7: --class gpu --gpu-quiet exclusive needs --claim-cpus LIST (whole-host timing jobs: --claim-cpus 0-95) or --no-fold-siblings (GPU-only claim, no CPU region); refusing to default to 0-95" >&2; exit 64
fi
if [ -n "$CLAIM_CPUS" ] && ! [[ $CLAIM_CPUS =~ ^[0-9]+(-[0-9]+)?(,[0-9]+(-[0-9]+)?)*$ ]]; then echo "bad --claim-cpus" >&2; exit 64; fi

FLAGS=${FILLER_FLAGS_DIR:-/mnt/raid0/llm/tmp/compute-flags}
GRANTS=${FILLER_GRANTS_DIR:-$FLAGS/grants}
FILLERS_MD=${FILLERS_MD:-$FLAGS/FILLERS.md}
POLL=${FILLER_POLL:-45}
STATE=${FILLER_STATE_DIR:-$HERE/state}
GPU_LOCK=${FILLER_GPU_LOCK:-/mnt/raid0/llm/tmp/gpu_device.mi210_0.lock}
RL=${FILLER_RL:-/workspace/repos/epyc-orchestrator/scripts/region-lock}
mkdir -p "$STATE"
LAUNCHER_LOCK=$STATE/$ID.launcher.lock
RUNNER_LOCK=$STATE/$ID.runner.lock
PIDFILE=$STATE/$ID.pids
GRANT=$GRANTS/$ID.grant; ENDED=$GRANTS/$ID.ended; COMPLETE=$GRANTS/$ID.complete
ts() { date -u +%FT%TZ; }
log() { echo "$(ts) [$ID] $*"; }
epoch() { date -u -d "$1" +%s 2>/dev/null; }
listening() { ss -ltn "sport = :$1" 2>/dev/null | grep LISTEN >/dev/null; }
any_listening() { local p; for p in ${1//,/ }; do listening "$p" && { echo "$p"; return 0; }; done; return 1; }

expand() { local t a b; IFS=, read -ra T <<<"$1"; for t in "${T[@]}"; do case $t in *-*) a=${t%-*}; b=${t#*-}; seq "$a" "$b";; *) echo "$t";; esac; done; }
valid_list() { [[ $1 =~ ^[0-9]+(-[0-9]+)?(,[0-9]+(-[0-9]+)?)*$ ]] && ! expand "$1" | awk '$1>191{f=1} END{exit !f}'; }
phys_count() { expand "$1" | awk '{print $1%96}' | sort -un | wc -l; }

parse_regions() { # sets CPUS THREADS NEEDGPU
  local tok qs="" list="" gpu=0 n a b s e parts=""
  IFS=, read -ra TK <<<"${1//;/,}"
  for tok in "${TK[@]}"; do
    case $tok in mi210_0) gpu=1;; q[0-3]) qs="$qs ${tok#q}";; [0-9]*) list="${list:+$list,}$tok";; *) ;; esac
  done
  NEEDGPU=0; CPUS=""
  case $CLASS in
    cpu) [ $gpu = 0 ] || return 1
      if [ -n "$list" ]; then CPUS=$list
      elif [ -n "$qs" ]; then
        for n in $qs; do a=$((n*24)); b=$((a+23)); s=$((a+96)); e=$((s+15)); parts="${parts:+$parts,}$a-$b,$s-$e"; done; CPUS=$parts
      else return 1; fi;;
    gpu) [ $gpu = 1 ] || return 1; NEEDGPU=1; CPUS=${list:-$GPUTHR};;
    cpu+gpu) [ $gpu = 1 ] || return 1; NEEDGPU=1
      if [ -n "$list" ]; then CPUS=$list
      elif [ -n "$qs" ]; then
        for n in $qs; do a=$((n*24)); b=$((a+23)); s=$((a+96)); e=$((s+15)); parts="${parts:+$parts,}$a-$b,$s-$e"; done; CPUS=$parts
      else return 1; fi;;
  esac
  valid_list "$CPUS" || return 1
  if [ $CLASS = gpu ]; then THREADS=$(expand "$CPUS" | sort -un | wc -l); else THREADS=$(phys_count "$CPUS"); fi
}

# VB-CAL-OVERRUN-WRITE: snapshot native duration at launch; never substitute
# min-window/grant length. Composite/ranged/missing estimates stay unchecked.
snapshot_overrun() {
  OV_OWNER=""; OV_EST=""; OV_REGIONS=$1
  IFS='|' read -r OV_OWNER OV_EST < <(LC_ALL=C awk -F'|' -v id="$ID" '
    function trim(s) { sub(/^[[:space:]]+/, "", s); sub(/[[:space:]]+$/, "", s); return s }
    trim($2) == id { n++; owner=trim($3); duration=trim($11) }
    END {
      if (n != 1 || owner == "") exit
      sub(/[[:space:]]*\(.*$/, "", duration)
      sub(/^~/, "", duration); duration=trim(duration)
      if (duration !~ /^[0-9]+([.][0-9]+)?[[:space:]]*(s|sec|secs|second|seconds|m|min|mins|minute|minutes|h|hr|hrs|hour|hours)$/) exit
      value=duration+0; unit=duration; sub(/^[0-9]+([.][0-9]+)?[[:space:]]*/, "", unit)
      if (unit ~ /^(m|min|mins|minute|minutes)$/) value*=60
      if (unit ~ /^(h|hr|hrs|hour|hours)$/) value*=3600
      formatted=sprintf("%.17g", value)
      # Overflow prints inf/nan on awk implementations: never publish it.
      if (value > 0 && formatted ~ /^[0-9]+([.][0-9]+)?([eE][+-]?[0-9]+)?$/)
        printf "%s|%s\n", owner, formatted
    }' "$FILLERS_MD" 2>/dev/null) || :
}

write_ended() { # rc reason
  LM_RESULT=$1
  local ov_started=${OV_STARTED:-} ov_owner=${OV_OWNER:-} ov_est=${OV_EST:-} ov_regions=${OV_REGIONS:-}
  # Consume before any I/O: a later TERM/unstarted repeat cannot reuse it.
  OV_STARTED=""; OV_OWNER=""; OV_EST=""; OV_REGIONS=""
  mkdir -p "$GRANTS"
  [ ! -e "$ENDED" ] || { log "REFUSED: .ended already exists; use a new row id"; return 66; }
  {
    printf 'rc=%s time=%s reason=%s\n' "$1" "$(ts)" "$2"
    if [ -n "$ov_started" ] && [ -n "$ov_est" ]; then
      printf 'job_id=%s\nowner=%s\nstep=job-run\nestimated_wall_s=%s\nstarted=%s\nregions=%s\n' \
        "$ID" "$ov_owner" "$ov_est" "$ov_started" "$ov_regions"
    fi
  } > "$ENDED.tmp"
  ln "$ENDED.tmp" "$ENDED" || { rm -f "$ENDED.tmp"; log "REFUSED: .ended race; use a new id"; return 66; }
  rm -f "$ENDED.tmp"
  rm -f "$GRANT"
  log "ended rc=$1 reason=$2 (grant deleted)"
}
gone() { ! kill -0 -- "-$1" 2>/dev/null; }
proc_birth() { sed 's/.*) //' "/proc/$1/stat" 2>/dev/null | awk '{print $20}'; }
kill_group() { # captured pgid + birth; qualifier verifies identity before TERM/KILL
  local g=$1 birth=$2
  gone "$g" && return 0
  [ -n "$birth" ] || { log "REFUSED: live group $g has no captured birth"; return 1; }
  python3 -I "$WS58_QUALIFIER_PATH" group-drain --manifest "$WS58_MANIFEST_PATH" \
    --flags "$FLAGS" --pgid "$g" --birth "$birth" || {
      log "REFUSED: group $g not safely drained"; return 1; }
  log "group $g dead (birth-verified)"
}
kill_pidfile() { # one pid birth_ticks pair per line; never signal a reused PID
  python3 -I "$WS58_QUALIFIER_PATH" pidfile-drain --manifest "$WS58_MANIFEST_PATH" \
    --flags "$FLAGS" --pidfile "$PIDFILE" --ports "$PORTS" || {
      log "REFUSED: registered native child not safely drained"; return 1; }
}
is_complete() { [ -n "$COMPLETE_CMD" ] || return 1; ( cd "$WORKDIR" && bash -c "$COMPLETE_CMD" ) >/dev/null 2>&1; }
mark_complete() {
  kill_pidfile || { log "REFUSED: completion while native child unverified"; return 70; }
  mkdir -p "$GRANTS"
  write_ended 0 complete || return 70
  printf 'complete time=%s id=%s\n' "$(ts)" "$ID" > "$COMPLETE"
  [ -f "$FILLERS_MD" ] && sed -i "/^| $ID |/ s/ARMED/COMPLETE/" "$FILLERS_MD"
  log "ALL DONE: wrote $COMPLETE, row marked COMPLETE; exiting for good"
}

# ------------------------------------------------------------------ inner (inside the region-lock claim)
if [ $INNER = 1 ]; then
  END=$FILLER_END
  [ $(( END - $(date -u +%s) )) -le 120 ] && { echo "no time left"; exit 3; }
  if p=$(any_listening "$PORTS"); then echo "port $p already in use"; exit 4; fi
  if [ "${FILLER_NEEDGPU:-0}" = 1 ]; then
    exec 9>"$GPU_LOCK"
    flock -w $(( END - $(date -u +%s) - 60 )) 9 || { echo "GPU flock busy"; exit 9; }
    echo "$(ts) mi210_0 flock held"
  fi
  export FILLER_END_ISO=$(date -u -d "@$END" +%FT%TZ) FILLER_ID=$ID FILLER_DEADLINE=$(( END - 90 )) FILLER_STOPFILE=$STOPFILE FILLER_PORTS=$PORTS FILLER_PIDFILE=$PIDFILE FILLER_LIB=$HERE/filler_lib.sh FILLER_DISK_POLICY=$HERE/dryrun_disk_policy.json
  cd "$WORKDIR" || exit 3
  local_t1_scope=()
  [ "${FILLER_PREFLIGHT:-0}" != 1 ] || local_t1_scope+=(--scoped-pf)
  taskset -c "$FILLER_CPUS" python3 -B "$T1_CHECK" resources --id "$ID" \
      --row-file "$FILLERS_MD" --allowed-cpus "$FILLER_CPUS" "${local_t1_scope[@]}" || {
    echo "REFUSED: in-claim RLIMIT/affinity/cgroup proof failed for $ID" >&2; exit 70;
  }
  # No `timeout` wrapper: it moves the job into its own process group, out of reach of the launcher's captured-group kill.
  # The hard end is enforced by the launcher (TERM, wait, KILL on the whole setsid group); the job also honours FILLER_DEADLINE.
  taskset -c "$FILLER_CPUS" bash -c "$JOBCMD" 8>&- 9>&-
  rc=$?; echo "job rc=$rc"
  exit $rc
fi

# ------------------------------------------------------------------ keeper-owned pre-grant qualification
# This invokes the SAME --cmd job entry as normal, with isolated fixture/result
# paths and a synthetic grant. The launcher itself must forward every WS58_*
# variable through its actual env/chroot command; a forked smoke branch cannot pass.
if [ "${WS58_QUAL:-0}" = 1 ]; then
  [ -n "${WS58_QUAL_NONCE:-}" ] && [ -n "${WS58_QUAL_CPUS:-}" ] &&
  [ -n "${WS58_QUAL_RESULTS:-}" ] && [ -n "${WS58_QUAL_FIXTURE:-}" ] &&
  [ -n "${WS58_MANIFEST_PATH:-}" ] && [ -n "${WS58_QUALIFIER_PATH:-}" ] || {
    echo "REFUSED: qualification plumbing missing in actual namespace" >&2; exit 70; }
  [[ $WS58_QUAL_NONCE =~ ^[0-9a-f]{64}$ ]] || { echo "REFUSED: nonce malformed" >&2; exit 70; }
  if [ "$CLASS" != cpu ] || [ "$GPUQ" = exclusive ] || [ "$GPUQ" = shared ]; then
    [ "${WS58_QUAL_GPU_HELD:-0}" = 1 ] || { echo "REFUSED: GPU qualification lacks actual exclusive claim marker" >&2; exit 70; }
  fi
  [ "$(basename "$(dirname "$GRANTS")")" = "$WS58_QUAL_NONCE" ] || { echo "REFUSED: grant dir not nonce-bound" >&2; exit 70; }
  [ -f "$GRANT" ] || { echo "REFUSED: isolated synthetic grant absent" >&2; exit 70; }
  [ -d "$WS58_QUAL_RESULTS" ] || { echo "REFUSED: isolated results dir absent" >&2; exit 70; }
  [ "$(readlink -f "$STATE")" = "$(readlink -f "$(dirname "$GRANTS")/state")" ] || {
    echo "REFUSED: qualification state/PID file is not nonce-bound" >&2; exit 70; }
  if ! FILLER_PREFLIGHT=1 DRYRUN_NONCE="$WS58_QUAL_NONCE" DRYRUN_REQUIRED_CPUS="$WS58_QUAL_CPUS" \
    python3 -B "$T1_CHECK" admit --id "$ID" --row-file "$FILLERS_MD" --grant "$GRANT" \
      --min-window-s "$MINWIN" --require-proof --engine "$SELF"; then
    echo "REFUSED: normal admission failed on synthetic grant" >&2; exit 70
  fi
  python3 -I "$WS58_QUALIFIER_PATH" placement-local --manifest "$WS58_MANIFEST_PATH" \
    --qual-cpus "$WS58_QUAL_CPUS" --engine-class "$CLASS" --no-fold "$NOFOLD" \
    --claim-cpus "$CLAIM_CPUS" >/dev/null || { echo "REFUSED: placement plan" >&2; exit 64; }
  export FILLER_ID="$ID" FILLER_CPUS="$WS58_QUAL_CPUS" FILLER_THREADS=2 \
         FILLER_QUAL_FIXTURE="$WS58_QUAL_FIXTURE" FILLER_RESULTS_DIR="$WS58_QUAL_RESULTS" \
         FILLER_PORTS="$PORTS" FILLER_STOPFILE="$STOPFILE" FILLER_PIDFILE="$PIDFILE" FILLER_LIB="$HERE/filler_lib.sh" FILLER_DISK_POLICY="$HERE/dryrun_disk_policy.json"
  # The synthetic grant carries a genuine window. A native worker with a
  # reserve budget must be able to start before the active cutoff is issued.
  export FILLER_END=$(( $(date -u +%s) + WS58_QUAL_WINDOW_S - 60 ))
  export FILLER_DEADLINE=$(( FILLER_END - 90 ))
  export FILLER_END_ISO="$(date -u -d "@$FILLER_END" +%FT%TZ)"
  cd "$WORKDIR" || exit 65
  # First fixture item must do the real first request and write a native result.
  export FILLER_QUAL_PHASE=normal WS58_QUAL_PROOF="$(dirname "$GRANTS")/proof-normal.json"
  taskset -c "$FILLER_CPUS" bash -c "$JOBCMD"; qrc=$?
  [ "$qrc" = 0 ] || { echo "REFUSED: fixture normal entry rc=$qrc" >&2; exit 70; }
  is_complete || { echo "REFUSED: --complete-cmd did not accept fixture result" >&2; exit 70; }
  export FILLER_QUAL_PHASE=cutoff WS58_QUAL_PROOF="$(dirname "$GRANTS")/proof-cutoff.json"
  if [ "${WS58_QUAL_PRODUCTION:-0}" = 1 ]; then
    export FILLER_STOPFILE="$(dirname "$GRANTS")/cutoff.stop"
    export WS58_QUAL_CUTOFF_EVENT="$(dirname "$GRANTS")/cutoff-event.json"
    taskset -c "$FILLER_CPUS" bash -c "$JOBCMD" & jobpid=$!
    python3 -I "$WS58_QUALIFIER_PATH" trigger-cutoff --manifest "$WS58_MANIFEST_PATH" \
      --nonce "$WS58_QUAL_NONCE" --flags "$FLAGS" --stop-file "$FILLER_STOPFILE" \
      --job-pid "$jobpid" --timeout 240 || { kill "$jobpid" 2>/dev/null; wait "$jobpid" 2>/dev/null; exit 70; }
    wait "$jobpid"; qrc=$?
  else
    export FILLER_DEADLINE="$(date -u +%s)"
    taskset -c "$FILLER_CPUS" bash -c "$JOBCMD"; qrc=$?
  fi
  [ "$qrc" = 75 ] || { echo "REFUSED: forced cutoff rc=$qrc, expected75" >&2; exit 70; }
  python3 -I "$WS58_QUALIFIER_PATH" engine-partial --manifest "$WS58_MANIFEST_PATH" \
    --nonce "$WS58_QUAL_NONCE" --flags "$FLAGS" || exit 70
  exit 0
fi

# Defense in depth for a directly started poller; keeper verifies again before
# grant, including the exact namespace fingerprint and disk floor.
[ -n "${WS58_MANIFEST_PATH:-}" ] && [ -n "${WS58_QUALIFIER_PATH:-}" ] || {
  echo "REFUSED: canonical qualification manifest/qualifier missing" >&2; exit 70; }
resolve_manifest_path() {
  [ -f "$WS58_MANIFEST_PATH" ] && return 0
  local armed="$FLAGS/ready/armed/$ID.json"
  [ -f "$armed" ] || return 1
  export WS58_MANIFEST_PATH="$armed"
}
resolve_manifest_path || { echo "REFUSED: qualification manifest vanished before arm" >&2; exit 70; }
python3 -I "$WS58_QUALIFIER_PATH" verify --manifest "$WS58_MANIFEST_PATH" --flags "$FLAGS" --no-fingerprint-now >/dev/null || {
  echo "REFUSED: valid keeper qualification absent" >&2; exit 70; }

# ------------------------------------------------------------------ launcher (poll loop; shell only)
mkdir -p "$GRANTS"
exec 7>"$LAUNCHER_LOCK"
flock -n 7 || { log "another launcher for $ID already running; exiting"; exit 0; }
CUR=""; CUR_BIRTH=""; STARTED_ONE=0
sleep_poll() { sleep "$1" 7>&- 8>&- & SLP=$!; wait $SLP 2>/dev/null; }
on_term() {
  log "launcher signalled"
  if [ -n "$CUR" ]; then
    kill_group "$CUR" "$CUR_BIRTH" && kill_pidfile || { log "REFUSED: signal cleanup incomplete; grant retained"; exit 70; }
  fi
  [ -e "$GRANT" ] && write_ended 143 launcher-signalled
  exit 143
}
trap on_term TERM INT

run_one() {
  local regions start end s e now rc reason p
  OV_STARTED=""; OV_OWNER=""; OV_EST=""; OV_REGIONS=""
  regions=$(sed -n 's/.*regions=\([^ ]*\).*/\1/p' "$GRANT" | tr -d '\n')
  start=$(sed -n 's/.*start=\([^ ]*\).*/\1/p' "$GRANT" | tr -d '\n')
  end=$(sed -n 's/.*end=\([^ ]*\).*/\1/p' "$GRANT" | tr -d '\n')
  s=$(epoch "$start"); e=$(epoch "$end")
  if [ -z "$regions" ] || [ -z "$s" ] || [ -z "$e" ] || [ "$s" -ge "$e" ]; then write_ended 2 "malformed-grant"; return; fi
  # CTC-Q-G: a running sibling (runner lock held elsewhere) owns this grant: never write .ended / delete it.
  if ! ( exec 5>>"$RUNNER_LOCK"; flock -n 5 ) 2>/dev/null; then
    log "runner lock held by a running sibling; leaving grant and .ended untouched"; GRANT_WAIT=$POLL; return 9
  fi
  now=$(date -u +%s)
  if [ "$now" -ge "$e" ]; then write_ended 3 "grant-expired-unrun"; return; fi
  if [ "$now" -lt "$s" ]; then GRANT_WAIT=$(( s - now )); return 9; fi
  [ ! -e "$ENDED" ] || { log "REFUSED: .ended exists; use new id"; return 66; }
  resolve_manifest_path || { log "REFUSED: qualification manifest vanished after arm"; write_ended 70 "qualification-manifest-absent-after-arm"; return; }
  python3 -I "$WS58_QUALIFIER_PATH" verify --manifest "$WS58_MANIFEST_PATH" --flags "$FLAGS" --no-fingerprint-now >/dev/null || {
    write_ended 70 "qualification-stale-after-grant"; return; }
  if ! parse_regions "$regions"; then write_ended 2 "regions-unusable-for-$ID($CLASS):$regions"; return; fi
  local admission_log admission_rc
  admission_log=$(python3 -B "$T1_CHECK" admit --id "$ID" --row-file "$FILLERS_MD" \
      --grant "$GRANT" --min-window-s "$MINWIN" --engine "$SELF" 2>&1); admission_rc=$?
  if [ "$admission_rc" -ne 0 ]; then
    local why
    why=$(printf '%s\n' "$admission_log" | tail -n 1 | tr -c '[:print:]' ' ' | cut -c1-180)
    log "REFUSED t1-admission rc=$admission_rc $why"
    write_ended 6 "t1-admission:$why"
    return
  fi
  log "$admission_log"
  if [ $(( e - now )) -lt "$MINWIN" ]; then write_ended 3 "window-$(( e - now ))s-below-min-$MINWIN"; return; fi
  if [ -e "$STOPFILE" ]; then write_ended 0 "stop-file-before-start"; return; fi
  if [ -n "$PRECOND_CMD" ]; then
    local pout prc; pout=$( cd "$WORKDIR" && bash -c "$PRECOND_CMD" 2>&1 ); prc=$?
    if [ $prc -ne 0 ]; then write_ended 5 "build-missing:$(printf '%s' "$pout" | head -n1 | tr -c '[:print:]' ' ' | cut -c1-160)"; return; fi
  fi
  if p=$(any_listening "$SCHED_PORTS"); then write_ended 4 "refused:scheduled-runner-port-$p-listening"; return; fi
  if p=$(any_listening "$PORTS"); then write_ended 4 "refused:own-port-$p-already-listening"; return; fi
  if [ -n "$EXCL_LOCK" ]; then
    ( exec 6>>"$EXCL_LOCK"; flock -n 6 ) || { write_ended 4 "refused:scheduled-runner-lock-held"; return; }
  fi
  exec 8>"$RUNNER_LOCK"
  if ! flock -n 8; then exec 8>&-; write_ended 4 "refused:runner-lock-held"; return; fi
  if is_complete; then
    exec 8>&-
    mark_complete || return 70
    return 20
  fi
  log "START regions=$regions cpus=$CPUS threads=$THREADS gpu=$NEEDGPU end=$end"
  export FILLER_END=$e FILLER_CPUS="$CPUS" FILLER_THREADS=$THREADS FILLER_NEEDGPU=$NEEDGPU
  rm -f "$PIDFILE"
  local rlargs
  local gq=$GPUQ cc=${CLAIM_CPUS:-} rl_role=${ROLE:-build}
  if [ "$gq" = exclusive ]; then
    [ -n "$cc" ] || cc=0-95
    [ -n "$ROLE" ] || rl_role=bench
  fi
  case $CLASS in
    cpu) rlargs=(--cpu-list "${cc:-$CPUS}"); [ -n "$gq" ] && [ "$gq" != none ] && rlargs+=(--gpu-quiet "$gq");;
    gpu) if [ "$gq" = exclusive ]; then rlargs=(--cpu-list "$cc" --gpu-quiet exclusive)
         elif [ "$gq" = none ]; then rlargs=()
         else rlargs=(--gpu-quiet "${gq:-shared}"); [ -n "$cc" ] && rlargs=(--cpu-list "$cc" --gpu-quiet "${gq:-shared}"); fi;;
    cpu+gpu) rlargs=(--cpu-list "${cc:-$CPUS}"); [ "$gq" != none ] && rlargs+=(--gpu-quiet "${gq:-shared}");;
  esac
  # --no-fold-siblings (2026-10-22): a GPU job's host threads 184-191 must not fold into a whole-q3 claim (MI210 sat idle behind a q3 build)
  # filler_run6 (2026-10-22): region-lock REFUSES --no-fold-siblings for an SMT-only list ("maps to no regions"), so for a
  # GPU job --no-fold-siblings means: claim gpu-quiet ONLY (no CPU region) and let the job taskset its host threads (184-191).
  if [ $NOFOLD = 1 ]; then
    if [ "$CLASS" = gpu ]; then
      _n=(); _skip=0; for a in "${rlargs[@]}"; do if [ $_skip = 1 ]; then _skip=0; continue; fi; [ "$a" = --cpu-list ] && { _skip=1; continue; }; _n+=("$a"); done
      rlargs=("${_n[@]}"); [[ " ${rlargs[*]} " == *" --gpu-quiet "* ]] || rlargs+=(--gpu-quiet shared)
    elif [[ " ${rlargs[*]} " == *" --cpu-list "* ]]; then rlargs+=(--no-fold-siblings); fi
  fi
  snapshot_overrun "$regions"
  if [ -n "${FILLER_STUB_CMD:-}" ]; then
    setsid bash -c "$FILLER_STUB_CMD" 7>&- &
  elif [ $SELFCLAIM = 1 ]; then
    setsid /bin/bash "$SELF" --inner --id "$ID" --class "$CLASS" --cmd "$JOBCMD" --min-window "$MINWIN" --stop "$STOPFILE" \
        --port "$PORTS" --workdir "$WORKDIR" --gpu-threads "$GPUTHR" 7>&- &
  else
    setsid "$RL" run "${rlargs[@]}" --role "$rl_role" --timeout-s $(( e - $(date -u +%s) )) --tag "filler-$ID" -- \
      /bin/bash "$SELF" --inner --id "$ID" --class "$CLASS" --cmd "$JOBCMD" --min-window "$MINWIN" --stop "$STOPFILE" \
        --port "$PORTS" --workdir "$WORKDIR" --gpu-threads "$GPUTHR" 7>&- &
  fi
  CUR=$!
  CUR_BIRTH=$(proc_birth "$CUR")
  lm_job_dispatched
  OV_STARTED=$(ts)
  [ "$(ps -o pgid= -p $CUR | tr -d ' ')" = "$CUR" ] || log "WARN: $CUR is not a group leader"
  reason=exited
  while kill -0 "$CUR" 2>/dev/null; do
    if [ "$(date -u +%s)" -ge "$e" ]; then reason=hard-end; kill_group "$CUR" "$CUR_BIRTH" || reason=cleanup-failed; break; fi
    if ! python3 -I "$WS58_QUALIFIER_PATH" disk-breach --manifest "$WS58_MANIFEST_PATH" --flags "$FLAGS" >/dev/null 2>&1; then
      reason=disk-floor; kill_group "$CUR" "$CUR_BIRTH" || reason=cleanup-failed; break; fi
    sleep 3 7>&- 8>&-
  done
  wait "$CUR" 2>/dev/null; rc=$?
  case $reason in hard-end|disk-floor) rc=75;; esac
  local cleanup_bad=0
  kill_group "$CUR" "$CUR_BIRTH" || cleanup_bad=1
  kill_pidfile || cleanup_bad=1
  CUR=""
  CUR_BIRTH=""
  exec 8>&-
  if [ "$cleanup_bad" = 1 ] || [ "$reason" = cleanup-failed ]; then
    log "REFUSED: native cleanup incomplete; grant retained, no .ended or .complete"
    STARTED_ONE=1; return 70
  fi
  if is_complete; then mark_complete || return 70; return 20; fi
  if [ "$rc" -eq 0 ]; then rc=75; reason=partial-native-incomplete; fi
  [ "$rc" -eq 75 ] || reason="job-rc-$rc:$reason"
  write_ended "$rc" "$reason"
  STARTED_ONE=1
}

# Disabled metadata has no new file dependency or EXIT trap.
lm_attempt_begin() { :; }
lm_attempt_end() { :; }
lm_job_dispatched() { :; }
if [ -n "${LOOP_METRICS_LEDGER:-}" ]; then
  if [ -n "$(trap -p EXIT)" ]; then
    printf '%s\n' 'loop metrics: existing EXIT trap preserved; coverage unavailable' >&2
  elif [ -r "${LOOP_METRICS_HOOK:-$(dirname "$SELF")/loop_metrics_hook.sh}" ]; then
    source "${LOOP_METRICS_HOOK:-$(dirname "$SELF")/loop_metrics_hook.sh}"
    lm_start
    trap lm_close EXIT
  else
    printf '%s\n' 'loop metrics: helper unavailable; coverage unavailable' >&2
  fi
fi
log "launcher up pid=$$ class=$CLASS poll=${POLL}s grants=$GRANTS stop=$STOPFILE minwin=${MINWIN}s ports=${PORTS:-none}"
if is_complete; then mark_complete || exit 70; exit 0; fi
while :; do
  [ -e "$COMPLETE" ] && { log "complete marker present; exiting"; exit 0; }
  if [ ! -e "$GRANT" ]; then sleep_poll "$POLL"; continue; fi
  GRANT_WAIT=""
  lm_attempt_begin
  run_one; rc=$?
  lm_attempt_end "$rc"
  [ "$rc" = 70 ] && exit 70
  [ $rc = 20 ] && exit 0
  if [ "${STARTED_ONE:-0}" = 1 ] && [ $REPEAT = 0 ]; then log "one window done; exiting (no --repeat)"; exit 0; fi
  if [ $rc = 9 ]; then w=$GRANT_WAIT; [ "$w" -gt "$POLL" ] && w=$POLL; sleep_poll "$w"; fi
done
