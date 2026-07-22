#!/bin/bash
# =============================================================================
# hub_supervisor.sh — userspace health-check / restart supervisor for the
#                     epyc-root project dashboard hub (:8100).
# =============================================================================
#
# WHY: the :8100 handoff-dashboard hub has been launched with a bare `setsid`
# and has died silently >=3x (Jul 17-18, 2026) with no watchdog to bring it
# back (see progress/2026-07/2026-07-05-dashboard-hub.md and
# handoffs/active/loops-and-dashboards-audit-2026-07-05.md P1 ":8100 hub
# process durability"). This script is that watchdog, entirely in userspace —
# NO systemd unit (host config is operator territory).
#
# WHAT IT DOES: polls http://127.0.0.1:8100/health on an interval. While the
# hub answers healthy it does nothing (so a currently-running hub is NEVER
# disrupted). When /health fails it clears any wedged :8100 instance and
# relaunches the hub with the SAME command the stack manager uses
# (`python -m dashboard.server --host 0.0.0.0 --port 8100`, cwd=epyc-root),
# with exponential backoff on repeated restart failures. It only ever touches
# :8100 — the orchestrator API (:8000) is never inspected or restarted.
#
# ---------------------------------------------------------------------------
# ADOPTION (short note)
# ---------------------------------------------------------------------------
#   Start (detached, survives logout; idempotent — a 2nd copy self-exits):
#       nohup /mnt/raid0/llm/epyc-root/scripts/dashboard/hub_supervisor.sh \
#             > /mnt/raid0/llm/epyc-root/logs/hub_supervisor.out 2>&1 &
#
#   One-shot check (for a cron entry instead of the daemon loop):
#       */2 * * * * /mnt/raid0/llm/epyc-root/scripts/dashboard/hub_supervisor.sh once
#
#   Inspect / stop:
#       hub_supervisor.sh status          # supervisor + hub liveness
#       kill "$(cat /mnt/raid0/llm/epyc-root/logs/hub_supervisor.pid)"
#
#   Interaction with the stack manager: the hub stays a first-class
#   `handoff_dashboard` service in orchestrator_stack.py — this supervisor only
#   *revives* :8100 when it has died between stack operations; it does not
#   replace the managed launch. Before a FULL `orchestrator_stack.py` stack
#   reload, stop the supervisor (or run `once` afterwards) so the two do not
#   race for the port. The relaunched instance is byte-identical in behavior
#   (stdlib-only hub); it is simply not registered in the stack's ProcessInfo
#   until the next managed start.
#
#   Tunables (env overrides): HUB_PORT HUB_HOST HEALTH_PATH POLL_INTERVAL
#   MAX_BACKOFF HEALTH_TIMEOUT STARTUP_TIMEOUT HUB_PYTHON EPYC_ROOT.
# =============================================================================
set -euo pipefail

# --------------------------------------------------------------------------- #
# Configuration (all env-overridable)
# --------------------------------------------------------------------------- #
EPYC_ROOT="${EPYC_ROOT:-/mnt/raid0/llm/epyc-root}"
HUB_HOST="${HUB_HOST:-127.0.0.1}"
HUB_PORT="${HUB_PORT:-8100}"
HEALTH_PATH="${HEALTH_PATH:-/health}"
POLL_INTERVAL="${POLL_INTERVAL:-15}"     # seconds between healthy polls
MAX_BACKOFF="${MAX_BACKOFF:-300}"        # cap on restart backoff (seconds)
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-5}"    # per-probe curl timeout (seconds)
STARTUP_TIMEOUT="${STARTUP_TIMEOUT:-30}" # wait for /health after a relaunch

LOG_DIR="${EPYC_ROOT}/logs"
SUP_LOG="${LOG_DIR}/hub_supervisor.log"       # this supervisor's own log
HUB_LOG="${LOG_DIR}/handoff_dashboard.log"    # the hub's stdout/stderr
LOCK_FILE="/tmp/hub_supervisor_${HUB_PORT}.lock"
SUP_PIDFILE="${LOG_DIR}/hub_supervisor.pid"
HUB_PIDFILE="${LOG_DIR}/hub_supervisor_hub.pid"

