#!/bin/bash
set -uo pipefail
#
# Tests for scripts/hooks/pre_push_serialization_guard.sh
#
# Run:  bash scripts/hooks/tests/test_pre_push_serialization_guard.sh
# Exit: 0 iff every assertion passed AND at least one assertion ran.
#
# ─── HOW THESE TESTS ARE CONSTRUCTED ─────────────────────────────────────────
#
# Nothing here is mocked. Each case builds a throwaway repo under $TMPDIR with a
# real `git init --bare` acting as origin, real commits, and a real `git push`
# that git itself feeds to the guard via core.hooksPath. That matters twice
# over: the stdin format is produced by git rather than by this test's idea of
# it, and the ALLOW cases are checked by looking at what actually landed in
# origin — not merely at an exit code. A guard that exits 0 without publishing,
# or exits 1 after publishing, fails here.
#
# core.hooksPath is passed with `git -c`, per invocation. No .git/hooks anywhere
# is written, no git config file is modified, and no real remote is contacted:
# origin is a bare repo in the same throwaway directory, removed at the end.
#
# ─── HOW THESE TESTS AVOID BEING VACUOUS ─────────────────────────────────────
#
# The defect class this guard exists to fix also afflicts test files, so:
#   * every assertion runs at top level, in a `for` over the case list — there
#     is no function that nobody calls;
#   * every failure increments FAILURES, and the script exits non-zero when
#     FAILURES > 0, so a failure cannot be swallowed by a later passing command;
#   * the script exits non-zero if ZERO assertions ran, so "counted nothing" can
#     never look like "counted all passes";
#   * both directions are covered for every property. A guard that refuses
#     everything fails the ALLOW cases; a guard that allows everything fails the
#     REFUSE cases;
#   * refusals assert on the SPECIFIC cause text, so a guard that refuses for
#     the wrong reason (e.g. "no session identity" where "schema unreadable" was
#     the property under test) is not credited;
#   * ALLOW cases assert on origin's refs, so "exit 0" alone never passes.
#
# EPYC_PUSH_GUARD_UNDER_TEST points the suite at a copy of the guard. It exists
# for mutation testing: break a property in a copy, confirm the corresponding
# case FAILS and that the failure reaches the exit code, restore, confirm pass.

GUARD="${EPYC_PUSH_GUARD_UNDER_TEST:-/workspace/scripts/hooks/pre_push_serialization_guard.sh}"

if [[ ! -r "$GUARD" ]]; then
  printf 'FATAL: guard under test not readable: %s\n' "$GUARD" >&2
  exit 2
fi

PASSES=0
FAILURES=0
pass() { PASSES=$((PASSES + 1)); printf '  ok   %s\n' "$1"; }
fail() {
  FAILURES=$((FAILURES + 1))
  printf '  FAIL %s\n         %s\n' "$1" "$2" >&2
  if [[ -s "${ERRFILE:-/dev/null}" ]]; then
    printf '         --- guard stderr ---\n' >&2
    sed 's/^/         | /' "$ERRFILE" >&2 | head -40
  fi
}

SANDBOX=""
cleanup() { [[ -n "$SANDBOX" && -d "$SANDBOX" ]] && rm -rf "$SANDBOX"; }
trap cleanup EXIT

# ── sandbox ──────────────────────────────────────────────────────────────────

new_sandbox() {
  cleanup
  SANDBOX="$(mktemp -d)"
  ERRFILE="$SANDBOX/err"
  mkdir -p "$SANDBOX/hooks" "$SANDBOX/locks"
  printf '#!/bin/bash\nexec %q "$@"\n' "$GUARD" > "$SANDBOX/hooks/pre-push"
  chmod +x "$SANDBOX/hooks/pre-push"
  git init -q --bare "$SANDBOX/origin.git"
  git init -q -b main "$SANDBOX/work"
  (
    cd "$SANDBOX/work" || exit 1
    git config user.email guard-test@example.invalid
    git config user.name  guard-test
    git remote add origin "$SANDBOX/origin.git"
    printf 'base\n' > file.txt
    git add file.txt
    git commit -qm "base commit"
  ) >/dev/null 2>&1
  LOCKFILE="$(lock_path_for "$SANDBOX/work")"
}

