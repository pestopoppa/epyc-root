#!/bin/bash
# C48 (mainD, 2026-08-12): supervisor liveness must derive from the FLOCK, not the
# pid file. The measured incident: pid 1510370 alive, holding the lock, supervising
# for 7h40m, and `status` said "not running" because $SUP_PIDFILE had vanished.
set -uo pipefail
SUP="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/bus_supervisor.sh"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"; [[ -n "${HOLDER:-}" ]] && kill "$HOLDER" 2>/dev/null; true' EXIT
export LOCK_FILE="$TMP/sup.lock" LOG_DIR="$TMP"
pass=0; fail=0
ok(){ if [[ "$2" == "$3" ]]; then echo "  PASS $1"; pass=$((pass+1)); else echo "  FAIL $1: expected [$3] got [$2]"; fail=$((fail+1)); fi; }
has(){ if [[ "$2" == *"$3"* ]]; then echo "  PASS $1"; pass=$((pass+1)); else echo "  FAIL $1: [$2] lacks [$3]"; fail=$((fail+1)); fi; }

source_fns() { source <(sed -n '/^lock_is_held()/,/^supervisor_status_line() {/p;/^supervisor_status_line() {/,/^}/p' "$SUP"); }

# 1. No holder, no pidfile -> not running
out=$(bash -c 'LOCK_FILE="'"$LOCK_FILE"'" SUP_PIDFILE="'"$TMP"'/x.pid"; '"$(sed -n '/^lock_is_held()/,/^}/p;/^lock_holder_pid()/,/^}/p;/^supervisor_status_line()/,/^}/p' "$SUP")"'; supervisor_status_line')
ok "free lock, no pidfile -> not running" "$out" "not running"

# 2. Live holder, NO pidfile -> must still report RUNNING and name it (the incident)
flock "$LOCK_FILE" -c 'sleep 20' & HOLDER=$!
sleep 0.4
out=$(bash -c 'LOCK_FILE="'"$LOCK_FILE"'" SUP_PIDFILE="'"$TMP"'/x.pid"; '"$(sed -n '/^lock_is_held()/,/^}/p;/^lock_holder_pid()/,/^}/p;/^supervisor_status_line()/,/^}/p' "$SUP")"'; supervisor_status_line')
has "held lock, pidfile MISSING -> not 'not running'" "$out" "from lock"

# 3. Mutation: the old pid-file-only logic would say 'not running' here
old=$( [[ -f "$TMP/x.pid" ]] && cat "$TMP/x.pid" || echo 'not running' )
ok "old logic on the same state reported" "$old" "not running"

# 4. Disagreement is announced, not silently resolved
echo 999999 > "$TMP/x.pid"
out=$(bash -c 'LOCK_FILE="'"$LOCK_FILE"'" SUP_PIDFILE="'"$TMP"'/x.pid"; '"$(sed -n '/^lock_is_held()/,/^}/p;/^lock_holder_pid()/,/^}/p;/^supervisor_status_line()/,/^}/p' "$SUP")"'; supervisor_status_line')
has "lock vs pidfile disagreement is stated" "$out" "DISAGREEMENT"

# `flock -c 'sleep N'` forks: the CHILD inherits fd and keeps the lock, so killing
# the wrapper is not enough. This cost a false FAIL on first run — the code was
# right and the test method was wrong. Kill both, by pid, and confirm release.
REAL=$(bash -c 'LOCK_FILE="'"$LOCK_FILE"'"; '"$(sed -n '/^lock_holder_pid()/,/^}/p' "$SUP")"'; lock_holder_pid')
kill "$HOLDER" 2>/dev/null; [[ -n "$REAL" ]] && kill "$REAL" 2>/dev/null
wait "$HOLDER" 2>/dev/null; HOLDER=""
for _ in 1 2 3 4 5 6 7 8 9 10; do
  ps -p "${REAL:-0}" >/dev/null 2>&1 || break
  sleep 0.2
done
ps -p "${REAL:-0}" >/dev/null 2>&1 && { echo "  FAIL could not release the lock (holder $REAL alive)"; fail=$((fail+1)); }
# 5. Holder gone but pidfile remains -> stale pidfile called out, lock is truth
out=$(bash -c 'LOCK_FILE="'"$LOCK_FILE"'" SUP_PIDFILE="'"$TMP"'/x.pid"; '"$(sed -n '/^lock_is_held()/,/^}/p;/^lock_holder_pid()/,/^}/p;/^supervisor_status_line()/,/^}/p' "$SUP")"'; supervisor_status_line')
has "dead holder, stale pidfile -> not running + stale called out" "$out" "stale"

echo "  --- $pass passed, $fail failed ---"
[[ "$fail" -eq 0 ]]