# The hub is stdlib-only, so any python3 runs it; prefer the interpreter the
# stack manager uses so the relaunched process matches the managed one.
if [[ -z "${HUB_PYTHON:-}" ]]; then
  if [[ -x /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python ]]; then
    HUB_PYTHON=/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python
  else
    HUB_PYTHON="$(command -v python3 || true)"
  fi
fi

# A precise pgrep pattern scoped to THIS hub's port so it can never match the
# orchestrator API, an unrelated server, or this supervisor script itself.
HUB_PATTERN="dashboard\\.server .*--port ${HUB_PORT}"

mkdir -p "${LOG_DIR}"

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
log() {
  local ts
  ts="$(date '+%Y-%m-%dT%H:%M:%S%z')"
  printf '%s [hub-sup] %s\n' "${ts}" "$*" | tee -a "${SUP_LOG}" >&2
}

# --------------------------------------------------------------------------- #
# Health probe — true iff /health answers 200 with a "status"/"ok" body
# --------------------------------------------------------------------------- #
health_ok() {
  local body
  body="$(curl -fsS --max-time "${HEALTH_TIMEOUT}" \
          "http://${HUB_HOST}:${HUB_PORT}${HEALTH_PATH}" 2>/dev/null)" || return 1
  case "${body}" in
    *'"status"'*'ok'*) return 0 ;;
    *) return 1 ;;
  esac
}

wait_health() {
  # Poll /health for up to $1 seconds; return 0 as soon as healthy.
  local deadline=$(( SECONDS + ${1:-$STARTUP_TIMEOUT} ))
  while (( SECONDS < deadline )); do
    if health_ok; then return 0; fi
    sleep 1
  done
  return 1
}

# --------------------------------------------------------------------------- #
# Clear a wedged :8100 instance (only called when /health is already failing)
# --------------------------------------------------------------------------- #
# Return only PIDs that are genuinely a python hub process (comm=python*),
# filtering out any shell / grep / monitor whose command line merely echoes the
# pattern — this makes the `pgrep -f` match self-match-proof.
hub_pids() {
  local pid comm
  for pid in $(pgrep -f "${HUB_PATTERN}" 2>/dev/null || true); do
    [[ "${pid}" == "$$" ]] && continue
    comm="$(cat "/proc/${pid}/comm" 2>/dev/null || true)"
    case "${comm}" in
      [Pp]ython*) printf '%s ' "${pid}" ;;
    esac
  done
}

kill_wedged_hub() {
  local pids
  pids="$(hub_pids)"
  pids="${pids% }"
  [[ -z "${pids}" ]] && return 0
  log "clearing wedged hub PIDs: ${pids}"
  # Graceful first.
  # shellcheck disable=SC2086
  kill -TERM ${pids} 2>/dev/null || true
  local waited=0
  while (( waited < 8 )); do
    [[ -z "$(hub_pids)" ]] && { log "wedged hub exited on SIGTERM"; return 0; }
    sleep 1; waited=$(( waited + 1 ))
  done
  # Escalate — verify death (CLAUDE.md process-management rule).
  pids="$(hub_pids)"; pids="${pids% }"
  if [[ -n "${pids}" ]]; then
    log "SIGTERM did not clear ${pids}; escalating to SIGKILL"
    # shellcheck disable=SC2086
    kill -KILL ${pids} 2>/dev/null || true
    sleep 1
  fi
  pids="$(hub_pids)"; pids="${pids% }"
  if [[ -n "${pids}" ]]; then
    log "WARN: hub PIDs still present after SIGKILL: ${pids}"
    return 1
  fi
  return 0
}