# The lock file the guard must consult, computed INDEPENDENTLY of the guard
# (python's os.stat, not the guard's `stat -c`), from the same rule the writer
# scripts/coordination/serialized_push.py uses: push-<st_dev>-<st_ino>.json of
# the git COMMON dir. If the guard's derivation ever drifts from the writer's,
# the compliant-path cases below stop finding their lock and fail — which is the
# point: agreeing on the path is part of the contract, not an implementation
# detail.
lock_path_for() {
  python3 - "$1" "$SANDBOX/locks" <<'PYEOF'
import os, subprocess, sys
common = subprocess.run(
    ["git", "-C", sys.argv[1], "rev-parse", "--path-format=absolute", "--git-common-dir"],
    capture_output=True, text=True).stdout.strip()
st = os.stat(common)
print(os.path.join(sys.argv[2], "push-%d-%d.json" % (st.st_dev, st.st_ino)))
PYEOF
}

commit_more() {
  (
    cd "$SANDBOX/work" || exit 1
    printf '%s\n' "$1" >> file.txt
    git add file.txt
    git commit -qm "$1"
  ) >/dev/null 2>&1
}

# run_push <env assignments as one string> <push args...>
# Executes a REAL git push through the guard. Sets RC.
run_push() {
  local envs="$1"; shift
  local quoted="" a
  for a in "$@"; do quoted+=" $(printf '%q' "$a")"; done
  ( cd "$SANDBOX/work" \
      && eval "env $envs git -c core.hooksPath=$(printf '%q' "$SANDBOX/hooks") push$quoted" \
  ) >"$SANDBOX/out" 2>"$ERRFILE"
  RC=$?
}

# run_direct <env assignments> <stdin text>
# Invokes the guard exactly as git would (argv + stdin), for ref-update shapes
# that a real push cannot easily be made to produce in one go. Sets RC.
run_direct() {
  local envs="$1" stdin="$2"
  printf '%s' "$stdin" \
    | ( cd "$SANDBOX/work" && eval "env $envs bash \"$GUARD\" origin \"$SANDBOX/origin.git\"" ) \
      >"$SANDBOX/out" 2>"$ERRFILE"
  RC=$?
}

origin_has() { git --git-dir="$SANDBOX/origin.git" rev-parse --verify --quiet "$1" >/dev/null 2>&1; }
origin_sha() { git --git-dir="$SANDBOX/origin.git" rev-parse --verify --quiet "$1" 2>/dev/null; }
work_sha()   { git -C "$SANDBOX/work" rev-parse --verify --quiet "$1" 2>/dev/null; }
err_has()    { grep -qF -- "$1" "$ERRFILE"; }

# refused_with <specific cause substring>
#
# A refusal must be the GUARD's refusal, not merely a non-zero exit: a guard
# that crashed (unbound variable, syntax error, missing python3) also exits
# non-zero and would otherwise be credited as "correctly refused". So this
# requires the guard's own banner AND the specific cause.
#
# It also requires the cause substring to be one the guard PRINTS. An earlier
# version of this suite asserted only err_has "malformed"; during mutation
# testing the mutant copy happened to be named ...-malformed-....sh, bash's
# crash message quoted that path, and the assertion passed on the mutant's own
# FILENAME. That is the exact "assertion pins a spelling / matches for the
# wrong reason" defect this suite exists to avoid, so causes are matched as
# whole phrases from the guard's text.
refused_with() {
  [[ "$RC" -ne 0 ]]      || return 1
  err_has "PUSH REFUSED" || return 1
  grep -qF -- "$1" "$ERRFILE"
}

BASE_ENV_NOLOCK="AGENT_ID=mainA EPYC_PUSH_LOCK_DIR=$PWD"   # replaced per-case

printf '\n== pre-push serialization guard ==\n'
printf 'guard under test: %s\n\n' "$GUARD"

# ─────────────────────────────────────────────────────────────────────────────
# CASE 1 — lock ABSENT → push to main REFUSED, nothing published, message names
#          the lock file.
# ─────────────────────────────────────────────────────────────────────────────
new_sandbox
ENVS="AGENT_ID=mainA EPYC_PUSH_LOCK_DIR=$SANDBOX/locks"
run_push "$ENVS" origin main
if refused_with "serialization lock is NOT HELD"; then
  pass "lock absent: push to main refused with a lock-not-held cause (exit $RC)"
else
  fail "lock absent: push to main" "guard exited 0, crashed, or refused for a different reason"
fi
if err_has "$LOCKFILE"; then
  pass "lock absent: refusal names the lock file it looked for"
else
  fail "lock absent: message" "refusal does not name the lock path $SANDBOX/locks/work.lock"
fi
if err_has "PUSH REFUSED" && ! err_has "unbound variable" && ! err_has "syntax error"; then
  pass "lock absent: the refusal is the guard's own, not an interpreter crash"
else
  fail "lock absent: message" "stderr looks like a crash rather than a deliberate refusal"
