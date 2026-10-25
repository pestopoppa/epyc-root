#!/bin/bash
# Proposed regression harness. Run only under an owner-approved compute grant.
set -uo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
TMP=${TMPDIR:-/mnt/raid0/llm/tmp}/g1-gate-verdict.$$
mkdir -p "$TMP"
trap 'rm -rf "$TMP"' EXIT
sed -n '/^# BEGIN GATE VERDICT HELPERS$/,/^# END GATE VERDICT HELPERS$/p' \
  "$SCRIPT_DIR/gate_verdict_helpers.sh" | sed '1d;$d' > "$TMP/helpers.sh"
source "$TMP/helpers.sh"

fail=0
sh -c 'exit 134'
rc=$?
old_fail=0
old_verdict=$([ "$rc" -eq 0 ] && echo PASS || { echo FAIL; old_fail=1; })
[ "$old_verdict" = FAIL ] && [ "$old_fail" -eq 0 ] || {
  echo "FAIL: planted old pattern did not reproduce subshell masking"
  exit 1
}
echo "OLD rc=$rc verdict=$old_verdict outer_fail=$old_fail (reproduced masked failure)"

fail=0
sh -c 'exit 134'
rc=$?
gate_set_verdict "$rc"
[ "$GATE_VERDICT" = FAIL ] && [ "$fail" -eq 1 ] || {
  echo "FAIL: rc=134 did not set the gate failure in the parent shell"
  exit 1
}
echo "NEW rc=$rc verdict=$GATE_VERDICT outer_fail=$fail"
gate_set_verdict 0
[ "$GATE_VERDICT" = PASS ] && [ "$fail" -eq 1 ] || {
  echo "FAIL: a later passing test cleared an earlier failure"
  exit 1
}
if [ "$fail" -eq 0 ]; then gate_rc=0; else gate_rc=1; fi
[ "$gate_rc" -eq 1 ] || { echo "FAIL: overall gate rc was not nonzero after rc=134"; exit 1; }
echo "OVERALL gate_rc=$gate_rc after later PASS (prior failure retained)"

fail=0
sh -c 'exit 7'
rc=$?
gate_set_verdict "$rc"
[ "$GATE_VERDICT" = FAIL ] && [ "$fail" -eq 1 ] || {
  echo "FAIL: nonzero child status did not fail the gate"
  exit 1
}

printf 'test A  OK\n\033[1;32mtest B  OK\033[0m\n\033[1;31mtest C  FAIL\033[0m\n' > "$TMP/archs.log"
ok=$(count_ok_lines "$TMP/archs.log")
[ "$ok" = 2 ] || { echo "FAIL: expected two ANSI/plain OK lines, got $ok"; exit 1; }
: > "$TMP/empty.log"
empty_ok=$(count_ok_lines "$TMP/empty.log")
[ "$empty_ok" = 0 ] || { echo "FAIL: expected zero OK lines for empty log, got $empty_ok"; exit 1; }

printf 'knob default  OK\n\033[1;32mknob off-only  OK\033[0m\nknob on-zero  OK\n\033[1;32mknob on-off  OK\033[0m\nknob on-only  OK\nknob broken  FAIL\n\033[1;32mnative rope  OK\033[0m\nyarn-f4-orig32 rope  OK\nfreq-base-1e4 rope  OK\n' > "$TMP/c5.log"
knob_ok=$(count_matching_lines '^knob .*  OK$' "$TMP/c5.log")
rope_ok=$(count_matching_lines '^(native|yarn-f4-orig32|freq-base-1e4) .*  OK$' "$TMP/c5.log")
[ "$knob_ok" = 5 ] && [ "$rope_ok" = 3 ] || {
  echo "FAIL: ANSI/plain C5 counts were knob=$knob_ok rope=$rope_ok; expected 5 and 3"
  exit 1
}
echo "PASS: synthetic child rc 134/7 propagation, retained overall failure, and ANSI/plain/empty OK counts"
