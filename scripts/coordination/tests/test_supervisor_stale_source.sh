#!/bin/bash
# Regression test: bus_supervisor.sh must notice a daemon running a DIFFERENT
# COMMITTED TREE than HEAD — and must not fire on anything else.
#
# WHY THIS EXISTS (2026-08-11). Five fixes sat committed-not-live in one evening —
# C39, C28, C38's tick path, R1 and R2 — because a running daemon keeps executing
# the code it loaded at start and nothing noticed. `health_ok` asks "is a process
# there" and "is its heartbeat fresh"; a daemon running twelve-hour-old code
# answers yes to both.
#
# WHY THE PREDICATE CHANGED (H-4, 2026-08-12). The first version compared the
# NEWEST MTIME under scripts/coordination against the daemon's process start time.
# In a five-writer tree that mtime moves for an editor save, a subagent scratch
# write or a `git checkout` restoring a byte-identical file — none of which change
# what a restarted daemon would execute. It restarted a healthy daemon 14 times in
# 54 minutes, and its one-restart-per-distinct-mtime state file was no bound at all.
# The predicate now compares two INDEPENDENTLY SOURCED values: the tree object the
# daemon captured at its own start (heartbeat `source_tree`) against
# `git rev-parse HEAD:scripts/coordination` now. Comparing HEAD to HEAD would agree
# forever; comparing RUNNING to COMMITTED is the actual question.
#
# SCOPE, and it is not optional. This tests the PREDICATE ONLY. It never sources
# the supervisor (its case block would run) and never reaches stop_wedged or
# start_daemon. A test stub named session_bus_coordinator.py matches the production
# `pgrep -f` pattern, and on 2026-07-27 a test that believed itself isolated killed
# the live daemon that way. The restart branch, the rate limiter and the loop wiring
# are covered by tests/test_bus_supervisor.py, which runs the real script.
set -euo pipefail   # MATCH PRODUCTION: a failing command substitution aborts under -e,
                    # and running without it is what hid the bug this line now catches
cd "$(dirname "$0")/../../.." || exit 1
SUP=scripts/coordination/bus_supervisor.sh
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/hb" "$TMP/notgit"
HEARTBEAT="$TMP/hb/coordinator-daemon.json"

# A REAL git checkout, because `current_source_tree` runs real git. A fake would
# test the test. `scripts/coordination` must exist and be committed for
# `HEAD:scripts/coordination` to resolve at all.
EPYC_ROOT="$TMP/repo"
mkdir -p "$EPYC_ROOT/scripts/coordination"
: > "$EPYC_ROOT/scripts/coordination/session_bus_coordinator.py"
git -C "$EPYC_ROOT" init -q
git -C "$EPYC_ROOT" -c user.email=t@t -c user.name=t add scripts/coordination >/dev/null
git -C "$EPYC_ROOT" -c user.email=t@t -c user.name=t commit -qm init >/dev/null
HEAD_TREE=$(git -C "$EPYC_ROOT" rev-parse HEAD:scripts/coordination)
OTHER_TREE=0000000000000000000000000000000000000000

# Extract just the functions under test. `resolve_daemon` is in the list because
# the predicate must not trust a raw heartbeat pid: a RECYCLED pid belongs to a
# stranger, and a stranger's marker is not evidence about the daemon (C49).
eval "$(sed -n '/^daemon_pid_from_heartbeat()/,/^}/p;/^resolve_daemon()/,/^}/p;/^current_source_tree()/,/^}/p;/^heartbeat_source_tree()/,/^}/p;/^daemon_source_is_stale()/,/^}/p' "$SUP")"

# The globals those functions read, which live outside their bodies. DAEMON_MARKER
# is THIS SCRIPT'S OWN name, so the "daemon" the predicate resolves is this test
# process ($$) and nothing else on the host can satisfy it — the marker is only ever
# matched against the one pid the heartbeat below names, never used to search.
DAEMON_MARKER="$(basename "$0")"
DAEMON_STATE=""; DAEMON_PID=""; DAEMON_WHY=""

pass=0; fail=0
chk() { if [ "$2" = "$3" ]; then echo "  PASS  $1"; pass=$((pass+1));
        else echo "  FAIL  $1 (got $2, want $3)"; fail=$((fail+1)); fi; }

