#!/bin/bash
# churn_up.sh — idempotent bring-up of the backlog-churn pipeline (ws58, 2026-11-01).
#
# Operator goal: after a host reboot the churn pipeline comes back from FORMALIZED, PERSISTED rules and code; nothing
# depends on any session's memory. This script is the one command. Runbook: docs/guides/agent-workflows/backlog-churn-flow.md
# -> "Reboot / cold start".
#
#   churn_up.sh            install git copies -> compute-flags, clean reboot residue, start what is not running,
#                          recreate the tmux session, print the manual steps (start Claude ws58 + codex-gen).
#   churn_up.sh --dry-run  same, printing every action instead of doing it (safe on a live system).
#   churn_up.sh --status   read-only report: per component pid / alive / sha-vs-git; lanes; grants; sessions; tmux.
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
case "${1:-}" in
  "") ;;
  --dry-run) MODE=dry;;
  --status) MODE=status;;
  -h|--help) sed -n 2,20p "$0"; exit 0;;
  *) echo "usage: churn_up.sh [--dry-run|--status]" >&2; exit 2;;
esac
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
  "ws58-calendar-keeper-v10.sh    $RF/ws58-calendar-keeper-v10.sh"
  "ws58-keeper-watchdog.sh        $CH/ws58-keeper-watchdog.sh"
  "ws58-disk-trend.sh             $CH/ws58-disk-trend.sh"
  "ws58-backlog-gen-v1.sh         $CH/ws58-backlog-gen-v1.sh"
  "ws58-flow-scoreboard-v1.sh     $CH/ws58-flow-scoreboard-v1.sh"
  "grant_ok.sh                    $RF/grant_ok_v4.sh"
  "grant_ok_v4.sh                 $RF/grant_ok_v4.sh"
  "grant_ok_launcher.py           $CH/legacy/grant_ok_launcher.py"
  "validate_fillers.py            $CO/validate_fillers.py"
  "ram_admit.sh                   $CH/ram_admit.sh"
  "GOAL-codex-gen.md              $CH/GOAL-codex-gen.md"
  "bin/backlog_gen.py             $CO/backlog_gen.py"
  "bin/handoff_sessions.py        $CO/handoff_sessions.py"
  "bin/flow_scoreboard.py         $CO/flow_scoreboard.py"
  "bin/rowflow/rowflow.py         $RF/rowflow.py"
  "bin/rowflow/filler_run15.sh    $RF/filler_run15.sh"
  "bin/rowflow/filler_lib.sh      $RF/filler_lib.sh"
  "bin/rowflow/grant_ok_launcher.py $RF/grant_ok_launcher.py"
  "bin/rowflow/publish_row.py     $RF/publish_row.py"
  "bin/rowflow/grant_ok_v4.sh     $RF/grant_ok_v4.sh"
  "bin/rowflow/dryrun_disk_policy.json $RF/dryrun_disk_policy.json"
  # grant-writer TEMPLATES: the keeper derives each day's / version's writer from the newest one by sed (see gen_* below)
  "grant-ws58-quarters-20261101.sh $CH/grant-ws58-quarters-20261101.sh"
  "grant-gpu-1101-v20.sh          $CH/grant-gpu-1101-v20.sh"
)
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
  cp -p "$src" "$dst.churn-tmp.$$" && mv -f "$dst.churn-tmp.$$" "$dst" || fail "install $rel"
}
do_install() {
  say "== install (git -> $F)"
  local line
  for line in "${INSTALL[@]}"; do install_one $line; done
  local cur; cur=$(cat "$F/ws58-calendar-keeper.current" 2>/dev/null)
  if [ "$cur" != "ws58-calendar-keeper-v10.sh" ]; then
    act "SET ws58-calendar-keeper.current = ws58-calendar-keeper-v10.sh (was '${cur:-}')"
    [ $MODE = dry ] || echo ws58-calendar-keeper-v10.sh > "$F/ws58-calendar-keeper.current"
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
  [ -n "$p" ] || p=$(cat "$F"/ws58-quarters-2026????.queue "$F"/ws58-gpu.queue 2>/dev/null | awk -F'|' -v id="$id" '$1==id{print $2}' | tail -1)
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

# ---------------------------------------------------------------- 3. grant writers
# Both writers are per-day / per-version files that the keeper generates from the newest one by sed and starts when the
# predecessor is dead (succession walks ONE day/version per 120 s tick). After a reboot we fast-forward with the SAME
# recipes so the lanes are not idle for hours, then the keeper owns succession again.
active_day() { date -u -d '-5 hours -52 minutes' +%Y%m%d; }   # the quarter day rolls at 05:52Z
live_quarter_writer() { local d f; for f in "$F"/grant-ws58-quarters-2026????.pid; do [ -e "$f" ] || continue; d=$(basename "$f" .pid); is_proc "$(pid_of "$f")" "$d.sh" && { echo "${d#grant-ws58-quarters-} $(pid_of "$f")"; return 0; }; done; return 1; }
ensure_quarter_writer() {
  say "== quarter grant writer"
  local live; if live=$(live_quarter_writer); then say "  live: $live"; return; fi
  local day last src dst cap0 cap1 s0 prevs0
  day=$(active_day); dst=$F/grant-ws58-quarters-$day.sh
  last=$(ls "$F"/grant-ws58-quarters-2026????.sh 2>/dev/null | sed -n 's/.*quarters-\(2026[0-9]\{4\}\)\.sh$/\1/p' | sort | tail -1)
  [ -n "$last" ] || { fail "no quarter writer template in $F"; return; }
  if [ ! -e "$dst" ]; then
    src=$F/grant-ws58-quarters-$last.sh
    cap0=$(sed -n "s/^CAP=\$(date -u -d '\([^']*\)'.*/\1/p" "$src" | sed -n 1p)
    prevs0=$(sed -n 's/.*S0=$(date -u -d "\([^"]*\)".*/\1/p' "$src" | sed -n 1p)
    cap1=$(date -u -d "${day:0:4}-${day:4:2}-${day:6:2} +1 day" +%Y-%m-%d)T06:00:00Z
    s0="${day:0:4}-${day:4:2}-${day:6:2}T05:52:00Z"
    [ -n "$cap0" ] && [ -n "$prevs0" ] || { fail "cannot parse CAP/S0 from $src"; return; }
    act "GENERATE $dst from $src ($last->$day, CAP $cap0->$cap1, gate $prevs0->$s0) [keeper recipe]"
    if [ $MODE != dry ]; then
      sed -e "s/$last/$day/g" -e "s/$cap0/$cap1/g" -e "s/$prevs0/$s0/g" \
          -e "1a # churn_up $(date -u +%FT%TZ): successor of grant-ws58-quarters-$last.sh (reboot fast-forward); start gated $s0, cap $cap1." "$src" > "$dst.tmp" \
        && mv -f "$dst.tmp" "$dst" && chmod +x "$dst"
      bash -n "$dst" || { fail "bash -n $dst"; return; }
      grep -q "CAP=\$(date -u -d '$cap1'" "$dst" || { fail "CAP line not $cap1 in $dst"; return; }
    fi
  fi
  [ -e "$F/ws58-quarters-$day.queue" ] || act "CREATE $F/ws58-quarters-$day.queue"
  [ $MODE = dry ] || [ -e "$F/ws58-quarters-$day.queue" ] || echo "# ws58 ${day:4:2}-${day:6:2} quarter queue (id|launcher_pid|window_s|gib|regions); created by churn_up" > "$F/ws58-quarters-$day.queue"
  act "START quarter writer $dst (marker ws58-keeper-state/started-quarters-$day)"
  [ $MODE = dry ] && return
  touch "$F/ws58-keeper-state/started-quarters-$day"
  (cd "$F" && setsid bash "$dst" </dev/null >/dev/null 2>&1 &)
  sleep 2; live=$(live_quarter_writer) && say "      live: $live" || fail "quarter writer did not stay up (see $F/grant-ws58-quarters-$day.log)"
}
gpu_newest() { ls "$F"/grant-gpu-????-v[0-9]*.sh 2>/dev/null | sed -n 's/.*grant-gpu-\([0-9]\{4\}\)-v\([0-9]*\)\.sh$/\2 \1/p' | sort -n | tail -1; }
ensure_gpu_writer() {
  say "== GPU grant writer"
  local cur n md name p3 now pid cap1 nd next dst oldwait oldbirth
  cur=$(gpu_newest); [ -n "$cur" ] || { fail "no GPU writer template in $F"; return; }
  n=${cur% *}; md=${cur#* }; name="grant-gpu-$md-v$n"
  pid=$(pid_of "$F/$name.pid")
  if is_proc "$pid" "$name.sh"; then say "  live: $name pid $pid"; return; fi
  p3=$(sed -n "s/^P3=\$(date -u -d '\([^']*\)'.*/\1/p" "$F/$name.sh" | sed -n 1p); now=$(date -u +%s)
  if [ ! -e "$F/$name.pid" ] && [ $(( $(date -u -d "$p3" +%s) - now )) -gt 10800 ]; then
    # never started and its cap is still useful: its predecessor wait is false for a missing or reused pid
    act "START never-started GPU writer $name (cap $p3)"
    [ $MODE = dry ] && return
    touch "$F/ws58-keeper-state/started-$name"; (cd "$F" && setsid bash "$F/$name.sh" </dev/null >/dev/null 2>&1 &)
    sleep 2; is_proc "$(pid_of "$F/$name.pid")" "$name.sh" && say "      live pid $(pid_of "$F/$name.pid")" || fail "GPU writer $name did not stay up (see $F/$name.log)"
    return
  fi
  # successor: cap = the next 06:00Z at least 3 h away; predecessor = the dead pid with birth 0 (keeper v7d rule)
  cap1=$(date -u -d "$(date -u +%Y-%m-%d)T06:00:00Z" +%s); while [ $(( cap1 - now )) -le 10800 ]; do cap1=$(( cap1 + 86400 )); done
  cap1=$(date -u -d "@$cap1" +%Y-%m-%dT%H:%M:%SZ); nd=$(date -u -d "$cap1" +%m%d); next=$((n+1)); dst=$F/grant-gpu-$nd-v$next.sh
  [ -n "$pid" ] || pid=999999999   # no pid file: a pid that cannot exist; predecessor_alive is false for it
  oldwait=$(sed -n 's/^while ps -o pid= -p \([0-9]*\) .*&& predecessor_alive [0-9]* \([0-9]*\); do sleep 30; done$/\1/p' "$F/$name.sh" | sed -n 1p)
  oldbirth=$(sed -n 's/^while ps -o pid= -p [0-9]* .*&& predecessor_alive [0-9]* \([0-9]*\); do sleep 30; done$/\1/p' "$F/$name.sh" | sed -n 1p)
  [[ "$oldwait" =~ ^[0-9]+$ && "$oldbirth" =~ ^[0-9]+$ ]] || { fail "GPU writer $name: wait line format unknown; keeper succession will handle it"; return; }
  if [ -e "$dst" ]; then
    act "START existing successor $dst"
  else
    act "GENERATE $dst from $name.sh (cap $p3->$cap1; predecessor $pid birth 0) [keeper recipe]"
    if [ $MODE != dry ]; then
      sed -e "s/grant-gpu-$md-v$n/grant-gpu-$nd-v$next/g" -e "s/$p3/$cap1/g" \
          -e "s/^while ps -o pid= -p $oldwait /while ps -o pid= -p $pid /" \
          -e "s/predecessor_alive $oldwait $oldbirth/predecessor_alive $pid 0/g" \
          -e "s/^log \"v$((n-1)) ($oldwait) gone; v$n starting\"/log \"v$n ($pid) gone; v$next starting\"/" \
          -e "s/^log \"armed v$n /log \"armed v$next /" \
          -e "1a # v$next (churn_up $(date -u +%FT%TZ), reboot fast-forward): successor of $name; predecessor $pid is dead (birth 0); cap $cap1." \
          "$F/$name.sh" > "$dst.tmp" && mv -f "$dst.tmp" "$dst" && chmod +x "$dst"
      bash -n "$dst" || { fail "bash -n $dst"; return; }
      grep -q "^P3=\$(date -u -d '$cap1'" "$dst" || { fail "P3 line not $cap1 in $dst"; return; }
      grep -q "predecessor_alive $pid 0" "$dst" || { fail "predecessor rewrite failed in $dst"; return; }
    fi
  fi
  [ $MODE = dry ] && return
  touch "$F/ws58-keeper-state/started-grant-gpu-$nd-v$next"; (cd "$F" && setsid bash "$dst" </dev/null >/dev/null 2>&1 &)
  sleep 2; is_proc "$(pid_of "$dst.pid" 2>/dev/null || pid_of "${dst%.sh}.pid")" "grant-gpu-$nd-v$next.sh" && say "      live pid $(pid_of "${dst%.sh}.pid")" || fail "GPU writer v$next did not stay up (see ${dst%.sh}.log)"
}

# ---------------------------------------------------------------- 4. loops
# name | pidfile | argv marker | cwd | command
LOOPS=(
  "watchdog|ws58-keeper-watchdog.pid|ws58-keeper-watchdog.sh|$F|bash $F/ws58-keeper-watchdog.sh"
  "backlog-gen|ws58-backlog-gen.pid|backlog_gen.py|$F|bash $F/ws58-backlog-gen-v1.sh"
  "flow-scoreboard|ws58-flow-scoreboard.pid|ws58-flow-scoreboard-v1.sh|$F|bash $F/ws58-flow-scoreboard-v1.sh"
  "dispatcher|handoff-sessions.dispatcher.pid|handoff_sessions.py|$F/bin|python3 -I $F/bin/handoff_sessions.py dispatch --loop --interval 60"
  "disk-trend|ws58-disk-trend.pid|ws58-disk-trend.sh|$F|bash $F/ws58-disk-trend.sh"
  "filing-watch|ws58-filing-watch.pid|filing_watch.sh|$REPO|env FILING_WATCH_FLAGS_ROOT=$F FILING_WATCH_BUS_ROOT=$REPO/coordination/session-bus bash $REPO/scripts/coordination/filing_watch.sh"
)
loop_pid() { local name=$1 l; for l in "${LOOPS[@]}"; do IFS='|' read -r n pf mk cwd cmd <<< "$l"; [ "$n" = "$name" ] && { pid_of "$F/$pf"; return; }; done; }
ensure_loops() {
  say "== loops"
  local l n pf mk cwd cmd p
  for l in "${LOOPS[@]}"; do
    IFS='|' read -r n pf mk cwd cmd <<< "$l"
    p=$(pid_of "$F/$pf")
    if is_proc "$p" "$mk"; then say "  $n: running pid $p"; continue; fi
    [ -n "$p" ] && say "  $n: pidfile pid $p is dead or not $mk"
    start_bg "$F/$pf" "$cwd" $cmd
  done
  # the keeper is started by the watchdog within 2 min; say so rather than racing it
  local k; k=$(pid_of "$F/ws58-calendar-keeper.pid")
  if is_proc "$k" "$(cat "$F/ws58-calendar-keeper.current" 2>/dev/null)"; then say "  keeper: running pid $k"; else say "  keeper: not running; the watchdog starts $(cat "$F/ws58-calendar-keeper.current" 2>/dev/null) within 120 s"; fi
}
status_loops() {
  say "== loops (pidfile -> pid, alive+argv, started)"
  local l n pf mk cwd cmd p st
  for l in "${LOOPS[@]}"; do
    IFS='|' read -r n pf mk cwd cmd <<< "$l"; p=$(pid_of "$F/$pf")
    if is_proc "$p" "$mk"; then st="UP   since $(ps -o lstart= -p "$p")"; else st="DOWN (pidfile pid '${p:-none}')"; RC=1; fi
    printf '  %-16s %-8s %s\n' "$n" "${p:-none}" "$st"
  done
  p=$(pid_of "$F/ws58-calendar-keeper.pid")
  if is_proc "$p" "$(cat "$F/ws58-calendar-keeper.current" 2>/dev/null)"; then printf '  %-16s %-8s UP   since %s (%s)\n' keeper "$p" "$(ps -o lstart= -p "$p")" "$(cat "$F/ws58-calendar-keeper.current")"; else printf '  %-16s %-8s DOWN\n' keeper "${p:-none}"; RC=1; fi
  local q; if q=$(live_quarter_writer); then printf '  %-16s %-8s UP   %s\n' quarter-writer "${q#* }" "grant-ws58-quarters-${q% *}.sh"; else printf '  %-16s %-8s DOWN\n' quarter-writer none; RC=1; fi
  local cur n2 md name gp; cur=$(gpu_newest); n2=${cur% *}; md=${cur#* }; name="grant-gpu-$md-v$n2"; gp=$(pid_of "$F/$name.pid")
  if [ -n "$cur" ] && is_proc "$gp" "$name.sh"; then printf '  %-16s %-8s UP   %s.sh cap %s\n' gpu-writer "$gp" "$name" "$(sed -n "s/^P3=\$(date -u -d '\([^']*\)'.*/\1/p" "$F/$name.sh" | sed -n 1p)"; else printf '  %-16s %-8s DOWN (newest %s)\n' gpu-writer "${gp:-none}" "${name:-none}"; RC=1; fi
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
  say "== disk"; printf '  /mnt/raid0/llm free: %s GiB (floor 150; dryrun policy %s)\n' "$(df -B1G --output=avail /mnt/raid0/llm | tail -1 | tr -d ' ')" "$(tr -d '\n ' < "$F/bin/rowflow/dryrun_disk_policy.json" 2>/dev/null | cut -c1-120)"
}
manual_steps() {
  cat <<EOF
== BY HAND (the only steps churn_up never does: it never starts an agent and never sends keys to a pane)
  tmux attach -t $TMUX_SESSION
  window 'claude' (tmux select-window -t $TMUX_SESSION:claude):
      cd $REPO && claude
      first message:  You are ws58, owner of the EPYC compute calendar. Run scripts/coordination/churn/churn_up.sh --status,
                      then follow docs/guides/agent-workflows/backlog-churn-flow.md (Roles -> ws58): keep the keeper, writers,
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
case $MODE in
  status) status_install; status_loops; status_tmux; status_state;;
  *)      do_install; clean_grants; clean_registry; show_lanes; ensure_loops; ensure_quarter_writer; ensure_gpu_writer; ensure_tmux; manual_steps;;
esac
[ $RC = 0 ] && say "churn_up $MODE: OK" || say "churn_up $MODE: PROBLEMS (see FAIL/DOWN/DIFFERS lines)"
exit $RC
