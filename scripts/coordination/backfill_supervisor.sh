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

# Canonical roots from ONE place (B7, 2026-08-12): env.sh resolves EPYC_ROOT to the
# canonical checkout from ANY worktree, so a lane-worktree copy of this supervisor
# still finds the one runner, the one queue dir and the one heartbeat.
_BS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${_BS_DIR}/../lib/env.sh"
RUNNER="${RUNNER:-${EPYC_ROOT}/scripts/coordination/hardware_backfill.py}"
QUEUE_DIR="${QUEUE_DIR:-${EPYC_ROOT}/coordination/backfill}"
HEARTBEAT="${HEARTBEAT:-${QUEUE_DIR}/heartbeat.json}"
PY="${PY:-python3}"

POLL_INTERVAL="${POLL_INTERVAL:-20}"       # seconds between healthy polls
STALE_AFTER="${STALE_AFTER:-120}"          # heartbeat older than this => unhealthy
MAX_BACKOFF="${MAX_BACKOFF:-300}"          # cap on restart backoff
STARTUP_TIMEOUT="${STARTUP_TIMEOUT:-30}"   # wait for a fresh heartbeat after relaunch

# TEST HOOK, and the ONLY one. 0 (the default, i.e. unset) means "loop forever" —
# production behaviour is bit-identical to a loop with no budget at all. A positive
# value stops the loop after that many iterations and makes the in-loop waits
# return immediately once the budget is spent, so `loop` — THE consumer, the one
# whose dangling `health_ok` call survived for two days precisely because no test
# ever ran it — is drivable by a test in under a second instead of paying a 300s
# backoff to observe one decision.
LOOP_MAX_ITERATIONS="${LOOP_MAX_ITERATIONS:-0}"
_loop_iters=0
_loop_budget_exhausted() {
  (( LOOP_MAX_ITERATIONS > 0 )) || return 1
  (( _loop_iters >= LOOP_MAX_ITERATIONS ))
}
# Every wait inside `loop` goes through here. With no budget set this is `sleep`.
sup_sleep() {
  _loop_budget_exhausted && return 0
  sleep "$1"
}

LOCK_FILE="${LOCK_FILE:-/tmp/backfill_supervisor.lock}"   # overridable so tests isolate
# NOTE: LOG_DIR and everything derived from it are assigned BELOW, after the last
# `source` — see the block just above `mkdir -p`. Assigning them here is wrong and
# fails in a way that only shows up in a sandbox.

# Substring used ONLY to corroborate identity in a read-only /proc walk. It is
# never a kill target and never the sole basis for a verdict — see the observation
# contract below.
RUNNER_MARK="${RUNNER_MARK:-hardware_backfill.py}"

# --------------------------------------------------------------------------- #
# OBSERVATION CONTRACT (adopted 2026-08-12)
# --------------------------------------------------------------------------- #
# This file used to say `runner_pids() { pgrep -f "$RUNNER_PATTERN"; }` and
# `health_ok() { [[ -n "$(runner_pids)" ]] && (( age <= STALE_AFTER )); }` — the
# exact two-state shape that made `bus_supervisor.sh` declare a healthy,
# heartbeating coordinator-daemon dead FOREVER and relaunch-loop for hours in
# silence (the daemon's real argv had `--bus-root <path>` between `.py` and `run`,
# so the pattern matched nothing). One `&&` turned "I cannot see it" into "it is
# dead", and there was no third state to say otherwise.
#
# Identity now comes from the runner's OWN published pid, corroborated by an
# independent read-only /proc walk, folded three-valued by observer_guard.sh.
# Disagreement between the two, or a channel that cannot be evaluated at all, is
# `unobservable`: alarm loudly, touch NOTHING. Only `absent` licenses action.
#
# (`health_ok` DOES exist again, further down, and it is NOT the two-state function
# quoted above — it returns 0/1/3 and its callers must capture the code. It came
# back because deleting it left `loop`'s two call sites dangling; see P0-4 there.)
# shellcheck source=scripts/coordination/observer_guard.sh
source "${EPYC_ROOT}/scripts/coordination/observer_guard.sh"

