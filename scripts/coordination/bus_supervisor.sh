#!/bin/bash
# =============================================================================
# bus_supervisor.sh — userspace watchdog for the session-bus coordinator-daemon
# =============================================================================
#
# WHY: the coordinator-daemon is the always-on tier of the coordinator. If it
# dies, the bus degrades to M1 manual mode silently — no assignments, no
# saturation records, and nothing says so. This is its watchdog, entirely in
# userspace, modelled on scripts/dashboard/hub_supervisor.sh — NO systemd unit
# (host config is operator territory).
#
# WHAT IT DOES: polls the daemon's OWN heartbeat file. While the heartbeat is
# fresh it does nothing (a healthy daemon is NEVER disrupted). When the
# heartbeat goes stale — or no daemon process is alive — it clears any wedged
# instance and relaunches, with exponential backoff on repeated failures.
#
# HEALTH = heartbeat mtime, not a port probe: the daemon has no socket, and its
# heartbeat is exactly the liveness signal the bus protocol already defines.
# A daemon restart increments the epoch, so a relaunch is self-announcing.
#
# ---------------------------------------------------------------------------
# ADOPTION
# ---------------------------------------------------------------------------
#   Start (detached, survives logout; idempotent — a 2nd copy self-exits):
#       nohup /mnt/raid0/llm/epyc-root/scripts/coordination/bus_supervisor.sh \
#             > /mnt/raid0/llm/epyc-root/logs/bus_supervisor.out 2>&1 &
#
#   One-shot check (for a cron entry instead of the daemon loop):
#       */2 * * * * /mnt/raid0/llm/epyc-root/scripts/coordination/bus_supervisor.sh once
#
#   Inspect / stop:
#       bus_supervisor.sh status
#       kill "$(cat /mnt/raid0/llm/epyc-root/logs/bus_supervisor.pid)"
#
# ROLLBACK: stop the supervisor and the daemon; the bus returns to M1 manual
# mode, which is fully functional — nothing depends on the daemon in advisory
# mode.
set -euo pipefail

EPYC_ROOT="${EPYC_ROOT:-/mnt/raid0/llm/epyc-root}"
BUS_ROOT="${BUS_ROOT:-${EPYC_ROOT}/coordination/session-bus}"
HEARTBEAT="${BUS_ROOT}/heartbeats/coordinator-daemon.json"
DAEMON="${DAEMON:-${EPYC_ROOT}/scripts/coordination/session_bus_coordinator.py}"

POLL_INTERVAL="${POLL_INTERVAL:-20}"      # seconds between healthy polls
STALE_AFTER="${STALE_AFTER:-150}"         # heartbeat older than this => unhealthy
MAX_BACKOFF="${MAX_BACKOFF:-300}"         # cap on restart backoff
STARTUP_TIMEOUT="${STARTUP_TIMEOUT:-30}"  # wait for a fresh heartbeat after relaunch

LOG_DIR="${EPYC_ROOT}/logs"
SUP_LOG="${LOG_DIR}/bus_supervisor.log"
DAEMON_LOG="${LOG_DIR}/coordinator_daemon.log"
LOCK_FILE="${LOCK_FILE:-/tmp/bus_supervisor.lock}"   # overridable so tests isolate
SUP_PIDFILE="${LOG_DIR}/bus_supervisor.pid"

# Deliberately specific so it cannot match this supervisor's own command line.
# OVERRIDABLE, and that matters: `pgrep -f` matches on the whole command line, so a
# test stub named session_bus_coordinator.py in a temp dir matches this pattern and
# `stop_wedged` will kill the PRODUCTION daemon. That happened 2026-07-27 — a test
# that believed itself isolated (own LOCK_FILE, own EPYC_ROOT, own BUS_ROOT) killed
# the live daemon, because the pattern is global while everything else was scoped.
DAEMON_PATTERN="${DAEMON_PATTERN:-session_bus_coordinator\\.py run}"

mkdir -p "$LOG_DIR"

log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "$SUP_LOG" >&2; }

heartbeat_age_s() {
  [[ -f "$HEARTBEAT" ]] || { echo 999999; return; }
  local mtime now
  mtime=$(stat -c %Y "$HEARTBEAT" 2>/dev/null || echo 0)
  now=$(date +%s)
  echo $(( now - mtime ))
}

daemon_pids() { pgrep -f "$DAEMON_PATTERN" 2>/dev/null || true; }

