#!/bin/bash
# filler_run15.sh - canonical engine of the simplified row flow (ws58, operator ruling 2026-11-01: remove every gate
# that is not indispensable). = filler_run14.sh MINUS the keeper-qualification coupling (WS58_QUAL fixture branch,
# nonce/receipt verify at start and at grant, dryrun_check.py T1 admission and in-claim resource proof against the
# FILLERS.md 18-cell row, FILLERS.md COMPLETE sed, qualifier-mediated group/pidfile drain) PLUS:
#   FILLER_DRYRUN=1 FILLER_DRYRUN_DIR=DIR  the keeper's dry run: the SAME launcher, engine, region-lock claim and job on
#       the real lane under a real short grants/<id>.grant; .ended/.complete/stop file live in DIR so the real row id is
#       never consumed. The keeper stops the job via DIR/stop once the first unit of output is in result_path.
#   FILLER_OWNER / FILLER_EST_WALL_S (env, set by rowflow arm) replace the FILLERS.md owner/duration lookup in .ended.
#   --requires-tool / --qual-interpreter are accepted and ignored (v14 launchers keep working once repointed).
# Region-lock default is the host path (valid in every namespace); /workspace is a devcontainer-only symlink and a
# keeper-launched job never sees it (class-A launch failures 2026-11-01: `region-lock: No such file or directory`).
# --- original header (filler_run2.sh) ---
# filler_run2.sh = filler_run.sh + exclusive-GPU mode + precondition gate (2026-10-21, v11-drivers). filler_run.sh is left untouched (it is RUNNING).
#   NEW  --gpu-quiet shared|exclusive|none  claim mode of the region-lock wrapper. Default none for EVERY class (2026-11-03 session
#                                           review item 6: gpu-quiet is opt-in for decision-grade/quiet rows only; a gpu row left at
#                                           `none` runs on the MI210 beside other work under the 2026-10-22 co-residency policy).
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
# Mid-job STOP (2026-11-05, keeper-friction-review refinement 4): the launcher polls --stop every 3 s while the job runs;
#   on STOP it TERMs the job's setsid group (region-lock child, inner engine group and every member), KILLs after
#   --stop-grace S (default ${FILLER_STOP_GRACE_S:-60}; not in a dry run: the keeper's harness owns that stop and its
#   600 s truncation warning), verifies the groups are gone, writes .ended rc=75 reason=stopped (grant released; the region-lock dies
#   with its group, so its claim is released) and exits. A STOP present when a grant arrives writes a terminal
#   .ended rc=75 reason=stopped-before-start (it used to release the grant silently and be re-granted every tick, F4).
# Test overrides (env): FILLER_RL FILLER_GRANTS_DIR FILLER_FLAGS_DIR FILLERS_MD FILLER_POLL FILLER_STATE_DIR FILLER_STUB_CMD FILLER_GPU_LOCK
set -uo pipefail
HERE=$(dirname "$(readlink -f "$0")")
SELF=$(readlink -f "$0")
ID=""; CLASS=""; JOBCMD=""; MINWIN=0; STOPFILE=""; COMPLETE_CMD=""; PORTS=""; SCHED_PORTS=""; EXCL_LOCK=""; GPUTHR="184-191"; WORKDIR=/workspace; SELFCLAIM=0; GPUQ=""; ROLE=""; CLAIM_CPUS=""; PRECOND_CMD=""; STOP_GRACE=""; REPEAT=0; NOFOLD=0; REQUIRES_TOOLS=(); QUAL_INTERPRETER=""
if [ "${1:-}" = "--inner" ]; then INNER=1; shift; else INNER=0; fi
while [ $# -gt 0 ]; do
  case $1 in
    --id) ID=$2; shift 2;; --class) CLASS=$2; shift 2;; --cmd) JOBCMD=$2; shift 2;; --min-window) MINWIN=$2; shift 2;;
    --stop) STOPFILE=$2; shift 2;; --complete-cmd) COMPLETE_CMD=$2; shift 2;; --port) PORTS=$2; shift 2;;
    --sched-port) SCHED_PORTS=$2; shift 2;; --excl-lock) EXCL_LOCK=$2; shift 2;; --gpu-threads) GPUTHR=$2; shift 2;; --self-claim) SELFCLAIM=1; shift;;
    --workdir) WORKDIR=$2; shift 2;;
    --requires-tool) REQUIRES_TOOLS+=("$2"); shift 2;; --qual-interpreter) QUAL_INTERPRETER=$2; shift 2;;
    --gpu-quiet) GPUQ=$2; shift 2;; --role) ROLE=$2; shift 2;; --claim-cpus) CLAIM_CPUS=$2; shift 2;; --precond-cmd) PRECOND_CMD=$2; shift 2;; --stop-grace) STOP_GRACE=$2; shift 2;; --repeat) REPEAT=1; shift;; --no-fold-siblings) NOFOLD=1; shift;; *) echo "unknown arg $1" >&2; exit 64;;
  esac
