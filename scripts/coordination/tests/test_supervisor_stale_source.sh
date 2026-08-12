#!/bin/bash
# Regression test: bus_supervisor.sh must notice a daemon running OLDER code than
# its own source.
#
# WHY THIS EXISTS (2026-08-11). Five fixes sat committed-not-live in one evening —
# C39, C28, C38's tick path, R1 and R2 — because a running daemon keeps executing
# the code it loaded at start and nothing noticed. `health_ok` asks "is a process
# there" and "is its heartbeat fresh"; a daemon running twelve-hour-old code
# answers yes to both. The recurrence proved it twice in seven minutes: a restart
# at 22:18:12Z was followed by a fix committed at 22:21:25Z, which therefore needed
# a SECOND human-initiated restart.
#
# SCOPE, and it is not optional. This tests the PREDICATE ONLY. It never sources
# the supervisor (its case block would run) and never reaches stop_wedged or
# start_daemon. A test stub named session_bus_coordinator.py matches the production
# `pgrep -f` pattern, and on 2026-07-27 a test that believed itself isolated killed
# the live daemon that way. The predicate is the whole of the new logic; the
# restart branch is the supervisor's existing, already-tested machinery.
set -euo pipefail   # MATCH PRODUCTION: a failing command substitution aborts under -e,
                    # and running without it is what hid the bug this line now catches
cd "$(dirname "$0")/../../.." || exit 1
SUP=scripts/coordination/bus_supervisor.sh
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/hb" "$TMP/src"
HEARTBEAT="$TMP/hb/coordinator-daemon.json"
DAEMON="$TMP/src/session_bus_coordinator.py"
STALE_SRC_SKEW_S=5   # the production default; the predicate reads it

# Extract just the functions under test. `resolve_daemon` joined the list with C49
# (2026-08-12): the predicate no longer trusts the raw heartbeat pid, because a
# RECYCLED pid would otherwise contribute a stranger's start time to the comparison
# — and a stranger older than the last source edit reads as "the daemon is stale",
# restarting a current daemon on the strength of an unrelated process's age.
eval "$(sed -n '/^daemon_pid_from_heartbeat()/,/^}/p;/^resolve_daemon()/,/^}/p;/^newest_source_mtime()/,/^}/p;/^source_is_newer_than_daemon()/,/^}/p' "$SUP")"

# The globals those functions read, which live outside their bodies. DAEMON_MARKER
# is THIS SCRIPT'S OWN name, so the "daemon" whose start time the predicate reads
# is this test process ($$) and nothing else on the host can satisfy it — the
# marker is only ever matched against the one pid the heartbeat below names, never
# used to search for a process.
DAEMON_MARKER="$(basename "$0")"
DAEMON_STATE=""; DAEMON_PID=""; DAEMON_WHY=""

pass=0; fail=0
chk() { if [ "$2" = "$3" ]; then echo "  PASS  $1"; pass=$((pass+1));
        else echo "  FAIL  $1 (got $2, want $3)"; fail=$((fail+1)); fi; }

# Every unknown must return 2 = "cannot tell", never 1 = "current". A check that
# cannot tell is not a clean one — the R2 discipline, applied here.
rc=0; source_is_newer_than_daemon || rc=$?; chk "no heartbeat -> fail closed" "$rc" 2
echo '{"agent":"coordinator-daemon"}' > "$HEARTBEAT"
rc=0; source_is_newer_than_daemon || rc=$?; chk "heartbeat carries no pid -> fail closed" "$rc" 2
echo '{"pid":999999999}' > "$HEARTBEAT"
rc=0; source_is_newer_than_daemon || rc=$?; chk "pid does not exist -> fail closed" "$rc" 2
# C49: a pid that EXISTS but is somebody else must fail closed too. Existence was
# never the question — the same lesson the daemon learned in C37, where a stale
# heartbeat naming pid 1 (/sbin/init) reported a ten-day-dead daemon as alive.
echo '{"pid":1}' > "$HEARTBEAT"
rc=0; source_is_newer_than_daemon || rc=$?; chk "pid recycled to another process -> fail closed" "$rc" 2
echo "{\"pid\":$$}" > "$HEARTBEAT"
rc=0; source_is_newer_than_daemon || rc=$?; chk "no source files -> fail closed" "$rc" 2

# The two real verdicts.
touch -d '2020-01-01' "$DAEMON"
rc=0; source_is_newer_than_daemon || rc=$?; chk "source older than process -> current" "$rc" 1
touch -d "+1 hour" "$DAEMON"
rc=0; source_is_newer_than_daemon || rc=$?; chk "source newer than process -> STALE" "$rc" 0


# ---------------------------------------------------------------------------
# THE BUG THE PREDICATE TESTS ABOVE COULD NOT CATCH (C42 bugfix, 2026-08-12).
#
# The check was hooked into check_once. The loop's HEALTHY branch does
# `sleep; continue` and never calls check_once — so the check only ever ran on
# the UNHEALTHY path, where the daemon is about to be restarted anyway and the
# question is moot. Live evidence: supervisor source-current from 00:26:26Z, a
# demonstrably stale daemon, the predicate returning STALE when run by hand, and
# ZERO detections logged.
#
# The predicate tests all passed throughout. They verified A consumer (check_once)
# and not THE consumer (the loop). This is a STATIC assertion about wiring, which
# is the only kind available without running a real supervisor against a real
# daemon — and it is exactly the assertion that was missing.
echo
echo "  -- wiring: the loop's healthy path must reach the check --"
healthy_block=$(sed -n '/while true; do/,/^      fi/p' "$SUP")
if printf '%s' "$healthy_block" | grep -q 'check_stale_source'; then
  echo "  PASS  loop healthy branch calls check_stale_source"; pass=$((pass+1))
else
  echo "  FAIL  loop healthy branch does NOT call check_stale_source —"
  echo "        a stale-but-UP daemon is invisible, which is the whole defect"
  fail=$((fail+1))
fi
# ...and it must still be reachable from `once`, which cron uses.
if sed -n '/^check_once()/,/^}/p' "$SUP" | grep -q 'check_stale_source'; then
  echo "  PASS  check_once still calls it (the cron path)"; pass=$((pass+1))
else
  echo "  FAIL  check_once no longer calls it — cron `once` would stop checking"; fail=$((fail+1))
fi

echo "  ---- $pass passed, $fail failed"
[ "$fail" -eq 0 ]