health_ok() {
  local age; age=$(heartbeat_age_s)
  [[ -n "$(daemon_pids)" ]] && (( age <= STALE_AFTER ))
}

stop_wedged() {
  local pids; pids=$(daemon_pids)
  [[ -z "$pids" ]] && return 0
  log "stopping wedged daemon pid(s): ${pids//$'\n'/ }"
  # SIGTERM first: the daemon drains at its tick boundary (never a kill first).
  kill $pids 2>/dev/null || true
  for _ in $(seq 1 10); do
    sleep 1
    [[ -z "$(daemon_pids)" ]] && return 0
  done
  log "escalating to SIGKILL"
  kill -9 $(daemon_pids) 2>/dev/null || true
  sleep 1
}

start_daemon() {
  log "launching coordinator-daemon"
  # `9>&-` is load-bearing: fd 9 holds this supervisor's flock, and a child
  # inherits it across fork+exec. Without closing it, the DAEMON ends up holding
  # the supervisor's lock for its entire life, so no supervisor can ever start
  # again while that daemon lives — a complete self-lockout. Observed 2026-07-27:
  # `bus_supervisor.sh once` started the daemon, exited, and the daemon kept fd 9,
  # after which every `loop` logged "another supervisor holds the lock" while
  # `status` reported no supervisor running.
  nohup "$DAEMON" run 9>&- >>"$DAEMON_LOG" 2>&1 &
  local waited=0
  while (( waited < STARTUP_TIMEOUT )); do
    sleep 1; waited=$(( waited + 1 ))
    if health_ok; then log "daemon healthy after ${waited}s"; return 0; fi
  done
  log "daemon did NOT become healthy within ${STARTUP_TIMEOUT}s"
  return 1
}

# ---------------------------------------------------------------- stale source
#
# 2026-08-11. FIVE fixes sat committed-not-live in one evening — C39, C28, C38's
# tick path, R1 and R2 — because a running daemon keeps executing the code it
# loaded at start, and nothing noticed. `health_ok` asks "is a process there" and
# "is its heartbeat fresh"; a daemon running twelve-hour-old code answers yes to
# both. The recurrence proved the point twice in seven minutes: a restart at
# 22:18:12 was followed by an R2 commit at 22:21:25, so that fix ALSO needed a
# human to notice and restart again.
#
# This is a delivery gap in the same family as R1: the mechanism worked, and
# nothing carried its result to where it takes effect.
#
# Identity comes from the HEARTBEAT's own pid, never from a name pattern — a
# pattern is a wildcard over other sessions' processes on this shared host
# (INC-20260731-broad-process-pattern-kills), and the daemon already publishes
# exactly the number we need.
daemon_pid_from_heartbeat() {
  python3 - "$HEARTBEAT" <<'PY_EOF' 2>/dev/null || true
import json, sys
try:
    pid = json.load(open(sys.argv[1])).get("pid")
    print(int(pid))
except Exception:
    pass
PY_EOF
}