done
[ -n "$ID" ] && [ -n "$JOBCMD" ] && [ -n "$STOPFILE" ] || { echo "need --id --cmd --stop" >&2; exit 64; }
# A missing completion predicate cannot consume a grant or become a false rc1.
[ "$INNER" = 1 ] || [ -n "$COMPLETE_CMD" ] || { echo "REFUSED: --complete-cmd required" >&2; exit 65; }
[ -d "$WORKDIR" ] || { echo "REFUSED: workdir $WORKDIR absent in exec namespace" >&2; exit 65; }
case $CLASS in cpu|gpu|cpu+gpu) ;; *) echo "bad --class" >&2; exit 64;; esac
case "$GPUQ" in ""|shared|exclusive|none) ;; *) echo "bad --gpu-quiet (shared|exclusive|none)" >&2; exit 64;; esac
# filler_run8 (2026-10-22): a CPU timing job that needs the GPU quiet is --class cpu --gpu-quiet exclusive --claim-cpus LIST.
# run7 refused it and the cpu+gpu workaround then refused workspace-58's CPU-only "0-95" grant (no mi210_0 token) -> slot lost 19:28Z.
[ "$GPUQ" = exclusive ] && [ "$CLASS" = cpu ] && [ -z "$CLAIM_CPUS" ] && { echo "--class cpu --gpu-quiet exclusive needs --claim-cpus LIST" >&2; exit 64; }
# filler_run7 (2026-10-22): a gpu-class exclusive claim used to silently default to a whole-host 0-95 CPU claim. Be explicit.
if [ "$CLASS" = gpu ] && [ "$GPUQ" = exclusive ] && [ -z "$CLAIM_CPUS" ] && [ $NOFOLD = 0 ]; then
  echo "filler_run7: --class gpu --gpu-quiet exclusive needs --claim-cpus LIST (whole-host timing jobs: --claim-cpus 0-95) or --no-fold-siblings (GPU-only claim, no CPU region); refusing to default to 0-95" >&2; exit 64
fi
[[ ${STOP_GRACE:-0} =~ ^[0-9]+$ ]] || { echo "bad --stop-grace (seconds)" >&2; exit 64; }
if [ -n "$CLAIM_CPUS" ] && ! [[ $CLAIM_CPUS =~ ^[0-9]+(-[0-9]+)?(,[0-9]+(-[0-9]+)?)*$ ]]; then echo "bad --claim-cpus" >&2; exit 64; fi