# Every unknown must return 2 = "cannot tell", never 1 = "current" and never
# 0 = "stale". UNKNOWN never restarts, and it never silently passes either.
rc=0; daemon_source_is_stale || rc=$?; chk "no heartbeat -> fail closed" "$rc" 2
echo '{"agent":"coordinator-daemon"}' > "$HEARTBEAT"
rc=0; daemon_source_is_stale || rc=$?; chk "heartbeat carries no pid -> fail closed" "$rc" 2
echo '{"pid":999999999}' > "$HEARTBEAT"
rc=0; daemon_source_is_stale || rc=$?; chk "pid does not exist -> fail closed" "$rc" 2
# C49: a pid that EXISTS but is somebody else must fail closed too. Existence was
# never the question — the same lesson the daemon learned in C37, where a stale
# heartbeat naming pid 1 (/sbin/init) reported a ten-day-dead daemon as alive.
echo '{"pid":1}' > "$HEARTBEAT"
rc=0; daemon_source_is_stale || rc=$?; chk "pid recycled to another process -> fail closed" "$rc" 2

# A daemon that publishes no marker at all (a pre-H-4 binary). Absent is UNKNOWN,
# NOT stale: restarting on a missing key would restart every old daemon forever,
# which is the storm shape wearing different clothes.
echo "{\"pid\":$$}" > "$HEARTBEAT"
rc=0; daemon_source_is_stale || rc=$?; chk "no source_tree key -> fail closed" "$rc" 2
echo "{\"pid\":$$,\"source_tree\":null}" > "$HEARTBEAT"
rc=0; daemon_source_is_stale || rc=$?; chk "source_tree null (daemon could not read git) -> fail closed" "$rc" 2

# ...and the mirror case: a marker we cannot compare against, because HEAD does not
# resolve here. Cannot tell, not stale.
echo "{\"pid\":$$,\"source_tree\":\"$OTHER_TREE\"}" > "$HEARTBEAT"
_saved_root="$EPYC_ROOT"; EPYC_ROOT="$TMP/notgit"
rc=0; daemon_source_is_stale || rc=$?
EPYC_ROOT="$_saved_root"
chk "HEAD tree unreadable (not a checkout) -> fail closed" "$rc" 2

# The two real verdicts.
echo "{\"pid\":$$,\"source_tree\":\"$HEAD_TREE\"}" > "$HEARTBEAT"
rc=0; daemon_source_is_stale || rc=$?; chk "marker equals HEAD tree -> current" "$rc" 1
echo "{\"pid\":$$,\"source_tree\":\"$OTHER_TREE\"}" > "$HEARTBEAT"
rc=0; daemon_source_is_stale || rc=$?; chk "marker differs from HEAD tree -> STALE" "$rc" 0

# AND THE DEFECT THE MTIME VERSION HAD: an uncommitted touch must be INVISIBLE.
# This is the whole point of the change, so it gets its own assertion.
echo "{\"pid\":$$,\"source_tree\":\"$HEAD_TREE\"}" > "$HEARTBEAT"
touch "$EPYC_ROOT/scripts/coordination/session_bus_coordinator.py"
echo "# a five-writer tree edits this constantly" \
  >> "$EPYC_ROOT/scripts/coordination/session_bus_coordinator.py"
rc=0; daemon_source_is_stale || rc=$?
chk "uncommitted edit + touch -> STILL current (the 14-restarts-in-54min defect)" "$rc" 1

# The deleted knobs must stay deleted. Reintroducing either brings the storm back.
echo
echo "  -- the mtime predicate must not come back --"
if grep -qE 'newest_source_mtime|STALE_SRC_SKEW_S=|STALE_SRC_STATE=' "$SUP"; then
  echo "  FAIL  bus_supervisor.sh still defines the mtime predicate or its knobs"; fail=$((fail+1))
else
  echo "  PASS  no newest_source_mtime / STALE_SRC_SKEW_S / STALE_SRC_STATE"; pass=$((pass+1))
fi

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
  echo "  FAIL  check_once no longer calls it — cron \`once\` would stop checking"; fail=$((fail+1))
fi

echo "  ---- $pass passed, $fail failed"
[ "$fail" -eq 0 ]
