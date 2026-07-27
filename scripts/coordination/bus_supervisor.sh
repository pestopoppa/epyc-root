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
DAEMON="${EPYC_ROOT}/scripts/coordination/session_bus_coordinator.py"

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
DAEMON_PATTERN="session_bus_coordinator\\.py run"

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

check_once() {
  if health_ok; then return 0; fi
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
