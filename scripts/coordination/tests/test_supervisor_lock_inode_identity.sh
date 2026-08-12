#!/bin/bash
# Regression test: the flock singleton is defeated by REPLACING the lock file, and the
# pid file's "unexplained" deletion is a downstream symptom of that, not a separate bug.
#
# WHY THIS EXISTS (C48 follow-up, 2026-08-12). `logs/bus_supervisor.pid` vanished while
# pid 1510370 was alive, holding the lock, and had been supervising for 7h40m. The hunt
# was for an external deleter and none was found: the path was never tracked, so no git
# operation could remove it; `git clean -ffdx` runs in /workspace and cannot reach
# /tmp; the three supervisor tests are isolated; and tmpfiles ages /tmp at 10d.
#
# THE DELETER IS THE SUPERVISOR'S OWN TRAP (bus_supervisor.sh:373,
# `trap 'rm -f "$SUP_PIDFILE"' TERM INT`), running in a SECOND instance that should
# never have acquired the lock. The chain:
#
#   1. something removes $LOCK_FILE while instance A holds it (any `rm`, a container
#      /tmp reset, a stray cleanup — the mechanism does not care which);
#   2. instance B runs `exec 9>"$LOCK_FILE"`, which CREATES A NEW INODE, and its
#      flock succeeds — C43's bounded acquire cannot refuse it, because the kernel is
#      being asked about an unrelated file;
#   3. B writes `echo $$ > "$SUP_PIDFILE"`, clobbering A's pid;
#   4. B is TERM'd; its trap `rm -f`s the pid file outright;
#   5. A is still alive, still holding the (now unlinked) lock, with NO pid file —
#      exactly the C48 symptom, and no external deleter to find.
#
# So the pid deletion is legitimate behaviour by a process that should not exist. That
# is why "probably the clean run" never fit: it is looking for a deleter one layer
# below the defect.
#
# THE PROPERTY UNDER TEST: flock identity is per-INODE, not per-PATH. Two holders of
# the same path are possible the instant the path is re-created.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../../.." || exit 1
pass=0; fail=0
chk() { if [ "$2" = "$3" ]; then echo "  PASS  $1"; pass=$((pass+1));
        else echo "  FAIL  $1 (got '$2' want '$3')"; fail=$((fail+1)); fi; }

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
L="$TMP/sup.lock"

( exec 9>"$L"; flock -n 9 || exit 1; sleep 5 ) & A=$!
sleep 0.5

( exec 9>"$L"; flock -n 9 ) 2>/dev/null && before=acquired || before=refused
chk "a second acquire on the SAME inode is refused" "$before" refused

rm -f "$L"     # the upstream defect, reproduced
( exec 9>"$L"; flock -n 9 ) 2>/dev/null && after=acquired || after=refused
chk "after the lock file is REPLACED, a second acquire SUCCEEDS (the hazard)" "$after" acquired

kill "$A" 2>/dev/null; wait "$A" 2>/dev/null

# Wiring: the pid write and its deleting trap must stay adjacent in the loop branch,
# so anyone reading one sees the other. If these drift apart, the chain above becomes
# invisible to a reader auditing either half alone.
SUP=scripts/coordination/bus_supervisor.sh
w=$(grep -n 'echo \$\$ > "\$SUP_PIDFILE"' "$SUP" | cut -d: -f1)
t=$(grep -n "trap 'rm -f \"\$SUP_PIDFILE\"" "$SUP" | cut -d: -f1)
if [ -n "$w" ] && [ -n "$t" ] && [ $((t - w)) -le 2 ]; then
  echo "  PASS  pid write and its deleting trap are still adjacent (:$w, :$t)"; pass=$((pass+1))
else
  echo "  FAIL  pid write / trap drifted apart (write=:$w trap=:$t)"; fail=$((fail+1))
fi

echo "  ---- $pass passed, $fail failed"
[ "$fail" -eq 0 ]
