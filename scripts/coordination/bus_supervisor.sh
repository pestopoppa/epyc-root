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
# fresh AND the pid it publishes is confirmably the daemon, it does nothing (a
# healthy daemon is NEVER disrupted). When the heartbeat goes stale, or the pid it
# publishes is gone, it clears any wedged instance and relaunches, with bounded
# backoff on repeated failures.
#
# HEALTH = heartbeat mtime, not a port probe: the daemon has no socket, and its
# heartbeat is exactly the liveness signal the bus protocol already defines.
# A daemon restart increments the epoch, so a relaunch is self-announcing.
#
# IDENTITY = the pid inside that heartbeat, verified against /proc/<pid>/cmdline.
# Never a `pgrep` name pattern (C49, below). The verdict is THREE-VALUED — alive,
# dead, unknown — because the two-valued version treated "I cannot see it" as
# "it is dead" and restart-looped a perfectly healthy daemon for as long as it was
# left running. Unknown never kills, never silently passes, and says so in the log.
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

# ONE SPELLING FOR THE BUS ROOT (Phase 3, 2026-08-12). `env.sh` resolves the
# canonical root from the git common dir's dev+inode, so it is correct from any
# worktree and from either path depth of the bind mount. It exports EPYC_BUS_ROOT
# using the `/workspace` spelling *deliberately*: that is byte-identical to what
# `session_bus.get_bus_root()` returns, and the supervisor passes this value to
# the daemon as `--bus-root`. When the two spellings differed, the supervisor and
# the agents named the same directory with different strings — same inode, two
# identities — which is the shape that made the pgrep watchdog blind (C49).
# Sourcing is best-effort so the supervisor still runs from a bare shell.
# shellcheck source=../lib/env.sh
if [[ -r "${BASH_SOURCE[0]%/*}/../lib/env.sh" ]]; then
  # shellcheck disable=SC1091
  source "${BASH_SOURCE[0]%/*}/../lib/env.sh" 2>/dev/null || true
fi
EPYC_ROOT="${EPYC_ROOT:-/mnt/raid0/llm/epyc-root}"

# NIB2-81 startup self-attestation for THIS supervisor's own script (never for
# the daemon it watches — that is H-4, `daemon_source_is_stale` below, already
# wired). Nothing watches the watcher's own inode: the 2026-09-17 census found
# this exact process (pid 4137635) holding a `(deleted)` inode after a
# `git reset --hard` orphaned it, content-identical that day but one commit
# away from silent divergence. Same directory as this script, so it resolves
# even when EPYC_ROOT is unset.
# shellcheck source=./daemon_provenance.sh
source "${BASH_SOURCE[0]%/*}/daemon_provenance.sh"
BUS_ROOT="${BUS_ROOT:-${EPYC_BUS_ROOT:-${EPYC_ROOT}/coordination/session-bus}}"
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
SUP_PROVENANCE="${SUP_PIDFILE}.provenance.json"      # NIB2-81 dp_attest record

# C49 (2026-08-12): DAEMON_PATTERN IS GONE ON PURPOSE — do not reintroduce it.
#
# It was `session_bus_coordinator\.py run`, fed to `pgrep -f`, and it encoded THIS
# SUPERVISOR'S OWN launch idiom rather than the daemon's identity. The live daemon
# is normally started as
#     <venv>/bin/python .../session_bus_coordinator.py --bus-root <path> run
# and `--bus-root <path>` sits BETWEEN `.py` and `run`, so the pattern matched only
# daemons this supervisor had started itself. A watchdog that can see none but its
# own children is not a watchdog. Observed 2026-08-12T10:35–10:36Z: pid 3259108 was
# alive and its heartbeat was FRESH the entire time, while the supervisor logged
# `unhealthy (heartbeat age 10s, pids '') — restarting` every ~10s and every
# relaunch self-exited on the daemon's flock. Perfect health, permanent restart loop.
#
# Widening the regex would have "fixed" that and kept the worse hazard: `pgrep -f`
# is a wildcard over EVERY process on this shared host and `stop_wedged` KILLS what
# it returns (INC-20260731-broad-process-pattern-kills). On 2026-07-27 a test that
# believed itself isolated on three axes killed the production daemon through
# exactly this hole, and the fix then was to scope a fourth axis — which is a fix
# that has to be remembered at every call site instead of one that cannot be got
# wrong. Identity now comes from the heartbeat, which is scoped by BUS_ROOT like
# everything else, so a mis-scoped test can no longer reach production at all.
#
# DAEMON_MARKER is NOT a search pattern: it is only ever checked against the argv of
# the ONE pid the heartbeat names. It cannot discover a process, so it cannot reach
# another session's. It matches the daemon's own `_DAEMON_MARKER`
# (session_bus_coordinator.py:87), which exists for the same reason: a recorded pid
# can be recycled to something else, and killing that is the accident to prevent.
DAEMON_MARKER="${DAEMON_MARKER:-session_bus_coordinator}"

# The daemon's flock singleton (session_bus_coordinator.py:84 LOCK_PATH). Used to
# answer "would a relaunch accomplish anything?" — never to kill. This path is
# GLOBAL while BUS_ROOT is scoped, which is the exact asymmetry that made
# DAEMON_PATTERN dangerous, so it is overridable and tests MUST override it. The
# blast radius is bounded by construction even if one forgets: this value only ever
# SUPPRESSES a spawn, so the worst case is a visibly failing test, never a kill.
DAEMON_LOCK_FILE="${DAEMON_LOCK_FILE:-/tmp/session_bus_coordinator.lock}"

# Consecutive failed relaunches before the supervisor stops trying at poll cadence
# and drops to one attempt per MAX_BACKOFF, saying loudly that the bus is unwatched.
MAX_RESTART_ATTEMPTS="${MAX_RESTART_ATTEMPTS:-5}"

mkdir -p "$LOG_DIR"

log() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "$SUP_LOG" >&2; }

heartbeat_age_s() {
  [[ -f "$HEARTBEAT" ]] || { echo 999999; return; }
  local mtime now
  mtime=$(stat -c %Y "$HEARTBEAT" 2>/dev/null || echo 0)
  now=$(date +%s)
  echo $(( now - mtime ))
}

# ------------------------------------------------------------- daemon identity
#
# Identity comes from the HEARTBEAT's own pid, never from a name pattern — the
# daemon already publishes exactly the number we need, scoped to the bus root we
# are watching. This reasoning was already written down below for the stale-source
# check and applied ONLY there; the health path still pattern-matched. C49 finishes
# the migration, so there is now one identity function and every caller uses it.
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

