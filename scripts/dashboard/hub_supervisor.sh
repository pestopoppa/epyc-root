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
# relaunches the hub with the SAME launch spec the stack manager uses
# (manifest `handoff_dashboard`: argv, cwd, pythonpath, env — see below),
# with exponential backoff on repeated restart failures. It only ever touches
# :8100 — the orchestrator API (:8000) is never inspected or restarted.
#
# STABLE MARKER (grepped by preflights): HUB_SUPERVISOR_MANIFEST_LAUNCH_V1
#
# WHERE AND HOW THE HUB RUNS (2026-09-16): the orchestrator launch manifest
# decides, not this script. Its `handoff_dashboard` entry (cwd, pythonpath, env,
# argv) is the single source of truth, and it is resolved exactly as
# orchestrator_stack.start_aux_service resolves it (scripts/dashboard/
# hub_launch_spec.py). Orchestrator commit f5476148 (2026-09-09) deliberately
# points the hub at a reviewed lane checkout, so a hub served from a lane is
# INTENDED. The supervisor keeps two locations apart:
#   * its HOME (EPYC_ROOT): logs, pidfiles and state. This must be the canonical
#     root, or the supervisor refuses to run.
#   * the HUB SOURCE (the manifest cwd): what the hub serves, what the stale-source
#     check compares mtimes against, and what deploy-sync targets. Deploy-sync is
#     SKIPPED when the hub source is a linked worktree: never write into a lane.
# If the manifest cannot be read, the pre-2026-09-16 behaviour applies
# (cwd=EPYC_ROOT) and a loud warning is logged.
#
# READ-ONLY VIEW (2026-09-16, dashboard fix A). A lane served by the hub stops
# advancing when the lane does (the AutoKernel lane sat 141 commits behind), so the
# manifest now points the hub at a VIEW: a standalone clone (never a linked
# worktree) carrying the marker file `.epyc-view-readonly`, detached at
# origin/main. When the hub source is such a view, this supervisor runs the
# sibling scripts/dashboard/refresh_hub_view.sh every HUB_VIEW_REFRESH_INTERVAL_S
# (fetch + checkout --detach --force origin/main + regenerate the untracked index
# graph/state and handoff timeline). Deploy-sync is skipped for a view (the
# refresher already moves the whole tree). checkout rewrites only changed files,
# so the stale-source check restarts the hub on a dashboard code change and not
# on a handoff-only refresh.
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
#       hub_supervisor.sh plan            # resolved launch spec + sync/stale verdicts (read-only)
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
#   MAX_BACKOFF HEALTH_TIMEOUT STARTUP_TIMEOUT HUB_PYTHON EPYC_ROOT
#   HUB_CANONICAL_ROOT HUB_LAUNCH_MANIFEST HUB_SERVICE_NAME
#   HUB_VIEW_REFRESH_ENABLED HUB_VIEW_REFRESH_INTERVAL_S HUB_VIEW_MARKER
#   HUB_VIEW_REFRESHER.
# =============================================================================
set -euo pipefail

