#!/bin/bash
# filler_run2.sh = filler_run.sh + exclusive-GPU mode + precondition gate (2026-10-21, v11-drivers). filler_run.sh is left untouched (it is RUNNING).
#   NEW  --gpu-quiet shared|exclusive|none  claim mode of the region-lock wrapper. Defaults reproduce filler_run.sh exactly (cpu: none, gpu/cpu+gpu: shared).
#   NEW  --role ROLE                        region-lock --role (default build; timing items use bench).
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
ID=""; CLASS=""; JOBCMD=""; MINWIN=0; STOPFILE=""; COMPLETE_CMD=""; PORTS=""; SCHED_PORTS=""; EXCL_LOCK=""; GPUTHR="184-191"; WORKDIR=/workspace; SELFCLAIM=0; GPUQ=""; ROLE=""; CLAIM_CPUS=""; PRECOND_CMD=""
if [ "${1:-}" = "--inner" ]; then INNER=1; shift; else INNER=0; fi
while [ $# -gt 0 ]; do
  case $1 in
    --id) ID=$2; shift 2;; --class) CLASS=$2; shift 2;; --cmd) JOBCMD=$2; shift 2;; --min-window) MINWIN=$2; shift 2;;
    --stop) STOPFILE=$2; shift 2;; --complete-cmd) COMPLETE_CMD=$2; shift 2;; --port) PORTS=$2; shift 2;;
    --sched-port) SCHED_PORTS=$2; shift 2;; --excl-lock) EXCL_LOCK=$2; shift 2;; --gpu-threads) GPUTHR=$2; shift 2;; --self-claim) SELFCLAIM=1; shift;;
    --workdir) WORKDIR=$2; shift 2;;
    --gpu-quiet) GPUQ=$2; shift 2;; --role) ROLE=$2; shift 2;; --claim-cpus) CLAIM_CPUS=$2; shift 2;; --precond-cmd) PRECOND_CMD=$2; shift 2;; *) echo "unknown arg $1" >&2; exit 64;;
  esac
done
[ -n "$ID" ] && [ -n "$JOBCMD" ] && [ -n "$STOPFILE" ] || { echo "need --id --cmd --stop" >&2; exit 64; }
case $CLASS in cpu|gpu|cpu+gpu) ;; *) echo "bad --class" >&2; exit 64;; esac
case "$GPUQ" in ""|shared|exclusive|none) ;; *) echo "bad --gpu-quiet (shared|exclusive|none)" >&2; exit 64;; esac
[ "$GPUQ" = exclusive ] && [ "$CLASS" = cpu ] && { echo "--gpu-quiet exclusive needs a gpu or cpu+gpu class" >&2; exit 64; }
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
listening() { ss -ltn "sport = :$1" 2>/dev/null | grep -q LISTEN; }
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