# THREE STATES, NOT TWO. `alive` / `dead` / `unknown`, published in DAEMON_STATE
# with the evidence in DAEMON_WHY and, when and only when the state is `alive`, a
# kill-safe pid in DAEMON_PID.
#
# `unknown` is the state whose absence caused this bug. The old code folded "I
# cannot see it" into "it is dead" and then acted on that — restarting a healthy
# daemon forever. Collapsing it the other way (unknown => alive) is the fail-open
# twin: the bus would sit unwatched while everything looked fine. So `unknown` is
# its own state, it NEVER kills and it NEVER silently passes; the caller reports it.
#
# Sets globals rather than echoing because a `$(...)` subshell cannot return three
# fields, and losing the pid is how a kill ends up aimed at the wrong thing.
# ALWAYS returns 0 — the verdict is the state, not the exit code (under `set -e` a
# non-zero return from a function used as a simple command aborts the supervisor).
DAEMON_STATE=""   # alive | dead | unknown
DAEMON_PID=""     # set ONLY when DAEMON_STATE=alive; the only pid we may signal
DAEMON_WHY=""

resolve_daemon() {
  DAEMON_STATE=""; DAEMON_PID=""; DAEMON_WHY=""
  local pid cmdline state_field
  if [[ ! -f "$HEARTBEAT" ]]; then
    DAEMON_STATE="dead"
    DAEMON_WHY="no heartbeat file at $HEARTBEAT — no daemon has ever published here"
    return 0
  fi
  pid=$(daemon_pid_from_heartbeat || true)
  if [[ -z "$pid" ]]; then
    DAEMON_STATE="unknown"
    DAEMON_WHY="heartbeat $HEARTBEAT carries no usable pid (unreadable, truncated mid-write, or written by a pre-pid daemon)"
    return 0
  fi
  if [[ ! -d /proc ]]; then
    DAEMON_STATE="unknown"
    DAEMON_WHY="no /proc on this host — heartbeat pid $pid cannot be resolved"
    return 0
  fi
  if [[ ! -d "/proc/$pid" ]]; then
    DAEMON_STATE="dead"
    DAEMON_WHY="heartbeat pid $pid does not exist"
    return 0
  fi
  # /proc/<pid>/cmdline is world-readable on Linux, so a daemon owned by another
  # uid is still identifiable — `kill -0` would only have said "permission denied"
  # and could not tell that apart from "gone".
  cmdline=$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)
  if [[ -z "$cmdline" ]]; then
    # Empty argv: a zombie, a kernel thread, or a process that vanished mid-read.
    state_field=$(awk '{ sub(/^[^)]*\) /, ""); print $1 }' "/proc/$pid/stat" 2>/dev/null || true)
    if [[ "$state_field" == "Z" ]]; then
      DAEMON_STATE="dead"
      DAEMON_WHY="heartbeat pid $pid is a ZOMBIE — it has exited and is awaiting reaping"
      return 0
    fi
    DAEMON_STATE="unknown"
    DAEMON_WHY="pid $pid exists but its argv is unreadable — identity unverifiable"
    return 0
  fi
  if [[ "$cmdline" != *"$DAEMON_MARKER"* ]]; then
    # A pid the kernel handed to somebody else. DEAD as far as the daemon goes, and
    # emphatically NOT a kill target — this branch is the whole reason the marker
    # exists (mirrors _identity_verdict in session_bus_coordinator.py).
    DAEMON_STATE="dead"
    DAEMON_WHY="heartbeat pid $pid was RECYCLED — it is now '${cmdline:0:70}', NOT the coordinator-daemon (left alone)"
    return 0
  fi
  DAEMON_STATE="alive"
  DAEMON_PID="$pid"
  DAEMON_WHY="pid $pid is alive and is the coordinator-daemon"
  return 0
}

# One line naming the state and its evidence, for logs and `status`.
daemon_identity_line() {
  resolve_daemon
  printf '%s — %s\n' "$(printf '%s' "$DAEMON_STATE" | tr '[:lower:]' '[:upper:]')" "$DAEMON_WHY"
}

health_ok() {
  resolve_daemon
  [[ "$DAEMON_STATE" == "alive" ]] || return 1
  local age; age=$(heartbeat_age_s)
  (( age <= STALE_AFTER ))
}

# Kills EXACTLY ONE pid, and only one whose identity is confirmed. Every other
# verdict is a no-op with a reason: there is nothing this function is allowed to
# guess at, because a guess here is a signal sent to another session's process.
stop_wedged() {
  local pid cmdline
  resolve_daemon
  if [[ "$DAEMON_STATE" != "alive" || -z "$DAEMON_PID" ]]; then
    log "  not signalling anything: daemon is ${DAEMON_STATE^^} — $DAEMON_WHY"
    return 0
  fi
  pid="$DAEMON_PID"
  log "stopping wedged daemon pid $pid"
  # SIGTERM first: the daemon drains at its tick boundary (never a kill first).
  kill "$pid" 2>/dev/null || true
  for _ in $(seq 1 10); do
    sleep 1
    [[ -d "/proc/$pid" ]] || { log "  pid $pid is gone"; return 0; }
    # Re-verify identity every second. A pid freed during the drain can be reissued
    # inside this very loop, and the SIGKILL below would then land on a stranger.
    cmdline=$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)
    if [[ "$cmdline" != *"$DAEMON_MARKER"* ]]; then
      log "  pid $pid is no longer the daemon — it exited during the drain; not escalating"
      return 0
    fi
  done
  log "  escalating to SIGKILL on pid $pid"
  kill -9 "$pid" 2>/dev/null || true
  sleep 1
}

