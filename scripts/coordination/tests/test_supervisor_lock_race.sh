#!/bin/bash
# C43 regression: the supervisor must not lose a race against a DYING supervisor's
# flock release.
#
# MEASURED 2026-08-12 by coordinator-agent: they killed supervisor 489217, verified
# it dead with ps, relaunched immediately, and the new process lost the race against
# the dying holder's release — logged "another supervisor holds the lock", exited 0,
# and died. For ~90 seconds nothing would have relaunched the daemon if it had died.
# That is the exact condition that went unnoticed for ten days from 2026-07-29.
#
# Note the first C43 fix (naming the holder) would NOT have helped: the holder was
# still alive while releasing, so it would have printed "(ALIVE)" and exited 0 —
# accurate, unhelpful, gap still open. Evidence about a race is not a fix for it.
set -euo pipefail
cd "$(dirname "$0")/../../.." || exit 1
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
LOCK="$TMP/sup.lock"
pass=0; fail=0
chk() { if [ "$2" = "$3" ]; then echo "  PASS  $1"; pass=$((pass+1));
        else echo "  FAIL  $1 (got $2, want $3)"; fail=$((fail+1)); fi; }

# A holder that releases after 2s, standing in for a dying supervisor.
( flock 8; sleep 2 ) 8>"$LOCK" &
holder=$!
sleep 0.3

# THE RACE: a bounded wait must win where -n would have lost.
start=$SECONDS
if flock -w 15 -E 99 9 2>/dev/null 9>"$LOCK"; then got=0; else got=$?; fi
waited=$(( SECONDS - start ))
chk "bounded wait ACQUIRES a lock released mid-wait" "$got" 0
[ "$waited" -ge 1 ] && echo "  PASS  it actually waited (${waited}s)" && pass=$((pass+1)) \
  || { echo "  FAIL  did not wait (${waited}s) — the race is not covered"; fail=$((fail+1)); }
wait $holder 2>/dev/null || true

# The non-blocking form is what LOST the race — kept as the contrast that shows the
# test is measuring the right thing.
( flock 8; sleep 2 ) 8>"$LOCK" &
holder2=$!
sleep 0.3
if flock -n -E 99 9 2>/dev/null 9>"$LOCK"; then old=0; else old=$?; fi
chk "the OLD non-blocking form loses that same race" "$old" 99
wait $holder2 2>/dev/null || true

# Wiring: neither entrypoint may go back to the non-blocking form.
SUP=scripts/coordination/bus_supervisor.sh
if grep -qE '^\s*flock -n 9' "$SUP"; then
  echo "  FAIL  a bare 'flock -n 9' is back — that is the losing form"; fail=$((fail+1))
else
  echo "  PASS  no bare non-blocking acquire remains"; pass=$((pass+1))
fi
if [ "$(grep -c 'acquire_supervisor_lock || exit 0' "$SUP")" = "2" ]; then
  echo "  PASS  both entrypoints (once, loop) use the bounded acquire"; pass=$((pass+1))
else
  echo "  FAIL  entrypoints do not both use acquire_supervisor_lock"; fail=$((fail+1))
fi

echo "  ---- $pass passed, $fail failed"
[ "$fail" -eq 0 ]