fi
if ! origin_has refs/heads/main; then
  pass "lock absent: origin/main was NOT created (refusal actually prevented publication)"
else
  fail "lock absent: origin" "refs/heads/main exists in origin — the push was published despite refusal"
fi

# ─────────────────────────────────────────────────────────────────────────────
# CASE 2 — lock HELD BY THIS SESSION → push ALLOWED and actually lands.
#          This is the compliant path; it must work or the guard is a wall.
# ─────────────────────────────────────────────────────────────────────────────
new_sandbox
printf '{"holder": "mainA", "pid": 4242, "taken_at": "2026-08-12T09:00:00Z"}\n' > "$LOCKFILE"
ENVS="AGENT_ID=mainA EPYC_PUSH_LOCK_DIR=$SANDBOX/locks"
run_push "$ENVS" origin main
if [[ "$RC" -eq 0 ]]; then
  pass "lock held by this session: push allowed (exit 0)"
else
  fail "lock held: compliant push" "guard refused the COMPLIANT path (exit $RC)"
fi
if [[ -n "$(origin_sha refs/heads/main)" && "$(origin_sha refs/heads/main)" == "$(work_sha refs/heads/main)" ]]; then
  pass "lock held: origin/main now matches local main (the push really landed)"
else
  fail "lock held: origin" "origin/main is '$(origin_sha refs/heads/main)', local is '$(work_sha refs/heads/main)'"
fi
if err_has "mainA"; then
  pass "lock held: guard announces the holder it verified"
else
  fail "lock held: message" "guard did not name the verified holder on stderr"
fi

# a second, non-fast-forward-free update under the same held lock still passes
commit_more "second"
run_push "$ENVS" origin main
if [[ "$RC" -eq 0 && "$(origin_sha refs/heads/main)" == "$(work_sha refs/heads/main)" ]]; then
  pass "lock held: a follow-up update to main also lands"
else
  fail "lock held: follow-up push" "exit $RC; origin '$(origin_sha refs/heads/main)' vs local '$(work_sha refs/heads/main)'"
fi

# ─────────────────────────────────────────────────────────────────────────────
# CASE 3 — lock file present but UNPARSEABLE → REFUSED, cause says the schema is
#          unreadable. Fail-closed: an unreadable lock is neither "held" nor
#          "unheld". Three shapes: truncated JSON, JSON without a holder field,
#          and binary.
# ─────────────────────────────────────────────────────────────────────────────
for shape in truncated-json no-holder-key binary; do
  new_sandbox
  case "$shape" in
    truncated-json) printf '{"holder": "mainA", "taken_at":' > "$LOCKFILE" ;;
    no-holder-key)  printf '{"pid": 4242, "taken_at": "2026-08-12T09:00:00Z"}\n' > "$LOCKFILE" ;;
    binary)         printf 'holder\x00\x01\x02\xff\xfe binary junk' > "$LOCKFILE" ;;
  esac
  ENVS="AGENT_ID=mainA EPYC_PUSH_LOCK_DIR=$SANDBOX/locks"
  run_push "$ENVS" origin main
  if [[ "$RC" -ne 0 ]]; then
    pass "unparseable lock ($shape): push refused (exit $RC)"
  else
    fail "unparseable lock ($shape)" "guard exited 0 — an unreadable lock was treated as permission"
  fi
  if refused_with "UNREADABLE SCHEMA"; then
    pass "unparseable lock ($shape): refusal says the schema was unreadable"
  else
    fail "unparseable lock ($shape): message" "no UNREADABLE SCHEMA cause — wrong cause, or a crash"
  fi
  if ! origin_has refs/heads/main; then
    pass "unparseable lock ($shape): nothing published"
  else
    fail "unparseable lock ($shape): origin" "refs/heads/main exists in origin despite refusal"
  fi
done

# ─────────────────────────────────────────────────────────────────────────────
# CASE 4 — BYPASS env var set → ALLOWED, announced on stderr, recorded in a log.
#          No lock file exists in this case, so only the bypass can explain a 0.
# ─────────────────────────────────────────────────────────────────────────────
new_sandbox
REASON="mainA: origin lock daemon down, operator-approved hotfix"
ENVS="AGENT_ID=mainA EPYC_PUSH_LOCK_DIR=$SANDBOX/locks EPYC_PUSH_GUARD_LOG=$SANDBOX/bypass.log EPYC_ALLOW_UNSERIALIZED_PUSH='$REASON'"
run_push "$ENVS" origin main
if [[ "$RC" -eq 0 ]]; then
  pass "bypass set: push allowed with no lock present (exit 0)"
