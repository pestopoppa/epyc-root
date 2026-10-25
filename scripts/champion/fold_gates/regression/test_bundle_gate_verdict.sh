#!/bin/bash
# Synthetic, model-free regression. Run only under an owner-approved compute grant.
set -uo pipefail
SCRIPT_PATH=$(cd -- "$(dirname -- "$0")" && pwd)/$(basename -- "$0")
SCRIPT_DIR=$(cd -- "$(dirname -- "$0")/.." && pwd)
TMP=${TMPDIR:-/mnt/raid0/llm/tmp}/bundle-gate-verdict.$$
mkdir -p "$TMP"
trap 'rm -rf "$TMP"' EXIT

sed -n '/^# BEGIN BUNDLE GATE VERDICT$/,/^# END BUNDLE GATE VERDICT$/p' \
  "$SCRIPT_DIR/bundle_gate_c3.sh" | sed '1d;$d' > "$TMP/helpers.sh"
sed -n '/^# BEGIN BUNDLE GATE VERDICT$/,/^# END BUNDLE GATE VERDICT$/p' \
  "$SCRIPT_DIR/bundle_gate_c4.sh" | sed '1d;$d' > "$TMP/helpers-c4.sh"
diff -u "$TMP/helpers.sh" "$TMP/helpers-c4.sh" || {
  echo 'FAIL: C3 and C4 bundle verdict helpers differ' >&2
  exit 1
}
source "$TMP/helpers.sh"

curl() { echo 'stub curl failure: no request sent' >&2; return 22; }
schema='"schema":"epyc.gpu_champion_ab.result.v1","kind":"mtp"'
fake_ab_ok() {
  printf '{%s,"verdict":{"PASS":true}}\n' "$schema" > "$TMP/result.json"
  echo 'RESULT mtp: PASS=True'
  return 0
}
fake_ab_nonok() {
  printf '{%s,"verdict":{"PASS":false},"other":{"PASS":true}}\n' "$schema" > "$TMP/result.json"
  echo 'RESULT mtp: PASS=False FAILED=identity_C_equals_P'
  return 0
}
fake_ab_malformed() {
  printf '{%s,"verdict":{"PASS":true}\n' "$schema" > "$TMP/result.json"
  echo 'synthetic malformed result'
  return 0
}
fake_ab_duplicate_key() {
  printf '{%s,"verdict":{"PASS":false,"PASS":true}}\n' "$schema" > "$TMP/result.json"
  echo 'synthetic duplicate PASS key'
  return 0
}
fake_ab_missing() {
  echo 'child rc=0 but no result file'
  return 0
}
fake_ab_child_error() {
  printf '{%s,"verdict":{"PASS":true}}\n' "$schema" > "$TMP/result.json"
  echo 'synthetic child error'
  return 7
}
fake_ab_curl_failure() {
  curl --fail http://127.0.0.1:1
}
fake_greedy_ok() {
  printf '{"results":[{"arm":"CHAMP","completed":true,"confirmed_dead":true},{"arm":"C","completed":true,"confirmed_dead":true}],"verdict_vs_CHAMP":{"C":{"p1":"IDENTICAL","p2":"IDENTICAL","p3":"IDENTICAL"}}}\n' > "$TMP/result.json"
  echo 'C vs CHAMP: p1 IDENTICAL p2 IDENTICAL p3 IDENTICAL'
  return 0
}
fake_greedy_nonok() {
  printf '{"results":[{"arm":"CHAMP","completed":true,"confirmed_dead":true},{"arm":"C","completed":true,"confirmed_dead":true}],"verdict_vs_CHAMP":{"C":{"p1":"IDENTICAL","p2":"DIVERGES at token 2","p3":"IDENTICAL"}},"other":{"p1":"IDENTICAL"}}\n' > "$TMP/result.json"
  echo 'C vs CHAMP: p1 IDENTICAL p2 DIVERGES at token 2 p3 IDENTICAL'
  return 0
}
run_case() {
  local expected=$1 mode=$2; shift 2
  rm -f "$TMP/result.json"
  "$@" 2>&1 | tee "$TMP/child.log" | grep -E 'RESULT|IDENTICAL|DIVERGES|failure|error|malformed|duplicate|no result'
  local child_rc=${PIPESTATUS[0]} actual
  bundle_gate_verdict_rc "$child_rc" "$TMP/result.json" "$mode"; actual=$?
  [ "$actual" -eq "$expected" ] || {
    echo "FAIL: $* mode=$mode child_rc=$child_rc verdict_rc=$actual expected=$expected" >&2
    return 1
  }
  echo "PASS: $* mode=$mode child_rc=$child_rc verdict_rc=$actual"
}

if [ "${INJECT_ASSERT_FAILURE:-0}" = 1 ]; then
  run_case 0 mtp fake_ab_nonok || exit 1
  echo 'FAIL: planted assertion did not fail' >&2
  exit 1
fi

run_case 0 mtp fake_ab_ok || exit 1
run_case 1 mtp fake_ab_nonok || exit 1
run_case 1 mtp fake_ab_malformed || exit 1
run_case 1 mtp fake_ab_duplicate_key || exit 1
run_case 1 mtp fake_ab_missing || exit 1
run_case 7 mtp fake_ab_child_error || exit 1
run_case 22 mtp fake_ab_curl_failure || exit 1
run_case 0 greedy fake_greedy_ok || exit 1
run_case 1 greedy fake_greedy_nonok || exit 1

if INJECT_ASSERT_FAILURE=1 bash "$SCRIPT_PATH" > "$TMP/injected-assertion.log" 2>&1; then
  echo 'FAIL: regression harness exited zero for a planted failed assertion' >&2
  exit 1
fi
grep -q 'FAIL: fake_ab_nonok mode=mtp child_rc=0 verdict_rc=1 expected=0' "$TMP/injected-assertion.log" || {
  echo 'FAIL: injected harness exit was not caused by the planted assertion' >&2
  exit 1
}
echo 'PASS: aggregate harness fails on an injected assertion; stub curl made no network request'