# --------------------------------------------------------------------------- #
# Launch a fresh hub, detached (mirrors orchestrator_stack.start_handoff_dashboard)
# --------------------------------------------------------------------------- #
start_hub() {
  if [[ -z "${HUB_PYTHON}" || ! -x "${HUB_PYTHON}" ]]; then
    log "ERROR: no usable python interpreter (HUB_PYTHON='${HUB_PYTHON}')"
    return 1
  fi
  if [[ ! -f "${EPYC_ROOT}/dashboard/server.py" ]]; then
    log "ERROR: hub server not found at ${EPYC_ROOT}/dashboard/server.py"
    return 1
  fi
  log "launching hub: ${HUB_PYTHON} -m dashboard.server --host 0.0.0.0 --port ${HUB_PORT} (cwd=${EPYC_ROOT})"
  # setsid fully detaches the hub so it outlives this supervisor; the supervisor
  # watches it by /health, not by being its parent.
  PYTHONPATH="${EPYC_ROOT}${PYTHONPATH:+:${PYTHONPATH}}" \
  setsid "${HUB_PYTHON}" -m dashboard.server \
      --host 0.0.0.0 --port "${HUB_PORT}" \
      >>"${HUB_LOG}" 2>&1 < /dev/null &
  local pid=$!
  echo "${pid}" > "${HUB_PIDFILE}"
  log "hub launched (pid=${pid}); waiting up to ${STARTUP_TIMEOUT}s for /health"
}

restart_hub() {
  kill_wedged_hub || true
  start_hub || return 1
  if wait_health "${STARTUP_TIMEOUT}"; then
    log "hub healthy after restart"
    return 0
  fi
  log "hub did NOT become healthy within ${STARTUP_TIMEOUT}s"
  return 1
}

# --------------------------------------------------------------------------- #
# Single-instance guard — makes the daemon idempotent + nohup-safe
# --------------------------------------------------------------------------- #
acquire_lock() {
  exec 9>"${LOCK_FILE}"
  if ! flock -n 9; then
    log "another supervisor already holds ${LOCK_FILE}; exiting (idempotent)"
    exit 0
  fi
}

# --------------------------------------------------------------------------- #
# Sub-commands
# --------------------------------------------------------------------------- #
cmd_status() {
  if health_ok; then
    echo "hub    : HEALTHY on http://${HUB_HOST}:${HUB_PORT}${HEALTH_PATH}"
  else
    echo "hub    : DOWN (no healthy /health on :${HUB_PORT})"
  fi
  local hp
  hp="$(hub_pids)"; hp="${hp% }"
  echo "hub pid: ${hp:-none}"
  if [[ -f "${SUP_PIDFILE}" ]] && kill -0 "$(cat "${SUP_PIDFILE}" 2>/dev/null)" 2>/dev/null; then
    echo "sup    : running (pid $(cat "${SUP_PIDFILE}"))"
  else
    echo "sup    : not running (no live pid in ${SUP_PIDFILE})"
  fi
}

cmd_once() {
  acquire_lock
  if health_ok; then
    log "once: hub healthy — no action"
    return 0
  fi
  log "once: hub down — attempting restart"
  restart_hub
}

cmd_loop() {
  acquire_lock
  echo "$$" > "${SUP_PIDFILE}"
  trap 'log "supervisor exiting (pid $$)"; rm -f "${SUP_PIDFILE}"' EXIT
  log "supervisor started (pid $$); watching :${HUB_PORT}${HEALTH_PATH} every ${POLL_INTERVAL}s"
  local backoff="${POLL_INTERVAL}"
  while true; do
    if health_ok; then
      backoff="${POLL_INTERVAL}"
      sleep "${POLL_INTERVAL}"
      continue
    fi
    log "hub UNHEALTHY — restarting"
    if restart_hub; then
      backoff="${POLL_INTERVAL}"
      sleep "${POLL_INTERVAL}"
    else
      log "restart failed; backing off ${backoff}s"
      sleep "${backoff}"
      backoff=$(( backoff * 2 ))
      (( backoff > MAX_BACKOFF )) && backoff="${MAX_BACKOFF}"
    fi
  done
}

usage() {
  cat <<EOF
hub_supervisor.sh — userspace watchdog for the :${HUB_PORT} dashboard hub

Usage: hub_supervisor.sh [loop|once|status|help]
  loop    (default) supervise forever: poll /health, restart on failure w/ backoff
  once    one health check; restart the hub only if it is down (cron-friendly)
  status  print hub + supervisor liveness and exit
  help    this message

Never restarts a healthy hub. Only ever touches :${HUB_PORT} (never :8000).
EOF
}

main() {
  case "${1:-loop}" in
    loop)   cmd_loop ;;
    once)   cmd_once ;;
    status) cmd_status ;;
    help|-h|--help) usage ;;
    *) usage; exit 2 ;;
  esac
}

main "$@"
