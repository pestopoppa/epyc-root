#!/bin/bash
# Regression test: scripts/nightshift/inference_guard.sh must be THREE-VALUED.
#
# AUD-7 (2026-08-12). The guard failed OPEN. Its whole measurement was one
# pipeline ending in `2>/dev/null ... || true`, so a missing pgrep, argv drift, a
# renamed binary or a /proc read error ALL summed to 0GB and printed "No heavy
# inference detected" — the same output as a genuinely idle host. run_wrapper.sh
# then launched an agent workload on top of a live 200GB inference run.
#
# The defect class is "an ERROR laundered into a plausible 0", so every case below
# is a laundering mutation: break one channel, and assert the guard says FAILED
# rather than producing a confident zero. The honest zero gets its own case,
# because a guard that reports FAILED unconditionally is equally useless.
#
# Nothing here signals a process. The guard's `pgrep` is read-only inspection and
# these cases only ever inspect this test's own shell.
set -uo pipefail
cd "$(dirname "$0")/../../.." || exit 1
GUARD="${INFERENCE_GUARD_SH:-scripts/nightshift/inference_guard.sh}"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0
chk() { if [ "$2" = "$3" ]; then echo "  PASS  $1"; pass=$((pass+1));
        else echo "  FAIL  $1 (got '$2', want '$3')"; fail=$((fail+1)); fi; }

# Run the guard in a clean bash, echo the resulting state. Extra env is passed
# through so each case can break exactly one channel.
guard_state() { env "$@" bash -c "source '$GUARD' >/dev/null 2>&1; echo \"\${NIGHTSHIFT_GUARD_STATE:-UNSET}\""; }
guard_var()   { local v="$1"; shift
  env "$@" bash -c "source '$GUARD' >/dev/null 2>&1; echo \"\${$v:-UNSET}\""; }
guard_out()   { env "$@" bash -c "source '$GUARD' 2>&1"; }

echo "== honest readings =="
# Nothing on this host matches a deliberately impossible pattern: an HONEST zero.
chk "no matching processes -> measured" \
    "$(guard_state NIGHTSHIFT_INFERENCE_PATTERN=zzz-no-such-binary-zzz)" measured
chk "no matching processes -> 0GB, not 'unknown'" \
    "$(guard_var NIGHTSHIFT_INFERENCE_RSS_GB NIGHTSHIFT_INFERENCE_PATTERN=zzz-no-such-binary-zzz)" 0
chk "no matching processes -> inference NOT active" \
    "$(guard_var NIGHTSHIFT_INFERENCE_ACTIVE NIGHTSHIFT_INFERENCE_PATTERN=zzz-no-such-binary-zzz)" 0
# The second channel must be a real number on a healthy host.
memavail="$(guard_var NIGHTSHIFT_MEMAVAIL_GB NIGHTSHIFT_INFERENCE_PATTERN=zzz-no-such-binary-zzz)"
if [[ "$memavail" =~ ^[0-9]+$ ]]; then
  echo "  PASS  MemAvailable channel reports a number (${memavail}GB)"; pass=$((pass+1))
else
  echo "  FAIL  MemAvailable channel reports '$memavail'"; fail=$((fail+1))
fi

echo
echo "== laundering mutations: each MUST report failed, not a confident zero =="
# M-A: pgrep is not installed. The old code hit `command not found`, `|| true`
# swallowed it, and the total was 0.
mkdir -p "$TMP/nopgrep"
for c in bash awk cat env printf sort head tr; do
  [ -x "/usr/bin/$c" ] && ln -sf "/usr/bin/$c" "$TMP/nopgrep/$c"
done
chk "pgrep missing -> failed" \
    "$(guard_state "PATH=$TMP/nopgrep" NIGHTSHIFT_INFERENCE_PATTERN=zzz)" failed
chk "pgrep missing -> RSS is 'unknown', never 0" \
    "$(guard_var NIGHTSHIFT_INFERENCE_RSS_GB "PATH=$TMP/nopgrep" NIGHTSHIFT_INFERENCE_PATTERN=zzz)" unknown
chk "pgrep missing -> INFERENCE_ACTIVE is UNSET, not a confident 0" \
    "$(guard_var NIGHTSHIFT_INFERENCE_ACTIVE "PATH=$TMP/nopgrep" NIGHTSHIFT_INFERENCE_PATTERN=zzz)" UNSET
