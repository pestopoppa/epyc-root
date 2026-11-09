#!/bin/bash
# churn_up.sh — idempotent bring-up of the backlog-churn pipeline (ws58, 2026-11-01).
#
# Operator goal: after a host reboot the churn pipeline comes back from FORMALIZED, PERSISTED rules and code; nothing
# depends on any session's memory. This script is the one command. Runbook: docs/guides/agent-workflows/backlog-churn-runbook.md
#
#   churn_up.sh            install git copies -> compute-flags, clean reboot residue, start what is not running,
#                          recreate the tmux session, print the manual steps (start Claude ws58 + codex-gen).
#   churn_up.sh --dry-run  same, printing every action instead of doing it (safe on a live system).
#   churn_up.sh --status   read-only report: per component pid / alive / sha-vs-git; lanes; grants; sessions; tmux.
#   churn_up.sh --stop     the 2026-11-02 operator stop order: (1) dispatcher, (2) keeper watchdog(s) THEN keeper (the
#                          watchdog restarts the keeper), (3) revoke open grants by MOVING them to grants-revoked-<ts>/,
#                          (4) armed launchers by their recorded pid (dryrun/*/ARMED.json|RUNNING.json, lane-*.queue),
#                          (5) the remaining zero-token loops. TERM, wait 10 s, KILL, verify with ps. `--stop --dry-run`
#                          prints the plan only. It does NOT stop the disk janitor (disk hygiene is not inference).
#   churn_up.sh --janitor=start|stop|status|dry-run   the disk janitor only (disk_janitor.sh: keeper --reap-now every
#                          30 min + trash-sweep --older-than 1 hourly; log disk-janitor.log). A normal bring-up starts it too.
# Start order (live): install -> residue -> watchdog -> keeper (started by the watchdog, verified here) -> dispatcher ->
# backlog-gen -> flow-scoreboard -> disk-trend -> filing-watch. A component already running (pidfile pid, or ANY pid whose
# argv holds its exact installed path) is never started twice.
#
# Rules it obeys (do not weaken): liveness is `ps -o pid= -p <pid>` + argv match, never a process-name search or kill; a running
# .sh is never edited in place (installs go through a temp file + mv, so a running bash keeps its old inode) and never
# restarted; starts happen only when the pidfile pid is dead or not the expected program; no tmux keys are ever sent to
# a pane; nothing outside /mnt/raid0/llm is touched. Exit 0 on success, 1 on a failed check, 2 on usage.
set -uo pipefail

F=${CHURN_FLAGS:-/mnt/raid0/llm/tmp/compute-flags}
REPO=${CHURN_REPO:-$(cd "$(dirname "$(readlink -f "$0")")/../../.." && pwd)}
CO=$REPO/scripts/coordination
CH=$CO/churn
RF=$CO/rowflow
RL=/mnt/raid0/llm/epyc-orchestrator/scripts/region-lock
TMUX_SESSION=${CHURN_TMUX_SESSION:-agent}
TMUX_WINDOWS="claude codex-gen"
MODE=live
STOP=0
JAN=""
for a in "$@"; do case "$a" in
  --dry-run) MODE=dry;;
  --status) MODE=status;;
  --stop) STOP=1;;
  --janitor=start|--janitor=stop|--janitor=status|--janitor=dry-run) JAN=${a#--janitor=};;
  -h|--help) sed -n 2,28p "$0"; exit 0;;
  *) echo "usage: churn_up.sh [--dry-run|--status|--stop [--dry-run]|--janitor=start|stop|status|dry-run]" >&2; exit 2;;
esac; done
[ $MODE = status ] && [ $STOP = 1 ] && { echo "usage: --status and --stop are exclusive" >&2; exit 2; }
KEEPER=ws58-calendar-keeper-v13.sh   # the version churn_up installs and writes into ws58-calendar-keeper.current
RC=0
TS=$(date -u +%Y%m%dT%H%M%SZ)
LOG=$F/churn-up.log