# --------------------------------------------------------------------------- #
# LOG PATHS — assigned HERE, AFTER THE LAST `source`, and that is load-bearing.
# --------------------------------------------------------------------------- #
#
# THE KNOB IS `BACKFILL_LOG_DIR`, NOT `LOG_DIR`, AND THAT IS NOT A STYLE CHOICE.
# `scripts/lib/env.sh` does an UNCONDITIONAL `export LOG_DIR=...` — it honours no
# caller value — so `LOG_DIR="${LOG_DIR:-...}"` would read env.sh's value, never
# the sandbox's, and isolate NOTHING while looking exactly like isolation.
#
# AND THE POSITION MATTERS AS MUCH AS THE NAME. observer_guard.sh sources env.sh
# AGAIN, so an assignment placed above that `source` is silently overwritten by
# it. Measured while fixing P0-4: LOG_DIR was reset to the production logs dir
# while SUP_LOG kept the sandbox path captured a line earlier, `mkdir -p` then
# created the PRODUCTION dir, and every `log` call died on
# `tee: .../logs/backfill_supervisor.log: No such file or directory` — which under
# `set -euo pipefail` aborts the whole supervisor at its first log line. The
# observation-contract harness caught it as "did NOT start its target when it was
# genuinely absent": a watchdog that cannot open its log stops watching.
#
# Sandboxing this supervisor therefore needs BACKFILL_LOG_DIR; before it existed,
# every contract-harness run appended to the production supervisor log instead.
LOG_DIR="${BACKFILL_LOG_DIR:-${EPYC_ROOT}/logs}"
SUP_LOG="${LOG_DIR}/backfill_supervisor.log"
RUNNER_LOG="${LOG_DIR}/hardware_backfill.out"
SUP_PIDFILE="${LOG_DIR}/backfill_supervisor.pid"

mkdir -p "$LOG_DIR"

log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "$SUP_LOG" >&2; }

heartbeat_age_s() {
  [[ -f "$HEARTBEAT" ]] || { echo 999999; return; }
  local mtime now
  mtime=$(stat -c %Y "$HEARTBEAT" 2>/dev/null || echo 0)
  now=$(date +%s)
  echo $(( now - mtime ))
}

# The AUTHORITATIVE identity: the pid the runner publishes about itself. The only
# pid this script will ever signal.
runner_pid() { og_json_pid "$HEARTBEAT"; }

# Three-valued identity verdict: present | absent | unobservable.
# Echoes the state; exit 0 / 1 / 3 respectively.
observe_runner() {
  og_round_begin
  local pid; pid="$(runner_pid)"

  if [[ ! -e "$HEARTBEAT" ]]; then
    # No heartbeat at all: the runner has never started here, or its queue dir
    # was wiped. That is a real negative, not a blind spot.
    og_channel hb_pid absent "no heartbeat file at $HEARTBEAT"
  elif [[ ! -r "$HEARTBEAT" ]]; then
    og_channel hb_pid unavailable "heartbeat exists but is unreadable"
  elif [[ -z "$pid" ]]; then
    og_channel hb_pid unavailable "heartbeat carries no parsable pid"
  else
    og_channel hb_pid "$(og_pid_alive "$pid" "$RUNNER_MARK")" "pid=$pid"
  fi

  # Independent corroboration. NOT a kill target (shared host — see
  # INC-20260731-broad-process-pattern-kills); its only job is to disagree.
  if [[ -r /proc/self/cmdline ]]; then
    og_channel proc_scan "$(og_present_if_any "$(og_proc_scan "$RUNNER_MARK")")"
  else
    og_channel proc_scan unavailable "/proc not readable"
  fi

  og_verdict
}

# Health is a SEPARATE axis from identity, and conflating the two is the bug this
# file was rewritten to avoid: a live runner with a stale heartbeat is `present`
# and WEDGED (actionable), not `unobservable`.
heartbeat_fresh() { (( $(heartbeat_age_s) <= STALE_AFTER )); }

