#!/bin/bash
# =============================================================================
# backfill_supervisor.sh — userspace watchdog for hardware_backfill.py
# =============================================================================
#
# WHY: modelled directly on bus_supervisor.sh, the coordinator-daemon's own
# watchdog. hardware_backfill.py is the mechanism that closes the
# 2026-08-11/12 hardware-idle gap (19 READY compute-gated tasks, 3h47m idle,
# 590 unread advisory.jsonl records nothing reads) by draining a bounded
# queue of region-lock-wrapped jobs and reporting, once, when the queue is
# empty while known READY work exists. If the runner dies silently, that gap
# reopens with nobody watching — so it gets the same watchdog shape as the
# coordinator-daemon: poll a heartbeat, do nothing while healthy, clear +
# relaunch on staleness/death, back off on repeated failure.
#
# WHAT THIS SCRIPT NEVER DOES: it never touches a CPU region, never starts an
# inference/benchmark run, and never preempts anything — that is entirely
# hardware_backfill.py's job (which itself only ever wraps `region-lock run`,
# waiting its turn like any other caller). This script's ENTIRE job is
# "is the runner alive; if not, relaunch it."
#
# C42 LESSON (verify the target's source exists before launching, never
# predate it): a supervisor that launches a target whose source file was
# deleted or moved crash-loops forever on a useless error every cycle.
# `source_present` checks explicitly and REFUSES to launch — logged, backed
# off — rather than trying and failing into that loop.
#
# NOT STARTED BY THIS COMMIT. Launching a new supervisor is the
# coordinator/operator's boundary (coordination/backfill/README.md); this
# delivers code only.
#
# ---------------------------------------------------------------------------
# ADOPTION
# ---------------------------------------------------------------------------
#   Start (detached, survives logout; idempotent — a 2nd copy self-exits):
#       nohup /workspace/scripts/coordination/backfill_supervisor.sh \
#             > /workspace/logs/backfill_supervisor.out 2>&1 &
#
#   One-shot check (for a cron entry instead of the loop):
#       */2 * * * * /workspace/scripts/coordination/backfill_supervisor.sh once
#
#   Inspect / stop:
#       backfill_supervisor.sh status
#       kill "$(cat /workspace/logs/backfill_supervisor.pid)"
#
# ROLLBACK: stop the supervisor and the runner. queue.jsonl / done.jsonl are
# inert files; nothing else in the fleet depends on the runner being alive
# (the detector is advisory-only, and every launched job is bounded).
set -euo pipefail

EPYC_ROOT="${EPYC_ROOT:-/workspace}"
RUNNER="${RUNNER:-${EPYC_ROOT}/scripts/coordination/hardware_backfill.py}"
QUEUE_DIR="${QUEUE_DIR:-${EPYC_ROOT}/coordination/backfill}"
HEARTBEAT="${HEARTBEAT:-${QUEUE_DIR}/heartbeat.json}"
PY="${PY:-python3}"

POLL_INTERVAL="${POLL_INTERVAL:-20}"       # seconds between healthy polls
STALE_AFTER="${STALE_AFTER:-120}"          # heartbeat older than this => unhealthy
MAX_BACKOFF="${MAX_BACKOFF:-300}"          # cap on restart backoff
STARTUP_TIMEOUT="${STARTUP_TIMEOUT:-30}"   # wait for a fresh heartbeat after relaunch

LOG_DIR="${EPYC_ROOT}/logs"
SUP_LOG="${LOG_DIR}/backfill_supervisor.log"
RUNNER_LOG="${LOG_DIR}/hardware_backfill.out"
LOCK_FILE="${LOCK_FILE:-/tmp/backfill_supervisor.lock}"   # overridable so tests isolate
SUP_PIDFILE="${LOG_DIR}/backfill_supervisor.pid"

# Deliberately specific so it cannot match this supervisor's own command line,
# and scoped to `run` so it never matches a one-shot `once` invocation either.
# INC-20260731-broad-process-pattern-kills: `pgrep -f` matches the WHOLE
# command line on a SHARED host — never widen this to a bare basename.
RUNNER_PATTERN="${RUNNER_PATTERN:-hardware_backfill\\.py run}"

mkdir -p "$LOG_DIR"

log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "$SUP_LOG" >&2; }

heartbeat_age_s() {
  [[ -f "$HEARTBEAT" ]] || { echo 999999; return; }
  local mtime now
  mtime=$(stat -c %Y "$HEARTBEAT" 2>/dev/null || echo 0)
  now=$(date +%s)
  echo $(( now - mtime ))
}