write_ended() { # rc reason
  mkdir -p "$GRANTS"
  printf 'rc=%s time=%s reason=%s\n' "$1" "$(ts)" "$2" > "$ENDED.tmp" && mv -f "$ENDED.tmp" "$ENDED"
  rm -f "$GRANT"
  log "ended rc=$1 reason=$2 (grant deleted)"
}
gone() { ! kill -0 -- "-$1" 2>/dev/null; }
kill_group() { # pgid : TERM, wait, KILL, verify
  local g=$1 i
  gone "$g" && return 0
  kill -TERM -- "-$g" 2>/dev/null
  for i in $(seq 1 15); do sleep 1; gone "$g" && break; done
  gone "$g" || { kill -KILL -- "-$g" 2>/dev/null; sleep 2; }
  if gone "$g"; then log "group $g dead (verified)"; return 0; else log "STILL ALIVE group $g"; return 1; fi
}
kill_pidfile() { # PIDs the job registered itself; only if cmdline still carries one of our ports (or no ports declared)
  local p ok=0 bad=0
  [ -s "$PIDFILE" ] || return 0
  while read -r p; do
    [ -n "$p" ] || continue
    kill -0 "$p" 2>/dev/null || continue
    if [ -n "$PORTS" ]; then
      local hit=0 q; for q in ${PORTS//,/ }; do tr '\0' ' ' < /proc/$p/cmdline 2>/dev/null | grep -q -- "--port $q" && hit=1; done
      [ $hit = 1 ] || { log "pid $p no longer ours; not touching"; continue; }
    fi
    kill "$p" 2>/dev/null; sleep 5; kill -0 "$p" 2>/dev/null && { kill -9 "$p" 2>/dev/null; sleep 2; }
    kill -0 "$p" 2>/dev/null && { log "STILL ALIVE pid $p"; bad=1; } || log "pid $p dead (verified)"
  done < "$PIDFILE"
  return $bad
}
is_complete() { [ -n "$COMPLETE_CMD" ] || return 1; ( cd "$WORKDIR" && bash -c "$COMPLETE_CMD" ) >/dev/null 2>&1; }
mark_complete() {
  mkdir -p "$GRANTS"
  printf 'complete time=%s id=%s\n' "$(ts)" "$ID" > "$COMPLETE"
  [ -f "$FILLERS_MD" ] && sed -i "/^| $ID |/ s/ARMED/COMPLETE/" "$FILLERS_MD"
  write_ended 0 complete
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
  cd "$WORKDIR" || exit 3
  # No `timeout` wrapper: it moves the job into its own process group, out of reach of the launcher's captured-group kill.
  # The hard end is enforced by the launcher (TERM, wait, KILL on the whole setsid group); the job also honours FILLER_DEADLINE.
  bash -c "$JOBCMD" 8>&- 9>&-
  rc=$?; echo "job rc=$rc"
  exit $rc
fi

# ------------------------------------------------------------------ launcher (poll loop; shell only)
mkdir -p "$GRANTS"
exec 7>"$LAUNCHER_LOCK"
flock -n 7 || { log "another launcher for $ID already running; exiting"; exit 0; }
CUR=""
sleep_poll() { sleep "$1" & SLP=$!; wait $SLP 2>/dev/null; }
on_term() {
  log "launcher signalled"
  [ -n "$CUR" ] && { kill_group "$CUR"; kill_pidfile; }
  [ -e "$GRANT" ] && write_ended 143 launcher-signalled
  exit 143
}
trap on_term TERM INT

run_one() {
  local regions start end s e now rc reason p
  regions=$(sed -n 's/.*regions=\([^ ]*\).*/\1/p' "$GRANT" | tr -d '\n')
  start=$(sed -n 's/.*start=\([^ ]*\).*/\1/p' "$GRANT" | tr -d '\n')
  end=$(sed -n 's/.*end=\([^ ]*\).*/\1/p' "$GRANT" | tr -d '\n')
  s=$(epoch "$start"); e=$(epoch "$end")
  if [ -z "$regions" ] || [ -z "$s" ] || [ -z "$e" ] || [ "$s" -ge "$e" ]; then write_ended 2 "malformed-grant"; return; fi
  now=$(date -u +%s)
  if [ "$now" -ge "$e" ]; then write_ended 3 "grant-expired-unrun"; return; fi
  if [ "$now" -lt "$s" ]; then GRANT_WAIT=$(( s - now )); return 9; fi
  rm -f "$ENDED"
  if ! parse_regions "$regions"; then write_ended 2 "regions-unusable-for-$ID($CLASS):$regions"; return; fi
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
  if is_complete; then exec 8>&-; mark_complete; return 20; fi
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
  if [ -n "${FILLER_STUB_CMD:-}" ]; then
    setsid bash -c "$FILLER_STUB_CMD" &
  elif [ $SELFCLAIM = 1 ]; then
    setsid /bin/bash "$SELF" --inner --id "$ID" --class "$CLASS" --cmd "$JOBCMD" --min-window "$MINWIN" --stop "$STOPFILE" \
        --port "$PORTS" --workdir "$WORKDIR" --gpu-threads "$GPUTHR" &
  else
    setsid "$RL" run "${rlargs[@]}" --role "$rl_role" --timeout-s $(( e - $(date -u +%s) )) --tag "filler-$ID" -- \
      /bin/bash "$SELF" --inner --id "$ID" --class "$CLASS" --cmd "$JOBCMD" --min-window "$MINWIN" --stop "$STOPFILE" \
        --port "$PORTS" --workdir "$WORKDIR" --gpu-threads "$GPUTHR" &
  fi
  CUR=$!
  [ "$(ps -o pgid= -p $CUR | tr -d ' ')" = "$CUR" ] || log "WARN: $CUR is not a group leader"
  reason=exited
  while kill -0 "$CUR" 2>/dev/null; do
    if [ "$(date -u +%s)" -ge "$e" ]; then reason=hard-end; kill_group "$CUR"; break; fi
    sleep 3
  done
  wait "$CUR" 2>/dev/null; rc=$?
  [ $reason = hard-end ] && rc=124
  kill_group "$CUR"; kill_pidfile
  CUR=""
  exec 8>&-
  if is_complete; then mark_complete; return 20; fi
  write_ended $rc "$reason"
}

log "launcher up pid=$$ class=$CLASS poll=${POLL}s grants=$GRANTS stop=$STOPFILE minwin=${MINWIN}s ports=${PORTS:-none}"
is_complete && { mark_complete; exit 0; }
while :; do
  [ -e "$COMPLETE" ] && { log "complete marker present; exiting"; exit 0; }
  if [ ! -e "$GRANT" ]; then sleep_poll "$POLL"; continue; fi
  GRANT_WAIT=""
  run_one; rc=$?
  [ $rc = 20 ] && exit 0
  if [ $rc = 9 ]; then w=$GRANT_WAIT; [ "$w" -gt "$POLL" ] && w=$POLL; sleep_poll "$w"; fi
done