FLAGS=${FILLER_FLAGS_DIR:-/mnt/raid0/llm/tmp/compute-flags}
GRANTS=${FILLER_GRANTS_DIR:-$FLAGS/grants}
FILLERS_MD=${FILLERS_MD:-$FLAGS/FILLERS.md}
POLL=${FILLER_POLL:-5}   # ws58 2026-11-02: a granted quarter starts within seconds, not 45 s
STATE=${FILLER_STATE_DIR:-$HERE/state}
GPU_LOCK=${FILLER_GPU_LOCK:-/mnt/raid0/llm/tmp/gpu_device.mi210_0.lock}
RL=${FILLER_RL:-/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock}
mkdir -p "$STATE"
LAUNCHER_LOCK=$STATE/$ID.launcher.lock
RUNNER_LOCK=$STATE/$ID.runner.lock
PIDFILE=$STATE/$ID.pids
GRANT=$GRANTS/$ID.grant; ENDED=$GRANTS/$ID.ended; COMPLETE=$GRANTS/$ID.complete
DRYRUN=${FILLER_DRYRUN:-0}
if [ "$DRYRUN" = 1 ]; then
  DR=${FILLER_DRYRUN_DIR:?FILLER_DRYRUN=1 needs FILLER_DRYRUN_DIR}; mkdir -p "$DR/state"
  ENDED=$DR/ended; COMPLETE=$DR/complete; STOPFILE=$DR/stop; STATE=$DR/state; REPEAT=0
  LAUNCHER_LOCK=$STATE/$ID.launcher.lock; RUNNER_LOCK=$STATE/$ID.runner.lock; PIDFILE=$STATE/$ID.pids
  # allocator 2026-11-01: a multi-quarter row is dry-run on ONE quarter - the region-lock claim is the grant's own cpus
  # (gpu class: its host threads, folding onto q3), so a dry run never holds more than it needs.
  if [ "${FILLER_DRYRUN_ONE_QUARTER:-0}" = 1 ]; then if [ "$CLASS" = gpu ]; then CLAIM_CPUS=$GPUTHR; else CLAIM_CPUS=""; GPUQ=none; fi; fi  # quiet-host rows: plumbing only
  # ws58 2026-11-02: publish_row's smoke (FILLER_SMOKE=1) is always small and must NEVER wait on a held region (a real
  # whole-host run held q0 and every smoke blocked on its full 0-95 claim). Its claim is exactly the smoke's cpus
  # (WS58_REGIONS), taken by taskset, not region-lock; it never takes gpu-quiet exclusive (gpu rows: shared gpu lock only).
  SMOKE_NOLOCK=0
  if [ "${FILLER_SMOKE:-0}" = 1 ]; then
    SMOKE_NOLOCK=1; CLAIM_CPUS=${WS58_REGIONS:-$CLAIM_CPUS}; NOFOLD=0
    if [ "$CLASS" = gpu ]; then GPUQ=shared; else GPUQ=none; fi
  fi