else
  fail "bypass set" "guard refused despite EPYC_ALLOW_UNSERIALIZED_PUSH (exit $RC) — the hatch does not work"
fi
if [[ "$(origin_sha refs/heads/main)" == "$(work_sha refs/heads/main)" ]]; then
  pass "bypass set: the push really landed"
else
  fail "bypass set: origin" "origin/main '$(origin_sha refs/heads/main)' != local '$(work_sha refs/heads/main)'"
fi
if err_has "EPYC_ALLOW_UNSERIALIZED_PUSH" && err_has "BYPASSED"; then
  pass "bypass set: use is announced on stderr, naming the env var"
else
  fail "bypass set: announcement" "stderr does not announce the bypass by name — a silent bypass is not attributable"
fi
if err_has "$REASON"; then
  pass "bypass set: the attributable reason is echoed"
else
  fail "bypass set: reason" "stderr does not echo the supplied reason string"
fi
if [[ -s "$SANDBOX/bypass.log" ]] && grep -qF -- "$REASON" "$SANDBOX/bypass.log"; then
  pass "bypass set: use is recorded in the bypass log"
else
  fail "bypass set: log" "bypass log $SANDBOX/bypass.log missing or lacks the reason"
fi

# CASE 4b — bypass set to a bare boolean → REFUSED (attribution is the point).
new_sandbox
ENVS="AGENT_ID=mainA EPYC_PUSH_LOCK_DIR=$SANDBOX/locks EPYC_ALLOW_UNSERIALIZED_PUSH=1"
run_push "$ENVS" origin main
if refused_with "attributes nothing"; then
  pass "bypass=1: refused because a boolean attributes nothing"
else
  fail "bypass=1" "exit $RC — a bare boolean bypass was accepted, so bypasses need not be attributable"
fi

# ─────────────────────────────────────────────────────────────────────────────
# CASE 5 — NON-MAIN refs. Decision under test: lane/* branches and tags are NOT
#          guarded (single-writer, publishing them exposes no one else's work),
#          while main stays guarded in the same sandbox so this cannot pass by
#          the guard having simply stopped working.
# ─────────────────────────────────────────────────────────────────────────────
new_sandbox
ENVS="AGENT_ID=mainA EPYC_PUSH_LOCK_DIR=$SANDBOX/locks"
( cd "$SANDBOX/work" && git branch lane/mainA && git tag v-test ) >/dev/null 2>&1

run_push "$ENVS" origin lane/mainA
if [[ "$RC" -eq 0 ]] && origin_has refs/heads/lane/mainA; then
  pass "no lock: push of lane/mainA ALLOWED and landed (non-main refs are not guarded)"
else
  fail "no lock: lane branch" "exit $RC, origin has lane/mainA: $(origin_has refs/heads/lane/mainA && echo yes || echo no) — over-blocking"
fi

run_push "$ENVS" origin v-test
if [[ "$RC" -eq 0 ]] && origin_has refs/tags/v-test; then
  pass "no lock: tag push ALLOWED and landed"
else
  fail "no lock: tag" "exit $RC — tag pushes are over-blocked"
fi

run_push "$ENVS" origin ":refs/heads/lane/mainA"
if [[ "$RC" -eq 0 ]] && ! origin_has refs/heads/lane/mainA; then
  pass "no lock: DELETION of a non-main ref ALLOWED and applied"
else
  fail "no lock: lane deletion" "exit $RC, lane/mainA still on origin: $(origin_has refs/heads/lane/mainA && echo yes || echo no)"
fi

run_push "$ENVS" origin main
if refused_with "serialization lock is NOT HELD" && ! origin_has refs/heads/main; then
  pass "no lock: main is STILL refused in the same sandbox (the guard did not just stop working)"
else
  fail "no lock: main control" "exit $RC — main was allowed in the sandbox where lanes were allowed"
fi

# main under an alias: remote ref is what counts, local ref is not
run_push "$ENVS" origin "HEAD:refs/heads/main"
if refused_with "serialization lock is NOT HELD"; then
  pass "no lock: HEAD:refs/heads/main refused (guard keys on the REMOTE ref, not the local one)"
else
  fail "no lock: HEAD:main" "exit 0 — pushing to main under an alias evaded the guard"
fi

# lane branch pushed INTO main is a trunk publish and must be refused
run_push "$ENVS" origin "lane/mainA:refs/heads/main" 2>/dev/null
if refused_with "serialization lock is NOT HELD"; then
  pass "no lock: lane/mainA:main refused (a trunk publish under any local name)"