# Newest mtime across the daemon's own sources. It imports its siblings, so a
# change to any of them is a change to what it would run.
newest_source_mtime() {
  stat -c %Y "$(dirname "$DAEMON")"/*.py 2>/dev/null | sort -n | tail -1
}

# 0 = the running daemon predates its source. FAIL CLOSED: every unknown returns
# 2 (cannot tell) and the caller escalates rather than passing.
source_is_newer_than_daemon() {
  local pid started elapsed src now
  # `|| true` on every capture is load-bearing, not defensive noise: this script
  # runs under `set -euo pipefail`, where a FAILING command substitution aborts the
  # whole supervisor. A dead pid makes `ps` fail and an empty source dir makes the
  # `stat | sort` pipeline fail under pipefail — so without these the fail-closed
  # branches below are unreachable and the watchdog exits instead of reporting.
  # (Caught by test_bus_supervisor.py; my own predicate test had missed it because
  # it ran without `set -e` — the test method differed from production.)
  pid=$(daemon_pid_from_heartbeat || true)
  [[ -z "$pid" ]] && return 2
  elapsed=$(ps -p "$pid" -o etimes= 2>/dev/null | tr -d ' ' || true)
  [[ -z "$elapsed" ]] && return 2
  src=$(newest_source_mtime || true)
  [[ -z "$src" ]] && return 2
  now=$(date +%s)
  started=$(( now - elapsed ))
  # SKEW is not padding, it is the resolution of the measurement. `ps -o etimes`
  # reports whole seconds, so `started` can land up to a second before the real
  # start, and a source written in the same second as a legitimate restart would
  # then read as NEWER than the process it produced. That false positive restarts
  # a daemon that is already current — and it recurs every cycle, which is a
  # restart loop, strictly worse than the staleness it thinks it is fixing.
  # Caught by test_bus_supervisor.py, which went 5/5 -> 4/5 on the untolerated
  # version: the pre-existing suite was defending exactly this.
  (( src > started + STALE_SRC_SKEW_S ))
}

STALE_SRC_STATE="${LOG_DIR}/bus_supervisor.stale_src"
# Whole-second resolution on both sides; 5s covers it with room to spare and
# still catches a source edited even a minute after a restart.
STALE_SRC_SKEW_S="${STALE_SRC_SKEW_S:-5}"

check_stale_source() {
  local src rc=0
  # `|| rc=$?`, never `cmd; rc=$?`. Under `set -e` a FUNCTION returning non-zero as
  # a simple command aborts the script, so the bare form killed the supervisor
  # mid-`once` on every "current" and every "cannot tell" — i.e. on the normal
  # path. That is how a watchdog silently stops watching.
  source_is_newer_than_daemon || rc=$?
  if (( rc == 2 )); then
    log "STALE-SOURCE CHECK UNAVAILABLE — cannot read the daemon pid, its start time, or the"
    log "  source mtimes. Reported, not passed: a check that cannot tell is not a clean one."
    return 0
  fi
  (( rc != 0 )) && return 0
  src=$(newest_source_mtime || true)
  # Restart ONCE per source version. Without this a file the fleet touches often
  # would put the supervisor in a restart loop, which is worse than the staleness.
  if [[ -f "$STALE_SRC_STATE" ]] && [[ "$(cat "$STALE_SRC_STATE" 2>/dev/null)" == "$src" ]]; then
    return 0
  fi
  log "daemon is running code OLDER than its source (source $(date -d @"$src" -u +%H:%M:%SZ)"
  log "  is newer than the running process) — restarting so committed fixes take effect"
  echo "$src" > "$STALE_SRC_STATE"
  stop_wedged
  start_daemon
}

check_once() {
  # A HEALTHY daemon can still be the wrong daemon. Order matters: a dead one is
  # restarted by the branch below and comes back on current source anyway, so the
  # stale-source question only applies to one that is up and answering.
  if health_ok; then check_stale_source; return 0; fi
  log "unhealthy (heartbeat age $(heartbeat_age_s)s, pids '$(daemon_pids | tr '\n' ' ')') — restarting"
  stop_wedged
  start_daemon
}

case "${1:-loop}" in
  status)
    age=$(heartbeat_age_s); pids=$(daemon_pids | tr '\n' ' ')
    printf 'daemon pids : %s\n' "${pids:-none}"
    printf 'heartbeat   : %ss old (stale after %ss)\n' "$age" "$STALE_AFTER"
    printf 'supervisor  : %s\n' "$( [[ -f "$SUP_PIDFILE" ]] && cat "$SUP_PIDFILE" || echo 'not running')"
    health_ok && printf 'health      : OK\n' || printf 'health      : UNHEALTHY\n'
    exit 0
    ;;
  once)
    exec 9>"$LOCK_FILE"
    flock -n 9 || { log "another supervisor holds the lock; exiting"; exit 0; }
    check_once
    exit 0
    ;;
  loop)
    exec 9>"$LOCK_FILE"
    flock -n 9 || { log "another supervisor holds the lock; exiting"; exit 0; }
    echo $$ > "$SUP_PIDFILE"
    trap 'rm -f "$SUP_PIDFILE"; log "supervisor stopped"; exit 0' TERM INT
    log "supervisor started (poll ${POLL_INTERVAL}s, stale after ${STALE_AFTER}s)"
    backoff=0
    while true; do
      if health_ok; then
        backoff=0
        sleep "$POLL_INTERVAL"
        continue
      fi
      check_once || true
      if health_ok; then backoff=0; else
        backoff=$(( backoff == 0 ? 10 : backoff * 2 ))
        (( backoff > MAX_BACKOFF )) && backoff=$MAX_BACKOFF
        log "restart failed; backing off ${backoff}s"
        sleep "$backoff"
      fi
    done
    ;;
  *)
    printf 'usage: %s [loop|once|status]\n' "$(basename "$0")" >&2
    exit 64
    ;;
esac