fi
STOP_GRACE=${STOP_GRACE:-${FILLER_STOP_GRACE_S:-60}}
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
snapshot_overrun() {  # v15: owner/estimate come from the row (rowflow arm exports them); no FILLERS.md lookup
  OV_OWNER=${FILLER_OWNER:-}; OV_EST=${FILLER_EST_WALL_S:-}; OV_REGIONS=$1
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
  notify_end "$1" "$2"
}
# 2026-11-04 incident (disk-floor kill, nobody told for 3 h): push every terminal event to the row owner (session bus)
# and rowflow-alerts.jsonl. Idempotent, best effort, never changes the caller's rc. Dry runs report via rowflow FAIL.
notify_end() { # rc reason
  [ "$DRYRUN" = 1 ] && return 0
  [ -f "$HERE/notify.py" ] || { log "WARN: $HERE/notify.py missing; terminal event NOT pushed"; return 0; }
  local ef=()
  [ -e "$ENDED" ] && ef=(--ended-file "$ENDED")
  ROWFLOW_FLAGS="$FLAGS" timeout 60 python3 -I "$HERE/notify.py" --flags "$FLAGS" row-ended --id "$ID" \
    --rc "$1" --reason "$2" ${FILLER_OWNER:+--owner "$FILLER_OWNER"} "${ef[@]}" </dev/null 7>&- 8>&- || log "WARN: notify rc=$?"
  return 0
}
gone() { ! kill -0 -- "-$1" 2>/dev/null; }
proc_birth() { sed 's/.*) //' "/proc/$1/stat" 2>/dev/null | awk '{print $20}'; }
kill_group() { # captured pgid + birth [grace s, default 20]: TERM, wait, KILL - only when the leader's birth still matches
  local g=$1 birth=$2 grace=${3:-20} i
  gone "$g" && return 0
  [ -n "$birth" ] || { log "REFUSED: live group $g has no captured birth"; return 1; }
  [ "$(proc_birth "$g")" = "$birth" ] || { log "group leader $g birth changed (pid reused); not signalling"; return 0; }
  kill -TERM -- "-$g" 2>/dev/null
  for i in $(seq "$grace"); do gone "$g" && { log "group $g ended after TERM"; return 0; }; sleep 1 7>&- 8>&-; done
  kill -KILL -- "-$g" 2>/dev/null; sleep 1
  gone "$g" && { log "group $g killed"; return 0; }
  log "REFUSED: group $g survives KILL"; return 1
}
INNERPG=$STATE/$ID.inner.pgid
kill_job() { # ws58 2026-11-02: the launcher's setsid group AND the inner engine's group (region_lock_cli may start the inner
  # engine in a session of its own, out of reach of the launcher-group kill); the inner records "pgid birth" at start
  local r=0 g b grace=${1:-20}
  kill_group "$CUR" "$CUR_BIRTH" "$grace" || r=1
  if [ -f "$INNERPG" ]; then
    read -r g b < "$INNERPG" || true
    if [[ ${g:-} =~ ^[0-9]+$ ]] && [ "$g" != "$CUR" ]; then kill_group "$g" "$b" "$grace" || r=1; fi
    [ $r = 1 ] || rm -f "$INNERPG"
  fi
  return $r
}
kill_pidfile() { # pids the job registered (fl_register_pid); TERM then KILL; never a pid that is already gone
  local p
  [ -f "$PIDFILE" ] || return 0
  while read -r p _; do
    [[ $p =~ ^[0-9]+$ ]] || continue
    ps -o pid= -p "$p" >/dev/null 2>&1 || continue
    kill -TERM "$p" 2>/dev/null; sleep 2; ps -o pid= -p "$p" >/dev/null 2>&1 && kill -KILL "$p" 2>/dev/null
  done < "$PIDFILE"
  return 0
}
is_complete() { [ -n "$COMPLETE_CMD" ] || return 1; ( cd "$WORKDIR" && bash -c "$COMPLETE_CMD" ) >/dev/null 2>&1; }
mark_complete() {
  kill_pidfile || { log "REFUSED: completion while native child unverified"; return 70; }
  mkdir -p "$GRANTS"
  write_ended 0 complete || return 70
  printf 'complete time=%s id=%s\n' "$(ts)" "$ID" > "$COMPLETE"
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
  export FILLER_END_ISO=$(date -u -d "@$END" +%FT%TZ) FILLER_ID=$ID FILLER_DEADLINE=$(( END - 90 )) FILLER_STOPFILE=$STOPFILE FILLER_PORTS=$PORTS FILLER_PIDFILE=$PIDFILE FILLER_LIB=$HERE/filler_lib.sh
  mkdir -p "$STATE"; _pg=$(ps -o pgid= -p $$ | tr -d ' '); printf '%s %s\n' "$_pg" "$(proc_birth "$_pg")" > "$INNERPG"
  cd "$WORKDIR" || exit 3
  # No `timeout` wrapper: it moves the job into its own process group, out of reach of the launcher's captured-group kill.
  # The hard end is enforced by the launcher (TERM, wait, KILL on the whole setsid group); the job also honours FILLER_DEADLINE.
  taskset -c "$FILLER_CPUS" bash -c "$JOBCMD" 8>&- 9>&-
  rc=$?; echo "job rc=$rc"
  exit $rc
fi


# ------------------------------------------------------------------ launcher (poll loop; shell only)
mkdir -p "$GRANTS"
exec 7>"$LAUNCHER_LOCK"
flock -n 7 || { log "another launcher for $ID already running; exiting"; exit 0; }
CUR=""; CUR_BIRTH=""; STARTED_ONE=0
sleep_poll() { sleep "$1" 7>&- 8>&- & SLP=$!; wait $SLP 2>/dev/null; }
on_term() {
  log "launcher signalled"
  if [ -n "$CUR" ]; then
    kill_job && kill_pidfile || { log "REFUSED: signal cleanup incomplete; grant retained"; exit 70; }
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
  if ! parse_regions "$regions"; then write_ended 2 "regions-unusable-for-$ID($CLASS):$regions"; return; fi
  if [ $(( e - now )) -lt "$MINWIN" ]; then write_ended 3 "window-$(( e - now ))s-below-min-$MINWIN"; return; fi
  # 2026-11-03 session review item 7: a STOP file at grant time is RETRYABLE - the grant is released and the id stays
  # usable (the allocator shows the row as `held` and does not re-grant it while the STOP file exists); it used to write
  # .ended, which burned the id and left the poller spinning on "REFUSED: .ended exists" (85k lines).
  # 2026-11-05 (keeper-friction-review F4/refinement 4): that silent release was re-granted every tick (1,344 grants in
  # 16 h of one row whose stop path the keeper could not resolve). A STOP at grant time is now terminal and recorded.
  if [ -e "$STOPFILE" ]; then write_ended 75 stopped-before-start; log "STOP present before start ($STOPFILE): terminal; publish a new row id to run it"; return 21; fi
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
         elif [ -z "$gq" ] || [ "$gq" = none ]; then rlargs=()
         else rlargs=(--gpu-quiet "$gq"); [ -n "$cc" ] && rlargs=(--cpu-list "$cc" --gpu-quiet "$gq"); fi;;
    cpu+gpu) rlargs=(--cpu-list "${cc:-$CPUS}"); [ -n "$gq" ] && [ "$gq" != none ] && rlargs+=(--gpu-quiet "$gq");;
  esac
  # GRANT_CPUS (ws58 2026-11-02): a gpu-class grant locks ONLY the cpus the grant names (its cpus= field, else its
  # regions list): primary cpus (0-95) as an exact --cpu-list claim, SMT-sibling host threads (184-191) unlocked and
  # pinned by the inner taskset (FILLER_CPUS). --claim-cpus / --no-fold-siblings no longer widen a gpu claim: the
  # allocator booked gpu-quiet + exactly these cpus, so the GPU runs beside a whole-q3 / host row.
  local gcl="" gprim=""
  if [ "$CLASS" = gpu ]; then
    gcl=$(sed -n 's/.* cpus=\([^ ]*\).*/\1/p' "$GRANT" | tr -d '\n'); valid_list "$gcl" || gcl=$CPUS
    gprim=$(expand "$gcl" | awk '$1<96' | sort -un | paste -sd, -)
    case $gq in exclusive|shared) rlargs=(--gpu-quiet "$gq");; *) rlargs=();; esac   # opt-in only (2026-11-03 item 6)
    [ -n "$gprim" ] && rlargs=(--cpu-list "$gprim" --no-fold-siblings "${rlargs[@]}")
  fi
  # --no-fold-siblings (2026-10-22): a GPU job's host threads 184-191 must not fold into a whole-q3 claim (MI210 sat idle behind a q3 build)
  # filler_run6 (2026-10-22): region-lock REFUSES --no-fold-siblings for an SMT-only list ("maps to no regions"), so for a
  # GPU job --no-fold-siblings means: claim gpu-quiet ONLY (no CPU region) and let the job taskset its host threads (184-191).
  if [ $NOFOLD = 1 ] && [ "$CLASS" != gpu ]; then   # GRANT_CPUS: a gpu claim is the grant's cpus (above)
    if [ "$CLASS" = gpu ]; then
      _n=(); _skip=0; for a in "${rlargs[@]}"; do if [ $_skip = 1 ]; then _skip=0; continue; fi; [ "$a" = --cpu-list ] && { _skip=1; continue; }; _n+=("$a"); done
      rlargs=("${_n[@]}")   # 2026-11-03 item 6: no implicit --gpu-quiet shared
    elif [[ " ${rlargs[*]} " == *" --cpu-list "* ]]; then rlargs+=(--no-fold-siblings); fi
  fi
  if [ "${SMOKE_NOLOCK:-0}" = 1 ]; then
    if [ "$CLASS" = gpu ]; then rlargs=(--gpu-quiet shared); else rlargs=(); fi
  fi
  snapshot_overrun "$regions"
  if [ -n "${FILLER_STUB_CMD:-}" ]; then
    setsid bash -c "$FILLER_STUB_CMD" 7>&- &
  elif [ "${SMOKE_NOLOCK:-0}" = 1 ] && [ ${#rlargs[@]} = 0 ]; then
    setsid taskset -c "${CLAIM_CPUS:-$CPUS}" /bin/bash "$SELF" --inner --id "$ID" --class "$CLASS" --cmd "$JOBCMD" --min-window "$MINWIN" --stop "$STOPFILE" \
        --port "$PORTS" --workdir "$WORKDIR" --gpu-threads "$GPUTHR" 7>&- &
  elif [ $SELFCLAIM = 1 ] || [ ${#rlargs[@]} = 0 ]; then   # nothing to lock (gpu row, gpu-quiet none, host threads only): no region-lock call
    setsid /bin/bash "$SELF" --inner --id "$ID" --class "$CLASS" --cmd "$JOBCMD" --min-window "$MINWIN" --stop "$STOPFILE" \
        --port "$PORTS" --workdir "$WORKDIR" --gpu-threads "$GPUTHR" 7>&- &
  else
    local rl_to=$(( e - $(date -u +%s) )); [ "$rl_to" -ge 1 ] || rl_to=1   # region-lock: 0 = wait forever; never that
    setsid "$RL" run "${rlargs[@]}" --role "$rl_role" --timeout-s "$rl_to" --tag "filler-$ID" -- \
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
    if [ "$DRYRUN" != 1 ] && [ -e "$STOPFILE" ]; then
      reason=stopped; log "STOP seen mid-run ($STOPFILE): TERM job group(s), KILL after ${STOP_GRACE}s"
      kill_job "$STOP_GRACE" || reason=cleanup-failed; break; fi
    if [ "$(date -u +%s)" -ge "$e" ]; then reason=hard-end; kill_job || reason=cleanup-failed; break; fi
    if [ "$(df -BG --output=avail /mnt/raid0 2>/dev/null | tail -1 | tr -dc 0-9)" -lt "${FILLER_DISK_FLOOR_GIB:-150}" ] 2>/dev/null; then
      reason=disk-floor; kill_job || reason=cleanup-failed; break; fi
    sleep 3 7>&- 8>&-
  done
  wait "$CUR" 2>/dev/null; rc=$?
  case $reason in hard-end|disk-floor|stopped) rc=75;; esac
  local cleanup_bad=0
  kill_job || cleanup_bad=1
  kill_pidfile || cleanup_bad=1
  CUR=""
  CUR_BIRTH=""
  exec 8>&-
  if [ "$cleanup_bad" = 1 ] || [ "$reason" = cleanup-failed ]; then
    log "REFUSED: native cleanup incomplete; grant retained, no .ended or .complete"
    notify_end 70 cleanup-failed
    STARTED_ONE=1; return 70
  fi
  if is_complete; then mark_complete || return 70; return 20; fi
  if [ "$rc" -eq 0 ]; then rc=75; reason=partial-native-incomplete; fi
  [ "$rc" -eq 75 ] || reason="job-rc-$rc:$reason"
  write_ended "$rc" "$reason"
  STARTED_ONE=1
  [ "$reason" = stopped ] && return 21
  return 0
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
log "launcher up pid=$$ class=$CLASS poll=${POLL}s grants=$GRANTS stop=$STOPFILE minwin=${MINWIN}s ports=${PORTS:-none}${DRYRUN:+ dryrun=$DRYRUN}"
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
  [ "$rc" = 21 ] && { log "row stopped (.ended reason=stopped*); poller exiting"; exit 0; }
  # 2026-11-03: rc=66 means the id is terminal (.ended exists); the grant can never be consumed - release it and exit
  # instead of re-reading it every poll (r3 poller: 85,235 REFUSED lines, ~10% of a core, grant shown as held).
  [ "$rc" = 66 ] && { rm -f "$GRANT"; log "terminal id (.ended exists): grant released, poller exiting; fix: publish a new row id"; exit 66; }
  if [ "${STARTED_ONE:-0}" = 1 ] && [ $REPEAT = 0 ]; then log "one window done; exiting (no --repeat)"; exit 0; fi
  if [ $rc = 9 ]; then w=$GRANT_WAIT; [ "$w" -gt "$POLL" ] && w=$POLL; sleep_poll "$w"; fi
done
