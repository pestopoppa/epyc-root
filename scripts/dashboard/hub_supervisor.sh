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
#       nohup setsid -f /mnt/raid0/llm/epyc-root/scripts/dashboard/hub_supervisor.sh \
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
# Resolve the hub by the PORT IT OWNS, never by a name pattern.
#
# This used to be `pgrep -f "dashboard\.server .*--port 8100"`. Two reasons that
# was wrong, and this function escalates to SIGKILL, so both mattered:
#
#   1. CLAUDE.md forbids pgrep/pkill on a name pattern on this shared host
#      (INC-20260731-broad-process-pattern-kills). A pattern is a wildcard over
#      every other session's processes, and a guard's own argv necessarily
#      contains the string it guards — this script, an editor with the file open,
#      or any shell running a command mentioning it, all match. `$$` was excluded;
#      nothing else was.
#   2. It answers a different question than the one being asked. The thing that
#      must die is whatever OWNS :8100 — that is what "wedged" means. A process
#      matching the pattern but bound to nothing is not wedged, and a process
#      holding the port under a different argv is invisible to the pattern.
#
# `ss` first (no extra dependency), `lsof` as fallback. Both key on the port only.
hub_pids() {
  local pids=""
  if command -v ss >/dev/null 2>&1; then
    pids="$(ss -tlnpH "sport = :${HUB_PORT}" 2>/dev/null \
            | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u || true)"
  fi
  if [[ -z "${pids}" ]] && command -v lsof >/dev/null 2>&1; then
    pids="$(lsof -ti ":${HUB_PORT}" -sTCP:LISTEN 2>/dev/null || true)"
  fi
  local pid
  for pid in ${pids}; do
    [[ "${pid}" == "$$" ]] && continue
    [[ -d "/proc/${pid}" ]] && printf '%s ' "${pid}"
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
  (
    cd "${EPYC_ROOT}"
    PYTHONPATH="${EPYC_ROOT}${PYTHONPATH:+:${PYTHONPATH}}" \
    setsid "${HUB_PYTHON}" -m dashboard.server \
        --host 0.0.0.0 --port "${HUB_PORT}" \
        >>"${HUB_LOG}" 2>&1 < /dev/null 9>&- &
  )
  # DO NOT record `$!` here. `setsid cmd &` backgrounds *setsid*, which forks and
  # exits; `$!` is that transient wrapper, not the hub, so the pidfile was wrong
  # from the instant it was written and pointed at a dead pid seconds later.
  # Measured 2026-08-10: the file named 543937 (long gone) while :8100 was served
  # by 3359733 — so nothing, including this supervisor, could identify the hub
  # from its own pidfile.
  #
  # The truthful identity is whoever ends up OWNING the port, and that is only
  # knowable once the listener exists — hence after wait_health, not here.
  log "hub launch issued; waiting up to ${STARTUP_TIMEOUT}s for /health"
}

# Record the pid of whatever actually owns the port. Called after /health passes.
record_hub_pid() {
  local pids
  pids="$(hub_pids)"; pids="${pids% }"
  if [[ -z "${pids}" ]]; then
    log "WARN: hub healthy but no listener resolved on :${HUB_PORT}; pidfile left stale"
    return 1
  fi
  # First (lowest) pid; a multi-pid answer means a wedged leftover, which
  # kill_wedged_hub clears on the next restart.
  local pid="${pids%% *}"
  echo "${pid}" > "${HUB_PIDFILE}"
  log "hub pid recorded: ${pid}"
}

