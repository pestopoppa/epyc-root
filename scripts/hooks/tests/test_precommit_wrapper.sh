#!/bin/bash
set -uo pipefail
# Asserts that each repo's INSTALLED pre-commit wrapper actually blocks.
#
# WHY THIS EXISTS
# ---------------
# On 2026-08-03, epyc-root's .git/hooks/pre-commit called its two hooks bare:
#
#     "…/pii_precommit.sh" "$@"
#     "…/hermes_drift_precommit.sh" "$@"
#
# A bash script exits with the status of its LAST command, so a failing
# pii_precommit.sh printed every BLOCKED line and was then discarded by a
# passing hermes_drift_precommit.sh. With a real AWS access key staged, the
# wrapper exited 0 and the commit proceeded. Every secret pattern — AWS keys,
# GitHub tokens, Anthropic keys, PEM private keys, JWTs — was advisory-only in
# the governance repo.
#
# Nothing tested the WRAPPER. pii_precommit.sh itself was correct and had its
# own tests; the composition around it was not covered, and the composition was
# the defect.
#
# CORRECTION 2026-08-03: an earlier version of this comment claimed the sibling
# repos "happened to be written correctly (research uses `exec`, orchestrator
# uses `|| exit $?`)". That was true of research and FALSE of orchestrator,
# which called both hooks bare exactly as epyc-root did. Reproduced there in a
# throwaway repo: AWS access key + secret staged, wrapper printed
# "BLOCKED: [secret] AWS secret access key", exited 0, commit landed. Fixed the
# same way (accumulate, exit non-zero if any hook failed). The assumption is
# recorded because it is the interesting part: the test was written believing
# two of three repos were fine, and it was the test — not the belief — that
# found otherwise.
#
# This test drives each installed wrapper end-to-end against a throwaway repo
# with a known-bad blob staged, and asserts a non-zero exit. It also asserts the
# clean case exits zero, so a wrapper cannot pass by simply always failing.
#
# Run: bash scripts/hooks/tests/test_precommit_wrapper.sh

REPOS=(
  "/workspace"
  "/mnt/raid0/llm/epyc-inference-research"
  "/mnt/raid0/llm/epyc-orchestrator"
)

# A syntactically valid AWS access key ID SHAPE. Not a real credential.
#
# Assembled from two literals on purpose: written whole, this line would itself
# match the hook's `AKIA[0-9A-Z]{16}` pattern and block every commit of this
# file. The quotes break the source-level match while bash still concatenates to
# the full shape at run time, which is what the wrapper under test must reject.
# Do NOT "simplify" this to a single literal, and do NOT add a secret-pattern
# exemption for this path — the exemption would be a real weakening; this is not.
BAD_BLOB="AKIA""1234567890ABCDEF"

FAILURES=0
pass() { printf '  ok   %s\n' "$1"; }
fail() { printf '  FAIL %s — %s\n' "$1" "$2"; FAILURES=$((FAILURES + 1)); }

for repo in "${REPOS[@]}"; do
  hook="${repo}/.git/hooks/pre-commit"
  name="$(basename "$repo")"

  if [[ ! -e "$hook" ]]; then
    printf '  skip %s — no pre-commit hook installed\n' "$name"
    continue
  fi
  if [[ ! -x "$hook" ]]; then
    fail "$name" "hook exists but is not executable — git silently skips it"
    continue
  fi

  tmp="$(mktemp -d)"
  (
    cd "$tmp" || exit 1
    git init -q .
    printf '%s\n' "$BAD_BLOB" > staged.txt
    git add staged.txt
  ) >/dev/null 2>&1

  ( cd "$tmp" && bash "$hook" ) >/dev/null 2>&1
  rc=$?
  if [[ "$rc" -ne 0 ]]; then
    pass "$name blocks a staged secret (exit $rc)"
  else
    fail "$name" "staged AWS-key-shaped blob did NOT block (exit 0) — the wrapper is discarding a hook failure"
  fi

  ( cd "$tmp" && printf 'ordinary content\n' > staged.txt && git add staged.txt ) >/dev/null 2>&1
  ( cd "$tmp" && bash "$hook" ) >/dev/null 2>&1
  rc=$?
  if [[ "$rc" -eq 0 ]]; then
    pass "$name allows a clean staged set"
  else
    fail "$name" "clean staged set was rejected (exit $rc) — wrapper fails closed on everything, so the block above proves nothing"
  fi

  rm -rf "$tmp"
done

if [[ "$FAILURES" -gt 0 ]]; then
  printf 'FAILED: %d assertion(s).\n' "$FAILURES" >&2
  exit 1
fi
echo "All assertions passed."