else
  fail "no lock: lane:main" "exit 0 — publishing to main from a lane ref evaded the guard"
fi

# ─────────────────────────────────────────────────────────────────────────────
# CASE 6 — DELETION OF MAIN with no lock → REFUSED. Deleting the shared trunk on
#          origin is worse than an unserialized append, not exempt from it.
# ─────────────────────────────────────────────────────────────────────────────
new_sandbox
printf '{"holder": "mainA"}\n' > "$LOCKFILE"
ENVS="AGENT_ID=mainA EPYC_PUSH_LOCK_DIR=$SANDBOX/locks"
run_push "$ENVS" origin main                                  # publish main legitimately
rm -f "$LOCKFILE"                              # …then drop the lock
run_push "$ENVS" origin ":refs/heads/main"
if refused_with "serialization lock is NOT HELD" && origin_has refs/heads/main; then
  pass "no lock: DELETION of main refused and main survives on origin"
else
  fail "no lock: main deletion" "exit $RC; main on origin: $(origin_has refs/heads/main && echo yes || echo no)"
fi

# ─────────────────────────────────────────────────────────────────────────────
# CASE 7 — MULTI-REF stdin including a delete, in git's REAL wire format.
#          7a drives a real 3-ref push (update main + create lane + delete lane)
#          so the format comes from git, not from this file. 7b feeds the same
#          shape directly to check that the guard picks main out of a mixed set
#          and reports each ref's kind, and 7c checks a mixed set with NO
#          protected ref is allowed — so "refuse anything multi-line" cannot
#          pass.
# ─────────────────────────────────────────────────────────────────────────────
new_sandbox
printf '{"holder": "mainA"}\n' > "$LOCKFILE"
ENVS="AGENT_ID=mainA EPYC_PUSH_LOCK_DIR=$SANDBOX/locks"
( cd "$SANDBOX/work" && git branch lane/a && git branch lane/b ) >/dev/null 2>&1
run_push "$ENVS" origin lane/b
commit_more "third"
rm -f "$LOCKFILE"
run_push "$ENVS" origin main lane/a ":refs/heads/lane/b"
if [[ "$RC" -ne 0 ]]; then
  pass "multi-ref (real push: update+create+delete): refused because main is in the set"
else
  fail "multi-ref real push" "exit 0 — a delete or an extra ref in the set masked the main update"
fi
if origin_has refs/heads/lane/b && ! origin_has refs/heads/lane/a; then
  pass "multi-ref (real push): nothing in the batch was applied (git pushes all-or-nothing per hook refusal)"
else
  fail "multi-ref real push: origin" "lane/b deleted or lane/a created despite refusal"
fi

MAIN_SHA="$(work_sha refs/heads/main)"
LANE_SHA="$(work_sha refs/heads/lane/a)"
ZERO="0000000000000000000000000000000000000000"

# 7b — mixed set containing main, fed directly in git's format
run_direct "$ENVS" "\
(delete) $ZERO refs/heads/lane/b $LANE_SHA
refs/heads/main $MAIN_SHA refs/heads/main $ZERO
refs/heads/lane/a $LANE_SHA refs/heads/lane/a $ZERO
"
if refused_with "refs/heads/main"; then
  pass "multi-ref stdin: 3 lines parsed, main identified as the guarded ref"
else
  fail "multi-ref stdin" "exit $RC — the guarded ref was not picked out of a 3-line update set"
fi
if err_has "delete refs/heads/lane/b" || ! err_has "refs/heads/lane/b"; then
  pass "multi-ref stdin: the all-zero local oid line is classified as a delete, not misparsed"
else
  fail "multi-ref stdin: delete classification" "the (delete) line was not recognised as a deletion"
fi

# 7c — mixed set with a delete and NO protected ref → allowed
run_direct "$ENVS" "\
(delete) $ZERO refs/heads/lane/b $LANE_SHA
refs/heads/lane/a $LANE_SHA refs/heads/lane/a $ZERO
"
if [[ "$RC" -eq 0 ]]; then
  pass "multi-ref stdin: a mixed lane-only set (incl. delete) is allowed without a lock"
else
  fail "multi-ref stdin: lane-only set" "exit $RC — multi-line input is being refused wholesale"
fi

# 7d — deletion of main expressed in wire format
run_direct "$ENVS" "(delete) $ZERO refs/heads/main $MAIN_SHA
"
if refused_with "serialization lock is NOT HELD"; then
  pass "multi-ref stdin: an all-zero-local-oid delete of main is refused"
