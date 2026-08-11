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

# Extract just the three functions under test.
eval "$(sed -n '/^daemon_pid_from_heartbeat()/,/^}/p;/^newest_source_mtime()/,/^}/p;/^source_is_newer_than_daemon()/,/^}/p' "$SUP")"

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
echo "{\"pid\":$$}" > "$HEARTBEAT"
rc=0; source_is_newer_than_daemon || rc=$?; chk "no source files -> fail closed" "$rc" 2

# The two real verdicts.
touch -d '2020-01-01' "$DAEMON"
rc=0; source_is_newer_than_daemon || rc=$?; chk "source older than process -> current" "$rc" 1
touch -d "+1 hour" "$DAEMON"
rc=0; source_is_newer_than_daemon || rc=$?; chk "source newer than process -> STALE" "$rc" 0

echo "  ---- $pass passed, $fail failed"
[ "$fail" -eq 0 ]
