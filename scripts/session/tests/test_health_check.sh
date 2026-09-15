#!/bin/bash
# Mutation test for the OBS-6 UNKNOWN-verdict fix in scripts/session/health_check.sh.
#
# THE DEFECT (2026-09-15): several probes did `cat /sys/... 2>/dev/null || echo
# "unknown"` and then COMPARED "unknown" against the expected value, reporting
# FAIL — an unreadable /sys node in a container scored identically to a real
# misconfiguration. Separately, `pgrep -f "claude"` is a bare substring matching
# this very check's own caller, and `pgrep -f "monitor_storage"` reads a
# renamed/relocated monitor as permanently absent; neither process publishes a
# pid file this script could check instead, so both became UNKNOWN rather than
# a guessed PASS/WARN.
#
# This test sources health_check.sh (safe: every side effect lives inside
# `main`, gated by the BASH_SOURCE guard at the bottom of that file — sourcing
# only defines check/sysfs_value/sysfs_bracketed/check_sysfs_eq) and drives the
# sysfs helpers directly against real-but-unreadable and missing paths, rather
# than executing the whole health check (which this task's constraints say to
# read fully and run only if provably read-only — exercised separately, once,
# for a live sanity check; the UNKNOWN path itself is tested here at the
# function level so it does not depend on this sandbox's actual /sys contents).
set -uo pipefail

SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/health_check.sh"
TMP=$(mktemp -d /workspace/tmp/sub-obs/hc_test.XXXXXX 2>/dev/null || mktemp -d)
trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0
chk() { if [ "$2" = "$3" ]; then echo "  PASS  $1"; pass=$((pass+1));
        else echo "  FAIL  $1 (got '$2', want '$3')"; fail=$((fail+1)); fi; }

# source_and_eval <shell to eval> — a clean bash that sources health_check.sh
# (`main` never runs under `source`: BASH_SOURCE[0] there is the script path
# while $0 stays "bash") and then evaluates the probe under test.
source_and_eval() {
  bash -c "source '$SCRIPT'; $1" 2>&1
}

echo "== sysfs_value: a genuinely missing node is __UNREADABLE__, not a guessed string =="
out="$(source_and_eval 'sysfs_value "'"$TMP"'/does-not-exist"')"
chk "sysfs_value on a missing path" "$out" "__UNREADABLE__"

echo
echo "== sysfs_value: a node that exists but is unreadable (chmod 000) =="
NODE="$TMP/unreadable_node"
echo "performance" > "$NODE"
chmod 000 "$NODE"
if [ "$(id -u)" = "0" ]; then
  echo "  SKIP  running as root — chmod 000 does not block root reads, case untestable here"
else
  out="$(source_and_eval 'sysfs_value "'"$NODE"'"')"
  chk "sysfs_value on a chmod-000 node" "$out" "__UNREADABLE__"
fi
chmod 644 "$NODE"

echo
echo "== sysfs_bracketed: unreadable node propagates the sentinel, not a parsed 'unknown' =="
BNODE="$TMP/unreadable_bracket"
echo "always [madvise] never" > "$BNODE"
chmod 000 "$BNODE"
if [ "$(id -u)" = "0" ]; then
  echo "  SKIP  running as root"
else
  out="$(source_and_eval 'sysfs_bracketed "'"$BNODE"'"')"
  chk "sysfs_bracketed on a chmod-000 node" "$out" "__UNREADABLE__"
fi
chmod 644 "$BNODE"

echo
echo "== sysfs_bracketed: a readable node still parses the [selected] token =="
GOOD="$TMP/good_bracket"
echo "always [madvise] never" > "$GOOD"
out="$(source_and_eval 'sysfs_bracketed "'"$GOOD"'"')"
chk "sysfs_bracketed on a readable node" "$out" "madvise"

echo
echo "== check_sysfs_eq: UNREADABLE is UNKNOWN — never PASS, never FAIL =="
out="$(source_and_eval '
  PASS=0; FAIL=0; UNKNOWN=0
  check_sysfs_eq "governor" "__UNREADABLE__" "performance" "Currently: __UNREADABLE__"
  printf "PASS=%s FAIL=%s UNKNOWN=%s\n" "$PASS" "$FAIL" "$UNKNOWN"