say()  { printf '%s\n' "$*"; }
act()  { if [ $MODE = dry ]; then say "[dry-run] $*"; else say "[do] $*"; printf '%s %s\n' "$(date -u +%FT%TZ)" "$*" >> "$LOG"; fi; }
warn() { say "[WARN] $*"; }
fail() { say "[FAIL] $*"; RC=1; }
alive() { [ -n "${1:-}" ] && [[ "$1" =~ ^[0-9]+$ ]] && ps -o pid= -p "$1" >/dev/null 2>&1; }
# pid alive AND its argv names the program (guards against pid reuse after a reboot)
is_proc() { alive "$1" && ps -o args= -p "$1" 2>/dev/null | grep -F -- "$2" >/dev/null; }
pid_of() { cat "$1" 2>/dev/null | tr -d ' \n'; }
sha() { sha256sum "$1" 2>/dev/null | cut -c1-16; }
start_bg() {  # start_bg <pidfile> <cwd> <cmd...>  (setsid, detached; pidfile written by us)
  local pf=$1 cwd=$2; shift 2
  act "START $* (cwd $cwd, pidfile $pf)"
  [ $MODE = dry ] && return 0
  local p
  (cd "$cwd" && setsid "$@" </dev/null >/dev/null 2>&1 & echo $! > "$pf.tmp.$$") || { fail "start failed: $*"; return 1; }
  p=$(cat "$pf.tmp.$$"); rm -f "$pf.tmp.$$"
  sleep 1
  alive "$p" && mv -f "$pf.tmp.$$" "$pf" 2>/dev/null; echo "$p" > "$pf"
  alive "$p" || { fail "started $* but pid $p died at once (see its log)"; return 1; }
  say "      pid $p"
}

