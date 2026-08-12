#!/bin/bash
# Regression test: hub_supervisor.sh must notice a hub serving OLDER code than
# dashboard/.
#
# WHY (2026-08-11). Ported from the bus supervisor's C42, where the same gap left
# five fixes committed-not-live in one evening. health_ok asks whether :8100
# answers 200; a hub serving twelve-hour-old code answers yes. The owning
# handoff's own row records the consequence: hub_supervisor.sh "was found dead on
# 2026-08-10 ... which is why the hub sat on stale code unnoticed".
#
# SCOPE: the PREDICATE only. It never sources the supervisor (its dispatch would
# run) and never reaches restart_hub. C42's sibling test carries the same
# restriction for the same reason -- on 2026-07-27 a supervisor test that believed
# itself isolated killed the live daemon.
set -euo pipefail   # MATCH PRODUCTION: running without -e is what hid two C42 bugs
cd "$(dirname "$0")/../../.." || exit 1
SUP=scripts/dashboard/hub_supervisor.sh
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/dashboard"
EPYC_ROOT="$TMP"
STALE_SRC_SKEW_S=5

eval "$(sed -n '/^hub_newest_source_mtime()/,/^}/p;/^hub_source_is_newer()/,/^}/p' "$SUP")"

FAKE_PID=""
hub_pids() { printf '%s ' "$FAKE_PID"; }

pass=0; fail=0
chk() { if [ "$2" = "$3" ]; then echo "  PASS  $1"; pass=$((pass+1));
        else echo "  FAIL  $1 (got $2, want $3)"; fail=$((fail+1)); fi; }

rc=0; hub_source_is_newer || rc=$?; chk "no hub pid -> fail closed" "$rc" 2
FAKE_PID=999999999
rc=0; hub_source_is_newer || rc=$?; chk "pid does not exist -> fail closed" "$rc" 2
FAKE_PID=$$
rc=0; hub_source_is_newer || rc=$?; chk "no dashboard sources -> fail closed" "$rc" 2

touch -d '2020-01-01' "$TMP/dashboard/server.py"
rc=0; hub_source_is_newer || rc=$?; chk "source older than hub -> current" "$rc" 1
touch -d '+1 hour' "$TMP/dashboard/server.py"
rc=0; hub_source_is_newer || rc=$?; chk "source newer than hub -> STALE" "$rc" 0

echo "  ---- $pass passed, $fail failed"
[ "$fail" -eq 0 ]
