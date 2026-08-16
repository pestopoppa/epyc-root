#!/bin/bash
# fleet_control.sh — the ONE handle for deploying and stopping the coordination loop.
#
# This is the mechanism behind `/coordinator-agent`. That slash command was always
# meant to be the operator's single control surface (D3 made it the replacement for
# cron); this script is what it calls, so the same actions are available whether you
# are talking to a session or typing at a prompt.
#
#   fleet_control.sh status      what is running, what it is doing, what is in flight
#   fleet_control.sh start       bring the loop plane up (supervisor starts the daemon)
#   fleet_control.sh pause       stop dispatching NEW work; let in-flight workers finish
#   fleet_control.sh resume      undo pause
#   fleet_control.sh stop        stop the loop plane; in-flight workers are left alone
#   fleet_control.sh stop --hard stop the loop plane AND kill in-flight workers (salvaged)
#
# ORDERING IS THE WHOLE TRICK, and getting it wrong is why this exists:
#   * The supervisor RESTARTS the daemon. Stop the daemon first and it comes back in
#     seconds, which reads as "the stop did not work" and invites a harder kill.
#     So: supervisor first, always.
#   * fleet_watch is supervised by NOTHING. Nobody else will notice it is gone, and
#     nobody else will bring it back. It is started and stopped explicitly here.
#   * Killing a worker is not the same as stopping the loop. `pause` exists because
#     the usual intent is "stop starting things", not "destroy what is running".
#
# EVERY KILL IS OF A PID THIS SCRIPT READ ITSELF, and is verified dead afterwards.
# No name patterns: on this shared host a pattern is a wildcard over other sessions'
# processes, and a guard's own argv necessarily contains the names it guards.

set -euo pipefail

REPO=/workspace
BUS="$REPO/coordination/session-bus"
CFG="$BUS/config.yaml"
POOL_ROOT=/mnt/raid0/llm/worktrees/pool
cd "$REPO"


alarm_is_inert() {
  # Precise: the sentinel that decides liveness lives in the ACTIVE BACKEND's
  # endpoint. A whole-file grep for REPLACE-ME also matches the comment that
  # explains the sentinel and the unused email placeholder, which made a LIVE
  # channel report as inert (observed 2026-08-16, right after go-live).
  python3 - "$1" <<'PY_INERT'
import re, sys
t = open(sys.argv[1], encoding="utf-8").read()
m = re.search(r"^backend:\s*(\w+)", t, re.M)
b = m.group(1) if m else ""
blk = re.search(rf"^{b}:\n((?:[ \t]+.*\n)+)", t, re.M)
body = blk.group(1) if blk else ""
ep = re.search(r"^\s*(?:url|to):\s*(.+)$", body, re.M)
sys.exit(0 if (ep and "REPLACE-ME" in ep.group(1)) else 1)
PY_INERT
}

say()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
ok()   { printf '   \033[32mOK\033[0m   %s\n' "$*"; }
warn() { printf '   \033[33m!!\033[0m   %s\n' "$*"; }
bad()  { printf '   \033[31mXX\033[0m   %s\n' "$*"; }
note() { printf '        %s\n' "$*"; }

# --- pid discovery: read it, never pattern-match a name -----------------------
daemon_pid() {
  python3 - <<'PY' 2>/dev/null || true
import json
from pathlib import Path
try:
    hb = json.loads(Path("/workspace/coordination/session-bus/heartbeats/coordinator-daemon.json").read_text())
    pid = int(hb.get("pid") or 0)
except Exception:
    raise SystemExit(0)
# the heartbeat names a pid; that pid must still exist AND still be the daemon
if pid and Path(f"/proc/{pid}").exists():
    try:
        cmd = Path(f"/proc/{pid}/cmdline").read_bytes().decode("utf-8", "replace")
    except Exception:
        raise SystemExit(0)
    if "session_bus_coordinator.py" in cmd:
        print(pid)
PY
}