# ---------------------------------------------------------------- 1. install git copies
# dst-relative-to-F  src-absolute
INSTALL=(
  "$KEEPER    $RF/$KEEPER"
  "ws58-keeper-watchdog.sh        $CH/ws58-keeper-watchdog.sh"
  "ws58-disk-trend.sh             $CH/ws58-disk-trend.sh"
  "disk_janitor.sh                $CH/disk_janitor.sh"
  "ws58-backlog-gen-v1.sh         $CH/ws58-backlog-gen-v1.sh"
  "ws58-flow-scoreboard-v1.sh     $CH/ws58-flow-scoreboard-v1.sh"
  "GOAL-codex-gen.md              $CH/GOAL-codex-gen.md"
  "bin/backlog_gen.py             $CO/backlog_gen.py"
  "bin/handoff_sessions.py        $CO/handoff_sessions.py"
  "bin/flow_scoreboard.py         $CO/flow_scoreboard.py"
  "bin/worktree_footprint.py      $CO/worktree_footprint.py"
  "bin/index_regen.py             $CO/index_regen.py"
  "bin/serialized_push.py         $CO/serialized_push.py"
  "bin/flip_checkbox.py           $CO/flip_checkbox.py"
  "bin/keeper_qual_memo.py        $CO/keeper_qual_memo.py"
  "bin/churn/wrapup.py            $CH/wrapup.py"
  "bin/churn/file_result.py       $CH/file_result.py"
  "bin/churn/filing.py            $CH/filing.py"
  "bin/churn/reclaim_row.py       $CH/reclaim_row.py"
  "bin/churn/typed_classify.py    $CH/typed_classify.py"
  "bin/churn/tokens_per_task.py   $CH/tokens_per_task.py"
  "bin/rowflow/rowflow.py         $RF/rowflow.py"
  "bin/rowflow/filler_run15.sh    $RF/filler_run15.sh"
  "bin/rowflow/filler_lib.sh      $RF/filler_lib.sh"
  "bin/rowflow/grant_ok_launcher.py $RF/grant_ok_launcher.py"
  "bin/rowflow/publish_row.py     $RF/publish_row.py"
  "bin/rowflow/hostutil.py        $RF/hostutil.py"
  "bin/rowflow/notify.py          $RF/notify.py"
  "bin/rowflow/run_direct.py      $RF/run_direct.py"
  "bin/rowflow/run_direct.sh      $RF/run_direct.sh"
)
# RETIRED 2026-11-01 evening (allocator): grant-writer templates, grant_ok*.sh, ram_admit.sh, validate_fillers.py, the legacy
# grant_ok_launcher.py. rowflow.py allocate (keeper v11) is the one actor that writes grants.
# every pid the pipeline records in a pidfile whose argv names <path> (liveness by recorded pid + argv, never by name search)
known_pids_using() {
  local f p out=""
  for f in "$F"/*.pid; do [ -e "$f" ] || continue; p=$(pid_of "$f"); alive "$p" && ps -o args= -p "$p" 2>/dev/null | grep -F -- "$1" >/dev/null && out="$out $p"; done
  echo "$out"
}
install_one() {
  local rel=$1 src=$2 dst=$F/$1
  [ -f "$src" ] || { fail "missing git source $src"; return; }
  if [ -f "$dst" ] && [ "$(sha "$dst")" = "$(sha "$src")" ]; then return; fi
  if [ -f "$dst" ]; then
    local run; run=$(known_pids_using "$dst")   # pidfile pids only: never a process-name search
    [ -n "$run" ] && warn "$rel: running pid(s)$run use the OLD copy; the new file is installed beside it (mv), restart at a safe boundary"
    act "BACKUP $dst -> $F/ws58-keeper-state/$(basename "$rel").bak-$TS"
    [ $MODE = dry ] || { mkdir -p "$F/ws58-keeper-state"; cp -p "$dst" "$F/ws58-keeper-state/$(basename "$rel").bak-$TS"; }
  fi
  act "INSTALL $src -> $dst"
  [ $MODE = dry ] && return
  mkdir -p "$(dirname "$dst")"
  cp -p "$src" "$dst.churn-tmp.$$" && mv -f "$dst.churn-tmp.$$" "$dst" || { fail "install $rel"; return; }
  cmp -s "$src" "$dst" || fail "install $rel: cmp differs after mv"
}
do_install() {
  say "== install (git -> $F)"
  local line
  for line in "${INSTALL[@]}"; do install_one $line; done
  local cur; cur=$(cat "$F/ws58-calendar-keeper.current" 2>/dev/null)
  if [ "$cur" != "$KEEPER" ]; then
    act "SET ws58-calendar-keeper.current = $KEEPER (was '${cur:-}')"
    [ $MODE = dry ] || { echo "$KEEPER" > "$F/ws58-calendar-keeper.current.tmp.$$" && mv -f "$F/ws58-calendar-keeper.current.tmp.$$" "$F/ws58-calendar-keeper.current"; }
  fi
  [ $MODE = dry ] || mkdir -p "$F/grants" "$F/ready" "$F/dryrun" "$F/ws58-keeper-state" "$F/filing-done" "$F/briefs" "$F/handoff-sessions"
}
status_install() {
  say "== install state (installed sha16 vs git sha16)"
  local line rel src dst a b
  for line in "${INSTALL[@]}"; do set -- $line; rel=$1; src=$2; dst=$F/$rel
    a=$(sha "$dst"); b=$(sha "$src")
    if [ -z "$a" ]; then printf '  %-36s MISSING (git %s)\n' "$rel" "${b:-MISSING}"; RC=1
    elif [ "$a" = "$b" ]; then printf '  %-36s ok %s\n' "$rel" "$a"
    else printf '  %-36s DIFFERS installed=%s git=%s\n' "$rel" "$a" "${b:-MISSING}"; RC=1; fi
  done
  printf '  %-36s %s\n' "ws58-calendar-keeper.current" "$(cat "$F/ws58-calendar-keeper.current" 2>/dev/null || echo MISSING)"
}

# ---------------------------------------------------------------- 2. reboot residue
# A grant whose launcher/poller pid is gone blocks its lane forever (writers treat an open .grant as busy). Move it and
# its stamp aside (never delete) so rowflow re-arms the row. Pid sources: dryrun/<id>/ARMED.json, else the queue lines.
grant_pid() {
  local id=$1 p
  p=$(python3 -I -c 'import json,sys
try: print(json.load(open(sys.argv[1])).get("pid") or "")
except Exception: print("")' "$F/dryrun/$id/ARMED.json" 2>/dev/null)
  [ -n "$p" ] || p=$(python3 -I -c 'import json,sys
try: print(json.load(open(sys.argv[1])).get("pid") or "")
except Exception: print("")' "$F/dryrun/$id/RUNNING.json" 2>/dev/null)   # a keeper dry run holds a real short grant
  [ -n "$p" ] || p=$(cat "$F"/*.queue 2>/dev/null | awk -F'|' -v id="$id" '$1==id{print $2}' | tail -1)
  echo "$p"
}
clean_grants() {
  say "== reboot residue: open grants whose pid is gone"
  local g id p n=0 dst=$F/grants/stale-reboot-$TS
  for g in "$F"/grants/*.grant; do
    [ -e "$g" ] || continue
    id=$(basename "$g" .grant)
    [ -e "$F/grants/$id.ended" ] || [ -e "$F/grants/$id.complete" ] && continue
    p=$(grant_pid "$id")
    if alive "$p"; then say "  $id: pid $p alive (kept)"; continue; fi
    n=$((n+1))
    act "MOVE stale grant $id (pid ${p:-none} dead) + stamps -> $dst/"
    [ $MODE = dry ] && continue
    mkdir -p "$dst"; mv -f "$g" "$dst/"; for s in "$F/.wsq-granted-$id" "$F/.wsg-granted-$id"; do [ -e "$s" ] && mv -f "$s" "$dst/"; done
  done
  [ $n = 0 ] && say "  none"
}
# region-lock claims are flock+pid records; the library drops dead-pid entries on every read, so a reboot clears them.
show_lanes() { say "== lanes (region-lock status)"; "$RL" status 2>&1 | sed -n "1,8s/^/  /p"; }
# Registry sessions recorded as live whose pid is gone (or reused by something that is not an engine). Only when the
# dispatcher is NOT running (it owns the file while it runs and handles its own dead children).
clean_registry() {
  say "== reboot residue: handoff-sessions.json live entries"
  if is_proc "$(pid_of "$F/handoff-sessions.dispatcher.pid")" handoff_sessions.py; then say "  dispatcher is running; it owns the registry (skipped)"; return; fi
  [ -f "$F/handoff-sessions.json" ] || { say "  no registry"; return; }
  local out; out=$(python3 -I - "$F/handoff-sessions.json" "$MODE" "$REPO" <<'PY'
import json, os, subprocess, sys
p, mode, repo = sys.argv[1:4]
reg = json.load(open(p)); changed = 0
def engine_alive(pid):
    try: argv = open(f"/proc/{pid}/cmdline", "rb").read().replace(b"\0", b" ").decode(errors="replace")
    except OSError: return False
    return any(k in argv for k in ("codex", "claude", "opencode"))
def landed(sha):
    if not sha: return False
    return subprocess.run(["git", "-C", repo, "merge-base", "--is-ancestor", sha, "origin/main"], capture_output=True).returncode == 0
for slug, e in (reg.get("sessions") or {}).items():
    pid = e.get("pid")
    if not pid: continue
    if engine_alive(pid): print(f"  {slug}: pid {pid} is a live engine (kept)"); continue
    new = "suspended" if landed(e.get("last_wrapup")) else "unpushed"
    print(f"  {slug}: pid {pid} gone -> pid=null status={new} (was {e.get('status')})"); changed += 1
    e["pid"] = None; e["status"] = new; e["pending_event"] = None
if changed and mode == "live":
    tmp = p + ".churn-tmp"; json.dump(reg, open(tmp, "w"), indent=1, sort_keys=True); os.replace(tmp, p); print(f"  wrote {changed} change(s)")
elif changed: print(f"  [dry-run] would write {changed} change(s)")
else: print("  clean")
PY
); say "$out"
}

# ---------------------------------------------------------------- 3. legacy grant writers (retired 2026-11-01 evening)
# The allocator (rowflow.py allocate, keeper v11) is the only grant writer. A live legacy writer beside it would double-book:
# report it (never kill it here: the owner stops it by captured pid at a safe boundary).
legacy_writers() { local f p; for f in "$F"/grant-*.pid; do [ -e "$f" ] || continue; p=$(pid_of "$f"); is_proc "$p" "$(basename "$f" .pid).sh" && echo "$(basename "$f" .pid) pid $p"; done; }
check_legacy_writers() {
  say "== legacy grant writers (must be none: the allocator writes grants)"
  local w n=0; while read -r w; do [ -n "$w" ] || continue; n=1; fail "legacy writer alive: $w (stop it by its pid at a safe boundary)"; done < <(legacy_writers)
  [ $n = 0 ] && say "  none"
}

# ---------------------------------------------------------------- 4. loops
# name | pidfile | argv marker | cwd | command | exact installed path (duplicate key: any pid with this argv element)
# ORDER IS THE START ORDER (the keeper is started by the watchdog between watchdog and dispatcher; see ensure_loops).
LOOPS=(
  "watchdog|ws58-keeper-watchdog.pid|ws58-keeper-watchdog.sh|$F|bash $F/ws58-keeper-watchdog.sh|$F/ws58-keeper-watchdog.sh"
  "dispatcher|handoff-sessions.dispatcher.pid|handoff_sessions.py|$F/bin|python3 -I $F/bin/handoff_sessions.py dispatch --loop --interval 60|$F/bin/handoff_sessions.py"
  "backlog-gen|ws58-backlog-gen.pid|backlog_gen.py|$F|bash $F/ws58-backlog-gen-v1.sh|$F/bin/backlog_gen.py"
  "flow-scoreboard|ws58-flow-scoreboard.pid|ws58-flow-scoreboard-v1.sh|$F|bash $F/ws58-flow-scoreboard-v1.sh|$F/ws58-flow-scoreboard-v1.sh"
  "disk-trend|ws58-disk-trend.pid|ws58-disk-trend.sh|$F|bash $F/ws58-disk-trend.sh|$F/ws58-disk-trend.sh"
  "disk-janitor|disk-janitor.pid|disk_janitor.sh|$F|bash $F/disk_janitor.sh|$F/disk_janitor.sh"
  "filing-watch|ws58-filing-watch.pid|filing_watch.sh|$REPO|env FILING_WATCH_FLAGS_ROOT=$F FILING_WATCH_BUS_ROOT=$REPO/coordination/session-bus bash $REPO/scripts/coordination/filing_watch.sh|$REPO/scripts/coordination/filing_watch.sh"
)
# pids whose argv has an element that IS <path> (or ./<basename> with cwd = dirname <path>). Exact-path match over
# /proc/*/cmdline: never a name pattern, never pgrep. Excludes this script's own pid.
argv_pids() {
  python3 -I - "$1" "$$" <<'PY'
import os, sys
path, me = sys.argv[1], sys.argv[2]
d, b = os.path.dirname(path), os.path.basename(path)
out = []
for pid in os.listdir("/proc"):
    if not pid.isdigit() or pid in (me, str(os.getpid())): continue  # never this script or this probe (its argv holds <path>)
    try:
        argv = open(f"/proc/{pid}/cmdline", "rb").read().split(b"\0")
        argv = [a.decode(errors="replace") for a in argv if a]
    except OSError: continue
    hit = path in argv
    if not hit and f"./{b}" in argv:
        try: hit = os.readlink(f"/proc/{pid}/cwd") == d
        except OSError: pass
    if hit: out.append(pid)
print(" ".join(sorted(out, key=int)))
PY
}
# pidfile pid (if alive with the marker) plus every exact-argv-path pid, deduplicated
component_pids() {  # component_pids <pidfile> <marker> <path>
  local p; p=$(pid_of "$F/$1"); { is_proc "$p" "$2" && echo "$p"; for q in $(argv_pids "$3"); do echo "$q"; done; } | sort -un | tr '\n' ' '
}
wait_keeper() {  # the watchdog starts the keeper on its first pass; verify (do not race it with a second start)
  local i k K; K=$(cat "$F/ws58-calendar-keeper.current" 2>/dev/null)
  if [ $MODE = dry ]; then say "  keeper: [dry-run] the watchdog would start ${K:-<.current missing>} (from .current); churn_up would wait <=30 s for ws58-calendar-keeper.pid"; return; fi
  for i in $(seq 30); do k=$(pid_of "$F/ws58-calendar-keeper.pid"); is_proc "$k" "$K" && { say "  keeper: running pid $k ($K)"; return; }; sleep 1; done
  fail "keeper $K not running 30 s after the watchdog (see ws58-keeper-watchdog.log, ws58-calendar-keeper.log)"
}
ensure_loops() {
  say "== loops (start order: watchdog -> keeper -> dispatcher -> backlog-gen -> flow-scoreboard -> disk-trend -> filing-watch)"
  local l n pf mk cwd cmd path p dup
  for l in "${LOOPS[@]}"; do
    IFS='|' read -r n pf mk cwd cmd path <<< "$l"
    p=$(pid_of "$F/$pf")
    if is_proc "$p" "$mk"; then say "  $n: running pid $p"
    else
      dup=$(argv_pids "$path")
      if [ -n "$dup" ]; then warn "$n: already running as pid(s) $dup (argv holds $path) but pidfile $pf says '${p:-none}': NOT starting a duplicate"
      else [ -n "$p" ] && say "  $n: pidfile pid $p is dead or not $mk"; start_bg "$F/$pf" "$cwd" $cmd; fi
    fi
    [ "$n" = watchdog ] && wait_keeper
  done
  ensure_shadow
}
# rowflow2 shadow (run_shadow.sh writes its own pid to $SHADOW_OUT/shadow.pid). Started from the git copy (it is read-only on
# compute-flags). Idempotent: a live pid (ps + argv, never kill -0) in shadow.pid, or any pid whose argv holds the script, blocks a start.
SHADOW_OUT=${CHURN_SHADOW_OUT:-/mnt/raid0/llm/tmp/rowflow2-shadow}
SHADOW_SH=$CO/rowflow2/run_shadow.sh
ensure_shadow() {
  local p dup; p=$(pid_of "$SHADOW_OUT/shadow.pid")
  if is_proc "$p" run_shadow.sh; then say "  rowflow2-shadow: running pid $p"; return; fi
  dup=$(argv_pids "$SHADOW_SH")
  if [ -n "$dup" ]; then warn "rowflow2-shadow: already running as pid(s) $dup but shadow.pid says '${p:-none}': NOT starting a duplicate"; return; fi
  [ -n "$p" ] && say "  rowflow2-shadow: shadow.pid pid $p is dead or not run_shadow.sh"
  [ $MODE = dry ] || mkdir -p "$SHADOW_OUT"
  start_bg "$SHADOW_OUT/shadow.pid" "$REPO" bash "$SHADOW_SH" --out "$SHADOW_OUT"
}
stop_pid() {  # stop_pid <label> <pid>: TERM, 10 s, KILL, verify with ps
  local label=$1 p=$2 i
  alive "$p" || return 0
  act "STOP $label pid $p ($(ps -o args= -p "$p" 2>/dev/null | cut -c1-120))"
  [ $MODE = dry ] && return 0
  kill -TERM "$p" 2>/dev/null
  for i in $(seq 10); do alive "$p" || break; sleep 1; done
  alive "$p" && { act "KILL $label pid $p (TERM ignored 10 s)"; kill -KILL "$p" 2>/dev/null; sleep 1; }
  alive "$p" && fail "$label pid $p still alive after KILL" || say "      pid $p gone (ps)"
}
loop_field() { local name=$1 l n pf mk cwd cmd path; for l in "${LOOPS[@]}"; do IFS='|' read -r n pf mk cwd cmd path <<< "$l"; [ "$n" = "$name" ] && { echo "$pf|$mk|$path"; return; }; done; }
stop_loop() { local pf mk path p; IFS='|' read -r pf mk path <<< "$(loop_field "$1")"; for p in $(component_pids "$pf" "$mk" "$path"); do stop_pid "$1" "$p"; done; }
do_stop() {
  say "== stop 1/5: dispatcher"; stop_loop dispatcher
  say "== stop 2/5: keeper watchdog(s), then keeper"; stop_loop watchdog
  local k f; k=$(pid_of "$F/ws58-calendar-keeper.pid"); is_proc "$k" ws58-calendar-keeper && stop_pid keeper "$k"
  for f in "$F"/ws58-calendar-keeper*.sh; do for k in $(argv_pids "$f"); do
    [ "$k" = "$(pid_of "$F/ws58-calendar-keeper.pid")" ] && [ $MODE != dry ] && continue
    warn "pid $k has keeper argv $f (job-wrapper subshell or a second keeper main loop): stop it by pid if it is a main loop"; done; done
  say "== stop 3/5: revoke open grants -> $F/grants-revoked-$TS/"
  local g id n=0
  for g in "$F"/grants/*.grant; do [ -e "$g" ] || continue; id=$(basename "$g" .grant)
    { [ -e "$F/grants/$id.ended" ] || [ -e "$F/grants/$id.complete" ]; } && continue
    n=$((n+1)); act "MOVE grant $id -> grants-revoked-$TS/"
    [ $MODE = dry ] && continue
    mkdir -p "$F/grants-revoked-$TS"; mv -f "$g" "$F/grants-revoked-$TS/"
    for s in "$F/.wsq-granted-$id" "$F/.wsg-granted-$id"; do [ -e "$s" ] && mv -f "$s" "$F/grants-revoked-$TS/"; done
  done; [ $n = 0 ] && say "  no open grant"
  say "== stop 4/5: armed launchers by recorded pid (dryrun/*/ARMED.json, RUNNING.json, lane-*.queue)"
  local p n2=0
  for p in $( { for f in "$F"/dryrun/*/ARMED.json "$F"/dryrun/*/RUNNING.json; do [ -e "$f" ] && python3 -I -c 'import json,sys
try: print(json.load(open(sys.argv[1])).get("pid") or "")
except Exception: pass' "$f"; done; cat "$F"/lane-*.queue 2>/dev/null | grep -v '^#' | awk -F'|' '{print $2}'; } | grep -E '^[0-9]+$' | sort -un ); do
    is_proc "$p" filler_run || continue; n2=$((n2+1)); stop_pid launcher "$p"; done
  [ $n2 = 0 ] && say "  no live recorded launcher"
  say "== stop 5/5: remaining zero-token loops"
  for f in backlog-gen flow-scoreboard disk-trend filing-watch; do stop_loop "$f"; done
}
status_loops() {
  say "== loops (pidfile -> pid, alive+argv, started)"
  local l n pf mk cwd cmd path p st d
  for l in "${LOOPS[@]}"; do
    IFS='|' read -r n pf mk cwd cmd path <<< "$l"; p=$(pid_of "$F/$pf")
    if is_proc "$p" "$mk"; then st="UP   since $(ps -o lstart= -p "$p")"
    else d=$(argv_pids "$path"); if [ -n "$d" ]; then st="UP WITHOUT PIDFILE: pid(s) $d hold $path (pidfile '${p:-none}')"; else st="DOWN (pidfile pid '${p:-none}')"; fi; RC=1; fi
    printf '  %-16s %-8s %s\n' "$n" "${p:-none}" "$st"
  done
  p=$(pid_of "$SHADOW_OUT/shadow.pid")
  if is_proc "$p" run_shadow.sh; then printf '  %-16s %-8s UP   since %s\n' rowflow2-shadow "$p" "$(ps -o lstart= -p "$p")"; else printf '  %-16s %-8s DOWN (restart: churn_up.sh)\n' rowflow2-shadow "${p:-none}"; RC=1; fi
  p=$(pid_of "$F/ws58-calendar-keeper.pid")
  if is_proc "$p" "$(cat "$F/ws58-calendar-keeper.current" 2>/dev/null)"; then printf '  %-16s %-8s UP   since %s (%s)\n' keeper "$p" "$(ps -o lstart= -p "$p")" "$(cat "$F/ws58-calendar-keeper.current")"; else printf '  %-16s %-8s DOWN\n' keeper "${p:-none}"; RC=1; fi
  local w; w=$(legacy_writers); if [ -n "$w" ]; then printf '  %-16s %s\n' legacy-writers "ALIVE: $w (double-booking risk; stop by pid)"; RC=1; else printf '  %-16s none\n' legacy-writers; fi
}

# ---------------------------------------------------------------- 5. tmux (windows by name; never send keys)
tmux_renumber() { local v; v=$(tmux show-options -qv -t "$TMUX_SESSION" renumber-windows 2>/dev/null); [ -n "$v" ] || v=$(tmux show-options -gqv renumber-windows 2>/dev/null); echo "${v:-unset}"; }
ensure_tmux() {
  say "== tmux session '$TMUX_SESSION' (windows: $TMUX_WINDOWS; renumber-windows off)"
  command -v tmux >/dev/null || { warn "tmux not installed"; return; }
  local w
  if ! tmux has-session -t "=$TMUX_SESSION" 2>/dev/null; then
    act "tmux new-session -d -s $TMUX_SESSION -n claude -c $REPO"
    [ $MODE = dry ] || tmux new-session -d -s "$TMUX_SESSION" -n claude -c "$REPO" || { fail "tmux new-session"; return; }
  fi
  for w in $TMUX_WINDOWS; do
    if [ $MODE = dry ] && ! tmux has-session -t "=$TMUX_SESSION" 2>/dev/null; then act "tmux new-window -t $TMUX_SESSION -n $w -c $REPO"; continue; fi
    tmux list-windows -t "=$TMUX_SESSION" -F '#{window_name}' 2>/dev/null | grep -x "$w" >/dev/null && { say "  window $w present"; continue; }
    act "tmux new-window -d -t $TMUX_SESSION -n $w -c $REPO"
    [ $MODE = dry ] || tmux new-window -d -t "=$TMUX_SESSION" -n "$w" -c "$REPO"
  done
  if tmux has-session -t "=$TMUX_SESSION" 2>/dev/null && [ "$(tmux_renumber)" != off ]; then
    act "tmux set-option -t $TMUX_SESSION renumber-windows off"; [ $MODE = dry ] || tmux set-option -t "=$TMUX_SESSION" renumber-windows off
  fi
}
status_tmux() {
  say "== tmux"
  if tmux has-session -t "=$TMUX_SESSION" 2>/dev/null; then
    tmux list-windows -t "=$TMUX_SESSION" -F '  window #{window_index} #{window_name}: #{pane_current_command} (pane pid #{pane_pid})'
    say "  renumber-windows (effective): $(tmux_renumber)  [handoff sessions run in windows h-<slug>, opened by the dispatcher]"
    [ "$(tmux_renumber)" = off ] || { say "  [WARN] renumber-windows is not off: window numbers shift when a window closes (address windows by NAME)"; RC=1; }
  else say "  session '$TMUX_SESSION' absent"; RC=1; fi
}

# ---------------------------------------------------------------- 6. state summary + manual steps
status_state() {
  show_lanes
  say "== grants"
  local g n=0 id p
  for g in "$F"/grants/*.grant; do [ -e "$g" ] || continue; id=$(basename "$g" .grant); p=$(grant_pid "$id"); n=$((n+1))
    printf '  %-56s %s pid=%s %s\n' "$id" "$(head -1 "$g" | cut -c1-60)" "${p:-?}" "$(alive "$p" && echo alive || echo DEAD)"; done
  [ $n = 0 ] && say "  no open grant"
  say "== handoff sessions"
  python3 -I - "$F/handoff-sessions.json" <<'PY' 2>/dev/null || say "  no registry"
import json, os, sys
r = json.load(open(sys.argv[1])); S = r.get("sessions") or {}
def alive(p): return bool(p) and os.path.exists(f"/proc/{p}")
live = [s for s, e in S.items() if alive(e.get("pid"))]
print(f"  max_live={r.get('max_live')} auto_start={r.get('auto_start')} engine={r.get('default_engine')} last_pass={r.get('dispatcher',{}).get('last_pass')} paused_until={r.get('paused_until')}")
print(f"  live ({len(live)}): " + ", ".join(f"{s} pid={S[s]['pid']}" for s in live) if live else "  live (0)")
for st in ("suspended", "unpushed", "yield", "done"):
    xs = [s for s, e in S.items() if (e.get("status") == st) or (st == "yield" and e.get("yield") and e.get("status") != "done")]
    if xs: print(f"  {st} ({len(xs)}): " + ", ".join(sorted(xs)))
PY
  say "== backlog freshness"
  local f; for f in BACKLOG-codex-gen.md FLOW-SCOREBOARD.md ws58-calendar-keeper.log; do
    [ -e "$F/$f" ] && printf '  %-28s %s\n' "$f" "$(date -u -r "$F/$f" +%FT%TZ)" || printf '  %-28s MISSING\n' "$f"; done
  say "== disk"; printf '  /mnt/raid0/llm free: %s GiB (floor 150 = filler_run15.sh FILLER_DISK_FLOOR_GIB default)\n' "$(df -B1G --output=avail /mnt/raid0/llm | tail -1 | tr -d ' ')"
}
manual_steps() {
  cat <<EOF
== BY HAND (the only steps churn_up never does: it never starts an agent and never sends keys to a pane)
  tmux attach -t $TMUX_SESSION
  window 'claude' (tmux select-window -t $TMUX_SESSION:claude):
      cd $REPO && claude
      first message:  You are ws58, owner of the EPYC compute calendar. Run scripts/coordination/churn/churn_up.sh --status,
                      then follow docs/guides/agent-workflows/backlog-churn-flow.md (Roles -> ws58): keep the keeper (allocator),
                      generator and dispatcher healthy, file results, put new work into the backlog. Fan out subagents; wrap up per task.
  window 'codex-gen' (tmux select-window -t $TMUX_SESSION:codex-gen):
      cd $REPO && codex
      first message:  Read $F/GOAL-codex-gen.md and follow it exactly. Your backlog is $F/BACKLOG-codex-gen.md.
  Per-handoff sessions are started by the dispatcher in tmux windows h-<slug> (max_live in $F/handoff-sessions.json); nothing by hand.
  Verify afterwards:  $0 --status   (every line UP, no DIFFERS, no DEAD grant)
EOF
}

# ---------------------------------------------------------------- main
say "churn_up $MODE  $(date -u +%FT%TZ)  repo=$REPO ($(git -C "$REPO" rev-parse --short HEAD 2>/dev/null)) flags=$F"
[ -d "$F" ] || { [ $MODE = live ] && mkdir -p "$F" || { fail "$F missing"; }; }
if [ -n "$JAN" ]; then  # the disk janitor alone; never touches inference components
  case $JAN in
    start) install_one "disk_janitor.sh" "$CH/disk_janitor.sh"; p=$(pid_of "$F/disk-janitor.pid")
           if is_proc "$p" disk_janitor.sh; then say "  disk-janitor: running pid $p"
           elif [ -n "$(argv_pids "$F/disk_janitor.sh")" ]; then warn "disk-janitor: already running as pid(s) $(argv_pids "$F/disk_janitor.sh"); not starting a duplicate"
           else start_bg "$F/disk-janitor.pid" "$F" bash "$F/disk_janitor.sh"; fi;;
    stop) stop_loop disk-janitor;;
    status) p=$(pid_of "$F/disk-janitor.pid"); if is_proc "$p" disk_janitor.sh; then say "  disk-janitor UP pid $p since $(ps -o lstart= -p "$p")"; else say "  disk-janitor DOWN (pidfile '${p:-none}')"; RC=1; fi
            say "  last log lines ($F/disk-janitor.log):"; tail -n 5 "$F/disk-janitor.log" 2>/dev/null | sed 's/^/    /';;
    dry-run) J=$F/disk_janitor.sh; [ -f "$J" ] || J=$CH/disk_janitor.sh; bash "$J" --dry-run || RC=1;;
  esac
  [ $RC = 0 ] && say "churn_up janitor $JAN: OK" || say "churn_up janitor $JAN: PROBLEMS"
  exit $RC
fi
case $MODE in
  status) status_install; status_loops; status_tmux; status_state;;
  *) if [ $STOP = 1 ]; then do_stop; else do_install; clean_grants; clean_registry; show_lanes; ensure_loops; check_legacy_writers; ensure_tmux; manual_steps; fi;;
esac
[ $RC = 0 ] && say "churn_up $MODE: OK" || say "churn_up $MODE: PROBLEMS (see FAIL/DOWN/DIFFERS lines)"
exit $RC