else
  fail "multi-ref stdin: main delete" "exit 0 — a trunk deletion slipped through as 'no new commits'"
fi

# 7e — EMPTY stdin (git's real behaviour on an up-to-date push) → allowed
run_direct "$ENVS" ""
if [[ "$RC" -eq 0 ]] && err_has "no ref updates"; then
  pass "empty stdin: allowed and explicitly reported as zero ref updates"
else
  fail "empty stdin" "exit $RC — git invokes pre-push with no lines on an up-to-date push; refusing blocks no-ops"
fi

# 7f — malformed stdin line → refused, cause names the malformation
run_direct "$ENVS" "refs/heads/main $MAIN_SHA refs/heads/main
"
if refused_with "malformed ref-update line on stdin"; then
  pass "malformed stdin (3 fields): refused with a malformed-input cause"
else
  fail "malformed stdin" "exit $RC — an unparseable line was not refused with a named cause (a crash does not count)"
fi

# ─────────────────────────────────────────────────────────────────────────────
# CASE 8 — lock held by ANOTHER session → REFUSED, both ids named.
# ─────────────────────────────────────────────────────────────────────────────
new_sandbox
printf '{"holder": "mainB"}\n' > "$LOCKFILE"
ENVS="AGENT_ID=mainA EPYC_PUSH_LOCK_DIR=$SANDBOX/locks"
run_push "$ENVS" origin main
if refused_with "held by ANOTHER session" && err_has "mainB" && err_has "mainA"; then
  pass "lock held by another session: refused, naming holder and this session"
else
  fail "foreign lock holder" "exit $RC — a lock held by mainB let mainA push, or the message named neither"
fi

# ─────────────────────────────────────────────────────────────────────────────
# CASE 9 — no session identity in env → REFUSED, naming the env vars.
# ─────────────────────────────────────────────────────────────────────────────
new_sandbox
printf '{"holder": "mainA"}\n' > "$LOCKFILE"
ENVS="-u AGENT_ID -u EPYC_PUSH_LOCK_HOLDER EPYC_PUSH_LOCK_DIR=$SANDBOX/locks"
run_push "$ENVS" origin main
if refused_with "no session identity" && err_has "AGENT_ID"; then
  pass "no session identity: refused, naming AGENT_ID/EPYC_PUSH_LOCK_HOLDER"
else
  fail "no session identity" "exit $RC — a lock file was accepted without proving it is THIS session's"
fi

# ─────────────────────────────────────────────────────────────────────────────
# CASE 10 — EXPIRED lock (holder matches) → REFUSED. A stale lock guarantees
#           nothing about who is pushing concurrently.
# ─────────────────────────────────────────────────────────────────────────────
new_sandbox
printf '{"holder": "mainA", "expires_at": %s}\n' "$(( $(date -u +%s) - 60 ))" > "$LOCKFILE"
ENVS="AGENT_ID=mainA EPYC_PUSH_LOCK_DIR=$SANDBOX/locks"
run_push "$ENVS" origin main
if refused_with "lock EXPIRED"; then
  pass "expired lock: refused with an expiry cause"
else
  fail "expired lock" "exit $RC — an expired lock was honoured as if live"
fi

new_sandbox
printf '{"holder": "mainA", "expires_at": "%s"}\n' \
  "$(date -u -d '+1 hour' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo 2099-01-01T00:00:00Z)" \
  > "$LOCKFILE"
ENVS="AGENT_ID=mainA EPYC_PUSH_LOCK_DIR=$SANDBOX/locks"
run_push "$ENVS" origin main
if [[ "$RC" -eq 0 ]] && [[ -n "$(origin_sha refs/heads/main)" ]]; then
  pass "unexpired ISO-8601 expiry: allowed (expiry parsing does not fail-closed on a live lock)"
else
  fail "unexpired lock" "exit $RC — a valid future ISO-8601 expiry was misread as expired/unreadable"
fi

# ─────────────────────────────────────────────────────────────────────────────
# CASE 11 — SCHEMA TOLERANCE. The lock writer's format is not settled, so the
#           two other plausible shapes must be understood rather than
#           fail-closed into a permanently blocked repo.
# ─────────────────────────────────────────────────────────────────────────────
new_sandbox
printf 'mainA\n' > "$LOCKFILE"
ENVS="AGENT_ID=mainA EPYC_PUSH_LOCK_DIR=$SANDBOX/locks"
run_push "$ENVS" origin main
if [[ "$RC" -eq 0 ]] && [[ -n "$(origin_sha refs/heads/main)" ]]; then
  pass "bare single-line lock file: understood, push allowed"