out="$(guard_out "PATH=$TMP/nopgrep" NIGHTSHIFT_INFERENCE_PATTERN=zzz)"
case "$out" in
  *"MEASUREMENT FAILED"*) echo "  PASS  the failure is printed in those words"; pass=$((pass+1));;
  *) echo "  FAIL  no 'MEASUREMENT FAILED' in the output"; fail=$((fail+1));;
esac
case "$out" in
  *"No heavy inference detected"*|*"All tasks eligible"*)
    echo "  FAIL  a BROKEN guard still printed an all-clear"; fail=$((fail+1));;
  *) echo "  PASS  a broken guard prints no all-clear"; pass=$((pass+1));;
esac

# M-B: pgrep errors (rc >= 2). A malformed regex makes the REAL pgrep exit 2 —
# an actual error path, not a stubbed one. rc 1 (no matches) and rc 2 (could not
# look) are the two the old `|| true` collapsed into one.
chk "pgrep rc>=2 (bad pattern) -> failed" \
    "$(guard_state 'NIGHTSHIFT_INFERENCE_PATTERN=*[')" failed

# M-C: pids are found but no VmRSS read succeeds. Achieved with a pattern that
# matches only KERNEL THREADS, which have a /proc/<pid>/status carrying no VmRSS
# line at all — the "pids > 0, reads = 0" shape, produced by the real kernel.
if pgrep -f 'kthreadd' >/dev/null 2>&1; then
  chk "pids found but zero VmRSS reads -> failed" \
      "$(guard_state NIGHTSHIFT_INFERENCE_PATTERN=kthreadd)" failed
else
  echo "  SKIP  no kthreadd on this host"
fi

echo
echo "== the second channel is argv-independent =="
# A MemAvailable floor above the machine's actual free RAM must mark inference
# active even though the process pattern matches nothing at all. This is the
# renamed-binary case: the process channel is blind and the guard still holds.
big=$(( ${memavail:-0} + 100 ))
chk "MemAvailable below the floor -> active, with NO matching process" \
    "$(guard_var NIGHTSHIFT_INFERENCE_ACTIVE NIGHTSHIFT_INFERENCE_PATTERN=zzz-no-such-binary-zzz \
        "NIGHTSHIFT_MIN_MEMAVAIL_GB=$big")" 1

echo
echo "== the consumer refuses =="
# Verifying THE consumer, not A consumer: run_wrapper.sh must exit non-zero on a
# failed guard, and the check must be upstream of the nightshift invocation.
if grep -q 'NIGHTSHIFT_GUARD_STATE' scripts/nightshift/run_wrapper.sh; then
  echo "  PASS  run_wrapper.sh reads NIGHTSHIFT_GUARD_STATE"; pass=$((pass+1))
else
  echo "  FAIL  run_wrapper.sh does not read NIGHTSHIFT_GUARD_STATE"; fail=$((fail+1))
fi
guard_line=$(grep -n 'NIGHTSHIFT_GUARD_STATE:-failed' scripts/nightshift/run_wrapper.sh | head -1 | cut -d: -f1)
run_line=$(grep -n '"\${NIGHTSHIFT_CMD\[@\]}"' scripts/nightshift/run_wrapper.sh | head -1 | cut -d: -f1)
if [[ -n "$guard_line" && -n "$run_line" && "$guard_line" -lt "$run_line" ]]; then
  echo "  PASS  the refusal ($guard_line) is upstream of the workload launch ($run_line)"; pass=$((pass+1))
else
  echo "  FAIL  refusal/launch ordering unverifiable (guard=$guard_line launch=$run_line)"; fail=$((fail+1))
fi
# And the exit status must survive the `{ ... } | tee` pipeline: the braces run in
# a subshell, so an `exit 4` inside them is invisible unless it is captured.
if grep -q 'wrapper_rc' scripts/nightshift/run_wrapper.sh; then
  echo "  PASS  the wrapper propagates its exit status past the tee pipeline"; pass=$((pass+1))
else
  echo "  FAIL  exit status is swallowed by \`| tee\` — a refusal would look like success"
  fail=$((fail+1))
fi

echo "  ---- $pass passed, $fail failed"
[ "$fail" -eq 0 ]