start_daemon() {
  # THE ANTI-STORM GATE. The daemon is a flock singleton, so while that lock is
  # held by a live process a relaunch is guaranteed to self-exit — spawning is
  # pure cost. Every ten seconds on 2026-08-12 that is precisely what happened,
  # and the log said "launching" each time as if something had been achieved.
  # Refusing here bounds the storm at its source, upstream of any backoff.
  local holder; holder="$(lock_holder_pid "$DAEMON_LOCK_FILE" || true)"
  if [[ -n "$holder" ]] && kill -0 "$holder" 2>/dev/null; then
    log "NOT LAUNCHING: the daemon singleton lock $DAEMON_LOCK_FILE is held by LIVE pid $holder"
    log "  A daemon IS running; what is in doubt is whether it is the one the heartbeat names."
    log "  A relaunch would self-exit on that flock, so this is reported, not spawned."
    return 1
  fi
  log "launching coordinator-daemon"
  # `9>&-` is load-bearing: fd 9 holds this supervisor's flock, and a child
  # inherits it across fork+exec. Without closing it, the DAEMON ends up holding
  # the supervisor's lock for its entire life, so no supervisor can ever start
  # again while that daemon lives — a complete self-lockout. Observed 2026-07-27:
  # `bus_supervisor.sh once` started the daemon, exited, and the daemon kept fd 9,
  # after which every `loop` logged "another supervisor holds the lock" while
  # `status` reported no supervisor running.
  #
  # `--bus-root "$BUS_ROOT"` is not cosmetic: without it the supervisor WATCHED
  # $BUS_ROOT's heartbeat while LAUNCHING a daemon that wrote to the daemon's own
  # default root. Identical in production, silently divergent under any override —
  # watch A, launch B, and conclude B never started.
  nohup "$DAEMON" --bus-root "$BUS_ROOT" run 9>&- >>"$DAEMON_LOG" 2>&1 &
  local child=$!
  local waited=0
  while (( waited < STARTUP_TIMEOUT )); do
    sleep 1; waited=$(( waited + 1 ))
    if health_ok; then log "daemon healthy after ${waited}s (pid $DAEMON_PID)"; return 0; fi
  done
  # Say WHICH failure this was. "did not become healthy" covers a child that died
  # instantly and a child that is up but not publishing, and those need opposite
  # responses. Both branches report what was OBSERVED — an exited child is equally
  # consistent with a crash and with a flock self-exit, and naming one of those as
  # the cause would be a diagnosis this function has not made.
  if [[ -d "/proc/$child" ]]; then
    log "daemon did NOT become healthy within ${STARTUP_TIMEOUT}s — spawned pid $child is still alive but"
    log "  its heartbeat is not fresh in $HEARTBEAT: $(daemon_identity_line)"
  else
    log "daemon did NOT become healthy within ${STARTUP_TIMEOUT}s — spawned pid $child ALREADY EXITED"
    log "  (it crashed, or it self-exited on the $DAEMON_LOCK_FILE flock). See $DAEMON_LOG."
  fi
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
# exactly the number we need. `daemon_pid_from_heartbeat` and `resolve_daemon` now
# live in the identity section above, where the HEALTH path uses them too; for ten
# days this paragraph was true of this one check and false of the rest of the file.

# H-4 (2026-08-12). THE MTIME PREDICATE IS GONE ON PURPOSE — do not reintroduce it.
#
# It was: newest mtime across `scripts/coordination/*.py` vs the daemon's process
# start time, tolerated by a 5s skew (STALE_SRC_SKEW_S) and de-duplicated by a state
# file (STALE_SRC_STATE) holding the mtime last acted on. All three are deleted.
#
# WHY. mtime answers "did somebody TOUCH a file", and this tree has five concurrent
# writers: an editor save, a subagent's scratch write, a `git checkout` restoring an
# identical file — each moves the newest mtime forward without changing one byte of
# what a restarted daemon would execute. Measured 2026-08-12: 14 restarts of a
# perfectly healthy daemon in 54 minutes. The state file bounded it to one restart
# per DISTINCT mtime, which in a live tree is not a bound at all, and the only thing
# that actually stopped the storm was an env var set on the running process.
#
# The question is not "was a file touched" but "is the code this process loaded the
# code that is COMMITTED now". `git rev-parse HEAD:scripts/coordination` names the
# tree object of the daemon's package at HEAD; it moves once per deploy and never
# for an uncommitted touch. The daemon captures it AT PROCESS START and publishes it
# in its heartbeat (`source_tree`, session_bus_coordinator.py `_source_tree_sha`),
# so the comparison is between what is RUNNING and what is COMMITTED — two
# independently-sourced values. Comparing HEAD against HEAD would agree forever.
#
# Identity still comes from the HEARTBEAT, never a name pattern — a pattern is a
# wildcard over other sessions' processes on this shared host
# (INC-20260731-broad-process-pattern-kills).

# The committed tree object for the daemon's package, as it is RIGHT NOW.
# Empty output = cannot tell (not a checkout, git absent) => UNKNOWN, never stale.
current_source_tree() {
  git -C "$EPYC_ROOT" rev-parse HEAD:scripts/coordination 2>/dev/null || true
}

# The marker the RUNNING daemon published at its own start. Empty = the key is
# absent (a pre-H-4 daemon, or one that could not read git) => UNKNOWN.
heartbeat_source_tree() {
  python3 - "$HEARTBEAT" <<'PY_EOF' 2>/dev/null || true
import json, sys
try:
    v = json.load(open(sys.argv[1])).get("source_tree")
    if isinstance(v, str) and v.strip():
        print(v.strip())
except Exception:
    pass
PY_EOF
}

# 0 = the running daemon was launched from a DIFFERENT committed tree than HEAD.
# 1 = current. 2 = cannot tell. FAIL CLOSED on 2: the caller reports and does not act.
daemon_source_is_stale() {
  local hb cur
  # `|| true` on every capture is load-bearing, not defensive noise: this script
  # runs under `set -euo pipefail`, where a FAILING command substitution aborts the
  # whole supervisor, making the fail-closed branches below unreachable.
  # resolve_daemon, not the raw heartbeat pid: a recycled or unidentifiable process
  # is not a daemon whose deploy marker means anything (C49).
  resolve_daemon
  [[ "$DAEMON_STATE" == "alive" ]] || return 2
  hb="$(heartbeat_source_tree || true)"
  [[ -z "$hb" ]] && return 2
  cur="$(current_source_tree || true)"
  [[ -z "$cur" ]] && return 2
  [[ "$hb" != "$cur" ]]
}

# THE RATE LIMIT THAT WAS MISSING (H-4). MAX_RESTART_ATTEMPTS/backoff below covers
# only FAILED relaunches, which is exactly why the storm never tripped it: every one
# of the 14 restarts SUCCEEDED, so `fails` reset to 0 each time and the backoff
# never engaged. This bounds the successful path: at most one stale-source restart
# per RESTART_MIN_INTERVAL_S; a second stale verdict inside the window ALARMS and
# does not restart. A predicate that keeps firing after a restart is a broken
# predicate, and looping on it destroys the daemon it is meant to protect.
RESTART_MIN_INTERVAL_S="${RESTART_MIN_INTERVAL_S:-900}"
STALE_RESTART_STAMP="${STALE_RESTART_STAMP:-${LOG_DIR}/bus_supervisor.last_stale_restart}"
# C43: how long to wait for a DYING supervisor to release the lock before giving up.
# Covers a handover, not a coexistence — a dying holder releases in milliseconds, a
# live one holds for its life and we still report and exit. 15s is generous for the
# former and short enough that a cron `once` never stacks up.
LOCK_WAIT_S="${LOCK_WAIT_S:-15}"

check_stale_source() {
  local rc=0 hb cur now last age
  # `|| rc=$?`, never `cmd; rc=$?`. Under `set -e` a FUNCTION returning non-zero as
  # a simple command aborts the script, so the bare form killed the supervisor
  # mid-`once` on every "current" and every "cannot tell" — i.e. on the normal
  # path. That is how a watchdog silently stops watching.
  daemon_source_is_stale || rc=$?
  if (( rc == 2 )); then
    log "STALE-SOURCE CHECK UNAVAILABLE — the daemon's identity, its heartbeat 'source_tree'"
    log "  marker, or the current HEAD tree could not be read. UNKNOWN, and UNKNOWN never"
    log "  restarts: a check that cannot tell is not a clean one, and it is not a verdict either."
    return 0
  fi
  (( rc != 0 )) && return 0
  hb="$(heartbeat_source_tree || true)"
  cur="$(current_source_tree || true)"

  # THE RATE LIMIT. The stamp is written when a restart is ATTEMPTED, not when one
  # succeeds: by the time start_daemon runs, stop_wedged has already signalled the
  # daemon, so the attempt is the event with the blast radius. A stamp written only
  # on success would let a repeatedly-failing stale restart kill the daemon every
  # poll — and failed relaunches already have their own bound (MAX_RESTART_ATTEMPTS).
  now=$(date +%s)
  last=0
  if [[ -f "$STALE_RESTART_STAMP" ]]; then
    last="$(cat "$STALE_RESTART_STAMP" 2>/dev/null || echo 0)"
    [[ "$last" =~ ^[0-9]+$ ]] || last=0
  fi
  age=$(( now - last ))
  if (( last > 0 && age < RESTART_MIN_INTERVAL_S )); then
    log "ALARM: STALE SOURCE AGAIN ${age}s AFTER THE LAST STALE-SOURCE RESTART — NOT RESTARTING."
    log "  running tree ${hb:0:12} vs HEAD tree ${cur:0:12}; limit is one per ${RESTART_MIN_INTERVAL_S}s."
    log "  A restart that does not clear this verdict is not fixing it. Either the daemon is"
    log "  relaunching from a different checkout, or HEAD moved again — a human closes this."
    return 0
  fi

  log "daemon is running a DIFFERENT COMMITTED TREE than HEAD (running ${hb:0:12}, HEAD ${cur:0:12})"
  log "  — restarting once so committed fixes take effect (next stale restart no sooner than ${RESTART_MIN_INTERVAL_S}s)"
  echo "$now" > "$STALE_RESTART_STAMP"
  stop_wedged
  # `|| true` is load-bearing, not tidiness. This function is called as a SIMPLE
  # COMMAND from both consumers (the loop's healthy branch and check_once), and
  # under `set -e` a non-zero return from a simple command aborts the whole
  # supervisor — so a failed relaunch here would have KILLED THE WATCHDOG instead
  # of being retried. start_daemon already logs which failure it was, and the very
  # next poll takes the unhealthy branch, where MAX_RESTART_ATTEMPTS and the
  # backoff apply. Same trap as the `|| rc=$?` above, one call deeper.
  start_daemon || true
}

# --------------------------------------------------------- registry restart
#
# NIB2-81 remedy (b), SCOPED TIGHTLY (tmp/daemon-staleness-20260917/report.md).
# H-4 above restarts exactly ONE daemon: the one THIS script watches via its
# own heartbeat's `source_tree` marker. This generalises the same idea — a
# running inode that has drifted from the committed one — to OTHER registered
# daemons, reusing the identical shape (identity from the CANDIDATE'S OWN
# pidfile + cmdline, never a name pattern; SIGTERM, re-verify identity every
# second of the drain, escalate to SIGKILL; rate-limited restarts; fail closed
# on anything unreadable). It is deliberately NOT a blanket "restart every
# stale registered daemon": this repo's own doctrine is "restart identity from
# the daemon's own pid record, never a name pattern" AND "never patch a
# running supervisor in place" (production kernels are frozen for the same
# reason), so an automatic kill-and-relaunch of, say, the hub or bus
# supervisor itself belongs to a human at a chosen boundary, not to a poll
# tick. Only registry rows the operator has explicitly marked
# `runtime.restart_on_stale: true` are ever touched here — today exactly ONE,
# the opencode reaper, because it is idempotent and stateless (a spurious
# restart costs one skipped 30-minute reap cycle against the live
# opencode.db, never a corrupted one; reap_once re-derives its whole answer
# from the DB every call, nothing carries over in-process). Every other
# runtime-enrolled row is report/alarm only — `observer_census.py --live`
# above, fed to the SAME alarm channel this script's own stale-source ALARM
# branch already uses.
REGISTRY_PATH="${REGISTRY_PATH:-${EPYC_ROOT}/scripts/coordination/observer_registry.json}"

# registry_restart_candidates — one TAB-separated line per registry row with
# runtime.restart_on_stale == true: id, pidfile, expected_path, provenance,
# start_argv (as a JSON array), log. Never fails the caller: a missing or
# unreadable registry, or one with zero such rows, is silent empty output —
# "nothing to restart", not an error this loop should ever abort on.
registry_restart_candidates() {
  [[ -r "$REGISTRY_PATH" ]] || return 0
  python3 - "$REGISTRY_PATH" <<'PY_EOF' 2>/dev/null || true
import json, sys
try:
    reg = json.load(open(sys.argv[1]))
except Exception:
    raise SystemExit(0)
for row in reg.get("observers", []):
    rt = row.get("runtime") or {}
    if not rt.get("restart_on_stale"):
        continue
    print("\t".join([
        str(row.get("id", "")),
        str(rt.get("pidfile", "")),
        str(rt.get("expected_path", "")),
        str(rt.get("provenance", "")),
        json.dumps(rt.get("start_argv") or []),
        str(rt.get("log", "")),
    ]))
PY_EOF
}

# registry_daemon_identity <pidfile> <expected_basename>
#
# Sets REG_STATE (alive|dead|unknown) / REG_PID (only when alive) / REG_WHY,
# the same three-valued shape as resolve_daemon() above but keyed off a THIRD
# PARTY's OWN pidfile + cmdline rather than this supervisor's heartbeat. Never
# trusts the pid number alone — a recycled pid belongs to a stranger, and
# `unknown` (an unreadable pidfile or cmdline) never becomes `dead`: this
# function only ever SUPPRESSES a restart, never causes one, so the fail-safe
# direction is UNKNOWN, not DEAD.
REG_PID=""; REG_STATE=""; REG_WHY=""
registry_daemon_identity() {
  local pidfile="$1" basename="$2" pid cmdline
  REG_PID=""; REG_STATE=""; REG_WHY=""
  if [[ ! -f "$pidfile" ]]; then
    REG_STATE="dead"; REG_WHY="no pidfile at $pidfile"; return 0
  fi
  pid="$(cat "$pidfile" 2>/dev/null || true)"
  if [[ ! "$pid" =~ ^[0-9]+$ ]]; then
    REG_STATE="unknown"; REG_WHY="pidfile $pidfile carries no usable pid"; return 0
  fi
  if [[ ! -d "/proc/$pid" ]]; then
    REG_STATE="dead"; REG_WHY="pid $pid (from $pidfile) does not exist"; return 0
  fi
  cmdline="$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)"
  if [[ -z "$cmdline" ]]; then
    REG_STATE="unknown"; REG_WHY="pid $pid argv unreadable (zombie or vanished mid-read)"; return 0
  fi
  if [[ "$cmdline" != *"$basename"* ]]; then
    REG_STATE="dead"
    REG_WHY="pid $pid was RECYCLED — argv is '${cmdline:0:70}', not $basename"
    return 0
  fi
  REG_STATE="alive"; REG_PID="$pid"; REG_WHY="pid $pid is alive and is $basename"
}

# registry_script_is_stale <pid> <expected_path>
#
# 0 = STALE, 1 = current, 2 = cannot tell (FAIL CLOSED, never acted on). Reads
# the RUNNING inode straight from the candidate's own open fd (255 first, the
# bash script-fd convention observed on every live daemon censused
# 2026-09-17, then a full fd scan) and compares it to whatever inode is on
# disk at EPYC_ROOT/<expected_path> RIGHT NOW — the same mechanism
# observer_census.py's live_check_row implements, and delegated to a tiny
# python3 helper rather than bash's own `stat`, DELIBERATELY: this host's
# `stat` is uutils-coreutils, which was measured (while writing this) to
# report a DIFFERENT, WRONG inode for a `/proc/<pid>/fd/<n>` symlink than for
# the same file's real path — `os.stat()` (what observer_census.py already
# uses, and what this helper uses) resolves both to the identical, correct
# value. A restart path built on a `stat`-through-/proc comparison would fail
# closed into "cannot tell" on THIS host on every single call, which is a
# worse failure than the one this remedy exists to fix — a python dependency
# here is one line, not the class of gap a missing python3 would be.
registry_script_is_stale() {
  local pid="$1" expected_path="$2"
  python3 - "$pid" "$EPYC_ROOT" "$expected_path" <<'PY_EOF'
import os, sys
pid, root, expected = sys.argv[1], sys.argv[2], sys.argv[3]
name = os.path.basename(expected)


def _fd_matching(pid: str, name: str) -> str | None:
    try:
        link = os.readlink(f"/proc/{pid}/fd/255")
        bare = link[: -len(" (deleted)")] if link.endswith(" (deleted)") else link
        if os.path.basename(bare) == name:
            return "255"
    except OSError:
        pass
    try:
        entries = os.listdir(f"/proc/{pid}/fd")
    except OSError:
        return None
    for entry in entries:
        if entry == "255":
            continue
        try:
            link = os.readlink(f"/proc/{pid}/fd/{entry}")
        except OSError:
            continue
        bare = link[: -len(" (deleted)")] if link.endswith(" (deleted)") else link
        if os.path.basename(bare) == name:
            return entry
    return None


fd = _fd_matching(pid, name)
if fd is None:
    sys.exit(2)
try:
    running = os.stat(f"/proc/{pid}/fd/{fd}")
except OSError:
    sys.exit(2)
try:
    current = os.stat(os.path.join(root, expected))
except OSError:
    sys.exit(0)  # the expected path no longer exists on disk at all -> stale
sys.exit(0 if (running.st_dev, running.st_ino) != (current.st_dev, current.st_ino) else 1)
PY_EOF
}

# stop_registry_daemon <pidfile> <basename> — stop_wedged's exact shape
# (SIGTERM, poll for up to 10s re-verifying identity every second, escalate to
# SIGKILL), pointed at a THIRD PARTY confirmed via ITS OWN pidfile + cmdline.
# Never signals anything registry_daemon_identity did not just confirm alive.
stop_registry_daemon() {
  local pidfile="$1" basename="$2" pid cmdline
  registry_daemon_identity "$pidfile" "$basename"
  if [[ "$REG_STATE" != "alive" || -z "$REG_PID" ]]; then
    log "  registry-restart: not signalling anything for $basename — $REG_STATE: $REG_WHY"
    return 0
  fi
  pid="$REG_PID"
  log "  registry-restart: stopping stale $basename, pid $pid"
  kill "$pid" 2>/dev/null || true
  for _ in $(seq 1 10); do
    sleep 1
    [[ -d "/proc/$pid" ]] || { log "    pid $pid is gone"; return 0; }
    cmdline="$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)"
    if [[ "$cmdline" != *"$basename"* ]]; then
      log "    pid $pid is no longer $basename — it exited during the drain; not escalating"
      return 0
    fi
  done
  log "    escalating to SIGKILL on pid $pid"
  kill -9 "$pid" 2>/dev/null || true
  sleep 1
}

# start_registry_daemon <start_argv-as-json> <log-path>
#
# `{canonical_root}` is substituted with EPYC_ROOT — "restart FROM ITS
# CANONICAL PATH" is the whole point (the class this closes is a daemon
# running a copy that is NOT the canonical path). `9>&-` mirrors start_daemon
# above: without closing this supervisor's own lock fd, a relaunched child
# would inherit it and lock out every future supervisor.
start_registry_daemon() {
  local argv_json="$1" log_path="${2:-/dev/null}" argv=() tok
  while IFS= read -r tok; do
    argv+=("${tok//\{canonical_root\}/$EPYC_ROOT}")
  done < <(python3 -c 'import json,sys; [print(x) for x in json.loads(sys.argv[1])]' \
             "$argv_json" 2>/dev/null)
  if [[ ${#argv[@]} -eq 0 ]]; then
    log "  registry-restart: no start_argv given — cannot relaunch"
    return 1
  fi
  log "  registry-restart: launching ${argv[*]}"
  [[ -n "$log_path" && "$log_path" != "None" ]] || log_path=/dev/null
  mkdir -p "$(dirname -- "$log_path")" 2>/dev/null || true
  nohup "${argv[@]}" 9>&- >>"$log_path" 2>&1 &
  disown
}

# check_registry_restarts — the tick. Independent of the coordinator-daemon's
# OWN health (unlike check_stale_source, which only makes sense for a healthy
# daemon) — a registry candidate's staleness has nothing to do with whether
# this supervisor's own watched daemon is up, so it runs unconditionally from
# both `once` and every `loop` iteration. Rate-limited exactly like H-4's own
# stale-source restart: at most one restart attempt per candidate per
# RESTART_MIN_INTERVAL_S, so a predicate that keeps firing after a restart
# cannot loop-restart the daemon it is meant to protect.
check_registry_restarts() {
  local id pidfile expected_path provenance argv_json log_path basename
  while IFS=$'\t' read -r id pidfile expected_path provenance argv_json log_path; do
    [[ -n "$id" ]] || continue
    basename="$(basename -- "$expected_path")"
    registry_daemon_identity "$pidfile" "$basename"
    if [[ "$REG_STATE" != "alive" ]]; then
      # not_running is deliverable-3 territory (report/alarm via
      # observer_census.py --live) — nothing to restart FROM here, and
      # relaunching a daemon that never claimed to be running is not what
      # this tick is for.
      continue
    fi
    local rc=0
    registry_script_is_stale "$REG_PID" "$expected_path" || rc=$?
    if (( rc == 2 )); then
      log "  registry-restart[$id]: STALE CHECK UNAVAILABLE — not acting (fail closed)"
      continue
    fi
    (( rc == 1 )) && continue  # current — nothing to do, the common case every tick

    local stamp="${LOG_DIR}/registry_restart.${id}.last"
    local now last age
    now=$(date +%s); last=0
    if [[ -f "$stamp" ]]; then
      last="$(cat "$stamp" 2>/dev/null || echo 0)"
      [[ "$last" =~ ^[0-9]+$ ]] || last=0
    fi
    age=$(( now - last ))
    if (( last > 0 && age < RESTART_MIN_INTERVAL_S )); then
      log "  registry-restart[$id]: STALE AGAIN ${age}s after the last restart — NOT restarting"
      log "    (limit is one per ${RESTART_MIN_INTERVAL_S}s; a restart that does not clear this"
      log "    verdict is not fixing it — a human closes this)"
      continue
    fi

    log "registry-restart[$id]: $basename (pid $REG_PID) is running a STALE inode — restarting from canon"
    echo "$now" > "$stamp"
    stop_registry_daemon "$pidfile" "$basename"
    start_registry_daemon "$argv_json" "$log_path" || true

    local waited=0
    while (( waited < STARTUP_TIMEOUT )); do
      sleep 1; waited=$(( waited + 1 ))
      registry_daemon_identity "$pidfile" "$basename"
      [[ "$REG_STATE" == "alive" ]] && break
    done
    if [[ "$REG_STATE" == "alive" ]]; then
      log "  registry-restart[$id]: relaunched — new pid $REG_PID ($REG_WHY)"
    else
      log "  registry-restart[$id]: relaunch did NOT come up healthy within ${STARTUP_TIMEOUT}s — $REG_STATE: $REG_WHY"
    fi
  done < <(registry_restart_candidates)
}

# ------------------------------------------------------------- lock contention
#
# C43 (2026-08-12). A relaunch attempt at 00:25:09Z logged "another supervisor
# holds the lock; exiting" and exited **0**. That was TRUE at the time — the old
# supervisor was still alive — but the exit code says SUCCESS, so nothing
# downstream can tell "correctly skipped, one is already running" from "failed to
# start, nothing is supervising". For the documented cron idiom
# (`*/2 * * * * bus_supervisor.sh once`) exit 0 is RIGHT and must stay: a skip is
# the normal case and a non-zero there would page on every ordinary tick.
#
# So the fix is not the exit code, it is the EVIDENCE. Name who holds the lock and
# whether that process is alive, so a reader — or a supervisor-of-supervisor — can
# tell the two apart. An unreadable or dead holder is reported LOUDLY, because that
# is the shape where nothing is supervising and everything still looks fine: the
# same fail-open family as a daemon whose heartbeat outlived it.
# C48 (2026-08-12): THE LOCK IS AUTHORITATIVE; THE PID FILE IS A CACHE OF IT.
#
# `status` reported "supervisor: not running" and health UNHEALTHY while pid 1510370
# was alive, holding the lock, and had been supervising for 7h40m — because
# $SUP_PIDFILE had vanished (cause non-git: the file was never tracked in any commit,
# so a70dbe1a could not have removed it even in principle — auditor, verified). The
# coordinator read UNHEALTHY, concluded the bus was unwatched, and launched a second
# supervisor; C43's bounded flock correctly refused it as a duplicate, but the refusal
# message could not NAME the holder because naming also read the missing pid file. The
# diagnostic and the thing it diagnoses shared a single point of failure.
#
# This is C35 one layer up, in the tool that watches the watcher: C35 made daemon
# status derive liveness from the PROCESS rather than a state file that outlives it.
# Here liveness derives from the FLOCK, which the kernel releases on process death and
# which no file operation can leave stale.

lock_is_held() {
  # 0 = somebody holds the lock. Uses a scratch fd so it cannot disturb fd 9.
  exec 8>"$LOCK_FILE" 2>/dev/null || return 1
  if flock -n 8; then flock -u 8; exec 8>&-; return 1; fi
  exec 8>&-; return 0
}

lock_holder_pid() {
  # WHO holds it — by scanning /proc for an fd on the lock file. Pure /proc, no lsof
  # or fuser dependency (neither netstat nor ss exists on this host; assuming a tool
  # is installed is how the port gate in start_orchestrator_test.sh became vacuous).
  # Takes the lock path as an argument (default: this supervisor's own) so the same
  # kernel-authoritative answer serves the DAEMON's singleton lock in start_daemon.
  # Note what this is NOT: it resolves a named file to its holders, so it can only
  # ever name processes that opened that exact file. It is not a name search.
  #
  # `find -lname` rather than a bash loop over /proc/[0-9]*/fd/* calling
  # `readlink -f` per descriptor: that shape forks tens of thousands of times on
  # this 2,200-process host and MEASURED 7.5s, against 0.03s here for an identical
  # answer. Latency mattered once C49 put this on the relaunch path — a watchdog
  # that takes 7s to decide whether to act spends its poll interval deciding.
  #
  # Both the resolved and the literal path are matched because the fd symlink
  # carries the text the opener used, which need not be the fully-resolved form.
  # (`-lname` takes a glob; lock paths here contain no glob metacharacters.)
  local file="${1:-$LOCK_FILE}"
  local resolved hit pid
  resolved="$(readlink -f "$file" 2>/dev/null || printf '%s' "$file")"
  while IFS= read -r hit; do
    pid="${hit#/proc/}"; pid="${pid%%/*}"
    [[ "$pid" == "$$" ]] && continue
    printf '%s\n' "$pid"
  done < <(find /proc/[0-9]*/fd -maxdepth 1 \
             \( -lname "$resolved" -o -lname "$file" \) -printf '%h\n' 2>/dev/null) \
    | sort -un | head -1
}

supervisor_status_line() {
  # Lock first, pid file only as a corroborating hint — and say when they disagree,
  # because a silent disagreement is how the stale-cache class hides.
  local held hint holder
  hint="$( [[ -f "$SUP_PIDFILE" ]] && cat "$SUP_PIDFILE" 2>/dev/null || true )"
  if lock_is_held; then
    holder="$(lock_holder_pid)"
    if [[ -n "$holder" && -n "$hint" && "$holder" != "$hint" ]]; then
      printf '%s (lock) — pidfile says %s, DISAGREEMENT: trust the lock\n' "$holder" "$hint"
    elif [[ -n "$holder" ]]; then
      printf '%s%s\n' "$holder" "$( [[ -z "$hint" ]] && printf ' (from lock; %s missing)' "$SUP_PIDFILE" )"
    else
      printf 'RUNNING (lock held; holder pid not resolvable from /proc)\n'
    fi
  else
    if [[ -n "$hint" ]]; then
      printf 'not running (stale %s claims %s — lock is free)\n' "$SUP_PIDFILE" "$hint"
    else
      printf 'not running\n'
    fi
  fi
}

lock_holder_report() {
  local holder="" alive="unknown"
  holder="$(lock_holder_pid)"
  if [[ -n "$holder" ]] || [[ -f "$SUP_PIDFILE" ]]; then
    [[ -n "$holder" ]] || holder="$(cat "$SUP_PIDFILE" 2>/dev/null || true)"
  fi
  if [[ -z "$holder" ]]; then
    log "  lock holder: UNKNOWN — no readable $SUP_PIDFILE. Cannot confirm anything is"
    log "  supervising. If no supervisor is running, this exit leaves the bus unwatched."
    return 0
  fi
  if kill -0 "$holder" 2>/dev/null; then
    alive="ALIVE"
  else
    alive="DEAD"
  fi
  log "  lock holder: pid $holder ($alive)"
  if [[ "$alive" == "DEAD" ]]; then
    log "  the recorded supervisor is NOT running, so this skip leaves the bus unwatched."
    log "  flock releases on process death, so a dead holder means the pidfile is stale"
    log "  rather than the lock being held — re-run once the stale pidfile is cleared."
  fi
}

# Bounded retry on the lock, then report. C43 SECOND HALF (2026-08-12).
#
# The evidence fix alone was not enough, and `coordinator-agent`'s measurement is
# why: they killed supervisor 489217, verified it dead with `ps`, relaunched
# immediately, and the new process lost the race against the DYING supervisor's
# flock release — logged "another supervisor holds the lock", exited 0, and died.
# For ~90 seconds nothing would have relaunched the daemon if it had died. That is
# the exact condition that went unnoticed for ten days from 2026-07-29.
#
# Note what my first C43 fix would have done here: the holder was still alive while
# releasing, so it would have printed "lock holder: pid 489217 (ALIVE)" and exited
# 0 — accurate, unhelpful, and the gap still open. Evidence about a race is not a
# fix for the race.
#
# `flock -w` blocks until the holder releases or the timeout expires, which is
# exactly the semantics wanted: a dying supervisor releases in milliseconds, so the
# relaunch wins; a genuinely running one holds for its life, so we still give up
# and report. The wait is short because the only case it needs to cover is a
# handover, not a coexistence.
acquire_supervisor_lock() {
  exec 9>"$LOCK_FILE"
  if flock -w "$LOCK_WAIT_S" 9; then
    return 0
  fi
  log "another supervisor holds the lock after ${LOCK_WAIT_S}s; exiting"
  lock_holder_report
  return 1
}

check_once() {
  # A HEALTHY daemon can still be the wrong daemon. Order matters: a dead one is
  # restarted by the branch below and comes back on current source anyway, so the
  # stale-source question only applies to one that is up and answering.
  if health_ok; then check_stale_source; return 0; fi
  # health_ok left the verdict in DAEMON_STATE/DAEMON_WHY. Each state gets its own
  # response, because the three need three different ones — the old single branch
  # ("restart") was correct for exactly one of them.
  local age; age=$(heartbeat_age_s)
  case "$DAEMON_STATE" in
    alive)
      # Confirmed ours, and it has stopped ticking: the wedged case, the only one
      # in which this supervisor may signal a process.
      log "WEDGED: $DAEMON_WHY, but its heartbeat is ${age}s old (stale after ${STALE_AFTER}s) — restarting"
      stop_wedged
      start_daemon
      ;;
    dead)
      log "DEAD: $DAEMON_WHY (heartbeat ${age}s old) — relaunching"
      stop_wedged   # a no-op that says why; nothing here is a valid kill target
      start_daemon
      ;;
    unknown|*)
      if (( age <= STALE_AFTER )); then
        # THE 2026-08-12 CASE. Something is ticking on time and we cannot name it.
        # Killing is impossible (no confirmed pid) and relaunching is pointless
        # (the flock). The old code called this "dead" and restarted forever.
        log "IDENTITY UNKNOWN with a FRESH heartbeat (${age}s) — $DAEMON_WHY"
        log "  A daemon is ticking; this supervisor cannot prove which process it is."
        log "  NOT killing (no confirmed pid) and NOT relaunching (it would self-exit on the"
        log "  daemon's flock). Reported, not passed: a check that cannot tell is not a clean one."
        return 3
      fi
      log "IDENTITY UNKNOWN and heartbeat STALE (${age}s) — $DAEMON_WHY"
      log "  Nothing here can be safely signalled. Attempting a bounded relaunch instead:"
      log "  the daemon's own flock makes a duplicate harmless, and a real start republishes"
      log "  the pid that ends this ambiguity."
      start_daemon
      ;;
  esac
}

case "${1:-loop}" in
  status)
    age=$(heartbeat_age_s)
    # Three states printed as three states. `daemon pids : none` used to be the
    # rendering of BOTH "no daemon" and "cannot see the daemon", which is the
    # ambiguity that let the restart loop look reasonable in the log.
    printf 'daemon      : %s\n' "$(daemon_identity_line)"
    printf 'heartbeat   : %ss old (stale after %ss)\n' "$age" "$STALE_AFTER"
    printf 'singleton   : %s\n' "$(h="$(lock_holder_pid "$DAEMON_LOCK_FILE" || true)"; \
        if [[ -z "$h" ]]; then printf '%s is unheld — no daemon holds the singleton' "$DAEMON_LOCK_FILE"; \
        elif kill -0 "$h" 2>/dev/null; then printf 'held by pid %s (ALIVE)' "$h"; \
        else printf 'held by pid %s (DEAD?)' "$h"; fi)"
    printf 'supervisor  : %s\n' "$(supervisor_status_line)"
    health_ok && printf 'health      : OK\n' || printf 'health      : UNHEALTHY\n'
    exit 0
    ;;
  once)
    acquire_supervisor_lock || exit 0
    # EXIT CODES. 0 = healthy, or unhealthy and dealt with. 3 = daemon identity
    # could not be determined — distinct on purpose, and distinct from 1 (a failed
    # relaunch) so a cron wrapper can tell "cannot tell" from "tried and failed".
    # The lock-contention skip above stays 0: for the documented
    # `*/2 * * * * bus_supervisor.sh once` idiom a skip is the normal case (C43).
    # Written out rather than left to `set -e`, which would exit 1 for both and
    # only by accident.
    rc=0
    check_once || rc=$?
    # NIB2-81 remedy (b): independent of the coordinator-daemon's own health —
    # never lets a registry-restart failure change THIS command's exit code,
    # same reasoning as check_stale_source's own `|| true` call sites above.
    check_registry_restarts || true
    exit "$rc"
    ;;
  loop)
    acquire_supervisor_lock || exit 0
    # NIB2-81: attest BEFORE writing the pidfile, so a refusal leaves no stale
    # pidfile for a peer to trust. Refuses only on step 1 (not under the
    # canonical root); an uncommitted local edit warns and continues.
    dp_attest "${BASH_SOURCE[0]}" "$SUP_PROVENANCE" || exit $?
    echo $$ > "$SUP_PIDFILE"
    trap 'rm -f "$SUP_PIDFILE"; log "supervisor stopped"; exit 0' TERM INT
    log "supervisor started (poll ${POLL_INTERVAL}s, stale after ${STALE_AFTER}s)"
    backoff=0
    fails=0
    gave_up=0
    while true; do
      # Per-iteration staleness LOG ONLY for this supervisor's OWN script — the
      # H-4 check below (check_stale_source) is about the DAEMON it watches, a
      # separate question. No restart, no self-re-exec: that is remedy (b),
      # out of scope for NIB2-81a. 2 (cannot tell) is silent, same fail-closed
      # convention as daemon_source_is_stale.
      dp_rc=0; dp_stale_since_start "${BASH_SOURCE[0]}" "$SUP_PROVENANCE" || dp_rc=$?
      if [[ "$dp_rc" -eq 0 ]]; then
        log "running stale code; restart from ${BASH_SOURCE[0]}"
      fi
      # NIB2-81 remedy (b): runs EVERY tick, unconditionally — a registry
      # candidate's staleness has nothing to do with whether the coordinator-
      # daemon this supervisor watches is itself healthy, unlike check_stale_source
      # below (which is specifically about THAT daemon and only fires once it is
      # confirmed up and answering).
      check_registry_restarts || true
      if health_ok; then
        backoff=0; fails=0; gave_up=0
        # C42 BUGFIX 2026-08-12: this `continue` skipped check_once, which is where
        # the stale-source check lived — so it only ever ran on the UNHEALTHY path,
        # i.e. when the daemon was about to be restarted anyway and the question is
        # moot. The whole point is a daemon that is UP and answering while running
        # old code, so it has to be asked exactly here, on the healthy path.
        # Measured: supervisor source-current from 00:26:26Z, daemon demonstrably
        # stale, predicate returning STALE when run by hand, and ZERO detections
        # logged. The tests passed because they exercised the predicate and
        # check_once directly and never the loop — verifying A consumer, not THE
        # consumer.
        check_stale_source
        sleep "$POLL_INTERVAL"
        continue
      fi
      check_once || true
      if health_ok; then
        backoff=0; fails=0; gave_up=0
      else
        # Bounded, not merely exponential. Exponential backoff still assumes the
        # next attempt might work; after MAX_RESTART_ATTEMPTS consecutive failures
        # it demonstrably does not, and the honest report is that the bus is
        # unwatched and needs a human — pinned at one attempt per MAX_BACKOFF so
        # a recovery is still picked up without a spawn every poll.
        fails=$(( fails + 1 ))
        backoff=$(( backoff == 0 ? 10 : backoff * 2 ))
        (( backoff > MAX_BACKOFF )) && backoff=$MAX_BACKOFF
        if (( fails >= MAX_RESTART_ATTEMPTS )); then
          backoff=$MAX_BACKOFF
          if (( gave_up == 0 )); then
            gave_up=1
            log "GIVING UP on fast retries after ${fails} consecutive failures — $(daemon_identity_line)"
            log "  THE BUS IS UNWATCHED BY A LIVE DAEMON AND THIS SUPERVISOR CANNOT FIX IT."
            log "  Retrying once per ${MAX_BACKOFF}s from here; operator action is what closes this."
          fi
        fi
        log "not healthy after the attempt; backing off ${backoff}s (failure ${fails})"
        sleep "$backoff"
      fi
    done
    ;;
  *)
    printf 'usage: %s [loop|once|status]\n' "$(basename "$0")" >&2
    exit 64
    ;;
esac