# --------------------------------------------------------------------------- #
# health_ok — THE LOOP'S PREDICATE, three-valued (P0-4, 2026-08-14)
# --------------------------------------------------------------------------- #
#
# THE DEFECT THIS CLOSES. The observation-contract rewrite (ed38041d) replaced the
# two-state `health_ok` quoted in the header above with `observe_runner` +
# `heartbeat_fresh`, and updated `start_runner`, `check_once` and `status` to use
# them — but it left the `loop` case block calling `health_ok`, which from that
# commit onward was DEFINED NOWHERE. Under `set -e` a `command not found` inside an
# `if` condition is not fatal, it is merely FALSE, so loop mode took the failure
# branch on EVERY iteration against a perfectly healthy runner: relaunch, "restart
# failed", back off, doubling to the 300s cap, forever and in silence. The exact
# family the rewrite existed to kill, reintroduced by the rewrite's own dangling
# call site — and invisible because the tests exercised `once`/`observe`, i.e. A
# consumer and not THE consumer.
#
# THREE VALUES, NOT TWO — the return code IS the verdict:
#
#   0  HEALTHY        present AND heartbeat fresh. Do nothing.
#   1  ACTIONABLE     absent (start it), or present-but-stale (wedged, restart it).
#                     Both are real negatives that license corrective action.
#   3  UNOBSERVABLE   this supervisor CANNOT TELL. Corrective action forbidden.
#
# Note carefully what is NOT here. `unobservable` is not folded into 1: doing so
# would restart-loop a possibly-healthy runner (the specimen's failure), and it is
# not folded into 0 either, which is the fail-open twin the callers must never be
# handed — an unreadable health signal read as "fine" leaves the runner unwatched
# while everything looks green (C3/C6/C8). The caller gets the third value and has
# to say what it does with it.
#
# `if health_ok` IS THEREFORE A BUG AT ANY CALL SITE. 3 is falsy, so that idiom
# re-collapses the third state into "unhealthy" at the point of use. Callers must
# capture: `rc=0; health_ok || rc=$?`. (`|| rc=$?`, never `health_ok; rc=$?` — a
# function returning non-zero as a simple command aborts the whole supervisor under
# `set -e`, which is how a watchdog silently stops watching.)
health_ok() {
  # `|| true` is load-bearing: og_verdict exits 1/3 BY DESIGN and a failing command
  # substitution in an assignment aborts the script under `set -e`.
  local state; state="$(observe_runner)" || true
  case "$state" in
    present)
      # Seeing the target is proof the eyes work — the loop's healthy path is the
      # only path that runs on a well behaved fleet, so the blind-streak counter
      # has to be cleared HERE or detector B slowly poisons a healthy supervisor.
      og_note_sighting
      if heartbeat_fresh; then og_clear; return 0; fi
      return 1   # alive but not ticking: WEDGED. Actionable, and check_once says so.
      ;;
    absent)       return 1 ;;
    unobservable) return 3 ;;
    *)
      # og_verdict only ever prints the three states; anything else means the
      # observation itself broke. That is a blind spot, never a clean bill.
      return 3
      ;;
  esac
}

source_present() { [[ -f "$RUNNER" ]]; }