# --------------------------------------------------------------------------- #
# Configuration (all env-overridable)
# --------------------------------------------------------------------------- #
# EPYC_ROOT is the supervisor's HOME (logs, pidfiles, state). It is not the hub
# source; see the header.
HUB_CANONICAL_ROOT="${HUB_CANONICAL_ROOT:-/mnt/raid0/llm/epyc-root}"
EPYC_ROOT="${EPYC_ROOT:-${HUB_CANONICAL_ROOT}}"
HUB_LAUNCH_MANIFEST="${HUB_LAUNCH_MANIFEST:-/mnt/raid0/llm/epyc-orchestrator/orchestration/launch_manifest.yaml}"
HUB_SERVICE_NAME="${HUB_SERVICE_NAME:-handoff_dashboard}"
HUB_SPEC_HELPER="${HUB_SPEC_HELPER:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/hub_launch_spec.py}"
HUB_HOST="${HUB_HOST:-127.0.0.1}"
HUB_PORT="${HUB_PORT:-8100}"
HEALTH_PATH="${HEALTH_PATH:-/health}"
POLL_INTERVAL="${POLL_INTERVAL:-15}"     # seconds between healthy polls
MAX_BACKOFF="${MAX_BACKOFF:-300}"        # cap on restart backoff (seconds)
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-5}"    # per-probe curl timeout (seconds)
STARTUP_TIMEOUT="${STARTUP_TIMEOUT:-30}" # wait for /health after a relaunch
# Two-sample rule (agents/shared/INVARIANTS.md): a single failed probe is not
# enough to kill a hub — re-probe once after this delay before restarting.
HEALTH_CONFIRM_DELAY_S="${HEALTH_CONFIRM_DELAY_S:-3}"
# Deployment sync: how often to look for dashboard code landed on origin/main.
# A network fetch, so it is rate-limited independently of POLL_INTERVAL.
DEPLOY_SYNC_INTERVAL_S="${DEPLOY_SYNC_INTERVAL_S:-300}"
# Set to 0 to disable the sync entirely (the watchdog keeps working without it).
DEPLOY_SYNC_ENABLED="${DEPLOY_SYNC_ENABLED:-1}"
# Read-only view refresh (see header). Runs only when the hub source carries the
# marker and is not a linked worktree. Rate-limited like deploy-sync.
HUB_VIEW_REFRESH_ENABLED="${HUB_VIEW_REFRESH_ENABLED:-1}"
HUB_VIEW_REFRESH_INTERVAL_S="${HUB_VIEW_REFRESH_INTERVAL_S:-180}"
HUB_VIEW_MARKER="${HUB_VIEW_MARKER:-.epyc-view-readonly}"
# The supervisor's OWN sibling copy, never the view's: the refresher rewrites the
# view's files, and bash reads a running script incrementally.
HUB_VIEW_REFRESHER="${HUB_VIEW_REFRESHER:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/refresh_hub_view.sh}"

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

# Only a canonical home gets a logs/ dir. A non-canonical EPYC_ROOT (for example a
# lane) is refused below, and it must not have a logs/ dir created in it first.
if [[ -d "${EPYC_ROOT}" && "${EPYC_ROOT}" -ef "${HUB_CANONICAL_ROOT}" ]]; then
  mkdir -p "${LOG_DIR}"
fi

# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
log() {
  local ts
  ts="$(date '+%Y-%m-%dT%H:%M:%S%z')"
  if [[ -d "${LOG_DIR}" ]]; then
    printf '%s [hub-sup] %s\n' "${ts}" "$*" | tee -a "${SUP_LOG}" >&2
  else
    printf '%s [hub-sup] %s\n' "${ts}" "$*" >&2
  fi
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

# 0 iff /health fails on TWO probes HEALTH_CONFIRM_DELAY_S apart. A hub that is
# merely slow for one probe (host under load) must not be SIGTERMed for it.
hub_down_confirmed() {
  health_ok && return 1
  sleep "${HEALTH_CONFIRM_DELAY_S}"
  health_ok && { log "transient /health failure — second probe healthy, no action"; return 1; }
  return 0
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
# Launch spec: resolved from the orchestrator launch manifest
# --------------------------------------------------------------------------- #
# Sets HUB_SRC (the tree the hub serves), HUB_M_CWD, HUB_M_ARGV, HUB_M_ENV,
# HUB_M_RESOLVER and HUB_SPEC_SOURCE (manifest|fallback). It re-resolves only when
# the manifest mtime changes, so a poll does not spawn a python every 15s. It
# returns 0 either way: an unreadable manifest falls back to the old behaviour.
HUB_SRC=""
HUB_SPEC_SOURCE=""
HUB_SPEC_KEY=""
HUB_M_ARGV=()
HUB_M_ENV=()

resolve_hub_spec() {
  local key out
  key="$(stat -c '%Y' "${HUB_LAUNCH_MANIFEST}" 2>/dev/null || echo missing):${HUB_PYTHON}"
  [[ -n "${HUB_SPEC_SOURCE}" && "${key}" == "${HUB_SPEC_KEY}" ]] && return 0
  HUB_SPEC_KEY="${key}"
  if [[ -n "${HUB_PYTHON}" && -x "${HUB_PYTHON}" ]] \
     && out="$("${HUB_PYTHON}" "${HUB_SPEC_HELPER}" --manifest "${HUB_LAUNCH_MANIFEST}" \
                 --service "${HUB_SERVICE_NAME}" 2>>"$([[ -d "${LOG_DIR}" ]] && echo "${SUP_LOG}" || echo /dev/stderr)")"; then
    HUB_M_ARGV=(); HUB_M_ENV=()
    # The output is shlex-quoted assignments from our own helper.
    eval "${out}"
    if [[ -n "${HUB_M_CWD:-}" && ${#HUB_M_ARGV[@]} -gt 0 ]]; then
      HUB_SRC="${HUB_M_CWD}"
      HUB_SPEC_SOURCE="manifest"
      if [[ "${HUB_M_PORT:-}" != "${HUB_PORT}" ]]; then
        log "WARN: manifest ${HUB_SERVICE_NAME} port=${HUB_M_PORT:-?} but supervisor watches :${HUB_PORT}"
      fi
      log "launch spec: manifest ${HUB_LAUNCH_MANIFEST} [${HUB_SERVICE_NAME}] resolver=${HUB_M_RESOLVER:-?} hub source=${HUB_SRC}"
      return 0
    fi
  fi
  log "!!!! WARNING: launch manifest UNREADABLE (${HUB_LAUNCH_MANIFEST} [${HUB_SERVICE_NAME}]) !!!!"
  log "!!!! FALLING BACK to cwd=EPYC_ROOT=${EPYC_ROOT}; this may NOT be the hub source the stack declares !!!!"
  HUB_SPEC_SOURCE="fallback"
  HUB_SRC="${EPYC_ROOT}"
  HUB_M_CWD="${EPYC_ROOT}"
  HUB_M_RESOLVER="fallback"
  HUB_M_ARGV=("${HUB_PYTHON}" -m dashboard.server --host 0.0.0.0 --port "${HUB_PORT}")
  HUB_M_ENV=("PYTHONPATH=${EPYC_ROOT}${PYTHONPATH:+:${PYTHONPATH}}")
  return 0
}

# 0 iff git positively reports $1 as a LINKED worktree (--git-dir differs from
# --git-common-dir). A tree that git cannot describe does not count as linked.
is_linked_worktree() {
  local dirs gd cdir
  dirs="$(git -C "$1" rev-parse --path-format=absolute \
            --git-dir --git-common-dir 2>/dev/null || true)"
  gd="$(printf '%s\n' "${dirs}" | sed -n 1p)"
  cdir="$(printf '%s\n' "${dirs}" | sed -n 2p)"
  [[ -n "${gd}" && -n "${cdir}" && "${gd}" != "${cdir}" ]]
}

# 0 iff $1 is a read-only hub VIEW: carries the marker and is NOT a linked
# worktree (a lane is never a view, whatever files it contains).
is_hub_view() {
  [[ -n "${1:-}" && -f "$1/${HUB_VIEW_MARKER}" ]] || return 1
  ! is_linked_worktree "$1"
}

# --------------------------------------------------------------------------- #
# Launch a fresh hub, detached (mirrors orchestrator_stack.start_aux_service)
# --------------------------------------------------------------------------- #
start_hub() {
  resolve_hub_spec
  if [[ -z "${HUB_PYTHON}" || ! -x "${HUB_PYTHON}" ]]; then
    log "ERROR: no usable python interpreter (HUB_PYTHON='${HUB_PYTHON}')"
    return 1
  fi
  if [[ ! -f "${HUB_M_CWD}/dashboard/server.py" ]]; then
    log "ERROR: hub server not found at ${HUB_M_CWD}/dashboard/server.py (manifest cwd)"
    return 1
  fi
  log "launching hub (${HUB_SPEC_SOURCE}): ${HUB_M_ARGV[*]} (cwd=${HUB_M_CWD}; env: ${HUB_M_ENV[*]:-<none>})"
  # setsid fully detaches the hub so it outlives this supervisor; the supervisor
  # watches it by /health, not by being its parent.
  (
    cd "${HUB_M_CWD}"
    env "${HUB_M_ENV[@]}" setsid "${HUB_M_ARGV[@]}" \
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
# --------------------------------------------------------------------------- #
# Supervisor home — refuse unless EPYC_ROOT is the canonical root
# --------------------------------------------------------------------------- #
# The supervisor's HOME (logs, pidfiles, deploy/stale state) must be the canonical
# root, so every copy of this watchdog reads and writes one set of state. Where the
# HUB runs is a separate question, and the launch manifest answers it. A hub
# serving a lane is intended (orchestrator f5476148), so this guard never looks at
# the hub source. The comparison is `-ef` (same device and inode), so
# /workspace, a bind mount of the canonical root, passes.
refuse_noncanonical_home() {
  if [[ -d "${EPYC_ROOT}" && "${EPYC_ROOT}" -ef "${HUB_CANONICAL_ROOT}" ]]; then
    return 0
  fi
  log "REFUSING: supervisor home EPYC_ROOT=${EPYC_ROOT} is not the canonical root ${HUB_CANONICAL_ROOT}."
  log "  Unset EPYC_ROOT. The hub source comes from ${HUB_LAUNCH_MANIFEST} [${HUB_SERVICE_NAME}], not from EPYC_ROOT."
  exit 3
}

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

# Source mtimes come from the HUB SOURCE (the manifest cwd), which is the tree the
# running hub imported. EPYC_ROOT is only where this supervisor keeps its state.
hub_newest_source_mtime() {
  resolve_hub_spec
  [[ -n "${HUB_SRC}" ]] || return 0
  find "${HUB_SRC}/dashboard" -name '*.py' -newermt '@0' -printf '%T@\n' 2>/dev/null \
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

# --------------------------------------------------------------------------- #
# Deployment sync — bring dashboard code landed on origin/main into the SERVED tree
# (the manifest's hub source; skipped entirely when that is a linked worktree)
# --------------------------------------------------------------------------- #
#
# WHY (2026-08-28). The stale-source watchdog below answers "is the running hub
# older than dashboard/ ON DISK". It was working correctly and still reported
# nothing, because nothing ever updated dashboard/ on disk: the hub serves
# ${EPYC_ROOT} directly, that tree sat 35 commits behind origin/main, and four
# dashboard fixes published that day were invisible for hours. The watchdog closed
# "committed but not restarted"; this closes "committed but never arrived".
#
# THREE SAFETY RULES, each protecting something this repo has actually lost before:
#
#   1. NEVER touch the git INDEX. Files are written with `git show origin/main:path >
#      path`, never `git checkout --`. ${EPYC_ROOT} is a SHARED clone: a staged file
#      rides into whatever a peer commits next, under their name.
#   2. NEVER overwrite a locally-modified file. If the working copy differs from
#      local HEAD, someone is editing it — skip it and say so. `git checkout --` on
#      a peer's edit reverts it with no conflict and NO REFLOG.
#   3. NEVER move the branch pointer, and never push. The served branch legitimately
#      carries other sessions' unpushed commits; reconciling those is not a
#      watchdog's decision.
#
# Scope is dashboard/ ONLY. This is a dashboard watchdog; it has no business
# advancing handoffs, scripts, or anyone else's work.
DEPLOY_SYNC_STATE="${LOG_DIR}/hub_supervisor.deploy_sync"

# Seconds since the last sync attempt, or a large number if never.
deploy_sync_age_s() {
  local last now
  [[ -f "${DEPLOY_SYNC_STATE}" ]] || { echo 999999; return 0; }
  last="$(cat "${DEPLOY_SYNC_STATE}" 2>/dev/null || echo 0)"
  [[ "${last}" =~ ^[0-9]+$ ]] || { echo 999999; return 0; }
  now="$(date +%s)"
  echo $(( now - last ))
}

# Copy dashboard/ files that origin/main has and the working tree does not.
# Returns 0 always: a deployment sync must never take the watchdog down with it.
sync_dashboard_from_origin() {
  local changed=0 path skipped=0 wt_blob known past
  [[ "${DEPLOY_SYNC_ENABLED}" == "1" ]] || return 0
  (( $(deploy_sync_age_s) >= DEPLOY_SYNC_INTERVAL_S )) || return 0
  date +%s > "${DEPLOY_SYNC_STATE}" 2>/dev/null || true

  # Target the tree the hub SERVES (manifest cwd), never a lane this supervisor
  # does not own. A linked worktree belongs to the session running that lane; its
  # dashboard/ advances by that lane's commits, not by a watchdog writing
  # origin/main files into it. Skip the sync; the stale-source check still runs.
  resolve_hub_spec
  local tree="${HUB_SRC}"
  if [[ -z "${tree}" || ! -d "${tree}" ]]; then
    log "deploy-sync: SKIPPED — hub source '${tree}' is not a directory"
    return 0
  fi
  if is_linked_worktree "${tree}"; then
    log "deploy-sync: SKIPPED — hub source ${tree} is a linked worktree (lane-owned); stale-source check only"
    return 0
  fi
  if is_hub_view "${tree}"; then
    # The view refresher moves the WHOLE tree to origin/main; nothing to copy.
    return 0
  fi

  git -C "${tree}" fetch origin --quiet >/dev/null 2>&1 || {
    log "deploy-sync: fetch failed (offline?) — leaving the served tree alone"
    return 0
  }

  # Only files that DIFFER between the working tree's HEAD and origin/main.
  while IFS= read -r path; do
    [[ -n "${path}" ]] || continue
    # ALREADY CURRENT? Nothing to do.
    if [[ -f "${tree}/${path}" ]] \
       && git -C "${tree}" show "origin/main:${path}" 2>/dev/null \
          | cmp -s - "${tree}/${path}"; then
      continue
    fi
    # Rule 2: never overwrite work in progress -- but "work in progress" cannot be
    # "differs from local HEAD". The served tree deliberately runs dashboard/ at
    # origin/main content while HEAD lags by design, so that test called every
    # correctly-deployed file a hand edit and the sync stopped forever. It did,
    # twice, each time looking like success.
    #
    # The honest test is PROVENANCE: if the working blob is one this project
    # published for that path, it is a deployed version, not somebody's edit. A hand
    # edit produces a blob that has never existed on origin/main.
    if [[ -f "${tree}/${path}" ]]; then
      wt_blob="$(git -C "${tree}" hash-object "${tree}/${path}" 2>/dev/null || echo "")"
      known=0
      if [[ -n "${wt_blob}" ]]; then
        while IFS= read -r past; do
          [[ -n "${past}" ]] || continue
          if [[ "${past}" == "${wt_blob}" ]]; then known=1; break; fi
        done < <(git -C "${tree}" rev-list --max-count=100 origin/main -- "${path}" 2>/dev/null \
                 | while IFS= read -r c; do
                     git -C "${tree}" rev-parse "${c}:${path}" 2>/dev/null || true
                   done)
      fi
      # Also fine if it simply matches local HEAD, i.e. nobody has touched it.
      if (( known == 0 )) && git -C "${tree}" diff --quiet -- "${path}" 2>/dev/null; then
        known=1
      fi
      if (( known == 0 )); then
        log "deploy-sync: SKIP ${path} — content never published for this path; treating as local work"
        skipped=$(( skipped + 1 ))
        continue
      fi
    fi
    # A file deleted upstream is left in place deliberately: removing a served file
    # is not something a watchdog should decide unattended.
    if ! git -C "${tree}" cat-file -e "origin/main:${path}" 2>/dev/null; then
      log "deploy-sync: SKIP ${path} — absent on origin/main (deletion is operator work)"
      skipped=$(( skipped + 1 ))
      continue
    fi
    # Rule 1: write the FILE, never the index.
    if git -C "${tree}" show "origin/main:${path}" > "${tree}/${path}" 2>/dev/null; then
      log "deploy-sync: updated ${path} from origin/main"
      changed=$(( changed + 1 ))
    else
      log "deploy-sync: FAILED to write ${path}"
    fi
  done < <(git -C "${tree}" diff --name-only HEAD origin/main -- dashboard/ 2>/dev/null || true)

  if (( changed > 0 )); then
    log "deploy-sync: ${changed} dashboard file(s) updated; the stale-source check restarts the hub"
  fi
  (( skipped > 0 )) && log "deploy-sync: ${skipped} file(s) skipped (see reasons above)"
  return 0
}

# --------------------------------------------------------------------------- #
# Read-only view refresh — advance the served VIEW to origin/main
# --------------------------------------------------------------------------- #
HUB_VIEW_REFRESH_STATE="${LOG_DIR}/hub_supervisor.view_refresh"

view_refresh_age_s() {
  local last now
  last="$(cat "${HUB_VIEW_REFRESH_STATE}" 2>/dev/null || echo)"
  [[ "${last}" =~ ^[0-9]+$ ]] || { echo 999999; return 0; }
  now="$(date +%s)"
  echo $(( now - last ))
}

# Returns 0 always: a refresh failure must never take the watchdog down. It only
# ever acts on a marked, non-linked hub source, so a lane or the canonical root is
# never force-checked-out.
refresh_hub_view() {
  [[ "${HUB_VIEW_REFRESH_ENABLED}" == "1" ]] || return 0
  resolve_hub_spec
  is_hub_view "${HUB_SRC}" || return 0
  (( $(view_refresh_age_s) >= HUB_VIEW_REFRESH_INTERVAL_S )) || return 0
  date +%s > "${HUB_VIEW_REFRESH_STATE}" 2>/dev/null || true
  if [[ ! -x "${HUB_VIEW_REFRESHER}" ]]; then
    log "view-refresh: refresher ${HUB_VIEW_REFRESHER} missing or not executable"
    return 0
  fi
  local rc=0
  HUB_VIEW_LOG="$([[ -d "${LOG_DIR}" ]] && echo "${SUP_LOG}" || echo "")" \
  HUB_VIEW_MARKER="${HUB_VIEW_MARKER}" HUB_VIEW_PYTHON="${HUB_PYTHON}" \
    "${HUB_VIEW_REFRESHER}" "${HUB_SRC}" </dev/null 9>&- || rc=$?
  (( rc == 0 )) || log "view-refresh: refresher exited ${rc} for ${HUB_SRC} (hub keeps serving the last good view)"
  return 0
}

check_hub_stale_source() {
  local src rc=0
  # Resolve in THIS shell: the mtime probe runs in command substitutions, and a
  # spec resolved only inside a subshell would be re-resolved on every call.
  resolve_hub_spec
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
  log "hub is serving code OLDER than ${HUB_SRC}/dashboard/ — restarting so landed changes take effect"
  echo "${src}" > "${STALE_SRC_STATE}"
  # Callers run this as a simple command under `set -e`; a bare failing
  # restart_hub here used to terminate the LOOP daemon itself (and leave the hub
  # killed). Report failure to the caller explicitly instead.
  restart_hub || { log "stale-source restart FAILED — hub may be down"; return 1; }
}

cmd_once() {
  refuse_noncanonical_home
  acquire_lock
  if ! hub_down_confirmed; then
    reconcile_hub_pid
    # Same healthy-path sequence as cmd_loop (view refresh, sync, then stale-source
    # check), so a cron `once` covers the whole surface while the daemon is dead.
    refresh_hub_view
    sync_dashboard_from_origin
    # A HEALTHY hub can still be the wrong hub.
    check_hub_stale_source || return 1
    log "once: hub healthy — no restart needed"
    return 0
  fi
  log "once: hub down (confirmed by two probes) — attempting restart"
  restart_hub
}

cmd_loop() {
  refuse_noncanonical_home
  acquire_lock
  echo "$$" > "${SUP_PIDFILE}"
  trap 'log "supervisor exiting (pid $$)"; rm -f "${SUP_PIDFILE}"' EXIT
  log "supervisor started (pid $$); watching :${HUB_PORT}${HEALTH_PATH} every ${POLL_INTERVAL}s"
  local backoff="${POLL_INTERVAL}"
  while true; do
    if health_ok; then
      reconcile_hub_pid
      # DEPLOYMENT (2026-08-28). These were missing here while `loop` is the mode
      # the long-lived supervisor actually uses. (2026-09-16: `cmd_once` now runs
      # the same sequence — before that it lacked the sync.)
      #
      # Order matters: refresh/sync first so the stale-source check sees the new
      # mtimes on the same pass and restarts once, rather than a cycle later.
      refresh_hub_view
      sync_dashboard_from_origin
      # A HEALTHY hub can still be the wrong hub.
      check_hub_stale_source || true   # failure: next poll takes the unhealthy path
      backoff="${POLL_INTERVAL}"
      sleep "${POLL_INTERVAL}"
      continue
    fi
    if ! hub_down_confirmed; then
      sleep "${POLL_INTERVAL}"
      continue
    fi
    log "hub UNHEALTHY (confirmed by two probes) — restarting"
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

# Read-only: what would this supervisor do right now? Never syncs, never restarts.
cmd_plan() {
  resolve_hub_spec
  local rc=0 live livecwd
  echo "home        : ${EPYC_ROOT} (canonical ${HUB_CANONICAL_ROOT}: $([[ "${EPYC_ROOT}" -ef "${HUB_CANONICAL_ROOT}" ]] && echo yes || echo NO — would refuse))"
  echo "spec source : ${HUB_SPEC_SOURCE} (resolver ${HUB_M_RESOLVER:-?}; ${HUB_LAUNCH_MANIFEST} [${HUB_SERVICE_NAME}])"
  echo "hub source  : ${HUB_SRC}"
  echo "argv        : ${HUB_M_ARGV[*]}"
  echo "env         : ${HUB_M_ENV[*]:-<none>}"
  if is_linked_worktree "${HUB_SRC}"; then
    echo "deploy-sync : SKIP (hub source is a linked worktree)"
    echo "view-refresh: no (linked worktree is never a view)"
  elif is_hub_view "${HUB_SRC}"; then
    echo "deploy-sync : SKIP (hub source is a read-only view; the refresher owns it)"
    echo "view-refresh: enabled=${HUB_VIEW_REFRESH_ENABLED} every ${HUB_VIEW_REFRESH_INTERVAL_S}s via ${HUB_VIEW_REFRESHER} (view HEAD $(git -C "${HUB_SRC}" rev-parse --short HEAD 2>/dev/null || echo '?'))"
  else
    echo "deploy-sync : enabled=${DEPLOY_SYNC_ENABLED} (primary checkout or non-git tree)"
    echo "view-refresh: no (no ${HUB_VIEW_MARKER} marker)"
  fi
  live="$(hub_pids)"; live="${live%% *}"
  if [[ -n "${live}" ]]; then
    livecwd="$(readlink "/proc/${live}/cwd" 2>/dev/null || echo '?')"
    echo "live hub    : pid ${live} cwd ${livecwd}$([[ "${livecwd}" -ef "${HUB_SRC}" ]] || echo '  (DIFFERS from the manifest cwd)')"
    # A relaunch applies the MANIFEST env; show where the live hub disagrees.
    local kv key livev
    for kv in "${HUB_M_ENV[@]}"; do
      key="${kv%%=*}"
      livev="$(tr '\0' '\n' < "/proc/${live}/environ" 2>/dev/null | sed -n "s|^${key}=||p" | head -1 || true)"
      [[ "${key}=${livev}" == "${kv}" ]] \
        || echo "env drift   : ${key}: live='${livev}' manifest='${kv#*=}' (a relaunch applies the manifest value)"
    done
  else
    echo "live hub    : none on :${HUB_PORT}"
  fi
  hub_source_is_newer || rc=$?
  case "${rc}" in
    0) echo "stale-source: STALE (the next healthy poll restarts the hub)" ;;
    1) echo "stale-source: current" ;;
    *) echo "stale-source: unavailable" ;;
  esac
}

usage() {
  cat <<EOF
hub_supervisor.sh — userspace watchdog for the :${HUB_PORT} dashboard hub

Usage: hub_supervisor.sh [loop|once|status|plan|help]
  loop    (default) supervise forever: poll /health, restart on failure w/ backoff
  once    one pass of loop: restart if down (two probes), else view refresh + sync + stale check
  status  print hub + supervisor liveness and exit
  plan    print the manifest-resolved launch spec and sync/stale verdicts (read-only)
  help    this message

Never restarts a healthy hub. Only ever touches :${HUB_PORT} (never :8000).
EOF
}

main() {
  case "${1:-loop}" in
    loop)   cmd_loop ;;
    once)   cmd_once ;;
    status) cmd_status ;;
    plan)   cmd_plan ;;
    help|-h|--help) usage ;;
    *) usage; exit 2 ;;
  esac
}

main "$@"