')"
chk "unreadable value -> UNKNOWN=1, PASS=0, FAIL=0" "$(echo "$out" | tail -1)" "PASS=0 FAIL=0 UNKNOWN=1"
case "$out" in
  *"❓ UNKNOWN"*) echo "  PASS  the UNKNOWN glyph/label is printed"; pass=$((pass+1));;
  *) echo "  FAIL  no UNKNOWN label in output: $out"; fail=$((fail+1));;
esac
case "$out" in
  *"❌ FAIL"*) echo "  FAIL  an unreadable node was ALSO reported as FAIL"; fail=$((fail+1));;
  *) echo "  PASS  an unreadable node is never reported as FAIL"; pass=$((pass+1));;
esac

echo
echo "== check_sysfs_eq: a readable, correct value still PASSes =="
out="$(source_and_eval '
  PASS=0; FAIL=0; UNKNOWN=0
  check_sysfs_eq "governor" "performance" "performance" "Currently: performance"
  printf "PASS=%s FAIL=%s UNKNOWN=%s\n" "$PASS" "$FAIL" "$UNKNOWN"
')"
chk "readable + matching value -> PASS=1" "$(echo "$out" | tail -1)" "PASS=1 FAIL=0 UNKNOWN=0"

echo
echo "== check_sysfs_eq: a readable, WRONG value still FAILs (the fix must not soften real drift) =="
out="$(source_and_eval '
  PASS=0; FAIL=0; UNKNOWN=0
  check_sysfs_eq "governor" "powersave" "performance" "Currently: powersave"
  printf "PASS=%s FAIL=%s UNKNOWN=%s\n" "$PASS" "$FAIL" "$UNKNOWN"
')"
chk "readable + wrong value -> FAIL=1" "$(echo "$out" | tail -1)" "PASS=0 FAIL=1 UNKNOWN=0"

echo
echo "== the pgrep-by-name process checks are gone; UNKNOWN is reported instead =="
# Matched against actual INVOCATION shape (>/dev/null immediately after), not
# prose that quotes the old pattern to explain the fix — the header comment and
# the UNKNOWN messages both quote it deliberately, and a bare string match would
# make this assertion fail on its own explanation.
if grep -qE 'pgrep -f "claude" *>/dev/null' "$SCRIPT"; then
  echo "  FAIL  script still EXECUTES the self-matching 'pgrep -f \"claude\"' probe"; fail=$((fail+1))
else
  echo "  PASS  the self-matching claude pgrep probe is no longer executed"; pass=$((pass+1))
fi
if grep -qE 'pgrep -f "monitor_storage" *>/dev/null' "$SCRIPT"; then
  echo "  FAIL  script still EXECUTES the renamed-binary-blind monitor_storage pgrep probe"; fail=$((fail+1))
else
  echo "  PASS  the monitor_storage pgrep probe is no longer executed"; pass=$((pass+1))
fi
if grep -qE '❓ UNKNOWN.*Claude sessions' "$SCRIPT" && grep -qE '❓ UNKNOWN.*[Ss]torage monitor' "$SCRIPT"; then
  echo "  PASS  both process checks now report UNKNOWN with their reasons"; pass=$((pass+1))
else
  echo "  FAIL  expected UNKNOWN reporting text for both process checks not found"; fail=$((fail+1))
fi

echo
echo "== Tooling Interpreters section (OBS-11) is untouched =="
if grep -q "6b. TOOLING INTERPRETERS" "$SCRIPT" && grep -q "uv python install" "$SCRIPT"; then
  echo "  PASS  the OBS-11 section is intact"; pass=$((pass+1))
else
  echo "  FAIL  the OBS-11 Tooling Interpreters section appears to have been altered/removed"; fail=$((fail+1))
fi

echo
echo "  ---- $pass passed, $fail failed"
[ "$fail" -eq 0 ]