stop_wedged() {
  # ONE pid, from the AUTHORITATIVE channel, re-verified before every signal.
  # The old body signalled every pid a `pgrep -f` returned and then `kill -9`'d
  # whatever it returned a second time — on a shared host that is a wildcard over
  # other sessions' processes, and the re-read could name a pid that had been
  # recycled between the two calls.
  local pid; pid="$(runner_pid)"
  [[ -n "$pid" ]] || return 0
  [[ "$(og_pid_alive "$pid" "$RUNNER_MARK")" == "present" ]] || return 0
  log "stopping wedged runner pid $pid"
  # SIGTERM first: hardware_backfill.py drains at its own boundary (forwards
  # SIGTERM to in-flight children via region-lock's signal forwarding, which
  # releases their region locks cleanly) — never a first-resort kill.
  kill "$pid" 2>/dev/null || true
  for _ in $(seq 1 15); do
    sleep 1
    [[ "$(og_pid_alive "$pid" "$RUNNER_MARK")" == "present" ]] || return 0
  done
  log "escalating to SIGKILL on pid $pid"
  # Re-verify identity one last time: 15s is long enough for the pid to have
  # exited and been reissued to somebody else's process.
  if [[ "$(og_pid_alive "$pid" "$RUNNER_MARK")" == "present" ]]; then
    kill -9 "$pid" 2>/dev/null || true
  fi
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
  # LAUNCH IS THE POSITIVE CONTROL. From here on, "I still cannot see it" is
  # evidence about this observer, not about the runner — og_note_launch arms the
  # blind-streak detector so that N fruitless relaunch cycles force `unobservable`
  # instead of looping in silence forever, which is exactly what the specimen did.
  og_note_launch
  local waited=0 st
  while (( waited < STARTUP_TIMEOUT )); do
    sleep 1; waited=$(( waited + 1 ))
    # `|| true` is LOAD-BEARING: og_verdict exits 1 (absent) / 3 (unobservable)
    # by design, and under `set -e` a failing command substitution in an
    # assignment aborts the whole supervisor. Without it the three-state
    # verdict silently kills the watchdog instead of being acted on.
    st="$(observe_runner)" || true
    if [[ "$st" == "present" ]] && heartbeat_fresh; then
      og_note_sighting; og_clear
      log "runner healthy after ${waited}s"; return 0
    fi
  done
  log "runner did NOT become healthy within ${STARTUP_TIMEOUT}s (last observation: ${st:-none})"
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
  local state; state="$(observe_runner)" || true   # see start_runner: og_verdict exits non-zero by design

  case "$state" in
    unobservable)
      # THE STATE THE SPECIMEN LACKED. Corrective action is forbidden here: the
      # runner may be perfectly healthy and it is this observer that is broken.
      # Alarm and return — do NOT kill, do NOT relaunch, do NOT back off quietly.
      og_alarm "$(og_why)"
      log "OBSERVER-BLIND — suppressing all corrective action: $(og_why)"
      return 0
      ;;
    present)
      og_note_sighting
      if heartbeat_fresh; then og_clear; return 0; fi
      log "runner pid $(runner_pid) is alive but its heartbeat is $(heartbeat_age_s)s old (stale after ${STALE_AFTER}s) — WEDGED, restarting"
      ;;
    absent)
      log "runner is absent (${OG_WHY:-no runner process}) — starting"
      ;;
  esac

  if ! source_present; then
    log "runner source missing ($RUNNER) — refusing to (re)start; reporting only"
    return 0
  fi
  stop_wedged
  start_runner
}

# Uniform observation entrypoint required of every watchdog under the observation
# contract. Externally testable: `tests/test_observer_contract.py` drives THIS,
# for every registered watchdog, so a sibling watchdog cannot quietly skip the
# conformance a per-file test would only ever give to one file.
cmd_observe() {
  local state; state="$(observe_runner)" || true   # see start_runner: og_verdict exits non-zero by design
  printf 'state=%s\n' "$state"
  printf 'why=%s\n' "$(og_why)"
  case "$state" in
    present) return 0 ;;
    absent)  return 1 ;;
    *)       return 3 ;;
  esac
}

og_init backfill_supervisor