restart_hub() {
  kill_wedged_hub || true
  start_hub || return 1
  if wait_health "${STARTUP_TIMEOUT}"; then
    log "hub healthy after restart"
    record_hub_pid || true
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

# Keep the pidfile truthful even when this supervisor did nothing. The hub is a
# stack-managed aux service, so `orchestrator_stack.py reload handoff_dashboard`
# can replace it without this process ever noticing — which is the OTHER way the
# pidfile went stale on 2026-08-10. A watchdog whose recorded pid disagrees with
# the port owner cannot do a targeted restart, so reconcile on every poll. Cheap:
# one `ss` call, and it writes only on a real mismatch.
reconcile_hub_pid() {
  local live recorded
  live="$(hub_pids)"; live="${live% }"; live="${live%% *}"
  [[ -z "${live}" ]] && return 0
  recorded="$(cat "${HUB_PIDFILE}" 2>/dev/null || true)"
  if [[ "${recorded}" != "${live}" ]]; then
    echo "${live}" > "${HUB_PIDFILE}"
    log "pidfile reconciled: recorded=${recorded:-<none>} -> live=${live} (hub replaced out-of-band)"
  fi
}

# --------------------------------------------------------------------------- #
# Stale source — the hub is UP but running code older than dashboard/
# --------------------------------------------------------------------------- #
#
# Ported from the bus supervisor's C42 (2026-08-11), where the same gap left five
# fixes committed-not-live in one evening. `health_ok` asks whether :8100 answers
# 200; a hub serving twelve-hour-old code answers yes. This handoff's own row
# records the consequence in its second sentence: hub_supervisor.sh "was found
# dead on 2026-08-10 ... which is why the hub sat on stale code unnoticed".
#
# NOT the operator half of that row. Whether a cron entry should restart this
# supervisor when it dies is a host-level change and the operator's call; this is
# the part that needs no host change — when the supervisor IS running, it now
# notices a stale hub instead of reporting it healthy.
#
# Identity comes from the LISTENING PORT via hub_pids, which is exact. The bus
# version takes it from the daemon's heartbeat for the same reason: never a name
# pattern, which on this shared host is a wildcard over other sessions' processes.
STALE_SRC_STATE="${LOG_DIR}/hub_supervisor.stale_src"
# Whole-second resolution on both sides. 5s covers it and still catches a source
# edited a minute after a restart. (C42: `ps -o etimes` truncates, so a source
# written in the same second as a legitimate restart read as NEWER — a false
# positive that recurs every cycle, i.e. a restart loop.)
STALE_SRC_SKEW_S="${STALE_SRC_SKEW_S:-5}"

hub_newest_source_mtime() {
  find "${EPYC_ROOT}/dashboard" -name '*.py' -newermt '@0' -printf '%T@\n' 2>/dev/null \
    | cut -d. -f1 | sort -n | tail -1
}

# 0 = running hub predates its source. FAIL CLOSED: every unknown returns 2.
hub_source_is_newer() {
  local pid elapsed src now started
  # `|| true` on every capture: this script runs under `set -euo pipefail`, where a
  # FAILING command substitution aborts the whole supervisor — so without them the
  # fail-closed branches below are unreachable and the watchdog exits instead of
  # reporting. (C42 learned this the hard way, twice.)
  pid="$(hub_pids | awk '{print $1}' || true)"
  [[ -z "${pid}" ]] && return 2
  elapsed="$(ps -p "${pid}" -o etimes= 2>/dev/null | tr -d ' ' || true)"
  [[ -z "${elapsed}" ]] && return 2
  src="$(hub_newest_source_mtime || true)"
  [[ -z "${src}" ]] && return 2
  now="$(date +%s)"
  started=$(( now - elapsed ))
  (( src > started + STALE_SRC_SKEW_S ))
}

check_hub_stale_source() {
  local src rc=0
  # `|| rc=$?`, never `cmd; rc=$?`. Under `set -e` a FUNCTION returning non-zero as
  # a simple command aborts the script, so the bare form kills the supervisor on
  # every "current" and every "cannot tell" — the normal path. A watchdog that
  # silently stops watching.
  hub_source_is_newer || rc=$?
  if (( rc == 2 )); then
    log "stale-source check UNAVAILABLE (no hub pid, start time, or source mtimes) —"
    log "  reported, not passed: a check that cannot tell is not a clean one"
    return 0
  fi
  (( rc != 0 )) && return 0
  src="$(hub_newest_source_mtime || true)"
  # Restart once per source version, or a frequently-touched file turns this into a
  # restart loop — worse than the staleness it thinks it is fixing.
  if [[ -f "${STALE_SRC_STATE}" ]] && [[ "$(cat "${STALE_SRC_STATE}" 2>/dev/null)" == "${src}" ]]; then
    return 0
  fi
  log "hub is serving code OLDER than dashboard/ — restarting so landed changes take effect"
  echo "${src}" > "${STALE_SRC_STATE}"
  restart_hub
}

cmd_once() {
  acquire_lock
  if health_ok; then
    reconcile_hub_pid
    # A HEALTHY hub can still be the wrong hub.
    check_hub_stale_source
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
      reconcile_hub_pid
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