# The supervisor and fleet_watch publish no heartbeat, so their pid comes from
# /proc with a FULL-COMMAND match on the absolute script path — not a bare name.
proc_pid_by_script() {
  local script="$1" pid cmd
  for pid in /proc/[0-9]*; do
    pid="${pid#/proc/}"
    [[ -r "/proc/$pid/cmdline" ]] || continue
    cmd=$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)
    [[ "$cmd" == *"$script"* ]] || continue
    [[ "$cmd" == *"fleet_control.sh"* ]] && continue     # never ourselves
    echo "$pid"; return 0
  done
  return 0
}

kill_verified() {
  local pid="$1" what="$2"
  [[ -z "$pid" ]] && { note "$what: not running"; return 0; }
  kill -TERM "$pid" 2>/dev/null || true
  for _ in 1 2 3 4 5 6; do sleep 1; [[ -d "/proc/$pid" ]] || break; done
  if [[ -d "/proc/$pid" ]]; then
    warn "$what ($pid) ignored SIGTERM — escalating to SIGKILL"
    kill -KILL "$pid" 2>/dev/null || true
    sleep 1
  fi
  if [[ -d "/proc/$pid" ]]; then bad "$what ($pid) STILL ALIVE"; return 1; fi
  ok "$what ($pid) confirmed dead"
}

live_workers() {
  local n=0 pid
  for f in "$POOL_ROOT"/lane*/.worker.lock; do
    [[ -f "$f" ]] || continue
    pid=$(awk '{print $1}' "$f" 2>/dev/null || true)
    [[ -n "$pid" && -d "/proc/$pid" ]] && n=$((n+1))
  done
  echo "$n"
}

set_pool_enabled() {
  python3 - "$1" <<'PY'
import re, sys
from pathlib import Path
want = sys.argv[1]
p = Path("/workspace/coordination/session-bus/config.yaml")
t = p.read_text(encoding="utf-8")
t2 = re.sub(r"^(  enabled:)\s*(true|false)\s*$", r"\1 " + want, t, count=1, flags=re.M)
if t2 == t:
    raise SystemExit("worker_pool.enabled not found in config.yaml")
p.write_text(t2, encoding="utf-8")
PY
}

# ============================================================== status
cmd_status() {
  say "LOOP PLANE"
  local d s f
  d=$(daemon_pid); s=$(proc_pid_by_script "bus_supervisor.sh"); f=$(proc_pid_by_script "fleet_watch.sh")
  [[ -n "$s" ]] && ok "bus_supervisor   pid $s" || bad "bus_supervisor   DOWN  (nothing will restart the daemon)"
  [[ -n "$d" ]] && ok "coordinator-daemon pid $d" || bad "coordinator-daemon DOWN"
  [[ -n "$f" ]] && ok "fleet_watch      pid $f" || warn "fleet_watch      DOWN  (supervised by nothing; alarms about idle compute stop)"

  say "DISPATCH"
  local auth pool
  auth=$(grep -E "^  authority:" "$CFG" | head -1 | sed 's/.*authority:[[:space:]]*//; s/[[:space:]]*#.*//')
  pool=$(awk '/^worker_pool:/{f=1} f&&/^  enabled:/{print $2; exit}' "$CFG")
  note "daemon authority : ${auth:-unknown}   (assign = it dispatches; advisory = it only reports)"
  note "worker_pool      : ${pool:-unknown}   (false = schedulable but NOT executable)"
  note "workers in flight: $(live_workers) of 4"

  say "ALARMS"
  if alarm_is_inert "$BUS/alarm_config.yaml" 2>/dev/null; then
    warn "channel INERT (placeholder endpoint) — nothing reaches you"
  else
    ok "channel configured"
  fi
  python3 scripts/coordination/alarm_channel.py status 2>/dev/null | sed 's/^/        /' || true

  say "QUEUE"
  python3 scripts/coordination/session_bus.py status 2>/dev/null | head -3 | sed 's/^/        /' || true
}