case "${1:-loop}" in
  observe)
    cmd_observe
    exit $?
    ;;
  status)
    age=$(heartbeat_age_s); state="$(observe_runner)" || true
    printf 'observation   : %s\n' "$state"
    printf '  why         : %s\n' "$(og_why)"
    printf 'runner pid    : %s\n' "$(runner_pid || true)"
    printf 'blind streak  : %s (alarm at %s)\n' "$(og_blind_streak)" "$OG_BLIND_STREAK_MAX"
    printf 'source present: %s\n' "$( source_present && echo yes || echo NO )"
    printf 'heartbeat     : %ss old (stale after %ss)\n' "$age" "$STALE_AFTER"
    printf 'supervisor    : %s\n' "$( [[ -f "$SUP_PIDFILE" ]] && cat "$SUP_PIDFILE" || echo 'not running')"
    # THREE lines, never two. Printing `UNHEALTHY` for `unobservable` is how the
    # operator-facing view re-collapses the third state that the code just won.
    case "$state" in
      present) heartbeat_fresh && printf 'health        : OK\n' || printf 'health        : WEDGED (alive, heartbeat stale)\n' ;;
      absent)  printf 'health        : DOWN (runner absent)\n' ;;
      *)       printf 'health        : %s — CANNOT OBSERVE (this supervisor is the suspect)\n' "$OG_ALARM_TOKEN" ;;
    esac
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
    rc=0
    while true; do
      if _loop_budget_exhausted; then
        log "LOOP_MAX_ITERATIONS=${LOOP_MAX_ITERATIONS} reached — exiting (bounded-loop test hook)"
        rm -f "$SUP_PIDFILE"
        exit 0
      fi
      _loop_iters=$(( _loop_iters + 1 ))

      # `rc=0; health_ok || rc=$?` — NOT `if health_ok`. health_ok is three-valued
      # and 3 is falsy, so the `if` form silently re-collapses `unobservable` into
      # "unhealthy, restart it", which is the specimen bug wearing the fix's clothes.
      rc=0; health_ok || rc=$?

      if (( rc == 0 )); then
        backoff=0
        sup_sleep "$POLL_INTERVAL"
        continue
      fi

      if (( rc == 3 )); then
        # CANNOT TELL. check_once's `unobservable` branch is THE canonical response
        # (alarm loudly, touch nothing), so it is reused rather than restated here.
        # What must NOT happen is the two lines below it: re-testing health after a
        # no-op and scoring the still-unobservable answer as "restart failed" would
        # walk the backoff to 300s against a runner that may be perfectly healthy,
        # while the actual fault is in this observer. Poll cadence is kept so that
        # recovery is noticed the moment the eyes come back.
        #
        # This line is LOOP-LEVEL and is not redundant with check_once's own
        # OBSERVER-BLIND line: it records that the loop declined to enter the
        # corrective branch AT ALL, which is a different fact from check_once
        # declining to act once inside it. Without it, collapsing this branch back
        # into the actionable one is invisible in the log — check_once would
        # suppress the action anyway and the trace would look identical.
        log "health verdict is UNOBSERVABLE — corrective branch NOT entered this cycle"
        check_once || true
        sup_sleep "$POLL_INTERVAL"
        continue
      fi

      # rc == 1: a REAL negative — absent, or present-but-wedged. Action permitted.
      check_once || true
      rc=0; health_ok || rc=$?
      if (( rc == 0 )); then
        backoff=0
      elif (( rc == 3 )); then
        # The post-attempt observation went blind. An observer that cannot see
        # cannot testify that the restart failed, so this is not counted as one.
        # The relaunch storm this could otherwise permit is already bounded by
        # observer_guard's blind streak: og_note_launch increments it on every
        # launch, and at OG_BLIND_STREAK_MAX the verdict is FORCED to unobservable,
        # which lands in the suppress-everything branch above.
        log "post-restart observation is UNOBSERVABLE — not scored as a failed restart: $(og_why)"
        sup_sleep "$POLL_INTERVAL"
      else
        backoff=$(( backoff == 0 ? 10 : backoff * 2 ))
        (( backoff > MAX_BACKOFF )) && backoff=$MAX_BACKOFF
        log "restart failed (or refused); backing off ${backoff}s"
        sup_sleep "$backoff"
      fi
    done
    ;;
  *)
    printf 'usage: %s [loop|once|status]\n' "$(basename "$0")" >&2
    exit 64
    ;;
esac