else
  fail "bare lock schema" "exit $RC — a plain holder-id lock file was not understood"
fi

new_sandbox
printf '# push lock\nholder=mainA\npid=99\n' > "$LOCKFILE"
ENVS="AGENT_ID=mainA EPYC_PUSH_LOCK_DIR=$SANDBOX/locks"
run_push "$ENVS" origin main
if [[ "$RC" -eq 0 ]] && [[ -n "$(origin_sha refs/heads/main)" ]]; then
  pass "key=value lock file: understood, push allowed"
else
  fail "key=value lock schema" "exit $RC — a holder=<id> lock file was not understood"
fi

# a bare single-line lock naming SOMEONE ELSE must still refuse
new_sandbox
printf 'mainB\n' > "$LOCKFILE"
ENVS="AGENT_ID=mainA EPYC_PUSH_LOCK_DIR=$SANDBOX/locks"
run_push "$ENVS" origin main
if refused_with "held by ANOTHER session"; then
  pass "bare lock file naming another session: still refused (tolerance is not blanket acceptance)"
else
  fail "bare lock, foreign holder" "exit 0 — any parseable lock was treated as this session's"
fi

# ─────────────────────────────────────────────────────────────────────────────
# CASE 12 — EPYC_PUSH_LOCK_FILE override and EPYC_PUSH_PROTECTED_REFS override,
#           both directions.
# ─────────────────────────────────────────────────────────────────────────────
new_sandbox
printf '{"holder": "mainA"}\n' > "$SANDBOX/locks/elsewhere.lock"
ENVS="AGENT_ID=mainA EPYC_PUSH_LOCK_FILE=$SANDBOX/locks/elsewhere.lock"
run_push "$ENVS" origin main
if [[ "$RC" -eq 0 ]]; then
  pass "EPYC_PUSH_LOCK_FILE override: the named lock is the one consulted"
else
  fail "lock file override" "exit $RC — an explicit lock path was ignored"
fi

new_sandbox
ENVS="AGENT_ID=mainA EPYC_PUSH_LOCK_DIR=$SANDBOX/locks EPYC_PUSH_PROTECTED_REFS=lane/mainA"
( cd "$SANDBOX/work" && git branch lane/mainA ) >/dev/null 2>&1
run_push "$ENVS" origin lane/mainA
if refused_with "serialization lock is NOT HELD"; then
  pass "EPYC_PUSH_PROTECTED_REFS override: a short name added to the protected set is guarded"
else
  fail "protected refs override" "exit 0 — the protected-ref override had no effect"
fi
run_push "$ENVS" origin main
if [[ "$RC" -eq 0 ]]; then
  pass "EPYC_PUSH_PROTECTED_REFS override: main is unguarded when the set no longer lists it"
else
  fail "protected refs override (negative)" "exit $RC — the override is additive-only, so it is not really read"
fi

# ─────────────────────────────────────────────────────────────────────────────
# CASE 13 — STRUCTURAL ownership proof. The companion wrapper runs `git push` as
#           a CHILD of the lock-holding process without exporting the holder id,
#           so the guard must also accept "the recorded holder process is an
#           ancestor of this push". This test writes the lock with the pid of
#           THIS test script — a real ancestor of the git process the hook runs
#           under — and unsets every identity env var, so only the structural
#           proof can explain an allow.
# ─────────────────────────────────────────────────────────────────────────────
new_sandbox
printf '{"agent": "someone-else", "pid": %s, "host": "%s"}\n' "$$" "$(hostname)" > "$LOCKFILE"
ENVS="-u AGENT_ID -u EPYC_PUSH_LOCK_HOLDER EPYC_PUSH_LOCK_DIR=$SANDBOX/locks"
run_push "$ENVS" origin main
if [[ "$RC" -eq 0 ]] && [[ -n "$(origin_sha refs/heads/main)" ]]; then
  pass "structural proof: a push descended from the lock-holding process is allowed with no env identity"
else
  fail "structural proof" "exit $RC — the compliant wrapper path (holder pid is an ancestor) was refused"
fi
if err_has "structural"; then
  pass "structural proof: the guard says which proof it accepted"
else
  fail "structural proof: message" "guard did not report the ownership proof it used"
fi

# 13b — a recorded pid that is NOT an ancestor proves nothing
new_sandbox
printf '{"agent": "someone-else", "pid": 999999, "host": "%s"}\n' "$(hostname)" > "$LOCKFILE"
ENVS="-u AGENT_ID -u EPYC_PUSH_LOCK_HOLDER EPYC_PUSH_LOCK_DIR=$SANDBOX/locks"
run_push "$ENVS" origin main
if refused_with "no session identity" && ! origin_has refs/heads/main; then
  pass "structural proof: an unrelated pid in the lock does not grant ownership"