# ============================================================== start
cmd_start() {
  say "START — bringing the loop plane up"
  local s f
  s=$(proc_pid_by_script "bus_supervisor.sh")
  if [[ -n "$s" ]]; then
    ok "bus_supervisor already running (pid $s) — it owns starting the daemon"
  else
    nohup /bin/bash "$REPO/scripts/coordination/bus_supervisor.sh" >> "$REPO/logs/bus_supervisor.out" 2>&1 &
    sleep 12
    s=$(proc_pid_by_script "bus_supervisor.sh")
    [[ -n "$s" ]] && ok "bus_supervisor started (pid $s)" || bad "bus_supervisor did not start"
  fi
  local d; d=$(daemon_pid)
  [[ -n "$d" ]] && ok "coordinator-daemon up (pid $d)" || warn "daemon not up yet — the supervisor starts it on its next poll"

  f=$(proc_pid_by_script "fleet_watch.sh")
  if [[ -n "$f" ]]; then
    ok "fleet_watch already running (pid $f)"
  else
    nohup /bin/bash "$REPO/scripts/coordination/fleet_watch.sh" >> "$REPO/logs/fleet_watch.out" 2>&1 &
    sleep 4
    f=$(proc_pid_by_script "fleet_watch.sh")
    [[ -n "$f" ]] && ok "fleet_watch started (pid $f)" || bad "fleet_watch did not start"
  fi
  note "verify the alarm path actually reaches you:"
  note "  bash scripts/coordination/tests/alarm_drill.sh"
}

# ============================================================== pause / resume
cmd_pause() {
  say "PAUSE — stop starting new work; let in-flight workers finish"
  set_pool_enabled false
  ok "worker_pool.enabled = false"
  note "In flight right now: $(live_workers) worker(s). They are NOT touched —"
  note "each finishes its batch, writes its report and exits. Use 'stop --hard'"
  note "only if you need them dead now (they are killed WITH salvage)."
  note "The daemon keeps folding and reporting; it just stops dispatching to the pool."
}

cmd_resume() {
  say "RESUME"
  set_pool_enabled true
  ok "worker_pool.enabled = true"
  if alarm_is_inert "$BUS/alarm_config.yaml" 2>/dev/null; then
    warn "alarms are still INERT — if the pool wedges overnight, nothing reaches you"
  fi
}

# ============================================================== stop
cmd_stop() {
  local hard="${1:-}"
  say "STOP — supervisor FIRST (it restarts the daemon), then the daemon"
  kill_verified "$(proc_pid_by_script "bus_supervisor.sh")" "bus_supervisor"
  kill_verified "$(daemon_pid)" "coordinator-daemon"
  kill_verified "$(proc_pid_by_script "fleet_watch.sh")" "fleet_watch"

  local n; n=$(live_workers)
  if [[ "$hard" == "--hard" ]]; then
    say "STOP --hard — killing $n in-flight worker(s)"
    local pid lane
    for f in "$POOL_ROOT"/lane*/.worker.lock; do
      [[ -f "$f" ]] || continue
      pid=$(awk '{print $1}' "$f" 2>/dev/null || true); lane=$(basename "$(dirname "$f")")
      [[ -n "$pid" && -d "/proc/$pid" ]] || continue
      kill_verified "$pid" "worker on $lane"
      note "$lane: the runner's own lease path performs the salvage commit;"
      note "        killing it here skips that, so check for uncommitted work:"
      note "        git -C $POOL_ROOT/$lane status --porcelain"
    done
  elif [[ "$n" -gt 0 ]]; then
    warn "$n worker(s) still running — deliberately left alone"
    note "They will finish, write their reports and exit. Their runner handles"
    note "salvage on lease expiry. Use 'stop --hard' to end them now."
  fi
  say "STOPPED"
  note "restart with:  $0 start      (or the /coordinator-agent skill)"
}

case "${1:-status}" in
  status) cmd_status ;;
  start)  cmd_start ;;
  pause)  cmd_pause ;;
  resume) cmd_resume ;;
  stop)   cmd_stop "${2:-}" ;;
  *) sed -n '2,30p' "$0"; exit 64 ;;
esac