runner_pids() { pgrep -f "$RUNNER_PATTERN" 2>/dev/null || true; }

health_ok() {
  local age; age=$(heartbeat_age_s)
  [[ -n "$(runner_pids)" ]] && (( age <= STALE_AFTER ))
}

source_present() { [[ -f "$RUNNER" ]]; }

stop_wedged() {
  local pids; pids=$(runner_pids)
  [[ -z "$pids" ]] && return 0
  log "stopping wedged runner pid(s): ${pids//$'\n'/ }"
  # SIGTERM first: hardware_backfill.py drains at its own boundary (forwards
  # SIGTERM to in-flight children via region-lock's signal forwarding, which
  # releases their region locks cleanly) — never a first-resort kill.
  kill $pids 2>/dev/null || true
  for _ in $(seq 1 15); do
    sleep 1
    [[ -z "$(runner_pids)" ]] && return 0
  done
  log "escalating to SIGKILL"
  kill -9 $(runner_pids) 2>/dev/null || true
  sleep 1
}

start_runner() {
  if ! source_present; then
    log "REFUSING to launch: $RUNNER does not exist (C42 — never launch a target whose"
    log "  source is gone; that crash-loops on a useless error every cycle instead)"
    return 1
  fi
  log "launching hardware_backfill.py run (queue-dir=$QUEUE_DIR)"
  # `9>&-` closes this supervisor's own flock fd in the child (see
  # bus_supervisor.sh's identical note) — without it, the runner inherits the
  # supervisor's lock for its whole life and no supervisor can start again
  # while it lives.
  nohup "$PY" "$RUNNER" run --queue-dir "$QUEUE_DIR" 9>&- >>"$RUNNER_LOG" 2>&1 &
  local waited=0
  while (( waited < STARTUP_TIMEOUT )); do
    sleep 1; waited=$(( waited + 1 ))
    if health_ok; then log "runner healthy after ${waited}s"; return 0; fi
  done
  log "runner did NOT become healthy within ${STARTUP_TIMEOUT}s"
  return 1
}

acquire_supervisor_lock() {
  exec 9>"$LOCK_FILE"
  if flock -n 9; then
    return 0
  fi
  log "another supervisor holds the lock; exiting"
  return 1
}

check_once() {
  if health_ok; then return 0; fi
  if ! source_present; then
    log "runner source missing ($RUNNER) — refusing to (re)start; reporting only"
    return 0
  fi
  log "unhealthy (heartbeat age $(heartbeat_age_s)s, pids '$(runner_pids | tr '\n' ' ')') — restarting"
  stop_wedged
  start_runner
}

case "${1:-loop}" in
  status)
    age=$(heartbeat_age_s); pids=$(runner_pids | tr '\n' ' ')
    printf 'runner pids   : %s\n' "${pids:-none}"
    printf 'source present: %s\n' "$( source_present && echo yes || echo NO )"
    printf 'heartbeat     : %ss old (stale after %ss)\n' "$age" "$STALE_AFTER"
    printf 'supervisor    : %s\n' "$( [[ -f "$SUP_PIDFILE" ]] && cat "$SUP_PIDFILE" || echo 'not running')"
    health_ok && printf 'health        : OK\n' || printf 'health        : UNHEALTHY\n'
    exit 0
    ;;
  once)
    acquire_supervisor_lock || exit 0
    check_once
    exit 0
    ;;
  loop)
    acquire_supervisor_lock || exit 0
    echo $$ > "$SUP_PIDFILE"
    trap 'rm -f "$SUP_PIDFILE"; log "supervisor stopped"; exit 0' TERM INT
    log "supervisor started (poll ${POLL_INTERVAL}s, stale after ${STALE_AFTER}s, runner=$RUNNER)"
    backoff=0
    while true; do
      if health_ok; then
        backoff=0
        sleep "$POLL_INTERVAL"
        continue
      fi
      check_once || true
      if health_ok; then
        backoff=0
      else
        backoff=$(( backoff == 0 ? 10 : backoff * 2 ))
        (( backoff > MAX_BACKOFF )) && backoff=$MAX_BACKOFF
        log "restart failed (or refused); backing off ${backoff}s"
        sleep "$backoff"
      fi
    done
    ;;
  *)
    printf 'usage: %s [loop|once|status]\n' "$(basename "$0")" >&2
    exit 64
    ;;
esac