else
  fail "structural proof (negative)" "exit $RC — a lock naming an unrelated pid was accepted"
fi

# 13c — pid 1 must NOT count: in a container init is everyone's ancestor
new_sandbox
printf '{"agent": "someone-else", "pid": 1, "host": "%s"}\n' "$(hostname)" > "$LOCKFILE"
ENVS="-u AGENT_ID -u EPYC_PUSH_LOCK_HOLDER EPYC_PUSH_LOCK_DIR=$SANDBOX/locks"
run_push "$ENVS" origin main
if [[ "$RC" -ne 0 ]] && ! origin_has refs/heads/main; then
  pass "structural proof: pid 1 is rejected (init is an ancestor of every process)"
else
  fail "structural proof (pid 1)" "exit $RC — a lock recording pid 1 would let ANY process push"
fi

# 13d — a lock recorded on a DIFFERENT host cannot be proven structurally here
new_sandbox
printf '{"agent": "someone-else", "pid": %s, "host": "not-this-host.invalid"}\n' "$$" > "$LOCKFILE"
ENVS="-u AGENT_ID -u EPYC_PUSH_LOCK_HOLDER EPYC_PUSH_LOCK_DIR=$SANDBOX/locks"
run_push "$ENVS" origin main
if [[ "$RC" -ne 0 ]]; then
  pass "structural proof: a pid recorded on another host is not matched against local pids"
else
  fail "structural proof (foreign host)" "exit 0 — a remote host's pid was matched against a local one"
fi

# ─────────────────────────────────────────────────────────────────────────────
# CASE 14 — WORKTREES share one lock. Every worktree of a clone pushes the same
#           branch to the same remote, so the lock is keyed on the git COMMON
#           dir. A push from a linked worktree must consult — and be governed by
#           — the very same lock file as the primary tree.
# ─────────────────────────────────────────────────────────────────────────────
new_sandbox
( cd "$SANDBOX/work" && git worktree add -q -b lane/wt "$SANDBOX/wt" ) >/dev/null 2>&1
if [[ -d "$SANDBOX/wt" ]]; then
  WT_LOCK="$(lock_path_for "$SANDBOX/wt")"
  if [[ "$WT_LOCK" == "$LOCKFILE" ]]; then
    pass "worktree: the linked worktree resolves to the same lock file as the primary tree"
  else
    fail "worktree: lock key" "worktree lock '$WT_LOCK' != primary '$LOCKFILE'"
  fi
  ENVS="AGENT_ID=mainA EPYC_PUSH_LOCK_DIR=$SANDBOX/locks"
  ( cd "$SANDBOX/wt" && eval "env $ENVS git -c core.hooksPath=$SANDBOX/hooks push origin main" ) \
    >"$SANDBOX/out" 2>"$ERRFILE"
  RC=$?
  if refused_with "serialization lock is NOT HELD"; then
    pass "worktree: a trunk push from a linked worktree is refused without the shared lock"
  else
    fail "worktree: unlocked push" "exit $RC — the worktree escaped the guard"
  fi
  printf '{"holder": "mainA"}\n' > "$LOCKFILE"
  ( cd "$SANDBOX/wt" && eval "env $ENVS git -c core.hooksPath=$SANDBOX/hooks push origin main" ) \
    >"$SANDBOX/out" 2>"$ERRFILE"
  RC=$?
  if [[ "$RC" -eq 0 ]] && [[ -n "$(origin_sha refs/heads/main)" ]]; then
    pass "worktree: with the shared lock held, the same push is allowed and lands"
  else
    fail "worktree: locked push" "exit $RC — the primary tree's lock did not satisfy the worktree"
  fi
else
  fail "worktree: setup" "git worktree add failed — the worktree property went untested"
fi

# ─────────────────────────────────────────────────────────────────────────────

printf '\n----------------------------------------\n'
printf 'PASS: %d   FAIL: %d   TOTAL: %d\n' "$PASSES" "$FAILURES" "$((PASSES + FAILURES))"

if [[ "$((PASSES + FAILURES))" -eq 0 ]]; then
  printf 'FAILED: zero assertions ran — the suite proved nothing.\n' >&2
  exit 1
fi
if [[ "$FAILURES" -gt 0 ]]; then
  printf 'FAILED: %d assertion(s).\n' "$FAILURES" >&2
  exit 1
fi
printf 'OK: all assertions passed.\n'
exit 0
